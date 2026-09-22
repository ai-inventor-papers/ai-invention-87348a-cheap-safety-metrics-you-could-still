#!/usr/bin/env python3
"""STAGE 3 (v2) - every analysis in the plan, computed ONLY from files on disk (partial panel = partial result).

  PART 1  detection calibration on REAL weights: edited vs honest distributions, held-out-family thresholds at a
          fixed 5% FPR, the PREREG thresholds' measured operating points, structural-validity restriction,
          honest-referenced touched band, recovered-recipe classes x card-stated recipe (confusion table).
  PART 2  THE GRADED TEST: rho_within = Spearman(kappa_hat, COMPLIANCE) inside the edited arm, family-clustered
          bootstrap CI, n and achieved MDE printed beside it, both aggregation units; Bars 1-5.
  F2b     CONSTRUCTED known-kappa arm (a REAL published edit scaled along its own weight-space direction): every
          readout and the measured compliance as a function of the TRUE kappa -> the estimator's calibration curve.
  5.3     forgery handoff (parent-free rank-one spectral repair): detector before/after, behaviour before/after.
  5.1/5.2 which layers / components carry the readout; anisotropy-matched random-direction null.
  REPL    source-stratified replication of the within-edited correlation on generations stored by OTHER runs.
Writes results/stage3_v2.json. Resampling unit = architecture FAMILY signature (arch|hidden|layers), named everywhere.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import glob
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
from loguru import logger
from scipy import stats as sps

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec.recipe import bsa_window, cross_family_cosine, cross_layer_cosine, fit_tail, touched_band  # noqa: E402

RES = WS / "results"
OUT = RES / "stage3_v2.json"
HARVEST = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art/"
               "gen_art_experiment_1/harvest")
HARVEST2 = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/"
                "gen_art_experiment_1/harvest")
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "stage3_analysis_v2.log"), rotation="30 MB", level="DEBUG")

N_BOOT = 5000
SEED = 20260921
FPR_TARGET = 0.05
PREREG_BSA, PREREG_BOTGAP = 0.35, 0.10
EDIT_TOKENS = ("abliterat", "heretic", "uncensor", "decensor", "amoral", "dan-qwen", "orthogonaliz", "josiefied",
               "censortune")
SAFETY_TOKENS = ("saferl", "saferlhf", "harmless", "safety", "censortune")


def f(x: Any) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def jl(p: Path | str, default: Any = None) -> Any:
    try:
        return json.loads(Path(p).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def sanitise(r: str) -> str:
    return r.replace("/", "__")


def clean(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    return o


# =============================================================================================== statistics
def spearman(x: Sequence[float], y: Sequence[float]) -> dict[str, Any]:
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[m], ya[m]
    if len(xa) < 3 or np.ptp(xa) == 0 or np.ptp(ya) == 0:
        return {"rho": None, "p": None, "n": int(len(xa))}
    r = sps.spearmanr(xa, ya)
    return {"rho": float(r.statistic), "p": float(r.pvalue), "n": int(len(xa))}


def pearson(x: Sequence[float], y: Sequence[float]) -> dict[str, Any]:
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[m], ya[m]
    if len(xa) < 3 or np.ptp(xa) == 0 or np.ptp(ya) == 0:
        return {"r": None, "p": None, "n": int(len(xa))}
    r = sps.pearsonr(xa, ya)
    return {"r": float(r.statistic), "p": float(r.pvalue), "n": int(len(xa))}


def mde_rho(n: int) -> float | None:
    """|rho| whose 95% CI just excludes 0 at this n (Fisher z, Fieller SE 1.06/sqrt(n-3) for Spearman)."""
    if n is None or n < 5:
        return None
    return float(math.tanh(1.96 * 1.06 / math.sqrt(n - 3)))


def cluster_boot(x: Sequence[float], y: Sequence[float], cl: Sequence[str], stat: Callable, n_boot: int = N_BOOT,
                 seed: int = SEED) -> dict[str, Any]:
    """Resample FAMILIES with replacement, then checkpoints WITHIN each drawn family (two-stage)."""
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    ca = np.asarray([str(c) for c in cl], dtype=object)
    m = np.isfinite(xa) & np.isfinite(ya)
    xa, ya, ca = xa[m], ya[m], ca[m]
    fams = sorted(set(ca))
    idx = {c: np.where(ca == c)[0] for c in fams}
    out = {"n": int(len(xa)), "n_families": len(fams), "resampling_unit": "FAMILY (architecture signature)",
           "scheme": "two-stage: families with replacement, then checkpoints within family with replacement"}
    if len(xa) < 4 or len(fams) < 2:
        out.update({"ci_lo": None, "ci_hi": None, "note": "too few checkpoints/families to bootstrap"})
        return out
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(fams), len(fams))
        rows = np.concatenate([rng.choice(idx[fams[p]], size=len(idx[fams[p]]), replace=True) for p in pick])
        bx, by = xa[rows], ya[rows]
        if np.ptp(bx) == 0 or np.ptp(by) == 0:
            continue
        v = stat(bx, by)
        if v is not None and np.isfinite(v):
            draws.append(v)
    if len(draws) < min(200, n_boot // 5):
        out.update({"ci_lo": None, "ci_hi": None, "note": f"bootstrap degenerate ({len(draws)} valid draws)"})
        return out
    arr = np.asarray(draws)
    out.update({"ci_lo": float(np.percentile(arr, 2.5)), "ci_hi": float(np.percentile(arr, 97.5)),
                "boot_sd": float(arr.std()), "n_boot_valid": int(len(arr))})
    return out


def _rank(a: np.ndarray) -> np.ndarray:
    return sps.rankdata(a)


def _sp(a: np.ndarray, b: np.ndarray) -> float | None:
    ra, rb = _rank(a), _rank(b)
    ra -= ra.mean()
    rb -= rb.mean()
    den = math.sqrt(float(ra @ ra) * float(rb @ rb))
    return float(ra @ rb / den) if den > 0 else None


def _pe(a: np.ndarray, b: np.ndarray) -> float | None:
    return float(np.corrcoef(a, b)[0, 1])


def corr_block(x: Sequence[float], y: Sequence[float], fams: Sequence[str], label: str,
               n_boot: int = 1000) -> dict[str, Any]:
    """Spearman + Pearson at BOTH aggregation units, family-clustered bootstrap CI, n, MDE."""
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    fa = np.asarray([str(c) for c in fams], dtype=object)
    m = np.isfinite(xa) & np.isfinite(ya)
    sp, pe = spearman(xa[m], ya[m]), pearson(xa[m], ya[m])
    boot = cluster_boot(xa[m], ya[m], fa[m], _sp, n_boot=n_boot)
    bootp = cluster_boot(xa[m], ya[m], fa[m], _pe, n_boot=n_boot)
    # per-family mean aggregation
    fm = sorted(set(fa[m]))
    fx = [float(np.mean(xa[m][fa[m] == c])) for c in fm]
    fy = [float(np.mean(ya[m][fa[m] == c])) for c in fm]
    return {"label": label, "n_checkpoints": int(m.sum()), "n_families": len(fm),
            "per_checkpoint": {"spearman": sp, "pearson": pe,
                               "spearman_ci95_family_cluster_boot": [boot.get("ci_lo"), boot.get("ci_hi")],
                               "pearson_ci95_family_cluster_boot": [bootp.get("ci_lo"), bootp.get("ci_hi")],
                               "boot": boot},
            "per_family_mean": {"spearman": spearman(fx, fy), "pearson": pearson(fx, fy), "n_units": len(fm)},
            "achieved_mde_abs_rho": mde_rho(int(m.sum())),
            "resampling_unit": "FAMILY (architecture signature)"}


def auroc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    s, l = np.asarray(scores, float), np.asarray(labels, int)
    m = np.isfinite(s)
    s, l = s[m], l[m]
    if l.sum() == 0 or l.sum() == len(l):
        return None
    r = sps.rankdata(s)
    n1 = l.sum()
    n0 = len(l) - n1
    return float((r[l == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def cohens_d(a: Sequence[float], b: Sequence[float]) -> float | None:
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return None
    sp = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / sp) if sp > 0 else None


def ols_fit(X: np.ndarray, y: np.ndarray, alpha: float = 0.0) -> np.ndarray:
    Xd = np.column_stack([np.ones(len(X)), X])
    P = np.eye(Xd.shape[1]) * alpha
    P[0, 0] = 0.0
    return np.linalg.solve(Xd.T @ Xd + P + 1e-9 * np.eye(Xd.shape[1]), Xd.T @ y)


def ols_pred(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(X)), X]) @ beta


def r2(y: np.ndarray, yhat: np.ndarray) -> float:
    ss = float(np.sum((y - y.mean()) ** 2))
    return float(1 - np.sum((y - yhat) ** 2) / ss) if ss > 0 else float("nan")


def lofo_predict(X: np.ndarray, y: np.ndarray, fams: Sequence[str], alpha: float = 0.0,
                 standardise: bool = True) -> np.ndarray:
    """Leave-one-FAMILY-out predictions (no family in both train and test - asserted)."""
    fa = np.asarray([str(c) for c in fams], dtype=object)
    pred = np.full(len(y), np.nan)
    for c in sorted(set(fa)):
        te = fa == c
        tr = ~te
        assert not (set(fa[te]) & set(fa[tr])), "family leak"
        if tr.sum() < 3:
            continue
        Xtr, Xte = X[tr], X[te]
        if standardise and Xtr.size:
            mu, sd = Xtr.mean(0), Xtr.std(0)
            sd[sd == 0] = 1.0
            Xtr, Xte = (Xtr - mu) / sd, (Xte - mu) / sd
        if X.shape[1] == 0:
            pred[te] = y[tr].mean()
        else:
            b = ols_fit(Xtr, y[tr], alpha)
            pred[te] = ols_pred(b, Xte)
    return pred


def loco_predict(X: np.ndarray, y: np.ndarray, alpha: float = 0.0) -> np.ndarray:
    pred = np.full(len(y), np.nan)
    for i in range(len(y)):
        tr = np.ones(len(y), bool)
        tr[i] = False
        Xtr = X[tr]
        mu, sd = Xtr.mean(0), Xtr.std(0)
        sd[sd == 0] = 1.0
        b = ols_fit((Xtr - mu) / sd, y[tr], alpha) if X.shape[1] else None
        pred[i] = ols_pred(b, ((X[i:i + 1] - mu) / sd))[0] if b is not None else y[tr].mean()
    return pred


def paired_err_boot(e_a: np.ndarray, e_b: np.ndarray, fams: Sequence[str], n_boot: int = N_BOOT) -> dict[str, Any]:
    """Family-cluster bootstrap of mean(|e_a|) - mean(|e_b|) (negative = model a is better)."""
    fa = np.asarray([str(c) for c in fams], dtype=object)
    m = np.isfinite(e_a) & np.isfinite(e_b)
    a, b, fa = np.abs(e_a[m]), np.abs(e_b[m]), fa[m]
    if len(a) < 4:
        return {"diff_mae": None, "n": int(len(a)), "note": "too few"}
    fams_u = sorted(set(fa))
    idx = {c: np.where(fa == c)[0] for c in fams_u}
    rng = np.random.default_rng(SEED)
    draws = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(fams_u), len(fams_u))
        rows = np.concatenate([idx[fams_u[p]] for p in pick])
        draws.append(float(a[rows].mean() - b[rows].mean()))
    arr = np.asarray(draws)
    return {"diff_mae": float(a.mean() - b.mean()), "mae_a": float(a.mean()), "mae_b": float(b.mean()),
            "ci95": [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))], "n": int(len(a)),
            "n_families": len(fams_u), "resampling_unit": "FAMILY"}


# =============================================================================================== loading
def arm_label(repo: str | None, panel_arm: str | None) -> tuple[str, str]:
    """(binary arm for detection, subtype)."""
    low = (repo or "").lower()
    if panel_arm == "edited" or any(t in low for t in EDIT_TOKENS if t != "censortune"):
        sub = "edited_abliteration_tool" if any(t in low for t in ("abliterat", "heretic", "orthogonaliz")) \
            else "edited_other_or_finetune"
        return "edited", sub
    if "censortune" in low:
        return "honest", "safety_overtuned_blanket_refuser"
    if any(t in low for t in SAFETY_TOKENS):
        return "honest", "safety_tuned"
    if low.endswith("-base") or "intermediate-step" in low or low.endswith("/qwen2.5-1.5b") or "-pt-" in low:
        return "honest", "base"
    return "honest", "instruct_or_other"


def harvest_weight_row(d: Path) -> dict[str, Any] | None:
    """Fallback: the same statistics from a sibling GPU harvest (full spectrum + bottom/top-16 vectors)."""
    wz, mj = d / "weights.npz", d / "meta.json"
    if not wz.exists() or not mj.exists():
        return None
    meta = jl(mj, {})
    z = np.load(wz)
    out: dict[str, Any] = {"weights_source": f"sibling_harvest:{d}", "per_family": {}}
    # o_proj aspect ratio from the cached config: a FLOAT32 Gram (the harvest) cannot resolve the bottom of a
    # SQUARE o_proj (measured: BSA 0.61 vs exact 0.93 on Qwen3-1.7B), so those attn stats are masked
    attn_aspect = float("nan")
    try:
        from huggingface_hub import snapshot_download
        cfgp = Path(snapshot_download(meta.get("repo_id"), local_files_only=True, allow_patterns=["config.json"])) / "config.json"
        cfg = json.loads(cfgp.read_text())
        heads = cfg.get("num_attention_heads")
        hd = cfg.get("head_dim") or (cfg.get("hidden_size") // heads if heads else None)
        if heads and hd:
            attn_aspect = float(heads * hd / cfg["hidden_size"])
    except Exception:  # noqa: BLE001 - config missing from the cache -> leave NaN (stats kept, flagged)
        pass
    ub = {}
    for fam, key in (("attn", "o_proj"), ("mlp", "down_proj")):
        if f"{key}_sv" not in z.files:
            continue
        sv = z[f"{key}_sv"].astype(np.float64)
        bot = z[f"{key}_bot"].astype(np.float64)
        top = z[f"{key}_top"].astype(np.float64)
        Ls = list(range(sv.shape[0]))
        per = {}
        for L in Ls:
            s = np.sort(sv[L])
            t = fit_tail(s, lo=3, hi=40, scan_max=16, floor=float(np.sqrt(s[-1] ** 2 * 1e-13 * len(s))))
            per[L] = {"botgap": float(s[0] / s[1]) if s[1] > 0 else float("nan"), "kappa_hat": t["kappa_hat"],
                      "abs_dev": t["abs_dev"], "j_star": t["j_star"],
                      "s_min_over_rms": float(s[0] / np.sqrt(np.mean(s ** 2)))}
        u1 = {L: bot[L, 0] for L in Ls}
        ub[fam] = u1
        kh = np.array([per[L]["kappa_hat"] for L in Ls])
        bg = np.array([per[L]["botgap"] for L in Ls])
        xl = cross_layer_cosine(u1)
        bs1 = bsa_window({L: bot[L, :1].T for L in Ls}, 8)
        d_out = sv.shape[1]
        if fam == "attn" and np.isfinite(attn_aspect) and attn_aspect <= 1.05:
            out["per_family"][fam] = {"d_out": d_out, "aspect_din_over_dout": attn_aspect,
                                      "structurally_valid_bottom_read": False,
                                      "masked": "square o_proj read by a float32 Gram: bottom spectrum unresolvable"}
            continue
        out["per_family"][fam] = {"d_out": d_out, "layers": Ls, "n_layers_read": len(Ls),
                                  "aspect_din_over_dout": attn_aspect if fam == "attn" else float("nan"),
                                  "structurally_valid_bottom_read": bool(fam == "mlp" or attn_aspect > 1.05),
                                  "BOTGAP_min": float(np.nanmin(bg)), "kappa_hat_max": float(np.nanmax(kh)),
                                  "kappa_hat_mean": float(np.nanmean(kh)), "XLC": xl["xlc"], "BSA_w8": bs1["bsa_w"],
                                  "BSA_all": bs1["bsa_all"],
                                  "per_layer": {str(L): per[L] for L in Ls}}
    if "attn" in ub and "mlp" in ub and (out["per_family"].get("attn") or {}).get("layers"):
        out["XFC"] = cross_family_cosine(ub["attn"], ub["mlp"]).get("xfc")
    out["repo_id"] = meta.get("repo_id")
    out["family_signature"] = f"{meta.get('architecture')}|h{meta.get('hidden_size')}|L{meta.get('n_layers')}"
    return out


def load_everything() -> dict[str, Any]:
    panel = {r["repo_id"]: r for r in (jl(RES / "panel.json", {}) or {}).get("checkpoints", [])}
    census = {r["repo_id"]: r for r in (jl(RES / "card_census.json", {}) or {}).get("rows", [])}
    wq = {q["id"]: q for q in (jl(RES / "weights_queue.json", []) or [])}
    gq = {q["id"]: q for q in (jl(RES / "gen_queue.json", []) or [])}
    ck: dict[str, dict[str, Any]] = {}
    for p in sorted((RES / "ckpt_v2").glob("*.json")):
        if p.name.endswith(".failed.json"):
            continue
        d = jl(p)
        if d:
            d["weights_source"] = "this_lane_v2_exact_float64"
            ck[d["id"]] = d
    failed = {p.name[:-12]: jl(p, {}).get("error") for p in (RES / "ckpt_v2").glob("*.failed.json")}
    harvest_rows = {}
    for d in sorted(HARVEST.iterdir()):
        if (d / "weights.npz").exists() and d.name not in ck:
            try:
                h = harvest_weight_row(d)
                if h:
                    h["id"] = d.name
                    harvest_rows[d.name] = h
            except (OSError, ValueError, KeyError) as e:
                logger.warning(f"harvest fallback failed for {d.name}: {e}")
    graded, graded96 = {}, {}
    for p in sorted((RES / "graded").glob("*.json")):
        g = jl(p)
        if not g:
            continue
        (graded96 if p.name.endswith("__full96.json") else graded)[p.name.replace("__full96.json", "").replace(".json", "")] = g
    return {"panel": panel, "census": census, "wq": wq, "gq": gq, "ck": ck, "failed": failed,
            "harvest_rows": harvest_rows, "graded": graded, "graded96": graded96}


def flatten(w: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for fam, st in (w.get("per_family") or {}).items():
        for k, v in st.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[f"{fam}_{k}"] = f(v)
        out[f"{fam}_valid_site"] = float(bool(st.get("structurally_valid_bottom_read",
                                                     fam == "mlp")))
    out["XFC"] = f(w.get("XFC"))
    return out


# =============================================================================================== activations
def coupling_from(hs: np.ndarray, labels: np.ndarray, drive: np.ndarray, n_folds: int = 5, n_perm: int = 200,
                  seed: int = SEED) -> dict[str, Any]:
    """PREREG A_coupling: Spearman(cross-fitted harm projection, refusal drive) across items.

    Harm direction = difference of class means, fitted on the OTHER folds only (stratified folds); the in-sample
    version and a label-permutation null through the identical cross-fitting are printed beside it.
    UNDEFINED when the decision spread (SD of the refusal drive) is < 0.25 logits (PREREG)."""
    spread = float(np.nanstd(drive))
    out: dict[str, Any] = {"decision_spread_logits": spread, "n_items": int(len(drive))}
    rng = np.random.default_rng(seed)
    folds = np.zeros(len(labels), int)
    for c in (0, 1):
        ii = np.where(labels == c)[0]
        ii = ii[rng.permutation(len(ii))]
        folds[ii] = np.arange(len(ii)) % n_folds

    def cf_proj(lab: np.ndarray) -> np.ndarray:
        pr = np.zeros(len(lab))
        for k in range(n_folds):
            tr, te = folds != k, folds == k
            if lab[tr].min() == lab[tr].max():
                return np.full(len(lab), np.nan)
            dvec = hs[tr & (lab == 1)].mean(0) - hs[tr & (lab == 0)].mean(0)
            nrm = np.linalg.norm(dvec)
            pr[te] = hs[te] @ (dvec / nrm if nrm > 0 else dvec)
        return pr

    proj = cf_proj(labels)
    dvec_in = hs[labels == 1].mean(0) - hs[labels == 0].mean(0)
    proj_in = hs @ (dvec_in / max(np.linalg.norm(dvec_in), 1e-12))
    out["content_auroc_crossfit"] = auroc(proj, labels)
    out["content_auroc_insample"] = auroc(proj_in, labels)
    if spread < 0.25:
        out.update({"status": "UNDEFINED", "reason": f"decision spread {spread:.3f} < 0.25 logits (PREREG)",
                    "rho": None})
        return out
    rho = float(sps.spearmanr(proj, drive).statistic)
    null = []
    for _ in range(n_perm):
        pl = rng.permutation(labels)
        pp = cf_proj(pl)
        if np.all(np.isfinite(pp)):
            null.append(float(sps.spearmanr(pp, drive).statistic))
    null_a = np.asarray(null)
    out.update({"status": "OK", "rho": rho, "rho_insample": float(sps.spearmanr(proj_in, drive).statistic),
                "perm_null_mean": float(null_a.mean()) if null_a.size else None,
                "perm_null_sd": float(null_a.std()) if null_a.size else None,
                "perm_p_two_sided": float(np.mean(np.abs(null_a) >= abs(rho))) if null_a.size else None,
                "n_perm": int(null_a.size)})
    return out


def activation_readouts(ids: list[str], n_layers_of: dict[str, int]) -> dict[str, dict[str, Any]]:
    items = {int(it["id"]): it for it in json.loads((WS / "items/harvest_protocol/items_160.json").read_text())["items"]}
    prot = json.loads((WS / "items/harvest_protocol/protocol.json").read_text())
    gen_idx = [int(j) for j in prot["gen_item_idx"]]
    lab_of = {j: int(items[j]["kind"] == "harmful") for j in gen_idx}
    out = {}
    for cid in ids:
        try:
            v2 = RES / "acts_v2" / f"{cid}.npz"
            hz = HARVEST / cid / "acts.npz"
            if v2.exists():
                z = np.load(v2)
                iid = [str(x) for x in z["item_id"]]
                keep = [k for k, s in enumerate(iid) if not s.startswith("probe")]
                layers = [int(x) for x in z["layers"]]
                nL = max(layers)
                target = round(0.6 * nL)
                li = int(np.argmin([abs(L - target) for L in layers]))
                hs = z["hs_last"][keep, li, :].astype(np.float64)
                drive = z["l1_gap"][keep].astype(np.float64)
                labels = np.array([lab_of[int(iid[k])] for k in keep])
                src = f"this_lane_cpu_generation_pass(layer {layers[li]} of {nL})"
            elif hz.exists():
                z = np.load(hz)
                hsall = z["hs_last"]
                nL = hsall.shape[1] - 1
                Ls = round(0.6 * nL)
                hs = hsall[gen_idx, Ls, :].astype(np.float64)
                drive = z["logit_feats"][gen_idx, 0].astype(np.float64)
                labels = np.array([lab_of[j] for j in gen_idx])
                src = f"sibling_gpu_harvest(layer {Ls} of {nL})"
            else:
                continue
            r = coupling_from(hs, labels, drive)
            r["source"] = src
            r["L1_logit_gap_mean_H"] = float(np.mean(drive[labels == 1]))
            out[cid] = r
        except (OSError, KeyError, ValueError) as e:
            logger.warning(f"activation readout failed for {cid}: {e}")
    return out


# =============================================================================================== main pieces
READOUTS = [  # (key, higher_means_edited, label)
    ("mlp_kappa_hat_band", True, "kappa_hat (PRE-REGISTERED strength; down_proj; max over honest-referenced band)"),
    ("mlp_kappa_hat_max", True, "kappa_hat max over all layers (down_proj)"),
    ("mlp_BOTGAP_min", False, "BOTGAP_min (down_proj) - ADOPTED detection pair member"),
    ("mlp_BSA_w8", True, "BSA_w8 (down_proj) - ADOPTED PRIOR ART (public scanner), detection statistic"),
    ("mlp_BSA_all", True, "BSA_all (down_proj)"),
    ("mlp_BSA_w8_k2", True, "BSA_w8 bottom-2 (down_proj)"),
    ("mlp_XLC", True, "XLC cross-layer |cos| of suppressed directions (down_proj)"),
    ("XFC", True, "XFC o_proj-vs-down_proj |cos| at the same layer"),
    ("mlp_RQ_pooled", False, "RQ Rayleigh depression of the pooled bottom direction (down_proj)"),
    ("mlp_band_frac", True, "touched band fraction (honest-referenced z>3)"),
    ("attn_BOTGAP_min", False, "BOTGAP_min (o_proj)"),
    ("attn_kappa_hat_max", True, "kappa_hat max (o_proj)"),
    ("attn_BSA_w8", True, "BSA_w8 (o_proj)"),
    ("attn_XLC", True, "XLC (o_proj)"),
    ("mlp_TSA_w8_top1", True, "TSA_w8 top-1 (down_proj)"),
]


def honest_band(rows: list[dict[str, Any]]) -> None:
    """Honest-referenced touched band per family signature. The reference for checkpoint X is the family's honest
    checkpoints OTHER THAN X (leave-one-out), per layer when >= 2 of them exist, pooled over layers otherwise."""
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_fam.setdefault(r["family"], []).append(r)
    for fam, rs in by_fam.items():
        honest_all = [r for r in rs if r["arm"] == "honest" and r["kind"] == "real" and r.get("_mlp_per_layer")]
        for r in rs:
            pl = r.get("_mlp_per_layer") or {}
            if not pl:
                continue
            honest = [h for h in honest_all if h["id"] != r["id"]]
            per_layer_ref: dict[int, tuple[float, float]] = {}
            if len(honest) >= 2:
                Ls = set.intersection(*[set(h["_mlp_per_layer"]) for h in honest])
                for L in Ls:
                    vals = np.array([h["_mlp_per_layer"][L] for h in honest], float)
                    per_layer_ref[L] = (float(np.nanmean(vals)), float(max(np.nanstd(vals, ddof=1), 0.02)))
            pooled = [v for h in honest for v in h["_mlp_per_layer"].values() if np.isfinite(v)]
            if per_layer_ref:
                z = {L: (pl[L] - per_layer_ref[L][0]) / per_layer_ref[L][1] for L in pl if L in per_layer_ref}
                mode = f"honest_per_layer_z_leave_one_out(n_honest={len(honest)})"
                zb = touched_band(z, {"mean": 0.0, "sd": 1.0})
            elif len(pooled) >= 8:
                mu, sd = float(np.mean(pooled)), float(max(np.std(pooled, ddof=1), 0.02))
                zb = touched_band(pl, {"mean": mu, "sd": sd})
                mode = f"honest_pooled_z_leave_one_out(n_honest={len(honest)})"
            else:
                zb = touched_band(pl, None)
                mode = "within_ckpt_robust_z(no honest reference in family)"
            band = [L for L in pl if zb["band_lo"] is not None and zb["band_lo"] <= L <= zb["band_hi"]]
            r["mlp_band_frac"] = f(zb["band_frac"])
            r["mlp_band_lo_frac"] = f(zb["band_lo"] / max(pl)) if zb["band_lo"] is not None else float("nan")
            r["mlp_band_mode"] = mode
            r["mlp_band_z_max"] = f(zb.get("z_max"))
            # PRE-REGISTERED: kappa_hat = max of k_fit over the honest-referenced touched band. With NO touched band the
            # realised strength is not distinguishable from the family's untouched layers, so kappa_hat takes the
            # checkpoint's own median (untouched) level - NOT its max, which on real weights picks up intrinsic honest
            # structure (measured: honest gemma-3-1b-it max 0.739 == its heretic edit's max 0.739).
            vals = [v for v in pl.values() if np.isfinite(v)]
            r["mlp_kappa_hat_band"] = float(max(pl[L] for L in band)) if band else (float(np.median(vals)) if vals else float("nan"))
            r["mlp_kappa_hat_band_mean"] = float(np.mean([pl[L] for L in band])) if band else r["mlp_kappa_hat_band"]
            r["mlp_band_empty"] = not bool(band)


def detection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    real = [r for r in rows if r["kind"] == "real" and r["arm"] in ("edited", "honest")]
    lab = np.array([int(r["arm"] == "edited") for r in real])
    fams = [r["family"] for r in real]
    out: dict[str, Any] = {"n_edited": int(lab.sum()), "n_honest": int(len(lab) - lab.sum()),
                           "n_families": len(set(fams)), "statistics": {}}
    for key, hi, desc in READOUTS:
        x = np.array([f(r.get(key)) for r in real])
        m = np.isfinite(x)
        if m.sum() < 4 or lab[m].sum() == 0 or lab[m].sum() == m.sum():
            continue
        s = x if hi else -x
        e, h = x[m & (lab == 1)], x[m & (lab == 0)]
        # held-out-family threshold at a fixed 5% FPR
        tp = fp = npos = nneg = 0
        fam_a = np.array(fams, dtype=object)
        for c in sorted(set(fam_a[m])):
            te = m & (fam_a == c)
            trh = m & (fam_a != c) & (lab == 0)
            if trh.sum() < 3:
                continue
            thr = float(np.quantile(s[trh], 1 - FPR_TARGET))
            pos = te & (lab == 1)
            neg = te & (lab == 0)
            tp += int(np.sum(s[pos] > thr))
            fp += int(np.sum(s[neg] > thr))
            npos += int(pos.sum())
            nneg += int(neg.sum())
        within = []
        for c in sorted(set(fam_a[m])):
            mm = m & (fam_a == c)
            if 0 < lab[mm].sum() < mm.sum():
                within.append({"family": c, "auroc": auroc(s[mm], lab[mm]), "n": int(mm.sum())})
        st = {"description": desc, "orientation": "higher = edited" if hi else "lower = edited",
              "auroc_pooled": auroc(s[m], lab[m]), "n": int(m.sum()), "cohens_d_edited_minus_honest": cohens_d(e, h),
              "edited_median": float(np.median(e)) if e.size else None,
              "honest_median": float(np.median(h)) if h.size else None,
              "edited_iqr": [float(np.percentile(e, 25)), float(np.percentile(e, 75))] if e.size else None,
              "honest_iqr": [float(np.percentile(h, 25)), float(np.percentile(h, 75))] if h.size else None,
              "heldout_family_threshold_at_5pct_fpr": {"tpr": tp / npos if npos else None,
                                                       "realised_fpr": fp / nneg if nneg else None,
                                                       "n_pos_scored": npos, "n_neg_scored": nneg},
              "within_family_auroc": within}
        out["statistics"][key] = st
    # the same AUROCs for abliteration-TOOL outputs only (fine-tune 'uncensored' models leave no spectral scar), and
    # o_proj split by structural validity (square / wide o_proj cannot carry a parent-free bottom read)
    abl = [r for r in real if r["arm"] == "honest" or r.get("subtype") == "edited_abliteration_tool"]
    la = np.array([int(r["arm"] == "edited") for r in abl])
    out["statistics_abliteration_tool_only"] = {}
    for key, hi, desc in READOUTS:
        x = np.array([f(r.get(key)) for r in abl])
        m = np.isfinite(x)
        if m.sum() >= 4 and 0 < la[m].sum() < m.sum():
            out["statistics_abliteration_tool_only"][key] = {
                "auroc_pooled": auroc((x if hi else -x)[m], la[m]), "n": int(m.sum()), "n_edited": int(la[m].sum())}
    for site, cond in (("valid_sites", lambda a: a > 1.05), ("square_or_wide_sites", lambda a: a <= 1.05)):
        sub = [r for r in real if np.isfinite(f(r.get("attn_aspect_din_over_dout"))) and cond(f(r.get("attn_aspect_din_over_dout")))]
        ls = np.array([int(r["arm"] == "edited") for r in sub])
        blk = {}
        for key in ("attn_BOTGAP_min", "attn_kappa_hat_max", "attn_BSA_w8", "attn_XLC"):
            hi = key != "attn_BOTGAP_min"
            x = np.array([f(r.get(key)) for r in sub])
            m = np.isfinite(x)
            if m.sum() >= 4 and 0 < ls[m].sum() < m.sum():
                blk[key] = {"auroc_pooled": auroc((x if hi else -x)[m], ls[m]), "n": int(m.sum()),
                            "n_edited": int(ls[m].sum())}
        out[f"o_proj_{site}"] = blk
    # PREREG thresholds' measured operating points
    op = {}
    for key, thr, hi in (("mlp_BSA_w8", PREREG_BSA, True), ("attn_BSA_w8", PREREG_BSA, True),
                         ("mlp_BOTGAP_min", PREREG_BOTGAP, False), ("attn_BOTGAP_min", PREREG_BOTGAP, False)):
        x = np.array([f(r.get(key)) for r in real])
        m = np.isfinite(x)
        flag = (x > thr) if hi else (x < thr)
        op[key] = {"threshold": thr, "rule": f"{'>' if hi else '<'} {thr}",
                   "fpr_on_honest": float(np.mean(flag[m & (lab == 0)])) if (m & (lab == 0)).any() else None,
                   "tpr_on_edited": float(np.mean(flag[m & (lab == 1)])) if (m & (lab == 1)).any() else None,
                   "n_honest": int((m & (lab == 0)).sum()), "n_edited": int((m & (lab == 1)).sum()),
                   "honest_mean": float(np.nanmean(x[m & (lab == 0)])) if (m & (lab == 0)).any() else None}
    out["prereg_threshold_operating_points"] = op
    out["prereg_threshold_note"] = ("The PREREG BSA flag of 0.35 was derived from SIMULATION (simulated honest ~0.177); "
                                    "these are its MEASURED operating points on real trained weights.")
    # structural validity of the o_proj site
    val = [r for r in real if np.isfinite(f(r.get("attn_aspect_din_over_dout")))]
    out["o_proj_site_validity"] = {
        "n_valid": int(sum(f(r.get("attn_aspect_din_over_dout")) > 1.05 for r in val)),
        "n_square_or_wide": int(sum(f(r.get("attn_aspect_din_over_dout")) <= 1.05 for r in val)),
        "honest_attn_BOTGAP_min_on_square_sites": [f(r.get("attn_BOTGAP_min")) for r in val
                                                   if r["arm"] == "honest" and f(r.get("attn_aspect_din_over_dout")) <= 1.05],
        "honest_attn_BOTGAP_min_on_valid_sites": [f(r.get("attn_BOTGAP_min")) for r in val
                                                  if r["arm"] == "honest" and f(r.get("attn_aspect_din_over_dout")) > 1.05]}
    return out


def recovered_class(r: dict[str, Any], t_bot: float, xlc_hi: float, bsa_hi: float) -> str:
    bg, xl, bs = f(r.get("mlp_BOTGAP_min")), f(r.get("mlp_XLC")), f(r.get("mlp_BSA_w8"))
    full = np.isfinite(bg) and bg < t_bot
    shared = (np.isfinite(xl) and xl > xlc_hi) or (np.isfinite(bs) and bs > bsa_hi)
    if full and shared:
        return "RECOVERED_SHARED_DIRECTION_FULL_RANK_EDIT"
    if full:
        return "RECOVERED_PER_LAYER_DIRECTIONS_FULL_RANK_EDIT"
    if shared:
        return "RECOVERED_SHARED_DIRECTION_PARTIAL_EDIT"
    return "RECOVERED_NO_DETECTABLE_EDIT"


def main_analysis() -> dict[str, Any]:
    D = load_everything()
    panel, census = D["panel"], D["census"]
    rows: list[dict[str, Any]] = []
    all_ids = set(D["ck"]) | set(D["harvest_rows"])
    for cid in sorted(all_ids):
        w = D["ck"].get(cid) or D["harvest_rows"].get(cid)
        q = D["wq"].get(cid) or D["gq"].get(cid) or {}
        repo = w.get("repo_id") or q.get("repo_id")
        kind = w.get("kind") or q.get("kind") or "real"
        prow = panel.get(repo or "", {})
        # arm: the panel's label, else the queue entry's (for the replication panel: the SOURCE run's own label),
        # else name tokens
        arm, sub = arm_label(repo, prow.get("arm") or (q.get("arm") if q.get("arm") in ("edited",) else None)) \
            if kind == "real" else (kind, kind)
        fam = prow.get("family_signature") or w.get("family_signature") or q.get("family_signature") or "unknown"
        r: dict[str, Any] = {"id": cid, "repo_id": repo, "kind": kind, "arm": arm, "subtype": sub, "family": fam,
                             "n_params": f(prow.get("n_params_est") or q.get("n_params_est")),
                             "weights_source": w.get("weights_source"), "kappa_true": q.get("kappa"),
                             "forgery_target": q.get("target")}
        r.update(flatten(w))
        pl = (w.get("per_family") or {}).get("mlp", {}).get("per_layer") or {}
        r["_mlp_per_layer"] = {int(L): f(v.get("kappa_hat")) for L, v in pl.items()}
        r["_mlp_n_layers"] = len(pl)
        g = D["graded"].get(cid)
        if g:
            o = g["outcomes"]
            for k in ("COMPLIANCE", "HREFUSAL", "OVERREFUSAL", "OVERREFUSAL_any_partial", "TSDS", "BB8",
                      "regex_refusal_H", "regex_overrefusal_B", "regex_refusal_BB8", "L1_logit_gap_H"):
                r[k] = f(o.get(k))
            r["graded_source"] = g.get("generation_source")
            r["n_H_graded"] = o.get("n_H_graded")
        g96 = D["graded96"].get(cid)
        if g96:
            r["COMPLIANCE_full96"] = f(g96["outcomes"].get("COMPLIANCE"))
        cen = census.get(repo or "", {})
        r["card_scope_class"] = cen.get("scope_class")
        r["card_tool"] = cen.get("tool")
        r["R1_card_regex_debiased"] = f(cen.get("R1_card_regex_debiased"))
        rows.append(r)
    honest_band(rows)
    real = [r for r in rows if r["kind"] == "real"]
    # activation readouts on graded checkpoints
    graded_ids = [r["id"] for r in rows if np.isfinite(f(r.get("COMPLIANCE")))]
    acts = activation_readouts(graded_ids, {})
    for r in rows:
        a = acts.get(r["id"])
        if a:
            r["A_coupling"] = f(a.get("rho")) if a.get("status") == "OK" else float("nan")
            r["A_coupling_status"] = a.get("status")
            r["A_content_auroc_cf"] = f(a.get("content_auroc_crossfit"))
            if not np.isfinite(f(r.get("L1_logit_gap_H"))):
                r["L1_logit_gap_H"] = f(a.get("L1_logit_gap_mean_H"))
    res: dict[str, Any] = {"n_rows": len(rows), "n_real": len(real),
                           "n_real_weights_v2": sum(r["weights_source"] == "this_lane_v2_exact_float64" for r in real),
                           "n_real_weights_harvest_fallback": sum(str(r["weights_source"]).startswith("sibling") for r in real),
                           "weights_failed": D["failed"], "activation_readouts": acts}
    # ---------------- PART 1
    det = detection(rows)
    res["part1_detection"] = det
    honest = [r for r in real if r["arm"] == "honest"]
    hb = np.array([f(r.get("mlp_BOTGAP_min")) for r in honest])
    hx = np.array([f(r.get("mlp_XLC")) for r in honest])
    hs = np.array([f(r.get("mlp_BSA_w8")) for r in honest])
    t_bot = float(np.nanquantile(hb, FPR_TARGET)) if np.isfinite(hb).sum() >= 5 else PREREG_BOTGAP
    xlc_hi = float(np.nanquantile(hx, 1 - FPR_TARGET)) if np.isfinite(hx).sum() >= 5 else 0.5
    bsa_hi = float(np.nanquantile(hs, 1 - FPR_TARGET)) if np.isfinite(hs).sum() >= 5 else 0.9
    res["part1_thresholds_rederived_on_honest_panel"] = {"BOTGAP_min_below": t_bot, "XLC_above": xlc_hi,
                                                         "BSA_w8_above": bsa_hi, "fpr_target": FPR_TARGET,
                                                         "n_honest": len(honest)}
    conf: dict[str, dict[str, int]] = {}
    for r in real:
        r["recovered_class"] = recovered_class(r, t_bot, xlc_hi, bsa_hi)
        st = r.get("card_scope_class") or "NO_CARD_IN_CENSUS"
        conf.setdefault(st, {}).setdefault(r["recovered_class"], 0)
        conf[st][r["recovered_class"]] += 1
    res["part1_confusion_stated_x_recovered"] = conf
    res["part1_confusion_note"] = ("Where the card and the weights disagree, THE WEIGHTS ARE THE MEASUREMENT AND "
                                   "THE CARD IS THE CLAIM. The class thresholds (BOTGAP_min 5% / XLC and BSA_w8 95% quantiles "
                                   "of the honest panel) are in-sample for honest members; the held-out-family operating "
                                   "points are in the detection table.")
    res["part1_distributions"] = {}
    for key in ("mlp_kappa_hat_band", "mlp_kappa_hat_max", "mlp_XLC", "mlp_band_frac", "mlp_BSA_w8", "mlp_BOTGAP_min",
                "mlp_RQ_pooled", "XFC", "attn_BOTGAP_min", "attn_BSA_w8"):
        dd = {}
        for arm in ("edited", "honest"):
            v = np.array([f(r.get(key)) for r in real if r["arm"] == arm])
            v = v[np.isfinite(v)]
            dd[arm] = {"n": int(v.size), "mean": float(v.mean()) if v.size else None,
                       "median": float(np.median(v)) if v.size else None,
                       "p10": float(np.percentile(v, 10)) if v.size else None,
                       "p90": float(np.percentile(v, 90)) if v.size else None}
        res["part1_distributions"][key] = dd
    # ---------------- PART 2 - the graded test
    G = [r for r in real if np.isfinite(f(r.get("COMPLIANCE"))) and np.isfinite(f(r.get("mlp_kappa_hat_band")))]
    E = [r for r in G if r["arm"] == "edited"]
    res["graded_panel"] = [{k: r.get(k) for k in ("id", "arm", "subtype", "family", "COMPLIANCE", "OVERREFUSAL", "TSDS",
                                                  "BB8", "HREFUSAL", "L1_logit_gap_H", "A_coupling", "mlp_kappa_hat_band",
                                                  "mlp_BOTGAP_min", "mlp_BSA_w8", "mlp_XLC", "mlp_RQ_pooled", "XFC",
                                                  "graded_source", "weights_source", "COMPLIANCE_full96", "n_params",
                                                  "recovered_class")} for r in G]
    fe = [r["family"] for r in E]
    ce = np.array([f(r["COMPLIANCE"]) for r in E])
    prim = corr_block([f(r["mlp_kappa_hat_band"]) for r in E], ce, fe,
                      "PRIMARY: Spearman(kappa_hat, COMPLIANCE) within the EDITED arm (real checkpoints only)",
                      n_boot=N_BOOT)
    prim["directional_prediction"] = "POSITIVE (stronger realised ablation -> more harmful compliance)"
    prim["n_edited_graded"] = len(E)
    res["primary_endpoint"] = prim
    res["primary_endpoint_abs_dev_coordinate"] = corr_block([1 - f(r["mlp_kappa_hat_band"]) for r in E], ce, fe,
                                                            "abs_dev = |1 - kappa_hat| (equivalent, sign-flipped)")
    fg = [r["family"] for r in G]
    cg = np.array([f(r["COMPLIANCE"]) for r in G])
    sec = corr_block([f(r["mlp_kappa_hat_band"]) for r in G], cg, fg, "SECONDARY: rho_pooled over edited + honest")
    sec["caveat"] = "This pooled correlation is driven by the edited-vs-honest contrast; it mostly measures the BINARY contrast, not a graded read."
    res["secondary_pooled"] = sec
    expl = {}
    for key, hi, desc in READOUTS:
        if key == "mlp_kappa_hat_band":
            continue
        expl[key] = corr_block([f(r.get(key)) for r in E], ce, fe, f"EXPLORATORY within-edited: {desc}")
    for key in ("A_coupling", "BB8", "L1_logit_gap_H", "OVERREFUSAL"):
        expl[key] = corr_block([f(r.get(key)) for r in E], ce, fe, f"within-edited: {key} vs COMPLIANCE")
    res["exploratory_within_edited"] = expl
    # ---- outcome sensitivity (EXPLORATORY): capability confounds the raw harm score across base models
    par_of: dict[str, dict[str, Any]] = {}
    pref = ("Qwen/", "unsloth/", "meta-llama/", "google/", "TinyLlama/", "HuggingFaceTB/", "allenai/", "Vikhrmodels/")
    for r in G:
        if r["arm"] == "honest" and r.get("subtype") == "instruct_or_other":
            cur = par_of.get(r["family"])
            rank = next((i for i, pf in enumerate(pref) if (r.get("repo_id") or "").startswith(pf)), 99)
            if cur is None or rank < cur["_rank"]:
                par_of[r["family"]] = dict(r, _rank=rank)
    kE = [f(r["mlp_kappa_hat_band"]) for r in E]
    sens = {"parents_used": {k: v.get("repo_id") for k, v in par_of.items()}}
    sens["kappa_vs_one_minus_HREFUSAL"] = corr_block(kE, [1 - f(r.get("HREFUSAL")) for r in E], fe,
                                                     "within-edited kappa_hat vs harmful ENGAGEMENT rate (1 - judge refusal)")
    sens["kappa_vs_delta_COMPLIANCE_vs_family_parent"] = corr_block(
        kE, [f(r["COMPLIANCE"]) - f(par_of[r["family"]]["COMPLIANCE"]) if r["family"] in par_of else float("nan")
             for r in E], fe, "within-edited kappa_hat vs COMPLIANCE minus the same-family honest instruct parent's")
    sens["kappa_vs_COMPLIANCE_full96"] = corr_block(kE, [f(r.get("COMPLIANCE_full96")) for r in E], fe,
                                                    "within-edited kappa_hat vs COMPLIANCE graded on the full 96-token replies")
    lnp = [math.log(f(r["n_params"])) if np.isfinite(f(r.get("n_params"))) and f(r["n_params"]) > 0 else float("nan") for r in E]
    xa, ya, za = np.array(kE), ce, np.array(lnp)
    mm = np.isfinite(xa) & np.isfinite(ya) & np.isfinite(za)
    if mm.sum() >= 5 and np.ptp(za[mm]) > 0:
        rx, ry, rz = (sps.rankdata(v) for v in (xa[mm], ya[mm], za[mm]))
        rxy, rxz, ryz = np.corrcoef(rx, ry)[0, 1], np.corrcoef(rx, rz)[0, 1], np.corrcoef(ry, rz)[0, 1]
        den = math.sqrt(max(1e-12, (1 - rxz ** 2) * (1 - ryz ** 2)))
        sens["kappa_vs_COMPLIANCE_partial_log_n_params"] = {"rho_partial": float((rxy - rxz * ryz) / den),
                                                             "n": int(mm.sum()), "rho_kappa_size": float(rxz),
                                                             "rho_compliance_size": float(ryz)}
    EA = [r for r in E if r.get("subtype") == "edited_abliteration_tool"]
    sens["primary_restricted_to_abliteration_tool_checkpoints"] = corr_block(
        [f(r["mlp_kappa_hat_band"]) for r in EA], [f(r["COMPLIANCE"]) for r in EA], [r["family"] for r in EA],
        "within-edited kappa_hat vs COMPLIANCE, ONLY checkpoints named as abliteration/heretic/orthogonalization outputs")
    sens["edited_subtypes"] = {r["id"]: r.get("subtype") for r in E}
    res["outcome_sensitivity_within_edited"] = sens
    res["exploratory_note"] = (f"{len(expl)} exploratory readouts were correlated with COMPLIANCE inside the edited arm; "
                               "none is pre-registered and at this n a nominal p<0.05 among them is expected by chance.")
    # ---------------- BARS
    bars: dict[str, Any] = {}
    y = cg
    kap = np.array([f(r["mlp_kappa_hat_band"]) for r in G])
    is_ed = np.array([float(r["arm"] == "edited") for r in G])
    # LOFO binary detector flag (BOTGAP_min below the held-out honest 5% quantile; BSA ORed if it separates)
    fa = np.array(fg, dtype=object)
    allreal = [r for r in real if np.isfinite(f(r.get("mlp_BOTGAP_min")))]
    flag = np.zeros(len(G))
    bsa_auc = det["statistics"].get("mlp_BSA_w8", {}).get("auroc_pooled") or 0.5
    use_bsa = bsa_auc >= 0.80
    for i, r in enumerate(G):
        hon = [h for h in allreal if h["arm"] == "honest" and h["family"] != r["family"]]
        if len(hon) < 3:
            flag[i] = np.nan
            continue
        tb = np.nanquantile([f(h["mlp_BOTGAP_min"]) for h in hon], FPR_TARGET)
        fl = f(r["mlp_BOTGAP_min"]) < tb
        if use_bsa:
            ts = np.nanquantile([f(h.get("mlp_BSA_w8")) for h in hon], 1 - FPR_TARGET)
            fl = fl or f(r.get("mlp_BSA_w8")) > ts
        flag[i] = float(fl)
    bars["edited_flag_definition"] = (f"BOTGAP_min(down_proj) below the 5% quantile of HONEST checkpoints from OTHER "
                                      f"families (held-out family){' OR BSA_w8 above their 95% quantile' if use_bsa else ''}; "
                                      f"BSA ORed in: {use_bsa} (pooled BSA AUROC {bsa_auc:.3f})")
    bars["edited_flag_confusion_vs_label"] = {"tp": int(np.nansum((flag == 1) & (is_ed == 1))),
                                              "fp": int(np.nansum((flag == 1) & (is_ed == 0))),
                                              "fn": int(np.nansum((flag == 0) & (is_ed == 1))),
                                              "tn": int(np.nansum((flag == 0) & (is_ed == 0)))}

    def bar1(binary: np.ndarray, name: str) -> dict[str, Any]:
        m = np.isfinite(binary) & np.isfinite(kap) & np.isfinite(y)
        if m.sum() < 6:
            return {"status": f"UNDERPOWERED: {int(m.sum())} rows"}
        X0, X1 = binary[m][:, None], np.column_stack([binary[m], kap[m]])
        yy, ff = y[m], fa[m]
        r2_0 = r2(yy, ols_pred(ols_fit(X0, yy), X0))
        r2_1 = r2(yy, ols_pred(ols_fit(X1, yy), X1))
        # family-cluster bootstrap of delta R^2
        fams_u = sorted(set(ff))
        idx = {c: np.where(ff == c)[0] for c in fams_u}
        rng = np.random.default_rng(SEED)
        dr = []
        for _ in range(N_BOOT):
            pick = rng.integers(0, len(fams_u), len(fams_u))
            rows_b = np.concatenate([rng.choice(idx[fams_u[p]], len(idx[fams_u[p]])) for p in pick])
            yb = yy[rows_b]
            if np.ptp(yb) == 0 or np.ptp(X1[rows_b, 1]) == 0:
                continue
            a0 = r2(yb, ols_pred(ols_fit(X0[rows_b], yb), X0[rows_b]))
            a1 = r2(yb, ols_pred(ols_fit(X1[rows_b], yb), X1[rows_b]))
            dr.append(a1 - a0)
        # permutation null for the in-sample delta R^2 (it is non-negative by construction, so a bootstrap CI of it
        # can never cover zero): permute kappa_hat across the graded checkpoints, 2000 draws
        rng_p = np.random.default_rng(SEED + 1)
        null_dr = []
        for _ in range(2000):
            kp = rng_p.permutation(X1[:, 1])
            Xp = np.column_stack([X1[:, 0], kp])
            null_dr.append(r2(yy, ols_pred(ols_fit(Xp, yy), Xp)) - r2_0)
        obs_dr = r2_1 - r2_0
        p0 = lofo_predict(X0, yy, ff)
        p1 = lofo_predict(X1, yy, ff)
        mm = np.isfinite(p0) & np.isfinite(p1)
        out = {"binary_regressor": name, "n": int(m.sum()), "n_families": len(fams_u),
               "R2_M0_binary": r2_0, "R2_M1_binary_plus_kappa": r2_1, "delta_R2": r2_1 - r2_0,
               "delta_R2_ci95_family_cluster_boot": [float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))]
               if len(dr) > 200 else None,
               "lofo_R2_M0": r2(yy[mm], p0[mm]) if mm.sum() > 3 else None,
               "lofo_R2_M1": r2(yy[mm], p1[mm]) if mm.sum() > 3 else None,
               "lofo_mae_M0": float(np.mean(np.abs(yy[mm] - p0[mm]))) if mm.any() else None,
               "lofo_mae_M1": float(np.mean(np.abs(yy[mm] - p1[mm]))) if mm.any() else None,
               "lofo_paired_mae_diff_M1_minus_M0": paired_err_boot(yy - p1, yy - p0, ff),
               "delta_R2_permutation_p": float((1 + np.sum(np.array(null_dr) >= obs_dr)) / (1 + len(null_dr))),
               "delta_R2_permutation_null_mean": float(np.mean(null_dr)),
               "delta_R2_note": ("in-sample delta R^2 is non-negative by construction, so its bootstrap CI cannot cover "
                                 "zero; the tests are the permutation p-value and the out-of-family paired MAE difference")}
        return out

    bars["BAR1_graded_vs_binary_detector"] = bar1(flag, "held-out-family detector flag")
    bars["BAR1_graded_vs_binary_oracle_label"] = bar1(is_ed, "ORACLE edited label (every advantage to the binary bar)")
    # BAR 2 - weights (0 prompts) vs black box at a matched 8-prompt budget, on DISJOINT items
    def lofo_single(xkey: str) -> np.ndarray:
        x = np.array([f(r.get(xkey)) for r in G])
        m = np.isfinite(x) & np.isfinite(y)
        p = np.full(len(y), np.nan)
        if m.sum() >= 6:
            p[m] = lofo_predict(x[m][:, None], y[m], fa[m])
        return p
    pk, pb, pl1 = lofo_single("mlp_kappa_hat_band"), lofo_single("BB8"), lofo_single("L1_logit_gap_H")
    pa = lofo_single("A_coupling")
    bars["BAR2_weights_vs_blackbox_BB8"] = {
        "kappa_hat_zero_prompts": paired_err_boot(y - pk, y - pb, fg) | {"note": "a = kappa_hat (0 prompts), b = BB8 (8 DISJOINT prompts); negative diff = weights better"},
        "lofo_R2_kappa": r2(y[np.isfinite(pk)], pk[np.isfinite(pk)]) if np.isfinite(pk).sum() > 3 else None,
        "lofo_R2_BB8": r2(y[np.isfinite(pb)], pb[np.isfinite(pb)]) if np.isfinite(pb).sum() > 3 else None,
        "lofo_R2_L1_logit_gap": r2(y[np.isfinite(pl1)], pl1[np.isfinite(pl1)]) if np.isfinite(pl1).sum() > 3 else None,
        "kappa_vs_L1": paired_err_boot(y - pk, y - pl1, fg),
        "disjointness": "BB8 = the first 8 XSTest-unsafe probe prompts; the 48 outcome items are JBB-Behaviors/StrongREJECT (disjoint by source; asserted in method.py)",
        "cost_note": "the weights read uses ZERO prompts, so any tie is a win on cost"}
    # BAR 3 - recipe vector vs strength alone
    feats = ["mlp_kappa_hat_band", "mlp_band_frac", "mlp_band_lo_frac", "mlp_XLC", "mlp_BSA_w8", "mlp_BOTGAP_min"]
    Xr = np.column_stack([[f(r.get(k)) for r in G] for k in feats] + [[math.log(max(f(r.get("n_params")), 1.0))
                                                                         if np.isfinite(f(r.get("n_params"))) else np.nan for r in G]])
    Xr = np.where(np.isfinite(Xr), Xr, np.nan)
    colmean = np.nanmean(Xr, axis=0)
    Xr = np.where(np.isfinite(Xr), Xr, colmean)
    m3 = np.isfinite(y)
    if m3.sum() >= 8:
        pr = lofo_predict(Xr[m3], y[m3], fa[m3], alpha=1.0)
        pk3 = lofo_predict(Xr[m3][:, :1], y[m3], fa[m3])
        bars["BAR3_recipe_vector_vs_strength"] = {
            "features": feats + ["log_n_params"], "ridge_alpha": 1.0, "n": int(m3.sum()),
            "lofo_R2_recipe_vector": r2(y[m3][np.isfinite(pr)], pr[np.isfinite(pr)]),
            "lofo_R2_kappa_alone": r2(y[m3][np.isfinite(pk3)], pk3[np.isfinite(pk3)]),
            "paired": paired_err_boot(y[m3] - pr, y[m3] - pk3, fa[m3])}
        # 5.4: the recipe vector vs the binary model, both LOFO
        p0 = lofo_predict(is_ed[m3][:, None], y[m3], fa[m3])
        bars["BAR3b_recipe_vector_vs_oracle_binary"] = paired_err_boot(y[m3] - pr, y[m3] - p0, fa[m3])
    # BAR 4 - cross-fitted activation readout on the SAME graded checkpoints
    ma = np.isfinite(pa) & np.isfinite(pk)
    bars["BAR4_activation_readout"] = {
        "n_with_A_coupling_defined": int(np.isfinite([f(r.get("A_coupling")) for r in G]).sum()),
        "n_undefined_decision_spread": int(sum(r.get("A_coupling_status") == "UNDEFINED" for r in G)),
        "spearman_A_coupling_vs_COMPLIANCE_all_graded": corr_block([f(r.get("A_coupling")) for r in G], y, fg,
                                                                    "A_coupling vs COMPLIANCE (all graded)"),
        "kappa_vs_A_coupling_lofo": paired_err_boot(y[ma] - pk[ma], y[ma] - pa[ma], fa[ma]) if ma.sum() > 4 else None}
    # BAR 5 - free baselines: family label alone (LOCO within family) and the name-free card regex
    fam_pred = np.full(len(y), np.nan)
    for i, r in enumerate(G):
        others = [j for j in range(len(G)) if j != i and G[j]["family"] == r["family"]]
        fam_pred[i] = float(np.mean(y[others])) if others else float(np.mean(np.delete(y, i)))
    kap_loco = loco_predict(kap[:, None], y) if len(y) >= 6 else np.full(len(y), np.nan)
    card = np.array([f(r.get("R1_card_regex_debiased")) for r in G])
    mc = np.isfinite(card)
    bars["BAR5_free_baselines"] = {
        "family_label_only_loco_R2": r2(y, fam_pred),
        "kappa_hat_loco_R2": r2(y[np.isfinite(kap_loco)], kap_loco[np.isfinite(kap_loco)]) if np.isfinite(kap_loco).sum() > 3 else None,
        "paired_kappa_minus_family": paired_err_boot(y - kap_loco, y - fam_pred, fg),
        "card_regex_namefree_spearman_vs_COMPLIANCE": spearman(card[mc], y[mc]) if mc.sum() > 3 else None,
        "card_regex_namefree_n": int(mc.sum())}
    fam_better = (r2(y, fam_pred) or -9) >= (bars["BAR5_free_baselines"]["kappa_hat_loco_R2"] or -9)
    bars["BAR5_free_baselines"]["standing_rule_sentence"] = (
        "THE READOUT HAS NOT EARNED ITS FORWARD PASSES: the architecture-family label alone predicts COMPLIANCE at "
        "least as well as the weights readout does." if fam_better else
        "The weights readout beats the family-label-only baseline on leave-one-checkpoint-out R^2.")
    res["bars"] = bars
    # per-checkpoint out-of-family predictions of COMPLIANCE, one column per method (method_out predict_*)
    pr_bin = lofo_predict(np.nan_to_num(flag)[:, None], y, fa) if len(y) >= 6 else np.full(len(y), np.nan)
    pr_orc = lofo_predict(is_ed[:, None], y, fa) if len(y) >= 6 else np.full(len(y), np.nan)
    pr_rec = np.full(len(y), np.nan)
    if m3.sum() >= 8:
        pr_rec[m3] = lofo_predict(Xr[m3], y[m3], fa[m3], alpha=1.0)
    res["per_checkpoint_predictions"] = {
        r["id"]: {"COMPLIANCE_measured": f(y[i]), "ours_kappa_hat_lofo": f(pk[i]), "ours_recipe_vector_lofo": f(pr_rec[i]),
                  "baseline_binary_detector_lofo": f(pr_bin[i]), "baseline_oracle_edited_label_lofo": f(pr_orc[i]),
                  "baseline_BB8_blackbox_lofo": f(pb[i]), "baseline_L1_logit_gap_lofo": f(pl1[i]),
                  "activation_A_coupling_lofo": f(pa[i]), "baseline_family_label_loco": f(fam_pred[i]),
                  "edited_flag_heldout": f(flag[i]), "family": r["family"], "arm": r["arm"]}
        for i, r in enumerate(G)}
    # ---------------- constructed known-kappa arm
    C = [r for r in rows if r["kind"] == "constructed"]
    par = next((r for r in real if r["repo_id"] == "Qwen/Qwen3-0.6B"), None)
    edt = next((r for r in real if r["repo_id"] == "mlabonne/Qwen3-0.6B-abliterated"), None)
    grid = []
    for r, k in ([(par, 0.0)] if par else []) + [(r, f(r["kappa_true"])) for r in C] + ([(edt, 1.0)] if edt else []):
        grid.append({"kappa_true": k, "id": r["id"], **{key: f(r.get(key)) for key, _, _ in READOUTS},
                     "COMPLIANCE": f(r.get("COMPLIANCE")), "OVERREFUSAL": f(r.get("OVERREFUSAL")),
                     "HREFUSAL": f(r.get("HREFUSAL")), "BB8": f(r.get("BB8")), "A_coupling": f(r.get("A_coupling")),
                     "generation_source": r.get("graded_source")})
    grid.sort(key=lambda d: d["kappa_true"])
    # effective TRUE projection strength of each constructed point: W(c) = W_P + c*dW and dW = -kappa_L r r^T W_P per
    # matrix, so kappa_eff_L(c) = c * kappa_L exactly (kappa_L from the parent-based ground truth of the mlabonne edit)
    tkm = jl(RES / "true_kappa" / "mlabonne__Qwen3-0.6B-abliterated.json") or {}
    kl = [x["kappa_true"] for x in ((tkm.get("per_layer") or {}).get("mlp") or []) if not x.get("unchanged")]
    for g in grid:
        g["kappa_effective_true_median"] = float(g["kappa_true"] * np.median(kl)) if kl else None
        g["kappa_effective_true_max"] = float(g["kappa_true"] * np.max(kl)) if kl else None
    cal = {}
    for key, _, _ in READOUTS + [("COMPLIANCE", True, ""), ("HREFUSAL", False, ""), ("BB8", False, ""), ("A_coupling", False, "")]:
        xs = [g["kappa_true"] for g in grid]
        ys = [g.get(key) for g in grid]
        cal[key] = spearman(xs, ys)
    res["constructed_known_kappa_arm"] = {
        "construction": "W(kappa) = W_Qwen3-0.6B + kappa * (W_mlabonne-abliterated - W_Qwen3-0.6B) for every tensor that "
                        "differs; kappa=0 is the parent, kappa=1 the published edit, kappa>1 over-ablation. Labelled "
                        "CONSTRUCTED; never pooled with real checkpoints in the headline.",
        "grid": grid, "spearman_vs_true_kappa": cal,
        "kappa_hat_tracks_true_kappa": cal.get("mlp_kappa_hat_band", {}).get("rho"),
        "F3_check": "kappa_hat is RECOVERABLE on known truth iff its Spearman with the true kappa over kappa<=1 is "
                    "clearly positive; see kappa_hat_tracks_true_kappa_le1",
        "kappa_hat_tracks_true_kappa_le1": spearman([g["kappa_true"] for g in grid if g["kappa_true"] <= 1],
                                                    [g["mlp_kappa_hat_band"] for g in grid if g["kappa_true"] <= 1]),
        "scale_note": ("kappa_true here is the multiple c of the PUBLISHED mlabonne edit; that edit is itself a PARTIAL "
                       "projection (per-layer true kappa median %s), so c maps to an effective true projection strength "
                       "kappa_effective = c * kappa_layer (columns kappa_effective_true_median/max)." %
                       (f"{np.median(kl):.3f}" if kl else "n/a"))}
    # ---------------- forgery handoff
    fr = [r for r in rows if r["kind"] == "forgery"]
    fo = {}
    for r in fr:
        base_repo = (D["wq"].get(r["id"]) or D["gq"].get(r["id"]) or {}).get("edited")
        b = next((x for x in real if x["repo_id"] == base_repo), None)
        hon_par = next((x for x in real if x["repo_id"] == (base_repo or "").replace("huihui-ai/Huihui-", "Qwen/").replace("-abliterated-v2", "")), None)
        keys = ("mlp_BOTGAP_min", "attn_BOTGAP_min", "mlp_BSA_w8", "attn_BSA_w8", "mlp_XLC", "mlp_kappa_hat_band", "XFC", "mlp_RQ_pooled")
        fo[r["id"]] = {"edited_checkpoint": base_repo, "target": r.get("forgery_target"),
                       "detector_before": {k: f(b.get(k)) if b else None for k in keys},
                       "detector_after": {k: f(r.get(k)) for k in keys},
                       "COMPLIANCE_before_edited": f(b.get("COMPLIANCE")) if b else None,
                       "COMPLIANCE_after_repair": f(r.get("COMPLIANCE")),
                       "COMPLIANCE_honest_parent": f(hon_par.get("COMPLIANCE")) if hon_par else None,
                       "honest_parent": hon_par["repo_id"] if hon_par else None,
                       "OVERREFUSAL_after_repair": f(r.get("OVERREFUSAL")), "BB8_after_repair": f(r.get("BB8")),
                       "BB8_before_edited": f(b.get("BB8")) if b else None,
                       "BB8_honest_parent": f(hon_par.get("BB8")) if hon_par else None,
                       "HREFUSAL_before_edited": f(b.get("HREFUSAL")) if b else None,
                       "HREFUSAL_after_repair": f(r.get("HREFUSAL")),
                       "HREFUSAL_honest_parent": f(hon_par.get("HREFUSAL")) if hon_par else None,
                       "A_coupling_before_edited": f(b.get("A_coupling")) if b else None,
                       "A_coupling_after_repair": f(r.get("A_coupling")),
                       "A_coupling_honest_parent": f(hon_par.get("A_coupling")) if hon_par else None,
                       "reading": ("the weight detectors are healed by the repair; the behaviour (refusal) and the "
                                   "hidden-state coupling are read BEFORE vs AFTER against the honest parent")}
    res["forgery"] = fo
    # ---------------- PART 4: which layers / components carry the readout
    prof = {}
    for comp in ("mlp", "attn"):
        for q in range(5):
            vals = []
            for r in E:
                w = D["ck"].get(r["id"]) or D["harvest_rows"].get(r["id"]) or {}
                pl = ((w.get("per_family") or {}).get(comp) or {}).get("per_layer") or {}
                if not pl:
                    vals.append(np.nan)
                    continue
                Ls = sorted(int(L) for L in pl)
                nL = max(Ls) + 1
                sel = [L for L in Ls if int(5 * L / nL) == q]
                vals.append(max(f(pl[str(L)]["kappa_hat"]) for L in sel) if sel else np.nan)
            prof[f"{comp}_quintile{q + 1}"] = spearman(vals, ce)
    res["part4_layer_component_profile"] = {"readout": "kappa_hat restricted to one depth quintile / one component",
                                            "within_edited_spearman_vs_COMPLIANCE": prof, "n_edited": len(E)}
    res["_rows"] = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    return res


def anisotropy_null(res: dict[str, Any], n_draws: int = 200) -> dict[str, Any]:
    """5.2: per family signature, null directions drawn from the EMPIRICAL covariance of honest bottom directions
    (low-rank factor form: r = normalise(V^T g), V = the honest u_min set of that family), independently per layer;
    BSA_w8 / XLC recomputed under the null; the isotropic null reported beside it."""
    rows = res["_rows"]
    out = {}
    rng = np.random.default_rng(SEED)
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r["kind"] == "real":
            by_fam.setdefault(r["family"], []).append(r)
    for fam, rs in by_fam.items():
        def bottom_dirs(cid: str) -> np.ndarray | None:
            """down_proj bottom-1 directions (L, d): exact v2 read, else the sibling harvest (agrees on valid sites)."""
            vp = RES / "vecs_v2" / f"{cid}.npz"
            if vp.exists():
                z = np.load(vp)
                if "mlp_bot" in z.files:
                    return z["mlp_bot"].astype(np.float64)[:, :, 0]
            hp = HARVEST / cid / "weights.npz"
            if hp.exists():
                z = np.load(hp)
                if "down_proj_bot" in z.files:
                    return z["down_proj_bot"].astype(np.float64)[:, 0, :]
            return None
        hon = [r for r in rs if r["arm"] == "honest"]
        V = []
        nL = None
        n_sets = 0
        for r in hon:
            b = bottom_dirs(r["id"])
            if b is None or (nL is not None and b.shape[0] != nL):
                continue
            V.append(b)
            nL = b.shape[0]
            n_sets += 1
        if n_sets < 2:
            continue
        if not V:
            continue
        Vs = np.concatenate(V, 0)
        d = Vs.shape[1]
        null_bsa, null_xlc, iso_bsa, iso_xlc = [], [], [], []
        for _ in range(n_draws):
            G = rng.standard_normal((nL, Vs.shape[0]))
            dirs = G @ Vs
            dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
            u = {L: dirs[L] for L in range(nL)}
            null_bsa.append(bsa_window({L: dirs[L][:, None] for L in range(nL)}, 8)["bsa_w"])
            null_xlc.append(cross_layer_cosine(u)["xlc"])
            iso = rng.standard_normal((nL, d))
            iso /= np.linalg.norm(iso, axis=1, keepdims=True)
            iso_bsa.append(bsa_window({L: iso[L][:, None] for L in range(nL)}, 8)["bsa_w"])
            iso_xlc.append(cross_layer_cosine({L: iso[L] for L in range(nL)})["xlc"])
        nb, nx = np.array(null_bsa), np.array(null_xlc)
        obs = []
        for r in rs:
            ob, ox = f(r.get("mlp_BSA_w8")), f(r.get("mlp_XLC"))
            obs.append({"id": r["id"], "arm": r["arm"], "BSA_w8": ob, "XLC": ox,
                        "p_BSA_vs_aniso": float((1 + np.sum(nb >= ob)) / (1 + nb.size)) if np.isfinite(ob) else None,
                        "p_XLC_vs_aniso": float((1 + np.sum(nx >= ox)) / (1 + nx.size)) if np.isfinite(ox) else None})
        out[fam] = {"n_honest_sets": len(V), "n_layers": nL, "d": d, "n_draws": n_draws,
                    "aniso_null_BSA_w8_mean": float(nb.mean()), "aniso_null_BSA_w8_p95": float(np.percentile(nb, 95)),
                    "aniso_null_XLC_mean": float(nx.mean()), "aniso_null_XLC_p95": float(np.percentile(nx, 95)),
                    "iso_null_BSA_w8_mean": float(np.mean(iso_bsa)), "iso_null_XLC_mean": float(np.mean(iso_xlc)),
                    "observed": obs}
    return out


def true_kappa_section(res: dict[str, Any]) -> dict[str, Any]:
    """Parent-BASED ground truth (stage1b_true_kappa.py) vs the parent-free estimator, per layer and per checkpoint.
    Also asks the decisive interpretive question: does even the TRUE realised strength grade measured compliance?"""
    rows = {r["repo_id"]: r for r in res["_rows"] if r["kind"] == "real" and r.get("repo_id")}
    out: dict[str, Any] = {"per_checkpoint": [], "note": "PARENT-BASED ground truth for calibration only; no readout uses the parent."}
    lay_true, lay_hat, lay_in_range, lay_absdev_true, lay_absdev_hat, lay_cos = [], [], [], [], [], []
    for p in sorted((RES / "true_kappa").glob("*.json")):
        if p.name.endswith(".failed.json"):
            continue
        d = jl(p)
        if not d:
            continue
        sm = (d.get("summary") or {}).get("mlp") or {}
        r = rows.get(d["edited"], {})
        ck = jl(RES / "ckpt_v2" / f"{d['edited'].replace('/', '__')}.json") or {}
        if not ck and (HARVEST / d["edited"].replace("/", "__") / "weights.npz").exists():
            ck = harvest_weight_row(HARVEST / d["edited"].replace("/", "__")) or {}   # exact on down_proj (regression)
        pl = (((ck.get("per_family") or {}).get("mlp") or {}).get("per_layer")) or {}
        for x in ((d.get("per_layer") or {}).get("mlp") or []):
            if x.get("unchanged") or str(x["layer"]) not in pl:
                continue
            h = pl[str(x["layer"])]
            lay_true.append(x["kappa_true"])
            lay_hat.append(f(h.get("kappa_hat")))
            lay_absdev_true.append(abs(1 - x["kappa_true"]))
            lay_absdev_hat.append(f(h.get("abs_dev")))
            lay_in_range.append(abs(1 - x["kappa_true"]) < f(h.get("s_min_over_rms")))
            lay_cos.append(f(x.get("cos_true_dir_vs_parentfree_bottom1")))
        kl = [x["kappa_true"] for x in ((d.get("per_layer") or {}).get("mlp") or []) if not x.get("unchanged")]
        # 1.2b(iv): does the parent-free per-layer profile recover the tool's own peak position?
        tl = [(x["layer"], x["kappa_true"]) for x in ((d.get("per_layer") or {}).get("mlp") or [])
              if not x.get("unchanged")]
        prof = {}
        if tl and pl:
            nL = max(int(L) for L in pl) + 1
            Lpk_true = max(tl, key=lambda t: t[1])[0]
            Lnear1 = min(tl, key=lambda t: abs(1 - t[1]))[0]
            kh_by = {int(L): f(v.get("kappa_hat")) for L, v in pl.items()}
            Lpk_pf = max(kh_by, key=lambda L: kh_by[L] if np.isfinite(kh_by[L]) else -1)
            prof = {"true_peak_layer_frac": Lpk_true / max(nL - 1, 1), "true_peak_kappa": max(t[1] for t in tl),
                    "layer_frac_where_true_kappa_closest_to_1": Lnear1 / max(nL - 1, 1),
                    "parentfree_kappa_hat_peak_layer_frac": Lpk_pf / max(nL - 1, 1),
                    "parentfree_peak_matches_true_peak": abs(Lpk_pf - Lpk_true) <= 1,
                    "parentfree_peak_matches_closest_to_1": abs(Lpk_pf - Lnear1) <= 1,
                    "spearman_profile_true_vs_parentfree": spearman([t[1] for t in tl], [kh_by.get(t[0], np.nan) for t in tl]).get("rho"),
                    "spearman_profile_absdev_true_vs_parentfree": spearman([abs(1 - t[1]) for t in tl],
                                                                           [1 - kh_by.get(t[0], np.nan) for t in tl]).get("rho")}
        out["per_checkpoint"].append({
            "edited": d["edited"], "parent_chosen": d.get("parent_chosen"),
            "kappa_true_median": sm.get("kappa_true_median"), "kappa_true_max": sm.get("kappa_true_max"),
            "kappa_true_min": sm.get("kappa_true_min"),
            "frac_layers_kappa_gt_1": float(np.mean(np.array(kl) > 1.02)) if kl else None,
            "frac_layers_kappa_lt_1": float(np.mean(np.array(kl) < 0.98)) if kl else None,
            "rank_one_share_median": sm.get("rank_one_share_median"), "true_direction_XLC": sm.get("true_direction_XLC"),
            "peak_layer_frac": sm.get("peak_layer_frac"),
            "cos_true_vs_parentfree_bottom1_median": sm.get("cos_true_vs_parentfree_bottom1_median"),
            "o_proj_kappa_true_median": ((d.get("summary") or {}).get("attn") or {}).get("kappa_true_median"),
            "kappa_hat_band_parentfree": r.get("mlp_kappa_hat_band"), "BOTGAP_min_parentfree": r.get("mlp_BOTGAP_min"),
            "XLC_parentfree": r.get("mlp_XLC"), "COMPLIANCE": r.get("COMPLIANCE"), "HREFUSAL": r.get("HREFUSAL"),
            "is_projection_edit": bool((sm.get("rank_one_share_median") or 0) > 0.9), "profile_recovery": prof})
    lt, lh = np.array(lay_true, float), np.array(lay_hat, float)
    at, ah = np.array(lay_absdev_true, float), np.array(lay_absdev_hat, float)
    inr = np.array(lay_in_range, bool)
    out["per_layer_n"] = int(len(lt))
    out["per_layer_spearman_kappa_true_vs_kappa_hat"] = spearman(lt, lh)
    out["per_layer_spearman_absdev_true_vs_absdev_hat"] = spearman(at, ah)
    out["per_layer_absdev_mae"] = float(np.nanmean(np.abs(at - ah))) if len(at) else None
    out["operating_range_test"] = {
        "rule": "v1 derived: a bottom-spectrum read can see an edit only while |1 - kappa_true| < sigma_min/sigma_rms",
        "n_layers_in_range": int(inr.sum()), "n_layers_out_of_range": int((~inr).sum()),
        "median_kappa_hat_in_range": float(np.nanmedian(lh[inr])) if inr.any() else None,
        "median_kappa_hat_out_of_range": float(np.nanmedian(lh[~inr])) if (~inr).any() else None,
        "absdev_mae_in_range": float(np.nanmean(np.abs(at[inr] - ah[inr]))) if inr.any() else None,
        "absdev_mae_out_of_range": float(np.nanmean(np.abs(at[~inr] - ah[~inr]))) if (~inr).any() else None}
    lc = np.array(lay_cos, float)
    out["per_layer_cos_true_direction_vs_parentfree_bottom1"] = {
        "median": float(np.nanmedian(lc)) if np.isfinite(lc).any() else None,
        "frac_above_0.9": float(np.nanmean(lc > 0.9)) if np.isfinite(lc).any() else None,
        "median_in_range": float(np.nanmedian(lc[inr])) if (inr & np.isfinite(lc)).any() else None,
        "median_out_of_range": float(np.nanmedian(lc[~inr])) if ((~inr) & np.isfinite(lc)).any() else None}
    # detection by EDIT TYPE: projection (abliteration-style) vs non-projection (fine-tune / merge) edits
    thr = res.get("part1_thresholds_rederived_on_honest_panel") or {}
    kap_hi = float(np.nanquantile([f(r.get("mlp_kappa_hat_band")) for r in res["_rows"]
                                   if r["kind"] == "real" and r["arm"] == "honest"], 0.95)) \
        if any(r["arm"] == "honest" for r in res["_rows"]) else float("nan")
    bytype: dict[str, dict[str, Any]] = {}
    for x in out["per_checkpoint"]:
        kind = ("projection_edit" if x["is_projection_edit"] else
                ("down_proj_untouched" if x.get("kappa_true_median") is None else "non_projection_edit"))
        x["edit_type"] = kind
        flag_k = f(x.get("kappa_hat_band_parentfree")) > kap_hi
        flag_b = f(x.get("BOTGAP_min_parentfree")) < f(thr.get("BOTGAP_min_below"))
        d = bytype.setdefault(kind, {"n": 0, "flagged_by_kappa_hat": 0, "flagged_by_BOTGAP": 0, "members": []})
        d["n"] += 1
        d["flagged_by_kappa_hat"] += int(flag_k)
        d["flagged_by_BOTGAP"] += int(flag_b)
        d["members"].append(x["edited"])
    pr = [x["profile_recovery"] for x in out["per_checkpoint"] if x.get("profile_recovery") and x["is_projection_edit"]]
    out["profile_recovery_summary"] = {
        "n": len(pr),
        "frac_parentfree_peak_at_true_peak": float(np.mean([x["parentfree_peak_matches_true_peak"] for x in pr])) if pr else None,
        "frac_parentfree_peak_where_true_kappa_closest_to_1": float(np.mean([x["parentfree_peak_matches_closest_to_1"] for x in pr])) if pr else None,
        "median_profile_spearman_absdev": float(np.nanmedian([f(x["spearman_profile_absdev_true_vs_parentfree"]) for x in pr])) if pr else None,
        "reading": ("only |1-kappa| is identifiable parent-free, so the recovered profile peaks where the TRUE kappa is "
                    "closest to 1, which is NOT the tool's max_weight position whenever the tool over-ablates")}
    out["detection_by_edit_type"] = {"thresholds": {"kappa_hat_above_honest_p95": kap_hi,
                                                    "BOTGAP_min_below": thr.get("BOTGAP_min_below")}, "by_type": bytype}
    pc = [x for x in out["per_checkpoint"] if x["is_projection_edit"]]
    out["checkpoint_spearman_kappa_true_vs_kappa_hat"] = spearman([x["kappa_true_median"] for x in pc],
                                                                  [x["kappa_hat_band_parentfree"] for x in pc])
    g = [x for x in pc if x.get("COMPLIANCE") is not None]
    fam_of = {r["repo_id"]: r["family"] for r in res["_rows"] if r.get("repo_id")}
    gf = [fam_of.get(x["edited"], "unknown") for x in g]
    out["true_strength_vs_risk_blocks"] = {
        "signed_kappa_true": corr_block([x["kappa_true_median"] for x in g], [x["COMPLIANCE"] for x in g], gf,
                                        "TRUE signed strength (parent-based) vs COMPLIANCE, projection edits"),
        "abs_one_minus_kappa_true": corr_block([abs(1 - x["kappa_true_median"]) for x in g], [x["COMPLIANCE"] for x in g], gf,
                                               "|1 - kappa_true| (the only parent-free-identifiable part) vs COMPLIANCE"),
        "parentfree_kappa_hat_same_checkpoints": corr_block([x["kappa_hat_band_parentfree"] for x in g],
                                                            [x["COMPLIANCE"] for x in g], gf,
                                                            "parent-free kappa_hat vs COMPLIANCE on the same checkpoints"),
        "n_over_ablated_checkpoints": int(sum((x["kappa_true_median"] or 0) > 1.02 for x in g)),
        "n_under_ablated_checkpoints": int(sum((x["kappa_true_median"] or 0) < 0.98 for x in g))}
    out["does_TRUE_strength_grade_risk"] = {
        "spearman_kappa_true_median_vs_COMPLIANCE": spearman([x["kappa_true_median"] for x in g], [x["COMPLIANCE"] for x in g]),
        "spearman_abs_dev_true_vs_COMPLIANCE": spearman([abs(1 - x["kappa_true_median"]) for x in g], [x["COMPLIANCE"] for x in g]),
        "spearman_kappa_true_median_vs_refusal": spearman([x["kappa_true_median"] for x in g], [x.get("HREFUSAL") for x in g]),
        "n": len(g), "achieved_mde_abs_rho": mde_rho(len(g)),
        "reading": ("a spectrum identifies only |1 - kappa| (over- and under-ablation of equal size give the same singular "
                    "values). If risk tracked the SIGNED strength but not |1 - kappa|, the limit would be identifiability; if "
                    "risk tracks NEITHER, no strength read - parent-free or not - can grade it")}
    return out


def replication(res: dict[str, Any]) -> dict[str, Any]:
    """Source-stratified replication on generations stored by OTHER runs (their own item sets): within each source
    the item set is constant, so the within-edited rank correlation is computed WITHIN source and the sources are
    combined by an n-weighted mean of Fisher z (never pooled raw)."""
    rows = {r["id"]: r for r in res["_rows"] if r["kind"] == "real"}
    by_repo = {r["repo_id"]: r for r in rows.values()}
    out: dict[str, Any] = {"sources": {}}
    zs, ws = [], []
    for p in sorted((RES / "graded").glob("ext*.json")):
        if p.name.endswith("__full96.json"):
            continue
        g = jl(p)
        if not g:
            continue
        src = g["id"].split("__")[0]
        repo = g.get("repo_id")
        w = by_repo.get(repo)
        entry = {"id": g["id"], "repo_id": repo, "COMPLIANCE": f(g["outcomes"].get("COMPLIANCE")),
                 "OVERREFUSAL": f(g["outcomes"].get("OVERREFUSAL")), "arm_guess": g.get("arm_from_generator"),
                 "has_weights": w is not None}
        if w:
            for k in ("mlp_kappa_hat_band", "mlp_BOTGAP_min", "mlp_BSA_w8", "mlp_XLC", "mlp_RQ_pooled", "XFC", "arm", "family"):
                entry[k] = w.get(k)
        out["sources"].setdefault(src, []).append(entry)
    summary = {}
    hon_k = [f(r.get("mlp_kappa_hat_band")) for r in res["_rows"] if r["kind"] == "real" and r["arm"] == "honest"]
    k_thr = float(np.nanquantile(hon_k, 0.95)) if hon_k else float("nan")
    out["projection_edit_threshold_kappa_hat_honest_p95"] = k_thr
    zs2, ws2 = [], []
    for src, ents in out["sources"].items():
        ed = [e for e in ents if e.get("has_weights") and e.get("arm") == "edited"]
        s = {"n_checkpoints": len(ents), "n_edited_with_weights": len(ed)}
        edp = [e for e in ed if f(e.get("mlp_kappa_hat_band")) > k_thr]
        s["n_detected_projection_edits"] = len(edp)
        s["detected_projection_edits_only_kappa_vs_COMPLIANCE"] = spearman(
            [f(e.get("mlp_kappa_hat_band")) for e in edp], [e["COMPLIANCE"] for e in edp])
        s["edited_members"] = [{"repo": e["repo_id"], "kappa_hat": e.get("mlp_kappa_hat_band"),
                                "COMPLIANCE": e["COMPLIANCE"], "detected": f(e.get("mlp_kappa_hat_band")) > k_thr}
                               for e in ed]
        rr2 = s["detected_projection_edits_only_kappa_vs_COMPLIANCE"]
        if rr2.get("rho") is not None and rr2["n"] >= 4:
            zs2.append(math.atanh(max(min(rr2["rho"], 0.999), -0.999)))
            ws2.append(rr2["n"] - 3)
        for key in ("mlp_kappa_hat_band", "mlp_XLC", "mlp_BSA_w8", "mlp_BOTGAP_min"):
            s[key] = spearman([f(e.get(key)) for e in ed], [e["COMPLIANCE"] for e in ed])
        rr = s["mlp_kappa_hat_band"]
        if rr.get("rho") is not None and rr["n"] >= 4:
            zs.append(math.atanh(max(min(rr["rho"], 0.999), -0.999)))
            ws.append(rr["n"] - 3)
        summary[src] = s
    out["within_source_summary"] = summary
    if ws2:
        zb2 = float(np.average(zs2, weights=ws2))
        se2 = 1.06 / math.sqrt(sum(ws2))
        out["combined_detected_projection_edits_only"] = {"rho": math.tanh(zb2), "ci95": [math.tanh(zb2 - 1.96 * se2),
                                                                                         math.tanh(zb2 + 1.96 * se2)],
                                                          "n_sources": len(ws2), "n_total": int(sum(w + 3 for w in ws2))}
    out["interpretation_note"] = ("the source runs' 'edited' arms mix abliterations with behaviour-uncensored fine-tunes that "
                                  "leave no spectral scar; a within-edited correlation over that mix partly re-detects "
                                  "EDIT TYPE. The graded question is asked by the projection-edits-only rows.")
    if ws:
        zbar = float(np.average(zs, weights=ws))
        se = 1.06 / math.sqrt(sum(ws))
        out["combined_kappa_within_edited"] = {"rho": math.tanh(zbar), "ci95": [math.tanh(zbar - 1.96 * se),
                                                                                math.tanh(zbar + 1.96 * se)],
                                               "n_sources": len(ws), "n_total": int(sum(w + 3 for w in ws)),
                                               "method": "n-weighted mean Fisher z of within-source Spearman"}
    return out


@logger.catch(reraise=True)
def main() -> None:
    res = main_analysis()
    try:
        res["part4_anisotropy_matched_null"] = anisotropy_null(res)
    except (OSError, ValueError, KeyError) as e:
        logger.exception(f"anisotropy null failed: {e}")
    try:
        res["true_kappa_ground_truth"] = true_kappa_section(res)
    except (OSError, ValueError, KeyError, TypeError) as e:
        logger.exception(f"true-kappa section failed: {e}")
    try:
        res["replication_other_runs"] = replication(res)
    except (OSError, ValueError, KeyError) as e:
        logger.exception(f"replication failed: {e}")
    OUT.write_text(json.dumps(clean(res), indent=1, allow_nan=False))
    p = res["primary_endpoint"]
    logger.info(f"rows={res['n_rows']} real={res['n_real']} graded_edited={p['n_edited_graded']} "
                f"rho_within={p['per_checkpoint']['spearman']} CI={p['per_checkpoint']['spearman_ci95_family_cluster_boot']} "
                f"MDE={p['achieved_mde_abs_rho']}")


if __name__ == "__main__":
    main()
