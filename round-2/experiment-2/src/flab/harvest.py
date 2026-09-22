"""S2 THE SHARED HARVEST -- one engine; every metric in S3 is a read of it.

Two passes per checkpoint:

WEIGHT PASS   zero prompts, seconds. Left singular subspaces of every matrix that
              writes to the residual stream (o_proj, down_proj), via
              ``eigh(W @ W.T)`` in float32.
ACTIVATION    teacher-forced prefill ONLY (no generation). Per item it stores the
PASS          hidden state at the last REAL user token and at the final position
              (the one that predicts the first generated token), plus the
              first-token logits restricted to a top-N slice and the explicit
              refusal/compliance onset ids.

The harvest is written to disk as .npz per checkpoint so every metric can be
recomputed OFFLINE without a second download or forward pass.

PINNED GOTCHA (a): Qwen3 chat models are HYBRID THINKING. Without
``enable_thinking=False`` the first generated token is ``<think>`` and every
first-token logit readout measures nothing. :func:`render_prompt` asserts this.
"""

from __future__ import annotations

import gc
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from loguru import logger

from flab.config import (
    COMPLIANCE_ONSET,
    HARVEST_BATCH,
    MAX_PROMPT_TOKENS,
    REFUSAL_ONSET,
    TOP_LOGITS_KEEP,
    WEIGHT_MODULES,
)
from flab.items import Item
from flab.wstats import LayerSpectrum, layer_spectrum


# --------------------------------------------------------------------------
# Prompt rendering
# --------------------------------------------------------------------------
@dataclass
class Rendered:
    text: str
    ids: list[int]
    last_user_idx: int          # index of the last REAL user-content token
    renderer: str               # 'chat' or 'plain' -- NEVER compare across renderers


def render_prompt(tok, text: str, system: str | None = None) -> Rendered:
    """Render one item. Chat template where one exists, a fixed plain renderer otherwise."""
    msgs = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": text}
    ]
    renderer = "chat"
    rendered: str | None = None
    if getattr(tok, "chat_template", None):
        for kw in ({"enable_thinking": False}, {}):
            try:
                rendered = tok.apply_chat_template(
                    msgs, tokenize=False, add_generation_prompt=True, **kw
                )
                break
            except (TypeError, ValueError):
                continue
    if rendered is None:
        renderer = "plain"
        pre = f"{system}\n\n" if system else ""
        rendered = f"{pre}User: {text}\nAssistant:"

    # GOTCHA (a): a live <think> tag means the thinking flag did not take effect;
    # fall back to string-level removal (fallback branch 13) rather than silently
    # measuring the wrong first token.
    if rendered.rstrip().endswith("<think>"):
        rendered = rendered.rstrip()[: -len("<think>")]
    enc = tok(rendered, add_special_tokens=False, return_offsets_mapping=True)
    ids = enc["input_ids"]
    offs = enc.get("offset_mapping") or []

    end_char = rendered.rfind(text)
    end_char = end_char + len(text) if end_char >= 0 else len(rendered)
    last_user = len(ids) - 1
    if offs:
        cand = [i for i, (a, _b) in enumerate(offs) if a < end_char]
        if cand:
            last_user = max(cand)

    if len(ids) > MAX_PROMPT_TOKENS:          # truncate from the LEFT, keep the tail
        cut = len(ids) - MAX_PROMPT_TOKENS
        ids = ids[cut:]
        last_user = max(0, last_user - cut)
    return Rendered(rendered, ids, last_user, renderer)


def onset_token_ids(tok) -> tuple[list[int], list[int]]:
    """First-token ids of the refusal and compliance onset words, with and without a space."""

    def collect(words) -> list[int]:
        out: set[int] = set()
        for w in words:
            for form in (w, " " + w):
                enc = tok(form, add_special_tokens=False)["input_ids"]
                if enc:
                    out.add(int(enc[0]))
        return sorted(out)

    ref, com = collect(REFUSAL_ONSET), collect(COMPLIANCE_ONSET)
    overlap = set(ref) & set(com)
    ref = [i for i in ref if i not in overlap]
    com = [i for i in com if i not in overlap]
    assert ref and com, "refusal/compliance onset id sets must be non-empty"
    return ref, com


# --------------------------------------------------------------------------
# Weight pass
# --------------------------------------------------------------------------
def weight_pass(model, device: str = "cuda") -> dict[str, list[LayerSpectrum]]:
    """Left singular subspaces of every residual-write matrix. Zero prompts."""
    layers = _get_layers(model)
    out: dict[str, list[LayerSpectrum]] = {m: [] for m in WEIGHT_MODULES}
    for li, layer in enumerate(layers):
        for mod in WEIGHT_MODULES:
            W = _get_module_weight(layer, mod)
            if W is None:
                continue
            out[mod].append(layer_spectrum(W, li, mod, device=device))
    for mod in list(out):
        if not out[mod]:
            del out[mod]
    return out


def _get_layers(model):
    for path in ("model.layers", "model.model.layers", "transformer.h"):
        obj = model
        try:
            for p in path.split("."):
                obj = getattr(obj, p)
            return obj
        except AttributeError:
            continue
    raise AttributeError("could not locate the decoder layer list")


def _get_module_weight(layer, mod: str):
    for parent in ("self_attn", "mlp", "attention", "feed_forward"):
        p = getattr(layer, parent, None)
        if p is None:
            continue
        m = getattr(p, mod, None)
        if m is not None and hasattr(m, "weight"):
            return m.weight
    return None


def has_residual_write_modules(model) -> tuple[bool, str]:
    """SKIP-WITH-REASON guard: MoE and SSM hybrids do not have these per layer."""
    try:
        layers = _get_layers(model)
    except AttributeError as e:
        return False, f"no decoder layer list: {e}"
    for mod in WEIGHT_MODULES:
        missing = [i for i, l in enumerate(layers) if _get_module_weight(l, mod) is None]
        if missing:
            return False, f"{mod} missing on {len(missing)}/{len(layers)} layers"
    return True, ""


# --------------------------------------------------------------------------
# Activation pass
# --------------------------------------------------------------------------
@torch.no_grad()
def activation_pass(
    model,
    tok,
    items: list[Item],
    *,
    system: str | None = None,
    batch_size: int = HARVEST_BATCH,
    device: str = "cuda",
    keep_logits: int = TOP_LOGITS_KEEP,
) -> dict:
    """Teacher-forced prefill over the item battery. No generation happens here."""
    ref_ids, com_ids = onset_token_ids(tok)
    rend = [render_prompt(tok, it.text, system) for it in items]
    renderers = {r.renderer for r in rend}
    assert len(renderers) == 1, f"mixed renderers in one stratum: {renderers}"

    pad_id = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    n_items = len(items)
    hs_last: list[np.ndarray] = []
    hs_gen: list[np.ndarray] = []
    top_vals = np.zeros((n_items, keep_logits), dtype=np.float16)
    top_idx = np.zeros((n_items, keep_logits), dtype=np.int32)
    onset_ref = np.zeros((n_items, len(ref_ids)), dtype=np.float32)
    onset_com = np.zeros((n_items, len(com_ids)), dtype=np.float32)

    for start in range(0, n_items, batch_size):
        chunk = rend[start : start + batch_size]
        maxlen = max(len(r.ids) for r in chunk)
        inp = torch.full((len(chunk), maxlen), pad_id, dtype=torch.long)
        att = torch.zeros((len(chunk), maxlen), dtype=torch.long)
        lu = []
        for b, r in enumerate(chunk):                      # LEFT padding
            off = maxlen - len(r.ids)
            inp[b, off:] = torch.tensor(r.ids, dtype=torch.long)
            att[b, off:] = 1
            lu.append(off + r.last_user_idx)
        inp, att = inp.to(device), att.to(device)
        out = model(input_ids=inp, attention_mask=att, output_hidden_states=True)
        hidden = out.hidden_states                          # (n_layers+1) x (B,T,d)
        H = torch.stack(hidden, dim=0)                      # (L+1,B,T,d)
        for b in range(len(chunk)):
            hs_last.append(H[:, b, lu[b], :].float().cpu().numpy().astype(np.float16))
            hs_gen.append(H[:, b, -1, :].float().cpu().numpy().astype(np.float16))
        lg = out.logits[:, -1, :].float()                   # (B, V)
        k = min(keep_logits, lg.shape[-1])
        v, i = torch.topk(lg, k, dim=-1)
        top_vals[start : start + len(chunk), :k] = v.cpu().numpy().astype(np.float16)
        top_idx[start : start + len(chunk), :k] = i.cpu().numpy().astype(np.int32)
        onset_ref[start : start + len(chunk)] = lg[:, ref_ids].cpu().numpy()
        onset_com[start : start + len(chunk)] = lg[:, com_ids].cpu().numpy()
        del out, hidden, H, lg
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
    gc.collect()

    return {
        "item_ids": [it.id for it in items],
        "pools": [it.pool for it in items],
        "folds": [it.fold_id for it in items],
        "categories": [it.harm_category for it in items],
        "hs_last_prompt": np.stack(hs_last),   # (N, L+1, d)
        "hs_gen": np.stack(hs_gen),            # (N, L+1, d)
        "top_logit_vals": top_vals,
        "top_logit_idx": top_idx,
        "onset_refusal": onset_ref,
        "onset_compliance": onset_com,
        "refusal_ids": ref_ids,
        "compliance_ids": com_ids,
        "renderer": rend[0].renderer,
        "rendered_example": rend[0].text,
    }


def refusal_drive(act: dict) -> np.ndarray:
    """r_i = logsumexp(refusal onset logits) - logsumexp(compliance onset logits)."""
    from scipy.special import logsumexp

    return (
        logsumexp(act["onset_refusal"].astype(np.float64), axis=1)
        - logsumexp(act["onset_compliance"].astype(np.float64), axis=1)
    )


def save_harvest(path: Path, weights: dict, act: dict | None) -> None:
    """Persist the two-tier harvest so every metric is re-analysable offline."""
    payload: dict[str, np.ndarray] = {}
    meta: dict[str, object] = {"modules": list(weights)}
    for mod, specs in weights.items():
        specs = sorted(specs, key=lambda s: s.layer)
        payload[f"w_{mod}_bottom1"] = np.stack([s.bottom_k1 for s in specs])
        payload[f"w_{mod}_top1"] = np.stack([s.top_k1 for s in specs])
        payload[f"w_{mod}_scalars"] = np.array(
            [[s.s_min, s.s_2, s.s_max, s.s_median, s.s_sum, s.participation_ratio]
             for s in specs], dtype=np.float32,
        )
        for r in sorted(specs[0].rank_band):
            payload[f"w_{mod}_band{r}"] = np.stack([s.rank_band[r] for s in specs])
    if act is not None:
        for k, v in act.items():
            if isinstance(v, np.ndarray):
                payload[f"a_{k}"] = v
            else:
                meta[k] = v
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **payload)
    path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1, default=str))
    logger.info(f"harvest -> {path} ({path.stat().st_size / 1e6:.1f} MB)")
