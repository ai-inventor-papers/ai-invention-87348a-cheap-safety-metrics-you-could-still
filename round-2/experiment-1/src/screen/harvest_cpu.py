"""CPU harvest: the iteration-1 harvest schema, reproduced without a GPU.

WHY THIS FILE EXISTS
--------------------
Iteration 1 ran on an RTX 4000 Ada.  This box has NO GPU, 2 CPU cores and a
16 GB cgroup limit, so `screen/harvest.py` (which assumes `device="cuda"`,
instantiates the full model and generates 128 tokens per item) is not runnable
here.  Rather than drop the family axis -- the one thing this artifact exists to
buy -- the harvest is TIERED, exactly as pre-registered in PREREG.json:

  tier W  weights only, streamed tensor-by-tensor out of the cached safetensors
          with `safetensors.safe_open`, NEVER instantiating a model.  This costs
          no model class, no GPU and ~1-10 CPU-minutes per checkpoint, and it
          produces byte-compatible `weights.npz` files.
  tier A  additionally a prefill-only activation pass on the frozen 160-item
          battery, producing `acts.npz` in the SAME schema as iteration 1 so
          inherited and new checkpoints are interchangeable in every read.

Two deliberate deviations from `screen/harvest.py`, both verified against
`screen/reads.py` so no downstream read changes:

  * `down_proj` gets EIGENVALUES ONLY (`np.linalg.eigvalsh`).  `weight_reads`
    consumes `down_proj_sv` and nothing else from that matrix -- no `_top`, no
    `_bot` -- and eigvalsh is ~2.5x faster than a full eigh at d=2048.
  * the bf16-as-shipped second decomposition is done for `o_proj` only, because
    `o_proj_botgap_bf16` is the only bf16 key any read touches.

Both deviations are recorded in each checkpoint's `meta.json` under
`schema_deviations`, so a later iteration can tell these harvests apart from
iteration 1's without re-reading this docstring.
"""

from __future__ import annotations

import gc
import json
import re
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

TOP_K_SV = 16
BOT_K_SV = 16

_LAYER_RE = re.compile(r"(?:^|\.)layers\.(\d+)\.")


# ---------------------------------------------------------------------------
# locating the cached weights without instantiating anything
# ---------------------------------------------------------------------------
def resolve_snapshot(repo_id: str, *, token: str | None = None) -> Path:
    """Return the local snapshot dir for `repo_id`, downloading only if absent.

    The shared cache is warm, so in the normal case this is a metadata-only
    resolution and touches no bytes.
    """
    from huggingface_hub import snapshot_download

    path = snapshot_download(
        repo_id,
        allow_patterns=["*.safetensors", "*.json", "tokenizer*", "*.model", "*.txt"],
        token=token,
    )
    return Path(path)


def safetensors_files(snap: Path) -> list[Path]:
    files = sorted(snap.glob("*.safetensors"))
    if not files:
        raise FileNotFoundError(f"no safetensors in {snap}")
    return files


def build_key_index(files: list[Path]) -> dict[str, Path]:
    """Map every tensor key -> the shard file holding it, without reading data."""
    from safetensors import safe_open

    index: dict[str, Path] = {}
    for f in files:
        with safe_open(str(f), framework="pt") as h:
            for k in h.keys():
                index[k] = f
    return index


def detect_quantization(index: dict[str, Path]) -> dict[str, Any]:
    """Is this checkpoint stored in a compressed / quantized tensor format?

    WHY THIS GETS ITS OWN CHECK AND ITS OWN DROP REASON.  A compressed-tensors
    FP8 checkpoint stores `...weight._data` (fp8) beside `...weight._scale` and
    per-layer `input_scale` / `output_scale`, so a plain `...weight` lookup finds
    nothing and the harvest fails with a misleading "produced nothing".

    It must be DROPPED rather than dequantized.  Every weight read in this study
    is a BOTTOM-OF-SPECTRUM statistic -- sigma_min/sigma_2nd-min, the bottom-16
    singular subspace, cross-layer alignment of the bottom-1 direction.  FP8
    rounding bites hardest exactly there, so a dequantized FP8 spectrum is not
    commensurable with a bf16 one, and a difference between them would be read as
    an editing scar when it is a storage format.  Recorded as a finding, not
    silently skipped.
    """
    markers = {
        "fp8_compressed_tensors": any(k.endswith("._data") for k in index),
        "has_weight_scale": any(k.endswith("._scale") for k in index),
        "has_activation_scales": any(k.endswith("input_scale") or k.endswith("output_scale")
                                     for k in index),
        "gptq_awq": any(k.endswith(".qweight") or k.endswith(".qzeros") for k in index),
        "bnb_4bit": any(".quant_state" in k or k.endswith(".absmax") for k in index),
    }
    markers["is_quantized"] = bool(
        markers["fp8_compressed_tensors"] or markers["gptq_awq"] or markers["bnb_4bit"])
    return markers


def find_matrix_keys(index: dict[str, Path], suffix: str) -> list[tuple[int, str]]:
    """All `...layers.<i>....<suffix>.weight` keys, sorted by layer index.

    Suffix is matched on the dotted path so `o_proj` never collides with, say,
    `qkv_proj`.  Returns [(layer_index, key), ...].
    """
    want = f".{suffix}.weight"
    hits: list[tuple[int, str]] = []
    for k in index:
        if not k.endswith(want):
            continue
        m = _LAYER_RE.search(k)
        if m is None:
            continue
        hits.append((int(m.group(1)), k))
    return sorted(hits)


# ---------------------------------------------------------------------------
# tier W -- the weight pass
# ---------------------------------------------------------------------------
def _left_spectrum_np(W: np.ndarray, *, want_vecs: bool) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Left singular values (descending) + optional top-k / bottom-k left vectors.

    Via eigh of the d_out x d_out Gram, never a full SVD of the rectangular
    matrix: the Gram route is the same numbers and roughly 50x faster.
    """
    Wf = np.ascontiguousarray(W, dtype=np.float32)
    gram = Wf @ Wf.T
    if want_vecs:
        evals, evecs = np.linalg.eigh(gram)          # ascending
    else:
        evals, evecs = np.linalg.eigvalsh(gram), None
    sv = np.sqrt(np.clip(evals, 0.0, None)).astype(np.float32)
    if not want_vecs:
        return sv[::-1].copy(), None, None
    k_top = min(TOP_K_SV, sv.shape[0])
    k_bot = min(BOT_K_SV, sv.shape[0])
    top_vecs = evecs[:, -k_top:][:, ::-1].T.copy().astype(np.float32)   # (k, d) descending sv
    bot_vecs = evecs[:, :k_bot].T.copy().astype(np.float32)             # (k, d) ascending sv
    return sv[::-1].copy(), top_vecs, bot_vecs


def _botgap_bf16(W_t: torch.Tensor) -> np.float32:
    """sigma_min / sigma_2nd-min recomputed on the bf16-as-shipped weights.

    Thresholds in this study are set against bf16, not fp32: the bottom of the
    spectrum is exactly where rounding bites, and an algebraic zero in fp32 is a
    small positive number in bf16.
    """
    wb = W_t.to(torch.bfloat16).to(torch.float32)
    g = (wb @ wb.T).numpy()
    eb = np.sqrt(np.clip(np.linalg.eigvalsh(g), 0.0, None))
    if eb.shape[0] > 1 and eb[1] > 0:
        return np.float32(eb[0] / eb[1])
    return np.float32(np.nan)


def select_band(n_layers: int, band: int, centre_frac: float = 0.5) -> list[int]:
    """The contiguous layer band this harvest actually decomposes.

    WHY A BAND AND NOT EVERY LAYER.  The host this ran on carries a load average
    near 290 across its cores, and a single eigh of a 1536x1536 Gram measured
    25-34 s here against 0.7 s on an idle box -- a ~40x contention penalty.  A
    full 28-layer pass would cost ~34 CPU-minutes per checkpoint and the family
    axis, which is the entire point of this artifact, would not be bought at all.

    A CONTIGUOUS band keeps every weight read well defined rather than
    approximating it: `BSA_w8` slides an 8-layer window and max-es over windows,
    so on an 8-layer band it is exactly ONE window -- the same functional form,
    evaluated at one depth instead of the max over depths.  `botgap`,
    `crosslayer_cos` and `spectral_entropy` are min/mean reductions over layers
    and restrict to the band cleanly.

    The band is applied IDENTICALLY to the inherited iteration-1 checkpoints
    (which hold every layer on disk and are simply sliced), so no comparison in
    this artifact is ever band-vs-full.  `band_depth_fraction` is recorded in
    every meta.json so the restriction is visible in the table, not buried here.
    """
    band = min(band, n_layers)
    centre = int(round(centre_frac * n_layers))
    start = max(0, min(n_layers - band, centre - band // 2))
    return list(range(start, start + band))


def weight_pass_streaming(
    snap: Path,
    index: dict[str, Path],
    *,
    band: int | None = None,
    centre_frac: float = 0.5,
    progress: Callable[[str], None] | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Stream o_proj / down_proj layer by layer and build the weights.npz payload.

    Memory discipline: exactly ONE weight matrix and ONE Gram are live at a
    time.  Nothing accumulates except the (small) per-layer outputs.
    """
    from safetensors import safe_open

    out: dict[str, np.ndarray] = {}
    diag: dict[str, Any] = {}
    open_handles: dict[Path, Any] = {}

    def _get(key: str) -> torch.Tensor:
        f = index[key]
        if f not in open_handles:
            open_handles[f] = safe_open(str(f), framework="pt")
        return open_handles[f].get_tensor(key)

    try:
        for mat_name, want_vecs in (("o_proj", True), ("down_proj", False)):
            keys = find_matrix_keys(index, mat_name)
            if not keys:
                diag[f"{mat_name}_missing"] = True
                continue
            diag[f"{mat_name}_n_layers_total"] = len(keys)
            if band is not None and band < len(keys):
                keep = set(select_band(len(keys), band, centre_frac))
                keys = [(li, k) for i, (li, k) in enumerate(keys) if i in keep]
                diag[f"{mat_name}_band_layers"] = [li for li, _ in keys]
                diag[f"{mat_name}_band_depth_fraction"] = [
                    round(li / max(1, diag[f"{mat_name}_n_layers_total"] - 1), 3)
                    for li, _ in keys]
            svs: list[np.ndarray] = []
            tops: list[np.ndarray] = []
            bots: list[np.ndarray] = []
            bf16_bot: list[np.float32] = []
            for li, key in keys:
                W_t = _get(key).to(torch.float32)
                W = W_t.numpy()
                sv, tv, bv = _left_spectrum_np(W, want_vecs=want_vecs)
                svs.append(sv)
                if want_vecs:
                    tops.append(tv)
                    bots.append(bv)
                    bf16_bot.append(_botgap_bf16(W_t))
                del W, W_t
                if progress is not None and li % 8 == 0:
                    progress(f"{mat_name} layer {li}/{keys[-1][0]}")
                gc.collect()
            # layers can differ in width on a few architectures; refuse to stack silently
            widths = {s.shape[0] for s in svs}
            if len(widths) != 1:
                diag[f"{mat_name}_ragged_widths"] = sorted(widths)
                continue
            out[f"{mat_name}_sv"] = np.stack(svs)
            if want_vecs:
                out[f"{mat_name}_top"] = np.stack(tops)
                out[f"{mat_name}_bot"] = np.stack(bots)
                out[f"{mat_name}_botgap_bf16"] = np.asarray(bf16_bot, dtype=np.float32)
            diag[f"{mat_name}_n_layers"] = len(keys)
            diag[f"{mat_name}_d_out"] = int(svs[0].shape[0])
    finally:
        for h in open_handles.values():
            try:
                h.__exit__(None, None, None)
            except (AttributeError, TypeError):
                pass
        open_handles.clear()
        gc.collect()
    return out, diag


# ---------------------------------------------------------------------------
# tier A -- prefill-only activation pass (CPU)
# ---------------------------------------------------------------------------
@torch.no_grad()
def activation_pass_cpu(
    model,
    tok,
    prompts: list[str],
    token_sets: dict[str, list[int]],
    *,
    batch_size: int = 4,
    max_length: int = 512,
) -> dict[str, np.ndarray]:
    """Hidden states at the LAST PROMPT TOKEN and at the FIRST GENERATED TOKEN.

    Schema-identical to `screen/harvest.py:activation_pass` so inherited and new
    checkpoints are interchangeable.  The first generated token is obtained by a
    REAL one-token decode off the prefill cache, which is also what makes the
    stored `first_token_id` a valid test of the Qwen3 hybrid-thinking trap.
    """
    n = len(prompts)
    hs_last: list[np.ndarray] = []
    hs_first: list[np.ndarray] = []
    logit_feats: list[np.ndarray] = []
    first_tok_ids: list[int] = []

    ref_ids = torch.tensor(token_sets["refusal"], dtype=torch.long)
    cmp_ids = torch.tensor(token_sets["compliance"], dtype=torch.long)

    orig_side = tok.padding_side
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    bs = batch_size
    i = 0
    try:
        while i < n:
            chunk = prompts[i : i + bs]
            enc = tok(chunk, return_tensors="pt", padding=True, truncation=True,
                      max_length=max_length, add_special_tokens=False)
            out = model(**enc, output_hidden_states=True, use_cache=True)
            h_last = torch.stack([h[:, -1, :] for h in out.hidden_states], dim=1)
            logits = out.logits[:, -1, :].float()
            lp = torch.log_softmax(logits, dim=-1)
            gap = torch.logsumexp(lp[:, ref_ids], -1) - torch.logsumexp(lp[:, cmp_ids], -1)
            ref_mass = torch.logsumexp(lp[:, ref_ids], -1).exp()
            ent = -(lp.exp() * lp).sum(-1)
            nxt = logits.argmax(-1)
            top1p = lp.max(-1).values.exp()
            am = torch.cat(
                [enc["attention_mask"],
                 torch.ones((len(chunk), 1), dtype=enc["attention_mask"].dtype)], dim=1)
            out2 = model(input_ids=nxt.unsqueeze(1), attention_mask=am,
                         past_key_values=out.past_key_values,
                         output_hidden_states=True, use_cache=False)
            h_first = torch.stack([h[:, -1, :] for h in out2.hidden_states], dim=1)

            hs_last.append(h_last.to(torch.float16).numpy())
            hs_first.append(h_first.to(torch.float16).numpy())
            logit_feats.append(
                torch.stack([gap, ref_mass, ent, top1p], dim=1).numpy().astype(np.float32))
            first_tok_ids.extend(nxt.tolist())
            del out, out2, h_last, h_first, enc, logits, lp
            gc.collect()
            i += bs
    finally:
        tok.padding_side = orig_side

    return {
        "hs_last": np.concatenate(hs_last, 0),
        "hs_first": np.concatenate(hs_first, 0),
        "logit_feats": np.concatenate(logit_feats, 0),
        "first_token_id": np.asarray(first_tok_ids, dtype=np.int64),
    }


# ---------------------------------------------------------------------------
# orchestration for ONE checkpoint
# ---------------------------------------------------------------------------
def harvest_checkpoint_cpu(
    repo_id: str,
    *,
    out_dir: Path,
    token: str | None,
    items: list[dict] | None = None,
    do_activations: bool = False,
    act_batch_size: int = 4,
    max_items: int | None = None,
    band: int | None = 8,
    centre_frac: float = 0.5,
) -> dict[str, Any]:
    """Harvest ONE checkpoint to `out_dir`, writing a DONE marker on success.

    Resume-safe: a slug that already carries DONE is skipped by the caller.
    Every sub-result is written the moment it is measured, never in a final
    packaging step, because a cleanup process reaped an earlier iteration's
    workspace mid-run.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    timings: dict[str, float] = {}
    meta: dict[str, Any] = {
        "repo_id": repo_id,
        "harvest_tier": "W",
        "schema_deviations": [
            "down_proj: eigenvalues only (down_proj_sv); no _top/_bot. weight_reads consumes "
            "only down_proj_sv, so no read changes.",
            "bf16 second decomposition for o_proj only (o_proj_botgap_bf16); no down_proj bf16 key.",
        ],
        "device": "cpu",
        "band": band,
        "band_centre_frac": centre_frac,
    }

    t = time.time()
    snap = resolve_snapshot(repo_id, token=token)
    files = safetensors_files(snap)
    index = build_key_index(files)
    timings["resolve"] = time.time() - t
    logger.info(f"{repo_id}: snapshot {snap} ({len(files)} shards, {len(index)} tensors)")

    cfg_path = snap / "config.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    meta["architecture"] = (cfg.get("architectures") or ["?"])[0]
    meta["model_type"] = cfg.get("model_type")
    meta["n_layers"] = cfg.get("num_hidden_layers")
    meta["hidden_size"] = cfg.get("hidden_size")
    meta["config_torch_dtype"] = cfg.get("torch_dtype") or cfg.get("dtype")
    meta["tie_word_embeddings"] = cfg.get("tie_word_embeddings")

    quant = detect_quantization(index)
    meta["quantization"] = quant
    if quant["is_quantized"]:
        raise RuntimeError(
            f"{repo_id}: QUANTIZED CHECKPOINT ({[k for k, v in quant.items() if v and k != 'is_quantized']}). "
            "Dropped, not dequantized: every weight read here is a bottom-of-spectrum statistic "
            "and FP8/GPTQ rounding is concentrated exactly there, so its spectrum is not "
            "commensurable with the bf16 checkpoints it would be compared against.")

    t = time.time()
    w, wdiag = weight_pass_streaming(
        snap, index, band=band, centre_frac=centre_frac,
        progress=lambda s: logger.info(f"{repo_id}: {s}"))
    timings["weight"] = time.time() - t
    if not w:
        raise RuntimeError(f"{repo_id}: weight pass produced nothing ({wdiag})")
    np.savez_compressed(out_dir / "weights.npz", **w)
    meta["weight_diag"] = wdiag
    logger.info(f"{repo_id}: weight pass {timings['weight']:.1f}s -> {list(w.keys())}")
    del w
    gc.collect()

    if do_activations and items is not None:
        t = time.time()
        acts, amet = _activation_stage(repo_id, snap, items, act_batch_size, max_items, token)
        timings["activation"] = time.time() - t
        np.savez_compressed(out_dir / "acts.npz", **acts)
        meta.update(amet)
        meta["harvest_tier"] = "A"
        logger.info(f"{repo_id}: activation pass {timings['activation']:.1f}s")
        del acts
        gc.collect()

    timings["total"] = time.time() - t0
    meta["timings_s"] = timings
    meta["n_items"] = 0 if not do_activations else int(meta.get("n_items", 0))
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, default=str))
    (out_dir / "DONE").write_text(f"{time.time()}\n")
    return meta


def _activation_stage(
    repo_id: str,
    snap: Path,
    items: list[dict],
    batch_size: int,
    max_items: int | None,
    token: str | None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Load the model on CPU, render the battery, run the prefill pass, free it."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from screen.harvest import probe_template, render_prompt, resolve_token_sets

    tok = AutoTokenizer.from_pretrained(str(snap))
    tinfo = probe_template(tok, snap)
    token_sets = resolve_token_sets(tok)
    assert not (set(token_sets["refusal"]) & set(token_sets["compliance"])), (
        f"{repo_id}: refusal and compliance token sets collide")

    use = items if max_items is None else items[:max_items]
    prompts = [render_prompt(tok, tinfo, it["prompt"]) for it in use]

    kw: dict[str, Any] = {"dtype": torch.float32, "low_cpu_mem_usage": True}
    if (snap / "config.json").exists():
        mt = json.loads((snap / "config.json").read_text()).get("model_type")
        if mt == "gemma2":
            # sdpa DROPS gemma-2's logit soft-capping; that is an upstream kernel
            # limitation, not a version bug, so eager is mandatory here.
            kw["attn_implementation"] = "eager"
    model = AutoModelForCausalLM.from_pretrained(str(snap), **kw)
    model.eval()
    try:
        acts = activation_pass_cpu(model, tok, prompts, token_sets, batch_size=batch_size)
    finally:
        del model
        gc.collect()

    think_id = None
    for cand in ("<think>", "<|think|>"):
        tid = tok.convert_tokens_to_ids(cand)
        if isinstance(tid, int) and tid >= 0 and tid != getattr(tok, "unk_token_id", None):
            think_id = tid
            break
    n_think = int((acts["first_token_id"] == think_id).sum()) if think_id is not None else 0

    meta: dict[str, Any] = {
        "n_items": len(use),
        "token_sets": token_sets,
        "n_refusal_ids": len(token_sets["refusal"]),
        "n_compliance_ids": len(token_sets["compliance"]),
        "template": {
            "template_sha256": tinfo.template_sha256,
            "renderer": tinfo.renderer,
            "enable_thinking_supported": tinfo.enable_thinking_supported,
        },
        "think_token_id": think_id,
        "n_first_token_is_think": n_think,
        "think_trap_fired": bool(n_think > 0),
        "attn_implementation": kw.get("attn_implementation", "default"),
        "act_dtype": "float32",
    }
    return acts, meta
