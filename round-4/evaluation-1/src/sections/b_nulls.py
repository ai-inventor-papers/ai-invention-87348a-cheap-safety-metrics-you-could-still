#!/usr/bin/env python3
"""STEP B: race null labels (B1), direction-null counts (B2), above-chance decomposition (B3)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from io_utils import EVAL2, EXP1, PROVENANCE, SEED, WS, dump, get, src, wilson  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs/b_nulls.log"), rotation="30 MB", level="DEBUG")

RACE = EXP1 / "results/race.json"
PIPE = "iter_2/gen_art/gen_art_experiment_1/screen/pipeline2.py"
AN2 = "iter_2/gen_art/gen_art_experiment_1/screen/analysis2.py"
NULL_NAME = "within-lineage label-permutation null"
NULL_DEF = ("role labels (instruct vs abliterated) are permuted WITHIN each lineage, the identical "
            "leave-one-lineage-out balanced-accuracy pipeline is re-run on every permutation, and the 95th "
            "percentile of the permuted BA is the bar (analysis2.py:label_permutation_null L501-535, called "
            "with group=primary holdout=lineage, n_perm=min(n_perm,300), pipeline2.py L1402-1403)")


def b1() -> dict:
    rows = get(RACE, "rows_primary")
    holdout = get(RACE, "primary_holdout")
    calib = EXP1 / "results/logo_null_calibration.json"
    out = []
    for i, r in enumerate(rows):
        if r.get("null_null_p95") is None:
            continue
        beats = r["primary_ba"] is not None and r["primary_ba"] > r["null_null_p95"]
        ties = r["primary_ba"] is not None and abs(r["primary_ba"] - r["null_null_p95"]) < 1e-9
        if not (beats or r["metric_id"] in ("w_bsa_w8_k4",)):
            continue
        out.append({
            "metric_id": r["metric_id"], "readout": r["readout"], "primary_ba_lolo": r["primary_ba"],
            "null_type": NULL_NAME, "resampling_unit": "role labels permuted within lineage",
            "holdout": "leave-one-lineage-out", "n_perm_requested": 300,
            "n_perm_usable": r["null_n_draws_usable"], "null_mean": r["null_null_mean"],
            "p95": r["null_null_p95"], "p_value": r["null_p_value"],
            "status": "BEATS p95" if beats else "TIES p95 (does not beat)",
            "source": src(RACE, f"rows_primary.{i}.{{primary_ba,null_null_p95,null_n_draws_usable,null_p_value}}"),
        })
        PROVENANCE.append([src(RACE, f"rows_primary.{i}"), "null_null_p95", r["null_null_p95"]])
    return {
        "null_name": NULL_NAME, "null_definition": NULL_DEF, "primary_holdout": holdout,
        "n_metrics_beating_p95": get(RACE, "n_metrics_beating_null_p95"),
        "rows": out,
        "logo_null_calibration": {"empirical_mean": get(calib, "empirical_logo_null_mean"),
                                  "empirical_sd": get(calib, "empirical_logo_null_sd"),
                                  "design": get(calib, "design"),
                                  "note": "leave-one-group-out BA on uninformative labels sits near 0.40, not 0.50"},
        "naming_note": ("the per_checkpoint_predictions column called 'anisonull' in race.json is a FEATURE "
                        "permutation (x values shuffled once, pipeline2.py L1387-1390), used only for display; "
                        "it is not an anisotropy null and not the null behind any race claim"),
        "old_wording": "family / anisotropy-matched null (paper wording flagged by the iter-3 review)",
        "new_wording": (f"{NULL_NAME}: {NULL_DEF}"),
        "sources": [f"{AN2}:L501-535", f"{PIPE}:L1387-1403"],
    }


def b2() -> dict:
    ev = EVAL2 / "results/d2_controls.json"
    agg = get(ev, "aggregate")
    dn = EXP1 / "results/direction_nulls.json"
    defs = {
        "span": "within-item-span random direction: centred TRAIN-fold activations times a Gaussian vector, "
                "unit-normed, sign fixed on train folds, scored out of fold (d2_controls.py:_draw 'span')",
        "aniso": "anisotropy-matched random direction: Ledoit-Wolf covariance square-root applied to an isotropic draw",
        "iso": "isotropic Gaussian random unit direction",
        "perm": "label-permutation null on the fitted cross-fitted direction (B_perm=1000)",
        "white": "LDA-whitened refit scored against its OWN within-span null",
    }
    table = []
    for ro, label in (("content_last", "harmful vs plain_benign, last prompt token (primary read)"),
                      ("twin_xstest", "xstest_contrast vs benign_alarming (twin pairs)"),
                      ("content_first", "harmful vs plain_benign, first token")):
        a = agg[ro]
        k, n = a["SURV_span_k"], a["n_checkpoints"]
        table.append({"count": f"{k}/{n}", "k": k, "n": n, "wilson95": wilson(k, n),
                      "readout": ro, "contrast": label, "null": "within-span random direction (NULL_span), B=1000",
                      "per_tier_k": {t: a.get(f"SURV_{t}_k") for t in ("span", "aniso", "iso", "perm", "white")},
                      "source": src(ev, f"aggregate.{ro}.SURV_span_k")})
        PROVENANCE.append([src(ev, f"aggregate.{ro}.SURV_span_k"), "", k])
    k = get(dn, "n_fitted_beats_within_span_p95"); n = get(dn, "n_checkpoints")
    table.append({"count": f"{k}/{n}", "k": k, "n": n, "wilson95": wilson(k, n),
                  "readout": "iter-2 exp1 harm direction at depth 0.6 (probe_cf harvest)",
                  "contrast": "harmful vs benign (plain+alarming), exp1 G8 gate",
                  "null": "within-item-span random direction, 1000 draws/tier, sign fixed on train folds",
                  "source": src(dn, "n_fitted_beats_within_span_p95")})
    ha = agg.get("harm_vs_allbenign")
    if ha:
        table.append({"count": f"{ha['SURV_span_k']}/{ha['n_checkpoints']}", "k": ha["SURV_span_k"],
                      "n": ha["n_checkpoints"], "wilson95": wilson(ha["SURV_span_k"], ha["n_checkpoints"]),
                      "readout": "harm_vs_allbenign", "contrast": "harmful vs all benign incl. contrast",
                      "null": "within-span random direction", "source": src(ev, "aggregate.harm_vs_allbenign.SURV_span_k")})
    return {"table": table, "null_definitions": defs,
            "print_together_note": "16/17, 17/17, 9/17 and 9/20 are always printed together; they are different "
                                   "contrasts/readouts/panels, not replications of one number",
            "reconciliation": ("9/20 (exp1, 20 checkpoints incl. base models, harmful vs ALL benign at probe layer) and "
                               "16/17 (eval1, 17 checkpoints, harmful vs plain_benign at fixed depth 0.6, last token) use "
                               "different panels, contrasts and item sets; the 9/17 is the FIRST-token readout")}


def b3() -> dict:
    ev = EVAL2 / "results/d2_controls.json"
    a = get(ev, "aggregate.content_last")
    fit, span, white = a["mean_AUROC_xf"], a["mean_null_span_mean"] if "mean_null_span_mean" in a else None, a["mean_AUROC_white_xf"]
    if span is None:
        pcs = get(ev, "per_checkpoint")
        span = float(np.mean([p["readouts"]["content_last"]["nulls"]["NULL_span"]["null_mean"] for p in pcs]))
    share_span = (span - 0.5) / (fit - 0.5)
    share_white = (fit - white) / (fit - 0.5)
    # lineage-cluster bootstrap over per-checkpoint AUROCs (ratio of means)
    pcs = get(ev, "per_checkpoint")
    lin_of = {r["slug"]: r["lineage"] for r in get(EXP1 / "results/per_checkpoint.json", "")}
    F, S, W, L = [], [], [], []
    for p in pcs:
        c = p["readouts"]["content_last"]
        F.append(c["AUROC_xf"]); S.append(c["nulls"]["NULL_span"]["null_mean"]); W.append(c["AUROC_white_xf"])
        L.append(lin_of.get(p["slug"], p["slug"]))
    F, S, W, L = map(np.asarray, (F, S, W, L))
    # checkpoint-mean reproduction
    rep = {"fit": float(F.mean()), "span": float(S.mean()), "white": float(W.mean())}
    groups = sorted(set(L.tolist()))
    rng = np.random.default_rng(SEED)
    bs, bw = [], []
    for _ in range(5000):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([np.where(L == groups[i])[0] for i in pick])
        f, s, w = F[idx].mean(), S[idx].mean(), W[idx].mean()
        bs.append((s - 0.5) / (f - 0.5)); bw.append((f - w) / (f - 0.5))
    return {
        "inputs": {"AUROC_fit_mean": fit, "AUROC_span_null_mean": span, "AUROC_whitened_mean": white,
                   "recomputed_from_per_checkpoint": rep,
                   "sources": [src(ev, "aggregate.content_last.mean_AUROC_xf"),
                               src(ev, "aggregate.content_last.mean_null_span_mean (or per_checkpoint NULL_span.null_mean)"),
                               src(ev, "aggregate.content_last.mean_AUROC_white_xf")]},
        "random_span_share": share_span, "whitening_removal_share": share_white,
        "formulas": {"random_span_share": "(AUC_span - 0.5)/(AUC_fit - 0.5)",
                     "whitening_removal_share": "(AUC_fit - AUC_white)/(AUC_fit - 0.5)"},
        "lineage_bootstrap_ci95": {"random_span_share": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                                   "whitening_removal_share": [float(np.percentile(bw, 2.5)), float(np.percentile(bw, 97.5))],
                                   "B": 5000, "n_lineages": len(groups), "n_checkpoints": int(len(F)),
                                   "note": f"only {len(groups)} lineages: the CI is a descriptive band, not inference"},
        "sentence": (f"About {100*share_span:.0f}% of the harm direction's above-chance AUROC is reachable by a random "
                     f"direction inside the item span, and whitening removes about {100*share_white:.0f}%."),
    }


@logger.catch(reraise=True)
def main() -> dict:
    res = {"B1_race_nulls": b1(), "B2_direction_nulls": b2(), "B3_above_chance": b3()}
    for r in res["B1_race_nulls"]["rows"]:
        logger.info(f"B1 {r['metric_id']}: BA {r['primary_ba_lolo']:.3f} vs p95 {r['p95']:.3f} ({r['status']})")
    for r in res["B2_direction_nulls"]["table"]:
        logger.info(f"B2 {r['count']} {r['readout']} wilson {np.round(r['wilson95'], 3)}")
    b = res["B3_above_chance"]
    logger.info(f"B3 span share {b['random_span_share']:.3f} whiten {b['whitening_removal_share']:.3f} "
                f"CI {b['lineage_bootstrap_ci95']}")
    dump(res, WS / "results/B_nulls.json")
    return res


if __name__ == "__main__":
    main()
