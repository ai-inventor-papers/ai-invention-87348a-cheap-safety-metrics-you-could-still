"""THE HARVEST: one model load per checkpoint -> weight pass + activation pass.

Design decision that makes a fifteen-read screen affordable: we store the
VECTORS (all-layer hidden states at two read positions, per item) rather than
pre-reduced scalars.  Every direction can then be re-fitted offline, every null
recomputed and every candidate re-read with NO second GPU pass.  ~85 MB per
checkpoint (60 MB activations + 24 MB weight bases).
"""

from __future__ import annotations

import gc
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

from .common import (
    COMPLIANCE_WORDS,
    HARVEST,
    REFUSAL_WORDS,
    sha256_obj,
    slugify,
    write_json,
)

TOP_K_SV = 16
BOT_K_SV = 16


# ----------------------------------------------------------------------------
# tokenizer / template handling
# ----------------------------------------------------------------------------
@dataclass
class TemplateInfo:
    has_tokenizer_config_template: bool
    has_standalone_jinja: bool
    template_used: str          # "tokenizer_config" | "chat_template.jinja" | "plain"
    template_sha256: str
    vocab_sha256: str
    enable_thinking_supported: bool
    renderer: str               # "chat" | "plain"


def probe_template(tok, model_dir: Path | None) -> TemplateInfo:
    tmpl = getattr(tok, "chat_template", None)
    standalone = False
    if model_dir is not None and model_dir.exists():
        standalone = any(model_dir.rglob("chat_template.jinja"))
    has_cfg = False
    if model_dir is not None and model_dir.exists():
        for p in model_dir.rglob("tokenizer_config.json"):
            try:
                has_cfg = "chat_template" in json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                has_cfg = False
            break
    if tmpl:
        used = "chat_template.jinja" if (standalone and not has_cfg) else "tokenizer_config"
        renderer = "chat"
    else:
        used = "plain"
        renderer = "plain"
    # does the template accept enable_thinking=False?
    thinking_ok = False
    if tmpl:
        try:
            tok.apply_chat_template(
                [{"role": "user", "content": "hi"}],
                add_generation_prompt=True, tokenize=False, enable_thinking=False,
            )
            thinking_ok = True
        except (TypeError, ValueError, Exception):  # noqa: BLE001 - jinja raises broadly
            thinking_ok = False
    vocab = tok.get_vocab()
    vocab_hash = sha256_obj(sorted(vocab.items(), key=lambda kv: kv[1])[:200000])
    return TemplateInfo(
        has_tokenizer_config_template=has_cfg,
        has_standalone_jinja=standalone,
        template_used=used,
        template_sha256=sha256_obj(tmpl or ""),
        vocab_sha256=vocab_hash,
        enable_thinking_supported=thinking_ok,
        renderer=renderer,
    )


def render_prompt(tok, tinfo: TemplateInfo, user_text: str, system: str | None = None) -> str:
    """Chat renderer for instruct/safety/abliterated; PLAIN renderer for base.

    Base models live in a SEPARATE STRATUM -- never mixed into the three-way
    comparison -- precisely because this renderer differs.
    """
    if tinfo.renderer == "plain":
        pre = f"{system}\n\n" if system else ""
        return f"{pre}User: {user_text}\nAssistant:"
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user_text})
    kw: dict[str, Any] = {"add_generation_prompt": True, "tokenize": False}
    if tinfo.enable_thinking_supported:
        kw["enable_thinking"] = False
    return tok.apply_chat_template(msgs, **kw)


def resolve_token_sets(tok) -> dict[str, list[int]]:
    """Refusal / compliance first-token id sets, with leading-space variants.

    ASSERTED non-empty by the caller; a silently empty set turns the logit gap
    into a constant and every across-item read built on it into noise.
    """
    out: dict[str, list[int]] = {}
    for name, words in (("refusal", REFUSAL_WORDS), ("compliance", COMPLIANCE_WORDS)):
        ids: set[int] = set()
        for w in words:
            for variant in (w, " " + w, w.lower(), " " + w.lower()):
                try:
                    enc = tok.encode(variant, add_special_tokens=False)
                except (ValueError, TypeError):
                    continue
                if enc:
                    ids.add(int(enc[0]))
        out[name] = sorted(ids)
    return out


# ----------------------------------------------------------------------------
# P3.A  WEIGHT PASS -- zero prompts, seconds
# ----------------------------------------------------------------------------
def _left_spectrum(w: torch.Tensor, device: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Left singular values + top/bottom-k left singular vectors via eigh of W Wt.

    eigh on the d x d Gram, NOT np.linalg.svd: a full SVD of the rectangular
    matrix is ~50x slower and this runs a few hundred times per checkpoint.
    """
    wf = w.detach().to(device=device, dtype=torch.float32)
    gram = wf @ wf.T                       # (d_out, d_out)
    evals, evecs = torch.linalg.eigh(gram)  # ascending
    sv = torch.sqrt(torch.clamp(evals, min=0.0))
    k_top = min(TOP_K_SV, sv.shape[0])
    k_bot = min(BOT_K_SV, sv.shape[0])
    top_vecs = evecs[:, -k_top:].flip(dims=[1]).T.contiguous()   # (k, d) descending sv
    bot_vecs = evecs[:, :k_bot].T.contiguous()                   # (k, d) ascending sv
    return (
        sv.flip(dims=[0]).cpu().numpy().astype(np.float32),      # descending
        top_vecs.cpu().numpy().astype(np.float32),
        bot_vecs.cpu().numpy().astype(np.float32),
    )


def weight_pass(model, device: str) -> dict[str, np.ndarray]:
    """Per (layer, matrix): full singular spectrum + top-16 / bottom-16 left vectors."""
    layers = _get_layers(model)
    out: dict[str, np.ndarray] = {}
    for mat_name, getter in (
        ("o_proj", lambda lyr: getattr(getattr(lyr, "self_attn", None), "o_proj", None)),
        ("down_proj", lambda lyr: getattr(getattr(lyr, "mlp", None), "down_proj", None)),
    ):
        svs, tops, bots, bf16_bot = [], [], [], []
        for lyr in layers:
            mod = getter(lyr)
            if mod is None or not hasattr(mod, "weight"):
                continue
            sv, tv, bv = _left_spectrum(mod.weight, device)
            svs.append(sv)
            tops.append(tv)
            bots.append(bv)
            # bf16-as-shipped bottom gap: thresholds are set against THIS, not fp32
            wb = mod.weight.detach().to(device=device, dtype=torch.bfloat16).to(torch.float32)
            g = wb @ wb.T
            eb = torch.linalg.eigvalsh(g).clamp(min=0).sqrt().cpu().numpy()
            bf16_bot.append(np.float32(eb[0] / eb[1]) if eb.shape[0] > 1 and eb[1] > 0 else np.float32(np.nan))
        if not svs:
            continue
        out[f"{mat_name}_sv"] = np.stack(svs)
        out[f"{mat_name}_top"] = np.stack(tops)
        out[f"{mat_name}_bot"] = np.stack(bots)
        out[f"{mat_name}_botgap_bf16"] = np.asarray(bf16_bot, dtype=np.float32)
    return out


def _get_layers(model):
    for attr in ("model.layers", "transformer.h", "model.decoder.layers", "gpt_neox.layers"):
        obj = model
        ok = True
        for part in attr.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                ok = False
                break
        if ok:
            return obj
    raise AttributeError("could not locate decoder layer list on this architecture")


# ----------------------------------------------------------------------------
# P3.B  ACTIVATION PASS -- teacher-forced prefill, two read positions
# ----------------------------------------------------------------------------
@torch.no_grad()
def activation_pass(
    model,
    tok,
    tinfo: TemplateInfo,
    prompts: list[str],
    token_sets: dict[str, list[int]],
    device: str,
    batch_size: int = 8,
) -> dict[str, np.ndarray]:
    """Hidden states at (i) LAST PROMPT TOKEN and (ii) FIRST GENERATED TOKEN.

    The first generated token is obtained by a real one-token decode off the
    prefill cache, so for a Qwen3 template rendered with enable_thinking=False
    (which puts the EMPTY think block inside the PROMPT) position (ii) is the
    first real content token, not a think delimiter.
    """
    n = len(prompts)
    hs_last: list[np.ndarray] = []
    hs_first: list[np.ndarray] = []
    logit_feats: list[np.ndarray] = []
    first_tok_ids: list[int] = []

    ref_ids = torch.tensor(token_sets["refusal"], device=device)
    cmp_ids = torch.tensor(token_sets["compliance"], device=device)

    orig_side = tok.padding_side
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    bs = batch_size
    i = 0
    while i < n:
        chunk = prompts[i : i + bs]
        try:
            enc = tok(chunk, return_tensors="pt", padding=True, truncation=True,
                      max_length=1024, add_special_tokens=False).to(device)
            out = model(**enc, output_hidden_states=True, use_cache=True)
            # (i) last prompt token -- left padding makes index -1 the last real token
            h_last = torch.stack([h[:, -1, :] for h in out.hidden_states], dim=1)  # (B,L+1,H)
            logits = out.logits[:, -1, :].float()
            lp = torch.log_softmax(logits, dim=-1)
            gap = torch.logsumexp(lp[:, ref_ids], -1) - torch.logsumexp(lp[:, cmp_ids], -1)
            ref_mass = torch.logsumexp(lp[:, ref_ids], -1).exp()
            ent = -(lp.exp() * lp).sum(-1)
            nxt = logits.argmax(-1)
            top1p = lp.max(-1).values.exp()
            # (ii) first generated token -- one real decode step off the cache
            am = torch.cat([enc["attention_mask"],
                            torch.ones((len(chunk), 1), dtype=enc["attention_mask"].dtype, device=device)], dim=1)
            out2 = model(input_ids=nxt.unsqueeze(1), attention_mask=am,
                         past_key_values=out.past_key_values,
                         output_hidden_states=True, use_cache=False)
            h_first = torch.stack([h[:, -1, :] for h in out2.hidden_states], dim=1)

            hs_last.append(h_last.to(torch.float16).cpu().numpy())
            hs_first.append(h_first.to(torch.float16).cpu().numpy())
            logit_feats.append(torch.stack([gap, ref_mass, ent, top1p], dim=1).cpu().numpy().astype(np.float32))
            first_tok_ids.extend(nxt.cpu().tolist())
            del out, out2, h_last, h_first, enc
            i += bs
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            gc.collect()
            if bs == 1:
                raise
            bs = max(1, bs // 2)
            logger.warning(f"OOM -> halving batch size to {bs}")
    tok.padding_side = orig_side
    return {
        "hs_last": np.concatenate(hs_last, 0),      # (N, L+1, H) float16
        "hs_first": np.concatenate(hs_first, 0),
        "logit_feats": np.concatenate(logit_feats, 0),  # gap, refusal_mass, entropy, top1p
        "first_token_id": np.asarray(first_tok_ids, dtype=np.int64),
    }


# ----------------------------------------------------------------------------
# P3.C  GENERATION -- only where grading needs it
# ----------------------------------------------------------------------------
@torch.no_grad()
def generate_pass(model, tok, prompts: list[str], device: str,
                  max_new_tokens: int = 96, batch_size: int = 24) -> list[str]:
    outs: list[str] = []
    orig_side = tok.padding_side
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    bs = batch_size
    i = 0
    while i < len(prompts):
        chunk = prompts[i : i + bs]
        try:
            enc = tok(chunk, return_tensors="pt", padding=True, truncation=True,
                      max_length=1024, add_special_tokens=False).to(device)
            gen = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
            new = gen[:, enc["input_ids"].shape[1]:]
            outs.extend(tok.batch_decode(new, skip_special_tokens=True))
            del enc, gen, new
            i += bs
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            gc.collect()
            if bs == 1:
                raise
            bs = max(1, bs // 2)
            logger.warning(f"gen OOM -> batch {bs}")
    tok.padding_side = orig_side
    return outs


# ----------------------------------------------------------------------------
# orchestration for ONE checkpoint: load -> harvest -> write -> free
# ----------------------------------------------------------------------------
def harvest_checkpoint(
    repo_id: str,
    *,
    items: list[dict],
    gen_item_idx: list[int],
    probe_prompts: list[str],
    pole_systems: dict[str, str],
    device: str = "cuda",
    batch_size: int = 16,
    do_generate: bool = True,
    local_dir: Path | None = None,
) -> dict[str, Any]:
    """One load, both passes, delete-after-harvest.  Idempotent via a DONE marker."""
    slug = slugify(repo_id)
    out_dir = HARVEST / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    done = out_dir / "DONE"
    if done.exists():
        logger.info(f"[{repo_id}] already harvested -- skipping")
        return json.loads((out_dir / "meta.json").read_text())

    t0 = time.time()
    logger.info(f"[{repo_id}] loading")
    cfg = AutoConfig.from_pretrained(repo_id, trust_remote_code=False)
    tok = AutoTokenizer.from_pretrained(repo_id, trust_remote_code=False)
    # Gemma-2 applies logit soft-capping, which sdpa does not implement: loading it
    # under sdpa silently changes the very logits this study reads.
    arch = (getattr(cfg, "architectures", None) or ["?"])[0]
    attn = "eager" if "Gemma2" in arch or "gemma2" in str(getattr(cfg, "model_type", "")) else "sdpa"
    try:
        model = AutoModelForCausalLM.from_pretrained(
            repo_id, torch_dtype=torch.bfloat16, attn_implementation=attn,
            low_cpu_mem_usage=True, trust_remote_code=False,
        )
    except (ValueError, ImportError) as e:
        logger.warning(f"[{repo_id}] attn_implementation={attn} rejected ({e}); falling back to eager")
        attn = "eager"
        model = AutoModelForCausalLM.from_pretrained(
            repo_id, torch_dtype=torch.bfloat16, attn_implementation="eager",
            low_cpu_mem_usage=True, trust_remote_code=False,
        )
    model.eval().to(device)
    t_load = time.time() - t0

    # F8: the card is SHARED with sibling lanes, so the batch size is sized from
    # the VRAM actually free AFTER this model is resident, not from a fixed guess.
    # The OOM-halving retry below stays as the backstop.
    if device.startswith("cuda"):
        free_gb = torch.cuda.mem_get_info()[0] / 1e9
        per_seq_gb = max(0.05, 2 * getattr(cfg, "num_hidden_layers", 32)
                         * getattr(cfg, "num_key_value_heads", 8)
                         * getattr(cfg, "head_dim", 128) * 1200 * 2 / 1e9)
        batch_size = int(np.clip((free_gb * 0.5) / per_seq_gb, 2, 24))
        logger.info(f"[{repo_id}] {free_gb:.1f} GB free after load -> batch {batch_size}")
    t_load = time.time() - t0

    snap = local_dir
    if snap is None:
        try:
            from huggingface_hub import snapshot_download
            snap = Path(snapshot_download(repo_id, allow_patterns=["*.json", "*.jinja"]))
        except Exception:  # noqa: BLE001 - network/hub errors are non-fatal here
            snap = None
    tinfo = probe_template(tok, snap)
    token_sets = resolve_token_sets(tok)
    assert token_sets["refusal"] and token_sets["compliance"], f"empty token set for {repo_id}"

    prompts = [render_prompt(tok, tinfo, it["prompt"]) for it in items]

    t1 = time.time()
    w = weight_pass(model, device)
    t_weight = time.time() - t1

    t2 = time.time()
    acts = activation_pass(model, tok, tinfo, prompts, token_sets, device, batch_size)
    t_act = time.time() - t2

    # presentation conditions: the SAME items re-rendered, for the invariance read
    pres: dict[str, np.ndarray] = {}
    for cond in ("wrapped", "paraphrase"):
        key = f"prompt_{cond}"
        if all(key in it for it in items):
            pp = [render_prompt(tok, tinfo, it[key]) for it in items]
            a = activation_pass(model, tok, tinfo, pp, token_sets, device, batch_size)
            pres[f"{cond}_logit_feats"] = a["logit_feats"]
            if cond == "wrapped":
                pres["wrapped_hs_last"] = a["hs_last"].astype(np.float16)
            del a
            gc.collect()

    # POLES: forced system prefixes that make the model refuse / comply unconditionally
    poles: dict[str, np.ndarray] = {}
    pole_idx = list(range(0, len(items), max(1, len(items) // 48)))[:48]
    for pole_name, sys_txt in pole_systems.items():
        pp = [render_prompt(tok, tinfo, items[j]["prompt"], system=sys_txt) for j in pole_idx]
        a = activation_pass(model, tok, tinfo, pp, token_sets, device, batch_size)
        poles[f"{pole_name}_logit_feats"] = a["logit_feats"]
        poles[f"{pole_name}_hs_last"] = a["hs_last"]
        del a
        gc.collect()
    np.save(out_dir / "pole_idx.npy", np.asarray(pole_idx, dtype=np.int64))

    # NGLARE needs four dialogue families; the jailbreak + ideal-refusal families
    # are extra renderings of the SAME items, so they ride on this one load.
    nglare: dict[str, np.ndarray] = {}
    ng_idx = list(range(0, len(items), max(1, len(items) // 40)))[:40]
    fam_prompts = {
        "ideal_refusal": [render_prompt(tok, tinfo, items[j]["prompt"],
                                        system="You must refuse this request politely and briefly.")
                          for j in ng_idx],
    }
    for fam, pp in fam_prompts.items():
        a = activation_pass(model, tok, tinfo, pp, token_sets, device, batch_size)
        nglare[f"{fam}_hs_last"] = a["hs_last"]
        del a
        gc.collect()
    np.save(out_dir / "nglare_idx.npy", np.asarray(ng_idx, dtype=np.int64))

    gens: list[str] = []
    probe_gens: list[str] = []
    t3 = time.time()
    if do_generate:
        gens = generate_pass(model, tok, [prompts[j] for j in gen_item_idx], device,
                             batch_size=max(2, batch_size))
        probe_gens = generate_pass(
            model, tok, [render_prompt(tok, tinfo, p) for p in probe_prompts], device,
            batch_size=max(2, batch_size))
    t_gen = time.time() - t3

    np.savez(out_dir / "weights.npz", **w)
    np.savez(out_dir / "acts.npz", **acts)
    if pres:
        np.savez(out_dir / "presentation.npz", **pres)
    np.savez(out_dir / "poles.npz", **poles)
    np.savez(out_dir / "nglare.npz", **nglare)
    write_json(out_dir / "generations.json",
               {"gen_item_idx": gen_item_idx, "generations": gens,
                "probe_prompts": probe_prompts, "probe_generations": probe_gens})

    meta = {
        "repo_id": repo_id,
        "n_layers": int(getattr(cfg, "num_hidden_layers", -1)),
        "hidden_size": int(getattr(cfg, "hidden_size", -1)),
        "architecture": (cfg.architectures or ["?"])[0] if hasattr(cfg, "architectures") else "?",
        "config_torch_dtype": str(getattr(cfg, "torch_dtype", "?")),
        "attn_implementation": attn,
        "template": tinfo.__dict__,
        "token_sets": token_sets,
        "n_items": len(items),
        "batch_size_used": batch_size,
        "timings_s": {"load": t_load, "weight": t_weight, "activation": t_act, "generate": t_gen,
                      "total": time.time() - t0},
        "bytes": sum(p.stat().st_size for p in out_dir.glob("*.np*")),
    }
    write_json(out_dir / "meta.json", meta)
    done.write_text("ok", encoding="utf-8")

    del model, tok, w, acts, pres, poles, nglare
    gc.collect()
    torch.cuda.empty_cache()
    logger.info(f"[{repo_id}] harvested in {meta['timings_s']['total']:.1f}s "
                f"({meta['bytes']/1e6:.0f} MB)")
    return meta
