"""ROSI 128-token side-arm library: functions COPIED (adapted, never sys.path-imported) from
iter-2 READ-ONLY sources. Every function below cites its exact source path + line numbers.

Sources (all under IT2 =
  /ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_2):

  IT2/behave2.py
    snapshot()              L230-236  -- locate the cached safetensors snapshot dir
    load()                  L239-257  -- AutoModelForCausalLM/AutoTokenizer load, fp32, sdpa
    accepts_system()        L260-267  -- does this tokenizer's chat template accept a system turn
    render()                L270-294  -- chat-render prompts, Qwen3 hybrid-thinking disabled
    assert_tokenizer_sane() L297-307  -- tokenizer sanity guard (missing tokenizer.json trap)
    layers_of()              L324-329 -- locate model.model.layers
    last_token_states()      L336-389 -- (N, L+1, d) residual at the last prompt token (no
                                          down_proj hook version used here; FIT stage only)
    pick_lstar()              L392-414 -- ROSI/Arditi-style l* selection (cited, NOT rerun: this
                                          script trusts the stored probe's l* and instead verifies
                                          that a from-scratch diff-in-means AT that stored l*
                                          reproduces the stored s_hat by cosine similarity)
    eos_ids()                 L663-670 -- resolve the model+tokenizer's EOS id set
    rosi_edit()                L565-599 -- THE EXACT EDIT iter-2's bcells cells used:
                                          W += alpha*outer(d, w_bar), alpha = mult*0.01*
                                          ||W||_F/||w_bar||, on o_proj+down_proj of ALL layers;
                                          hidden=True draws an INDEPENDENT random unit direction
                                          per matrix (not shared across matrices), from
                                          np.random.default_rng(seed + int(mult*1000)).

  IT2/lanec/rosi.py
    fit_safety_direction()  L106-114  -- unit-norm diff-in-means safety direction at one layer
                                         (the closed-form iter-2's own s_hat computation reduces
                                         to; used here as the citation for the refit formula)
    apply_rosi() 'paper' variant L60-103 -- an EQUIVALENT (not the one actually run) formulation
                                         of the same edit as behave2.rosi_edit; cited to show the
                                         alpha rule is the one from ROSI's paper (2508.20766),
                                         not a private invention of behave2.py.
    pick_lstar()              L117-136 -- cross-fitted-AUROC l* rule; cited for provenance, not
                                         re-run (see note above).

None of these are imported from IT2 (no sys.path insertion into IT2); every function is
re-typed here against this workspace's own venv_live packages.
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

# ---------------------------------------------------------------------------------------------
# model I/O -- IT2/behave2.py L230-329 (snapshot, load, accepts_system, render,
# assert_tokenizer_sane, layers_of)
# ---------------------------------------------------------------------------------------------


def snapshot(repo: str, cache_root: Path) -> Path:
    """IT2/behave2.py L230-236, verbatim logic."""
    base = cache_root / f"models--{repo.replace('/', '--')}" / "snapshots"
    snaps = sorted(base.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for s in snaps:
        if list(s.glob("*.safetensors")):
            return s
    raise FileNotFoundError(f"no safetensors snapshot for {repo}")


def load(repo: str, cache_root: Path, dtype: torch.dtype = torch.float32):
    """IT2/behave2.py L239-257, verbatim logic (AutoModelForCausalLM, sdpa->eager fallback,
    left padding, pad token = eos if unset)."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    snap = snapshot(repo, cache_root)
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(str(snap))
    try:
        model = AutoModelForCausalLM.from_pretrained(str(snap), dtype=dtype, attn_implementation="sdpa")
    except (ValueError, ImportError, TypeError) as exc:
        logger.warning(f"{repo}: sdpa unavailable ({exc}); eager")
        model = AutoModelForCausalLM.from_pretrained(str(snap), dtype=dtype, attn_implementation="eager")
    model.eval()
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    logger.info(f"loaded {repo} ({dtype}) in {time.time()-t0:.1f}s from {snap.name[:10]}")
    return model, tok, snap


def accepts_system(tok) -> bool:
    """IT2/behave2.py L260-267, verbatim logic."""
    try:
        tok.apply_chat_template(
            [{"role": "system", "content": "x"}, {"role": "user", "content": "y"}],
            add_generation_prompt=True, tokenize=False)
        return True
    except Exception:  # noqa: BLE001 - jinja raises its own TemplateError type
        return False


def render(tok, prompts: list[str], system: str | None, *, sys_ok: bool) -> list[str]:
    """IT2/behave2.py L270-294, verbatim logic (Qwen3 hybrid-thinking disabled via
    enable_thinking=False, falling back to no kwarg on TypeError)."""
    out = []
    for p in prompts:
        if system and not sys_ok:
            msgs = [{"role": "user", "content": f"{system}\n\n{p}"}]
        else:
            msgs = ([{"role": "system", "content": system}] if system else []) + [
                {"role": "user", "content": p}]
        try:
            out.append(tok.apply_chat_template(
                msgs, add_generation_prompt=True, tokenize=False, enable_thinking=False))
        except TypeError:
            out.append(tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False))
    return out


def assert_tokenizer_sane(tok, repo: str, sys_ok: bool) -> dict:
    """IT2/behave2.py L297-307, verbatim logic."""
    probe = "How do I kill a python process that is not responding to signals?"
    r = render(tok, [probe], None, sys_ok=sys_ok)[0]
    n_ids = len(tok(r, add_special_tokens=False)["input_ids"])
    n_words = len(probe.split())
    ok = n_ids >= n_words
    info = {"rendered_prefix": r[:160], "n_ids": n_ids, "n_words": n_words, "ok": ok}
    if not ok:
        raise RuntimeError(f"{repo}: tokenizer INSANE -- {n_words}-word prompt encodes to {n_ids} ids")
    return info


def layers_of(model):
    """IT2/behave2.py L324-329, verbatim logic."""
    for attr in ("model", "transformer"):
        inner = getattr(model, attr, None)
        if inner is not None and hasattr(inner, "layers"):
            return inner.layers
    raise AttributeError("cannot locate decoder layers")


def eos_ids(model, tok) -> list[int]:
    """IT2/behave2.py L663-670, verbatim logic."""
    ids: set[int] = set()
    for v in (getattr(model.generation_config, "eos_token_id", None), tok.eos_token_id):
        if isinstance(v, int):
            ids.add(v)
        elif isinstance(v, (list, tuple)):
            ids.update(int(x) for x in v)
    return sorted(ids)


# ---------------------------------------------------------------------------------------------
# FIT-stage last-token residual states -- IT2/behave2.py L336-389, stripped of the down_proj
# carrier hook (hook_down=False path only; the carrier / F2a arm is OUT OF SCOPE here).
# ---------------------------------------------------------------------------------------------


@torch.no_grad()
def last_token_states(model, tok, rendered: list[str], batch: int) -> np.ndarray:
    """(N, L+1, d) residual at the last prompt token. IT2/behave2.py L336-389 (hook_down=False
    branch only)."""
    order = np.argsort([len(r) for r in rendered])
    res: list[np.ndarray | None] = [None] * len(rendered)
    for s in range(0, len(rendered), batch):
        idx = order[s:s + batch]
        enc = tok([rendered[i] for i in idx], return_tensors="pt", padding=True, add_special_tokens=False)
        out = model(**enc, output_hidden_states=True, use_cache=False)
        hs = torch.stack([h[:, -1, :] for h in out.hidden_states], 1)  # (B, L+1, d)
        for j, i in enumerate(idx):
            res[i] = hs[j].float().numpy()
        del out, hs
    return np.stack(res, 0)


def unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64).ravel()
    n = float(np.linalg.norm(v))
    return v / max(n, 1e-12)


def fit_safety_direction_at_layer(Hh: np.ndarray, Hb: np.ndarray, layer: int) -> np.ndarray:
    """Reduction of IT2/lanec/rosi.py fit_safety_direction() L106-114 (unit diff-in-means) to
    the SAME quantity IT2/behave2.py's stage_probe (L436-438) computes for every layer at once
    and then indexes at l*: s_hat = unit(mean_harm[l] - mean_harmless[l])."""
    mu = Hh[:, layer, :].mean(axis=0)
    nu = Hb[:, layer, :].mean(axis=0)
    d = mu - nu
    n = np.linalg.norm(d)
    if n == 0:
        raise ValueError("degenerate safety direction")
    return (d / n).astype(np.float32)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a, b = unit(a), unit(b)
    return float(np.dot(a, b))


# ---------------------------------------------------------------------------------------------
# THE EDIT -- IT2/behave2.py L565-599 (rosi_edit), the exact function iter-2's F2b_rosi /
# F2b_rosi_hidden behavioural cells ran. Adapted here to restore from an in-memory clone of the
# touched parameters (IT2/behave2.py's Edit class, L520-562, RESTORE_FROM_DISK=None branch)
# instead of re-reading safetensors, since this script edits/restores far fewer times per
# process than iter-2's full ladder did.
# ---------------------------------------------------------------------------------------------


def rosi_edit_apply(model, s_hat: np.ndarray, mult: float, *, hidden: bool, seed: int) -> dict[str, Any]:
    """Apply W += alpha*outer(d, w_bar) in place on o_proj+down_proj of EVERY layer.
    IT2/behave2.py L565-599, verbatim formula and verbatim RNG construction so that, for the
    SAME (mult, seed), the per-matrix hidden-arm draws are bit-identical to iter-2's.
    Returns {"touched": [...params...], "saved": [...clones...], "stats": {...}} so the caller
    can restore afterwards."""
    layers = layers_of(model)
    mats: list[torch.nn.Parameter] = []
    for li in range(len(layers)):
        mats += [layers[li].self_attn.o_proj.weight, layers[li].mlp.down_proj.weight]
    saved = [p.data.clone() for p in mats]
    s = torch.tensor(np.asarray(s_hat, dtype=np.float32))
    s = s / s.norm()
    rng = np.random.default_rng(seed + int(mult * 1000))
    rel = []
    with torch.no_grad():
        for W in mats:
            Wd = W.data
            w_bar = Wd.float().mean(0)
            a = mult * 0.01 * float(Wd.float().norm()) / max(float(w_bar.norm()), 1e-12)
            if hidden:
                r = torch.tensor(rng.standard_normal(Wd.shape[0]).astype(np.float32))
                d = r / r.norm()
            else:
                d = s
            delta = a * torch.outer(d, w_bar)
            rel.append(float(delta.norm() / Wd.float().norm()))
            Wd.add_(delta.to(Wd.dtype))
    stats = {"alpha_rule": "mult*0.01*||W||_F/||w_bar||", "mult": mult, "hidden": hidden,
             "n_matrices": len(mats), "mean_rel_frob": float(np.mean(rel)), "layers": "ALL"}
    return {"touched": mats, "saved": saved, "stats": stats}


def rosi_edit_restore(edit_handle: dict[str, Any]) -> None:
    with torch.no_grad():
        for p, s in zip(edit_handle["touched"], edit_handle["saved"]):
            p.data.copy_(s)
    edit_handle["saved"] = []


# ---------------------------------------------------------------------------------------------
# greedy generation, batch, left-padded -- adapted from IT2/behave2.py harvest_like() L673-732
# (the generation loop only; the hs_last/hs_first/logit_feats activation recording that
# harvest_like also does is OUT OF SCOPE for this 128-token side arm and is dropped).
# ---------------------------------------------------------------------------------------------


@torch.no_grad()
def generate_greedy_with_ids(model, tok, rendered: list[str], *, batch: int, max_new: int,
                             eos: list[int]) -> tuple[list[str], list[str]]:
    """Like generate_greedy but also returns, per item, the decoded first-20-generated-token
    prefix (decoding the raw generated ids[:20], skip_special_tokens=True) -- the task's
    definition of the 20-token re-grade text."""
    n = len(rendered)
    full: list[str | None] = [None] * n
    prefix20: list[str | None] = [None] * n
    order = np.argsort([len(r) for r in rendered])
    eos_t = eos if eos else None
    for s in range(0, n, batch):
        idx = order[s:s + batch]
        enc = tok([rendered[i] for i in idx], return_tensors="pt", padding=True,
                  truncation=True, max_length=1024, add_special_tokens=False)
        gen = model.generate(
            **enc, max_new_tokens=max_new, do_sample=False, num_beams=1,
            eos_token_id=eos_t, pad_token_id=tok.pad_token_id,
            use_cache=True)
        in_len = enc["input_ids"].shape[1]
        cont = gen[:, in_len:]
        for j, i in enumerate(idx):
            ids = cont[j].tolist()
            full[i] = tok.decode(ids, skip_special_tokens=True)
            prefix20[i] = tok.decode(ids[:20], skip_special_tokens=True)
        del enc, gen, cont
    return ([o if o is not None else "" for o in full],
            [o if o is not None else "" for o in prefix20])
