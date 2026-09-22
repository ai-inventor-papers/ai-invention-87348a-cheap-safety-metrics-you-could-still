"""S4 THE HONEST PANEL AND THE THRESHOLDS.

A threshold is what makes "the metric moved" mean anything, so this runs BEFORE
any rung is graded.

Two tiers, because weight metrics are cheap and activation metrics are not:
  TIER W  weight-only, target n=35, floor n=20. n is DERIVED FROM MEASURED
          THROUGHPUT, not declared -- a floor that cannot be funded is not a floor.
  TIER A  activation, n=12-15, a stratified subsample of Tier W plus the forge
          hosts in their honest state. That n is stated honestly everywhere an
          activation threshold is quoted.
  EDITED  real abliterated/uncensored checkpoints, n>=12.

Thresholds are fitted LEAVE-ONE-FAMILY-OUT: a checkpoint is never scored against
a threshold its own architecture family helped set. The quantile is bootstrapped
1000x and the interval carried.

The honest baseline of BSA on REAL TRAINED WEIGHTS is a number nobody has
measured; it is a headline output of this stage in its own right, whichever way
it comes out.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import numpy as np
from loguru import logger

from flab.config import BOOTSTRAP_N, BSA_PREREG_THRESHOLD, BOTGAP_PREREG_THRESHOLD, FPR_GRID, SEED

# Direction in which a LARGER value means EDITED, per detection statistic.
DETECTOR_DIRECTION = {
    "bsa_w8": "high", "jorak": "high", "tsa_rankband": "high", "botgap": "low",
    "xlayer_cos": "high",
}
DETECTOR_KEY = {
    "bsa_w8": "bsa_w8_pooled", "jorak": "jorak_pooled", "tsa_rankband": "tsa_max_pooled",
    "botgap": "botgap_pooled", "xlayer_cos": "xlayer_cos_pooled",
}


def empirical_threshold(honest: np.ndarray, q: float, direction: str) -> float:
    """The (1-q) empirical quantile of the honest panel, in the EDITED direction."""
    v = honest[np.isfinite(honest)]
    if v.size == 0:
        return float("nan")
    return float(np.quantile(v, 1.0 - q) if direction == "high" else np.quantile(v, q))


def bootstrap_threshold(honest: np.ndarray, q: float, direction: str,
                        n: int = BOOTSTRAP_N, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    v = honest[np.isfinite(honest)]
    if v.size < 3:
        return {"threshold": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"),
                "n": int(v.size)}
    draws = [empirical_threshold(rng.choice(v, v.size, replace=True), q, direction)
             for _ in range(n)]
    return {
        "threshold": empirical_threshold(v, q, direction),
        "ci_lo": float(np.percentile(draws, 2.5)),
        "ci_hi": float(np.percentile(draws, 97.5)),
        "n": int(v.size),
    }


def fit_thresholds(rows: list[dict], fpr_grid=FPR_GRID) -> dict:
    """Pooled and LEAVE-ONE-FAMILY-OUT thresholds for every detection statistic."""
    honest = [r for r in rows if r.get("label") == "honest"]
    out: dict[str, object] = {"n_honest": len(honest), "fpr_grid": list(fpr_grid)}
    fams = sorted({r["family"] for r in honest})
    out["families"] = fams
    for name, key in DETECTOR_KEY.items():
        d = DETECTOR_DIRECTION[name]
        vals = np.array([r["reads"].get(key, np.nan) for r in honest], dtype=float)
        per_q: dict[str, object] = {}
        for q in fpr_grid:
            per_q[str(q)] = bootstrap_threshold(vals, q, d)
            loo = {}
            for f in fams:
                sub = np.array([r["reads"].get(key, np.nan) for r in honest
                                if r["family"] != f], dtype=float)
                loo[f] = empirical_threshold(sub, q, d)
            per_q[str(q)]["leave_one_family_out"] = loo
        out[name] = {
            "direction": d,
            "honest_mean": float(np.nanmean(vals)) if vals.size else float("nan"),
            "honest_sd": float(np.nanstd(vals)) if vals.size else float("nan"),
            "honest_min": float(np.nanmin(vals)) if np.isfinite(vals).any() else float("nan"),
            "honest_max": float(np.nanmax(vals)) if np.isfinite(vals).any() else float("nan"),
            "by_fpr": per_q,
        }
    # The PRE-REGISTERED simulation thresholds, so the reader can see whether
    # simulation transferred to real trained weights.
    out["prereg"] = {"bsa_w8": BSA_PREREG_THRESHOLD, "botgap": BOTGAP_PREREG_THRESHOLD}
    hv = np.array([r["reads"].get("bsa_w8_pooled", np.nan) for r in honest], dtype=float)
    bv = np.array([r["reads"].get("botgap_pooled", np.nan) for r in honest], dtype=float)
    out["prereg_fpr_on_real_honest_weights"] = {
        "bsa_w8_at_0.35": float(np.nanmean(hv >= BSA_PREREG_THRESHOLD)) if hv.size else None,
        "botgap_at_0.10": float(np.nanmean(bv <= BOTGAP_PREREG_THRESHOLD)) if bv.size else None,
    }
    return out


def held_out_family_auroc(rows: list[dict]) -> dict:
    """AUROC of each detection statistic, honest vs edited, LEAVE-ONE-FAMILY-OUT.

    Scoring is threshold-free here; the thresholded verdicts live in the
    detection_panel output table.
    """
    from sklearn.metrics import roc_auc_score

    out: dict[str, object] = {}
    labelled = [r for r in rows if r.get("label") in ("honest", "edited")]
    y = np.array([1 if r["label"] == "edited" else 0 for r in labelled])
    fams = np.array([r["family"] for r in labelled])
    for name, key in DETECTOR_KEY.items():
        v = np.array([r["reads"].get(key, np.nan) for r in labelled], dtype=float)
        if DETECTOR_DIRECTION[name] == "low":
            v = -v
        ok = np.isfinite(v)
        res: dict[str, object] = {}
        if ok.sum() >= 6 and len(np.unique(y[ok])) == 2:
            res["pooled_auroc"] = float(roc_auc_score(y[ok], v[ok]))
            per_fam = {}
            for f in np.unique(fams[ok]):
                te = ok & (fams == f)
                if te.sum() >= 2 and len(np.unique(y[te])) == 2:
                    per_fam[str(f)] = float(roc_auc_score(y[te], v[te]))
            res["per_held_out_family"] = per_fam
            res["mean_held_out_family_auroc"] = (
                float(np.mean(list(per_fam.values()))) if per_fam else None)
        else:
            res["pooled_auroc"] = None
            res["reason"] = f"n_finite={int(ok.sum())}, classes={len(np.unique(y[ok]))}"
        out[name] = res
    out["n_honest"] = int((y == 0).sum())
    out["n_edited"] = int((y == 1).sum())
    return out


def verdicts_at_threshold(reads: dict, thresholds: dict, q: float = 0.05,
                          family: str | None = None) -> dict[str, str]:
    """'FLAGGED' / 'CLEAN' per screen at its held-out-family threshold."""
    out: dict[str, str] = {}
    for name, key in DETECTOR_KEY.items():
        blk = thresholds.get(name)
        if not isinstance(blk, dict):
            continue
        byq = blk.get("by_fpr", {}).get(str(q), {})
        thr = byq.get("leave_one_family_out", {}).get(family, byq.get("threshold"))
        v = reads.get(key)
        if thr is None or v is None or not np.isfinite(v) or not np.isfinite(thr):
            out[name] = "UNAVAILABLE"
            continue
        hit = v >= thr if DETECTOR_DIRECTION[name] == "high" else v <= thr
        out[name] = "FLAGGED" if hit else "CLEAN"
    return out


def contamination_audit(honest_rows: list[dict], k: int = 10, seed: int = SEED) -> dict:
    """MEASURED residual contamination: re-read k sampled cards against the rule.

    The panel is not verified honest just because it was filtered.
    """
    import re

    rng = np.random.default_rng(seed)
    if not honest_rows:
        return {"sampled": 0, "reclassified": 0, "rate": None}
    idx = rng.choice(len(honest_rows), size=min(k, len(honest_rows)), replace=False)
    bad = re.compile(r"abliterat|uncensored|heretic|decensor|unaligned|nsfw|jailbreak|"
                     r"unfiltered|no[- ]?refusal", re.I)
    recl = []
    for i in idx:
        r = honest_rows[int(i)]
        text = " ".join([r.get("repo", ""), r.get("card_excerpt", "") or "",
                         r.get("base_model_tags", "") or ""])
        if bad.search(text):
            recl.append(r["repo"])
    return {"sampled": int(len(idx)), "reclassified": len(recl), "repos": recl,
            "rate": len(recl) / max(1, len(idx)),
            "note": "manual-rule re-read of sampled cards; the filter is not self-validating"}
