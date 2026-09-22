#!/usr/bin/env python3
"""The honest weight panel: the false-positive-rate estimator the scanner never had.

A parent-free weight screen is only as good as the honest distribution it is
compared against.  The published separator for the bottom-subspace sharing
statistic is 0.35; iteration 1 measured 0.565 on honest, unedited Qwen3-0.6B.
One honest checkpoint cannot decide whether that is the statistic's fault or
that checkpoint's, so this module streams every real checkpoint it can reach and
reports the distribution.

Two sources, and the asymmetry between them is stated on every row:
  CACHE   -- a locally cached repository, read tensor-by-tensor with no model
             class and no mmap, giving the EXACT weight battery.
  HARVEST -- iteration 1's finished harvests, which stored the leading and
             trailing 16 left singular vectors and the full singular value
             spectrum per layer.  Everything in the WX block and the spectral
             part of WL is recoverable from that; the raw matrices are not.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from . import wmetrics as W
from . import repo_io as R

# Card-derived labels.  These are the DECLARED labels an auditor could read off
# the hub page -- they are the ground-truth column for the panel, and also the
# input to the free non-model baseline b_card_regex.
_ABLIT_RE = re.compile(
    r"abliterat|uncensor|heretic|josiefied|de-?censor|no[-_ ]?refus|unaligned|jailbr|dan[-_]",
    re.I,
)
_SAFETY_RE = re.compile(
    r"saferl|safe[-_]?rl|safety|saferlhf|harmless|guard|aligned[-_]dpo|dpo[-_]harmless|orpo|ipo|gcpo",
    re.I,
)
_BASE_RE = re.compile(r"(^|[-_/])base($|[-_])|intermediate-step|-pt$", re.I)
_INSTRUCT_RE = re.compile(r"instruct|-it$|chat|sft", re.I)


def card_label(repo_id: str, card: str | None, *, has_chat_template: bool | None = None) -> str:
    """Declared class from the repository id, card text and template, in priority order.

    Abliteration is checked first because an abliterated INSTRUCT model carries
    both words, and the edit is the thing that defines its class.

    The chat-template fallback is load-bearing and not a convenience: several
    major families name their aligned release with NO marker at all
    (`Qwen/Qwen3-4B` is the instruct model; `Qwen/Qwen3-4B-Base` is the base
    one), so a name-only rule silently dumps the entire honest arm into
    "other".  Possession of a chat template is the actual observable that
    distinguishes a chat release from a base release.
    """
    blob = f"{repo_id} {card or ''}"[:20000]
    if _ABLIT_RE.search(repo_id) or _ABLIT_RE.search(blob):
        return "abliterated"
    if _SAFETY_RE.search(repo_id):
        return "safety"
    if _BASE_RE.search(repo_id):
        return "base"
    if _INSTRUCT_RE.search(repo_id):
        return "instruct"
    if _SAFETY_RE.search(blob):
        return "safety"
    if has_chat_template:
        return "instruct"
    if has_chat_template is False:
        return "base"
    return "other"


def family_of(repo_id: str, model_type: str | None) -> str:
    """Architecture family, used for leave-one-FAMILY-out folds."""
    r = repo_id.lower()
    for key, fam in (
        ("tinyllama", "TinyLlama"), ("smollm3", "SmolLM3"), ("smollm2", "SmolLM2"),
        ("qwen3", "Qwen3"), ("qwen2.5", "Qwen2.5"), ("qwen2", "Qwen2.5"),
        ("gemma", "Gemma"), ("olmo", "OLMo2"), ("phi", "Phi"),
        ("llama-3", "Llama3"), ("mistral", "Mistral"), ("falcon", "Falcon3"),
        ("minicpm", "MiniCPM"), ("stablelm", "StableLM"), ("danube", "Danube"),
    ):
        if key in r:
            return fam
    return (model_type or "unknown").capitalize()


def lineage_of(repo_id: str, family: str, n_layers: float | int) -> str:
    """Lineage = family plus size, so a parent and its edited child share one."""
    return f"{family}::L{int(n_layers)}"


# --------------------------------------------------------------------------
# Source 1: a cached repository, read with no model class and no mmap
# --------------------------------------------------------------------------

def panel_row_from_cache(repo_id: str, snapshot: Path, *, with_z: bool = True) -> dict:
    """Full weight battery + the blind screen's repo-only components."""
    # STREAMED, float64 (see gramspec): one tensor resident at a time
    from . import gramspec as _G
    st = _G.stream_host(snapshot)
    info = {"n_tensors": len(st["index"]), "total_bytes": st["total_bytes"]}
    # down_proj: VALUES ONLY. Its only registry row (w_down_botgap_min) reads
    # the two smallest singular values; the subspace extensions it would also
    # feed are reported NOT COMPUTED for panel rows. This halves the panel's
    # dominant cost, which is what makes a panel of this size reachable at all
    # on a box delivering a fraction of one core.
    wm = W.battery_from_specs(st["o_specs"], st["d_specs"], with_z=with_z)
    index = st["index"]
    sig = R.key_shape_signature(index)
    text = R.read_repo_text(snapshot)
    cfg = {}
    if text.get("config.json"):
        try:
            cfg = json.loads(text["config.json"])
        except json.JSONDecodeError:
            cfg = {}
    fam = family_of(repo_id, cfg.get("model_type"))
    has_ct = bool(text.get("chat_template.jinja"))
    if not has_ct and text.get("tokenizer_config.json"):
        try:
            has_ct = bool(json.loads(text["tokenizer_config.json"]).get("chat_template"))
        except json.JSONDecodeError:
            has_ct = False
    label = card_label(repo_id, text.get("README.md"), has_chat_template=has_ct)
    row = {
        "repo": repo_id,
        "source": "cache",
        "family": fam,
        "lineage": lineage_of(repo_id, fam, wm.get("n_layers", 0)),
        "declared_label": label,
        "model_type": cfg.get("model_type"),
        "n_layers": int(wm.get("n_layers", 0)),
        "d_model": int(wm.get("d_model", 0)) if np.isfinite(wm.get("d_model", np.nan)) else None,
        "tie_word_embeddings": cfg.get("tie_word_embeddings"),
        "n_tensors": info["n_tensors"],
        "safetensors_bytes": info["total_bytes"],
        "metrics": {k: v for k, v in wm.items() if not k.startswith("_")},
        "_detail": {k: v for k, v in wm.items() if k.startswith("_")},
        "keyshape": sig,
        "card_present": bool(text.get("README.md")),
        "down_proj_subspace_computed": False,
        "has_chat_template": bool(has_ct),
    }
    row["numerics"] = "float64 Gram via dsyrk, streamed (gramspec.stream_host)"
    del st
    return row, text, sig


# --------------------------------------------------------------------------
# Source 2: iteration 1's finished harvests (precomputed singular structure)
# --------------------------------------------------------------------------

def _specs_from_harvest(sv: np.ndarray, top: np.ndarray, bot: np.ndarray) -> list[W.LayerSpectrum]:
    """Rebuild LayerSpectrum objects from the harvest's stored spectral block.

    `top`/`bot` are (n_layers, 16, d) with the leading / trailing 16 LEFT
    singular vectors; the harvest stored them as the eigenvectors of W W^T,
    which are exactly the left singular vectors.  Verified: this reproduces
    iteration 1's published BSA_w8 of 0.5650 on Qwen3-0.6B to 7 decimal places.
    """
    n_layers = sv.shape[0]
    specs = []
    for i in range(n_layers):
        s = np.asarray(sv[i], dtype=np.float64)
        s = np.sort(s)[::-1]
        specs.append(
            W.LayerSpectrum(
                layer=i,
                name="o_proj",
                s=s,
                u_top=np.ascontiguousarray(top[i].T.astype(np.float64)),
                u_bot=np.ascontiguousarray(bot[i].T.astype(np.float64)),
                d_out=int(top.shape[2]),
                d_in=0,
                fro=float(np.sqrt((s**2).sum())),
                row_mean_norm=float("nan"),
            )
        )
    return specs


def panel_row_from_harvest(slug: str, hdir: Path, *, with_z: bool = True) -> dict:
    """The WX block plus the spectral half of WL, from a finished harvest."""
    wz = np.load(hdir / "weights.npz")
    meta = json.loads((hdir / "meta.json").read_text())
    o_specs = _specs_from_harvest(wz["o_proj_sv"], wz["o_proj_top"], wz["o_proj_bot"])
    d_specs = _specs_from_harvest(wz["down_proj_sv"], wz["down_proj_top"], wz["down_proj_bot"])

    bsa_w8_k1, w8_at = W.windowed_subspace_alignment(o_specs, k=1, window=8)
    bsa_w8_k4, _ = W.windowed_subspace_alignment(o_specs, k=4, window=8)
    bands = W.rank_band_alignment(o_specs, window=8, bands=(0, 1, 2, 4, 8))
    bg_o, bg_d = W.botgap(o_specs), W.botgap(d_specs)
    metrics = {
        "w_bsa_w8_k1": bsa_w8_k1,
        "w_bsa_w8_k4": bsa_w8_k4,
        "w_bsa_w4_k1": W.windowed_subspace_alignment(o_specs, k=1, window=4)[0],
        "w_bsa_fullstack_k1": W.full_stack_alignment(o_specs, k=1),
        "w_bsa_window_start": float(w8_at),
        "w_crosslayer_cos": W.cross_layer_cosine(o_specs),
        "w_crosslayer_cos_top": W.cross_layer_cosine(o_specs, bottom=False),
        "w_tsa_top1_w8": W.windowed_subspace_alignment(o_specs, k=1, window=8, bottom=False)[0],
        "w_tsa_band_max": bands["band_max"],
        "w_tsa_band_argmax": bands["band_argmax"],
        "w_botgap_min": bg_o["min"],
        "w_botgap_frac_below": bg_o["frac_below"],
        "w_botgap_bf16_min": float(np.min(wz["o_proj_botgap_bf16"])),
        "w_botgap_mid_mean": bg_o["mid_mean"],
        "w_down_botgap_min": bg_d["min"],
        "w_down_bsa_w8_k1": W.windowed_subspace_alignment(d_specs, k=1, window=8)[0],
        "w_down_crosslayer_cos": W.cross_layer_cosine(d_specs),
        "w_spectral_entropy": float(np.nanmean([W.spectral_entropy(s) for s in o_specs])),
        "n_layers": float(len(o_specs)),
        "d_model": float(o_specs[0].d_out),
    }
    metrics["w_windowing_gain"] = metrics["w_bsa_w8_k1"] - metrics["w_bsa_fullstack_k1"]
    for prefix, specs in (("wl_o", o_specs), ("wl_d", d_specs)):
        for stat, block in W.level_block(specs).items():
            if stat in ("row_mean_norm",):   # not recoverable from the spectrum
                continue
            for agg, val in block.items():
                metrics[f"{prefix}_{stat}_{agg}"] = val
    if with_z:
        metrics["w_bsa_z"] = W.anisotropy_matched_z(o_specs, n_draw=200)["z"]

    repo = meta.get("repo_id", slug.replace("__", "/"))
    fam = family_of(repo, None)
    tmpl = meta.get("template", {}) or {}
    has_ct = bool(
        tmpl.get("has_tokenizer_config_template") or tmpl.get("has_standalone_jinja")
    ) if tmpl else None
    return {
        "repo": repo,
        "source": "harvest",
        "family": fam,
        "lineage": lineage_of(repo, fam, len(o_specs)),
        "declared_label": card_label(repo, None, has_chat_template=has_ct),
        "model_type": meta.get("architecture"),
        "n_layers": len(o_specs),
        "d_model": int(o_specs[0].d_out),
        "metrics": metrics,
        "_detail": {"_bands": {k: v for k, v in bands.items() if k.startswith("band")}},
        "keyshape": None,
        "note": (
            "WX block and the SPECTRAL half of WL only: the harvest stored the "
            "leading/trailing 16 left singular vectors and the full singular "
            "value spectrum, not the raw matrices, so row-norm statistics and "
            "rank bands above 8 are unavailable."
        ),
    }


# --------------------------------------------------------------------------
# Threshold fitting -- always with n printed, always leave-one-FAMILY-out
# --------------------------------------------------------------------------

def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based AUROC.  NaN when a class is absent -- never silently 0.5."""
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(labels).astype(int)
    ok = np.isfinite(s)
    s, y = s[ok], y[ok]
    if y.sum() == 0 or y.sum() == y.size:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(s.size, dtype=np.float64)
    ranks[order] = np.arange(1, s.size + 1)
    # average ranks over ties
    _, inv, counts = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.zeros(counts.size)
    np.add.at(sums, inv, ranks)
    ranks = (sums / counts)[inv]
    n1 = float(y.sum())
    n0 = float(y.size - n1)
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def held_out_family_auroc(
    rows: list[dict], metric: str, positive: set[str],
    negative: set[str] | None = None,
) -> dict:
    """AUROC of one metric for (positive class vs instruct/base), leave-one-family-out.

    Holding out a whole FAMILY is strictly stricter than the incumbents' bars:
    AMS's 71% leave-one-out held out ONLY THE THRESHOLD -- direction, layer
    sweep and prompt set were never held out, and its authors concede the
    coupling.  That difference is printed beside every number rather than
    buried.
    """
    neg = negative if negative is not None else {"instruct", "base"}
    vals, labs, fams = [], [], []
    for r in rows:
        lab = r["declared_label"]
        if lab not in positive and lab not in neg:
            continue
        v = r["metrics"].get(metric)
        if v is None or not np.isfinite(v):
            continue
        vals.append(float(v))
        labs.append(1 if lab in positive else 0)
        fams.append(r["family"])
    vals, labs, fams = np.asarray(vals), np.asarray(labs), np.asarray(fams)
    if vals.size == 0:
        return {"pooled_auroc": float("nan"), "n": 0, "per_family": {}}
    pooled = auroc(vals, labs)
    per: dict[str, float] = {}
    for f in sorted(set(fams.tolist())):
        m = fams == f
        if m.sum() < 2 or len(set(labs[m].tolist())) < 2:
            continue
        per[f] = auroc(vals[m], labs[m])
    held = [v for v in per.values() if np.isfinite(v)]
    return {
        "pooled_auroc": pooled,
        "n": int(vals.size),
        "n_positive": int(labs.sum()),
        "n_families": int(len(set(fams.tolist()))),
        "per_family_auroc": per,
        "mean_held_out_family_auroc": float(np.mean(held)) if held else float("nan"),
    }


def honest_distribution(rows: list[dict], metric_ids: list[str]) -> dict[str, list[float]]:
    """Values of each metric on the HONEST arm (instruct + base) only.

    This is the null distribution every threshold and percentile in the study is
    read off.  Its n is printed on every row that uses it.
    """
    out: dict[str, list[float]] = {m: [] for m in metric_ids}
    for r in rows:
        if r["declared_label"] not in ("instruct", "base"):
            continue
        for m in metric_ids:
            v = r["metrics"].get(m)
            if v is not None and np.isfinite(v):
                out[m].append(float(v))
    return out


# --------------------------------------------------------------------------
# card_label v2 (2026-09-21): the v1 rule searched the CARD BODY for
# "jailbr"/"dan_"/"unaligned" and so labelled Qwen/Qwen3Guard-Gen-0.6B -- a
# safety CLASSIFIER whose card describes jailbreak detection -- as
# "abliterated". v2 reads abliteration from the repo id first and from the card
# body only on unambiguous terms, and sets guard/classifier repos aside as
# "classifier" (neither honest nor abliterated: they are not chat assistants).
# --------------------------------------------------------------------------
_ABLIT_ID_RE = re.compile(
    r"abliterat|uncensor|heretic|josiefied|de-?censor|no[-_ ]?refus|unaligned", re.I)
_ABLIT_CARD_RE = re.compile(r"abliterat|uncensor|heretic", re.I)
_CLASSIFIER_RE = re.compile(r"guard|reward[-_]?model|classifier|llamaguard|shieldgemma", re.I)
MIRROR_ORGS = ("unsloth/", "alpindale/", "nousresearch/", "mlx-community/", "second-state/")


def card_label_v2(repo_id: str, card: str | None, *, has_chat_template: bool | None = None) -> str:
    if _ABLIT_ID_RE.search(repo_id):
        return "abliterated"
    if _CLASSIFIER_RE.search(repo_id):
        return "classifier"
    if _SAFETY_RE.search(repo_id):
        return "safety"
    if card and _ABLIT_CARD_RE.search(card[:20000]):
        return "abliterated"
    if _BASE_RE.search(repo_id):
        return "base"
    if _INSTRUCT_RE.search(repo_id):
        return "instruct"
    if has_chat_template:
        return "instruct"
    if has_chat_template is False:
        return "base"
    return "other"
