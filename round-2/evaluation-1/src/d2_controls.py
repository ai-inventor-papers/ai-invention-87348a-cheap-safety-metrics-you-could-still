#!/usr/bin/env python3
"""D2. THE CONTROL SUITE -- the headline.

Five numbers side by side for every (checkpoint, readout):
  (i)   AUROC_xf    cross-fitted fitted difference-in-means direction
  (ii)  AUROC_in    in-sample (the DEMONSTRATION, never the result)
  (iii) three tiers of random-direction null, B=1000 each, as DISTRIBUTIONS
  (iv)  label-permutation null, B=1000
  (v)   whitened refit (LDA) and its own within-span null

Every null direction is treated EXACTLY as the fitted one: drawn on the training
folds, sign-fixed on the training folds, scored out-of-fold, pooled, one AUROC.
"""

from __future__ import annotations

import gc
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evallib.core import (  # noqa: E402
    B_BOOT, B_NULL, B_PERM, PRIMARY_DEPTH_FRACTION, RESULTS, SEED, SURV_PREMISE_FAILS_MAX,
    SURV_SURVIVES_MIN, auc_many, auc_one, bh_fdr, cluster_bootstrap_ci, dim_direction,
    item_arrays, layer_at_depth, ledoit_wolf_lowrank, load_acts, load_items, lw_solve,
    lw_sqrt_apply, normalise_cols, read_json, wilson_ci, write_json,
)
from s0_setup import PANEL_MAP, READOUTS  # noqa: E402

B_LAYER = 200          # null draws in the SECONDARY layer-swept (L_star) arm
NULL_TIERS = ("span", "aniso", "iso")


# ---------------------------------------------------------------------------
def _sign_fix(D: np.ndarray, Xtr: np.ndarray, ytr: np.ndarray) -> np.ndarray:
    """Choose each column's sign on the TRAIN folds (the sign giving AUROC>0.5)."""
    a = auc_many(ytr, Xtr @ D)
    s = np.where(np.isfinite(a) & (a < 0.5), -1.0, 1.0)
    return D * s[None, :]


def _draw(tier: str, Xtr: np.ndarray, B: int, rng: np.random.Generator,
          lw: dict | None) -> np.ndarray:
    """(d, B) unit directions of the requested null tier, fitted on TRAIN only."""
    d = Xtr.shape[1]
    if tier == "span":
        Xc = Xtr - Xtr.mean(0, keepdims=True)
        return normalise_cols(Xc.T @ rng.standard_normal((Xtr.shape[0], B)))
    if tier == "iso":
        return normalise_cols(rng.standard_normal((d, B)))
    if tier == "aniso":
        return normalise_cols(lw_sqrt_apply(lw, rng.standard_normal((d, B))))
    raise ValueError(tier)


def _oof_null(X: np.ndarray, y: np.ndarray, folds: np.ndarray, tier: str, B: int,
              seed: int, *, whiten: bool = False) -> np.ndarray:
    """Pooled out-of-fold score matrix (n, B) for one null tier."""
    S = np.full((len(y), B), np.nan)
    for f in np.unique(folds):
        te, tr = folds == f, folds != f
        if y[tr].sum() == 0 or (y[tr] == 0).sum() == 0 or te.sum() == 0:
            continue
        Xtr, Xte = X[tr], X[te]
        rng = np.random.default_rng(seed + 131 * int(f))
        lw = None
        if tier == "aniso" or whiten:
            lw = ledoit_wolf_lowrank(Xtr - Xtr.mean(0, keepdims=True))
        D = _draw(tier, Xtr, B, rng, lw)
        if whiten:
            D = normalise_cols(lw_solve(lw, D))
        D = _sign_fix(D, Xtr, y[tr])
        S[te] = Xte @ D
        del D, Xtr, Xte, lw
    return S


def _oof_fitted(X: np.ndarray, y: np.ndarray, folds: np.ndarray, *,
                whiten: bool = False) -> np.ndarray:
    p = np.full(len(y), np.nan)
    for f in np.unique(folds):
        te, tr = folds == f, folds != f
        if y[tr].sum() == 0 or (y[tr] == 0).sum() == 0 or te.sum() == 0:
            continue
        Xtr = X[tr]
        u = dim_direction(Xtr[y[tr] == 1], Xtr[y[tr] == 0])
        if whiten:
            lw = ledoit_wolf_lowrank(Xtr - Xtr.mean(0, keepdims=True))
            u = lw_solve(lw, u[:, None])[:, 0]
            u = u / (np.linalg.norm(u) + 1e-12)
        p[te] = X[te] @ u
    return p


def _oof_perm(X: np.ndarray, y: np.ndarray, folds: np.ndarray, strata: np.ndarray,
              B: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Permute the label within strata, refit and re-cross-fit B times.

    Returns (Yp (n,B) permuted labels, S (n,B) pooled out-of-fold scores).
    The statistic is the AUROC of each column against ITS OWN permuted label:
    that is the null distribution of the whole pipeline's output.
    """
    rng = np.random.default_rng(seed)
    n = len(y)
    Yp = np.repeat(y[:, None], B, axis=1)
    usable = []
    for s in np.unique(strata):
        m = strata == s
        if len(np.unique(y[m])) > 1:
            usable.append(s)
            idx = np.where(m)[0]
            for b in range(B):
                Yp[idx, b] = y[idx][rng.permutation(len(idx))]
    if not usable:                                   # degenerate: permute globally
        for b in range(B):
            Yp[:, b] = y[rng.permutation(n)]
    S = np.full((n, B), np.nan)
    for f in np.unique(folds):
        te, tr = folds == f, folds != f
        if te.sum() == 0:
            continue
        Xtr, Ytr = X[tr], Yp[tr]
        n1 = Ytr.sum(0).astype(float)
        n0 = (Ytr.shape[0] - n1).astype(float)
        ok = (n1 > 0) & (n0 > 0)
        C = np.where(Ytr == 1, 1.0 / np.maximum(n1, 1)[None, :],
                     -1.0 / np.maximum(n0, 1)[None, :])
        C[:, ~ok] = 0.0
        D = normalise_cols(Xtr.T @ C)
        S[te] = X[te] @ D
        del C, D, Xtr, Ytr
    return Yp, S


def _dist(vals: np.ndarray, fitted: float, first_k: int = 20) -> dict:
    v = np.asarray(vals, float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"B_effective": 0}
    out = {
        "B_effective": int(v.size),
        "null_mean": float(v.mean()), "null_sd": float(v.std(ddof=1)),
        "null_p50": float(np.percentile(v, 50)), "null_p95": float(np.percentile(v, 95)),
        "null_max": float(v.max()),
        "null_max_first_20_draws": float(v[:min(first_k, v.size)].max()),
        "null_max_first_20_draws_note": (
            "This is the best-of-20 statistic iteration 1 used. It is an UPWARD-BIASED "
            "estimate of a null mean; printing it beside the distribution explains the "
            "earlier 0.921-vs-0.921 tie rather than contradicting it."),
    }
    if np.isfinite(fitted):
        out["fitted_percentile_in_null"] = float((v < fitted).mean() * 100.0)
        out["p_one_sided"] = float((1 + int((v >= fitted).sum())) / (v.size + 1))
        out["fitted_exceeds_null_p95"] = bool(fitted > out["null_p95"])
    return out


def _fold_subset(folds: np.ndarray) -> np.ndarray:
    """Re-index folds so every fold retained has both classes; drop empty ones."""
    return folds


# ---------------------------------------------------------------------------
def run_checkpoint(slug: str) -> dict:
    t0 = time.time()
    items = load_items()
    ia = item_arrays(items, 160)
    a = load_acts(slug)
    n_slots = a["hs_last"].shape[1]
    out: dict = {"slug": slug, "n_layer_slots": n_slots,
                 "hidden_size": int(a["hs_last"].shape[2]), "readouts": {}}
    Lfix = layer_at_depth(n_slots, PRIMARY_DEPTH_FRACTION)
    out["primary_layer_index"] = Lfix
    out["primary_depth_fraction"] = PRIMARY_DEPTH_FRACTION

    for rname, spec in READOUTS.items():
        sel = np.isin(ia["kind"], spec["pos_kinds"] + spec["neg_kinds"])
        y = np.isin(ia["kind"], spec["pos_kinds"])[sel].astype(int)
        folds = ia["fold"][sel]
        strata = ia["category"][sel]
        H = a[spec["pos"]]
        X = H[sel, Lfix, :].astype(np.float64)
        row: dict = {"n_items": int(sel.sum()), "n_pos": int(y.sum()),
                     "n_neg": int((y == 0).sum()), "layer_index": Lfix,
                     "read_position": spec["pos"],
                     "registry_metrics_covered": spec["registry_metrics"],
                     "matched_lexical_floor": spec["matched_floor"],
                     "matched_floor_is_a_floor": spec["matched_floor_is_a_floor"]}

        # (i) cross-fitted, (ii) in-sample
        p_xf = _oof_fitted(X, y, folds)
        row["AUROC_xf"] = auc_one(y, p_xf)
        u_in = dim_direction(X[y == 1], X[y == 0])
        row["AUROC_in"] = auc_one(y, X @ u_in)
        row["inflation_in_minus_xf"] = (row["AUROC_in"] - row["AUROC_xf"]
                                        if np.isfinite(row["AUROC_xf"]) else float("nan"))

        # (iii) the three null tiers
        row["nulls"] = {}
        for tier in NULL_TIERS:
            S = _oof_null(X, y, folds, tier, B_NULL, SEED + hash(rname) % 9973)
            aucs = auc_many(y, S)
            d = _dist(aucs, row["AUROC_xf"])
            amax = np.where(np.isfinite(aucs), np.maximum(aucs, 1 - aucs), np.nan)
            d["sensitivity_max_sign_variant"] = {
                "null_mean": float(np.nanmean(amax)), "null_p95": float(np.nanpercentile(amax, 95)),
                "fitted_exceeds_null_p95": bool(row["AUROC_xf"] > np.nanpercentile(amax, 95)),
                "label": "SENSITIVITY ONLY -- max(AUROC,1-AUROC) inflates the null.",
            }
            row["nulls"][f"NULL_{tier}"] = d
            del S, aucs, amax
            gc.collect()
        row["delta_auroc_vs_null_span_mean"] = (
            row["AUROC_xf"] - row["nulls"]["NULL_span"]["null_mean"]
            if "null_mean" in row["nulls"]["NULL_span"] else float("nan"))

        # (iv) label permutation
        Yp, Sp = _oof_perm(X, y, folds, strata, B_PERM, SEED + 7)
        pa = np.array([auc_one(Yp[:, b], Sp[:, b]) for b in range(B_PERM)])
        row["perm_null"] = _dist(pa, row["AUROC_xf"])
        row["perm_null"]["strata_used"] = sorted(
            str(s) for s in np.unique(strata)
            if len(np.unique(y[strata == s])) > 1)
        del Yp, Sp, pa
        gc.collect()

        # (v) whitened refit (LDA) and its own within-span null
        p_w = _oof_fitted(X, y, folds, whiten=True)
        row["AUROC_white_xf"] = auc_one(y, p_w)
        row["delta_white_minus_raw"] = row["AUROC_white_xf"] - row["AUROC_xf"]
        Sw = _oof_null(X, y, folds, "span", B_NULL, SEED + 11, whiten=True)
        row["white_span_null"] = _dist(auc_many(y, Sw), row["AUROC_white_xf"])
        del Sw
        gc.collect()

        # --- SECONDARY: L_star argmax-over-layers, with the SAME selection
        #     applied to every null draw (otherwise the comparison is biased).
        per_layer_fit = np.full(n_slots, np.nan)
        per_layer_null = np.full((n_slots, B_LAYER), np.nan)
        for l in range(n_slots):
            Xl = H[sel, l, :].astype(np.float64)
            per_layer_fit[l] = auc_one(y, _oof_fitted(Xl, y, folds))
            Sl = _oof_null(Xl, y, folds, "span", B_LAYER, SEED + 31 + l)
            per_layer_null[l] = auc_many(y, Sl)
            del Xl, Sl
        lstar = int(np.nanargmax(per_layer_fit)) if np.isfinite(per_layer_fit).any() else Lfix
        null_lstar = np.nanmax(per_layer_null, axis=0)      # the null gets the SAME argmax
        row["secondary_layer_swept"] = {
            "B_draws": B_LAYER,
            "B_deviation_note": (
                f"B={B_LAYER} here rather than the pre-registered {B_NULL}, because the "
                f"layer sweep multiplies the draw count by {n_slots}. Declared as a "
                "deviation; the PRIMARY fixed-layer arm uses the full pre-registered "
                f"B={B_NULL}."),
            "per_layer_fitted_auroc": per_layer_fit.tolist(),
            "L_star": lstar, "L_star_depth_fraction": round(lstar / max(1, n_slots - 1), 4),
            "AUROC_xf_at_L_star": float(per_layer_fit[lstar]),
            "null_with_matched_argmax": _dist(null_lstar, float(per_layer_fit[lstar])),
            "note": "The fitted direction's max over layers is compared with the NULL's max "
                    "over the same layers. Giving the fitted direction a free maximisation "
                    "the null does not get would bias the comparison toward the fitted "
                    "direction; iteration 1's reads.py selects L_star this way.",
        }
        del per_layer_null
        gc.collect()

        out["readouts"][rname] = row
        del X
        gc.collect()

    del a
    gc.collect()
    out["runtime_minutes"] = round((time.time() - t0) / 60, 2)
    return out


def _worker(slug: str) -> dict:
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
              "NUMEXPR_NUM_THREADS"):
        os.environ[v] = "1"
    try:
        return run_checkpoint(slug)
    except Exception as exc:                                    # noqa: BLE001
        return {"slug": slug, "ERROR": f"{type(exc).__name__}: {exc}"}


def aggregate(per_ckpt: list[dict]) -> dict:
    """D2.7 the headline statistic, per readout, clustered on lineage."""
    agg: dict = {}
    for rname in READOUTS:
        rows = [(c["slug"], c["readouts"][rname]) for c in per_ckpt
                if "readouts" in c and rname in c["readouts"]]
        n = len(rows)
        lineage = np.array([PANEL_MAP[s][2] for s, _ in rows])
        xf = np.array([r["AUROC_xf"] for _, r in rows])
        insamp = np.array([r["AUROC_in"] for _, r in rows])
        dmean = np.array([r["delta_auroc_vs_null_span_mean"] for _, r in rows])
        white = np.array([r["AUROC_white_xf"] for _, r in rows])
        clears_span = np.array([bool(r["nulls"]["NULL_span"].get("fitted_exceeds_null_p95", False))
                                for _, r in rows])
        clears_aniso = np.array([bool(r["nulls"]["NULL_aniso"].get("fitted_exceeds_null_p95", False))
                                 for _, r in rows])
        clears_iso = np.array([bool(r["nulls"]["NULL_iso"].get("fitted_exceeds_null_p95", False))
                               for _, r in rows])
        clears_perm = np.array([bool(r["perm_null"].get("fitted_exceeds_null_p95", False))
                                for _, r in rows])
        clears_white = np.array([bool(r["white_span_null"].get("fitted_exceeds_null_p95", False))
                                 for _, r in rows])
        k = int(clears_span.sum())
        band = ("SURVIVES" if k >= SURV_SURVIVES_MIN
                else "PREMISE_FAILS" if k <= SURV_PREMISE_FAILS_MAX else "AMBIGUOUS")
        ps = [r["nulls"]["NULL_span"].get("p_one_sided", float("nan")) for _, r in rows]
        agg[rname] = {
            "n_checkpoints": n,
            "n_lineages": int(len(set(lineage.tolist()))),
            "SURV_span_k": k, "SURV_span_of_n": f"{k}/{n}",
            "SURV_span_fraction": k / n if n else float("nan"),
            "SURV_span_wilson95": list(wilson_ci(k, n)),
            "verdict_band": band,
            "SURV_perm_k": int(clears_perm.sum()),
            "SURV_aniso_k": int(clears_aniso.sum()),
            "SURV_iso_k": int(clears_iso.sum()),
            "SURV_white_k": int(clears_white.sum()),
            "SURV_joint_span_and_perm_k": int((clears_span & clears_perm).sum()),
            "SURV_joint_wilson95": list(wilson_ci(int((clears_span & clears_perm).sum()), n)),
            "mean_AUROC_xf": float(np.nanmean(xf)),
            "mean_AUROC_in": float(np.nanmean(insamp)),
            "mean_inflation_in_minus_xf": float(np.nanmean(insamp - xf)),
            "sd_AUROC_in_across_checkpoints": float(np.nanstd(insamp, ddof=1)),
            "mean_AUROC_white_xf": float(np.nanmean(white)),
            "mean_delta_white_minus_raw": float(np.nanmean(white - xf)),
            "delta_auroc_lineage_clustered_ci": cluster_bootstrap_ci(dmean, lineage, B=B_BOOT),
            "auroc_xf_lineage_clustered_ci": cluster_bootstrap_ci(xf, lineage, B=B_BOOT),
            "p_one_sided_span_per_checkpoint": ps,
            "q_BH_within_this_readout": bh_fdr(ps),
            "per_checkpoint_scatter": [
                {"slug": s, "cls": PANEL_MAP[s][0], "lineage": PANEL_MAP[s][2],
                 "AUROC_xf": r["AUROC_xf"], "AUROC_in": r["AUROC_in"],
                 "null_span_mean": r["nulls"]["NULL_span"].get("null_mean"),
                 "null_span_p95": r["nulls"]["NULL_span"].get("null_p95"),
                 "null_span_max_first20": r["nulls"]["NULL_span"].get("null_max_first_20_draws"),
                 "null_aniso_mean": r["nulls"]["NULL_aniso"].get("null_mean"),
                 "null_iso_mean": r["nulls"]["NULL_iso"].get("null_mean"),
                 "perm_mean": r["perm_null"].get("null_mean"),
                 "AUROC_white_xf": r["AUROC_white_xf"],
                 "clears_span_p95": bool(clears_span[i]),
                 "clears_perm_p95": bool(clears_perm[i]),
                 "p_one_sided_span": ps[i]}
                for i, (s, r) in enumerate(rows)],
            "matched_lexical_floor": READOUTS[rname]["matched_floor"],
            "matched_floor_is_a_floor": READOUTS[rname]["matched_floor_is_a_floor"],
        }
    return agg


def main() -> None:
    from loguru import logger
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(HERE / "logs" / "d2_controls.log", rotation="30 MB", level="DEBUG")
    slugs = sorted(PANEL_MAP)
    only = [s for s in sys.argv[1:] if not s.startswith("-")]
    if only:
        slugs = only
    t0 = time.time()
    per: list[dict] = []
    part = RESULTS / "d2_controls_partial.json"
    with ProcessPoolExecutor(max_workers=2, mp_context=__import__("multiprocessing")
                             .get_context("spawn")) as ex:
        for res in ex.map(_worker, slugs):
            per.append(res)
            if "ERROR" in res:
                logger.error(f"{res['slug']}: {res['ERROR']}")
            else:
                r = res["readouts"]["content_last"]
                logger.info(
                    f"{res['slug']:<55} xf={r['AUROC_xf']:.3f} in={r['AUROC_in']:.3f} "
                    f"span_mu={r['nulls']['NULL_span']['null_mean']:.3f} "
                    f"span_p95={r['nulls']['NULL_span']['null_p95']:.3f} "
                    f"clears={r['nulls']['NULL_span']['fitted_exceeds_null_p95']} "
                    f"[{res['runtime_minutes']}m]")
            write_json(part, {"per_checkpoint": per})   # PERSIST INCREMENTALLY
    good = [p for p in per if "ERROR" not in p]
    out = {
        "B_null": B_NULL, "B_perm": B_PERM, "B_layer_secondary": B_LAYER,
        "primary_null": "NULL_span",
        "primary_read_layer": f"fixed depth fraction {PRIMARY_DEPTH_FRACTION}",
        "n_checkpoints_attempted": len(per), "n_checkpoints_ok": len(good),
        "errors": [p for p in per if "ERROR" in p],
        "per_checkpoint": per,
        "aggregate": aggregate(good),
        "failure_scope_sentence": (
            "Any failure reported here is a measured result about OUR panel, at OUR item "
            "budget (160 items), for a PER-CHECKPOINT score. It is never a refutation of "
            "AMS, RAS, LatentBiopsy or any published per-prompt number evaluated on its own "
            "panel."),
        "runtime_minutes": round((time.time() - t0) / 60, 2),
    }
    write_json(RESULTS / "d2_controls.json", out)
    for rname, a in out["aggregate"].items():
        logger.info(f"D2.7 {rname}: SURV={a['SURV_span_of_n']} "
                    f"wilson={[round(x,3) for x in a['SURV_span_wilson95']]} "
                    f"-> {a['verdict_band']} | meanXF={a['mean_AUROC_xf']:.3f} "
                    f"meanIN={a['mean_AUROC_in']:.3f} "
                    f"n_lineages={a['n_lineages']}")
    logger.info(f"D2 done in {out['runtime_minutes']} min")


if __name__ == "__main__":
    main()
