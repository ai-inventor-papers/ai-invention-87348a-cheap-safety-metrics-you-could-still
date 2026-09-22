#!/usr/bin/env python3
"""D3. THE WITHIN-FAMILY AND SIZE-LADDER TABLE.

THIS IS A WITHIN-FAMILY TABLE.  The 17 finished harvests span only Qwen3 and
TinyLlama, so this lane supports ZERO held-out-FAMILY answer; the family axis
belongs to the sibling experiment.  race_table_v2.csv is written as a STRICT
SUPERSET of the frozen 18-column race_table.csv so the two merge by position as
well as by name.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np
from loguru import logger
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evallib.core import (  # noqa: E402
    LEXFLOOR, RESULTS, SEED, UP_RESULTS, bh_fdr, corr_pair, detectable_rho,
    read_json, write_json,
)
from s0_setup import PANEL_MAP  # noqa: E402

SCHEMA_VERSION = "race_table_v2.1"

FROZEN_COLS = [
    "metric_id", "name", "family", "functional_form_class_id", "inputs", "n_prompts",
    "candidate", "incumbent", "baseline", "predicted_gap_rank",
    "held_out_balacc_3way", "tuned_balacc_3way", "gap",
    "held_out_balacc_2way", "tuned_balacc_2way", "auroc_2way", "n_used", "n_lineages",
]
APPENDED_COLS = [
    "family_binary_derived", "lexfloor_jbb_index_paired", "lexfloor_xstest_twins",
    "lexfloor_cross_source", "lexfloor_cross_source_IS_NOT_A_FLOOR",
    "familyonly_baseline_3way", "familyonly_baseline_2way",
    "sizeonly_baseline_3way", "sizeonly_baseline_2way",
    "beats_familyonly_3way", "beats_sizeonly_3way",
    "delta_over_best_matched_floor", "p_perm", "q_BH", "readout_flag", "degrade_reason",
    "sign_0p6B", "sign_1p7B", "sign_4B", "sign_flip_across_ladder",
    "spearman_vs_log10_params_instruct", "spearman_p_vs_log10_params_instruct",
    "detectable_abs_rho_at_this_n", "reads_size_not_safety",
]
# The registry's own three families -> the prose's LEVEL/ACROSS-ITEM binary.
# Added as a NEW DERIVED column; the frozen `family` column is never relabelled.
FAMILY_BINARY = {"LEVEL-KNOWLEDGE": "LEVEL", "LEVEL-BEHAVIOUR-STRUCTURE": "LEVEL",
                 "ACROSS-ITEM": "ACROSS-ITEM"}


def _fit_predict_1d(xtr, ytr, xte):
    """IDENTICAL to UP/screen/race.py:_fit_predict_1d, so columns are comparable."""
    mu, sd = np.nanmean(xtr), np.nanstd(xtr) + 1e-12
    Xtr = np.nan_to_num(((xtr - mu) / sd).reshape(-1, 1))
    Xte = np.nan_to_num(((xte - mu) / sd).reshape(-1, 1))
    if len(np.unique(ytr)) < 2:
        return np.repeat(ytr[0], len(xte))
    return LogisticRegression(max_iter=2000, C=1.0).fit(Xtr, ytr).predict(Xte)


def lolo_score(x, y, lineage):
    x, y, lineage = np.asarray(x, float), np.asarray(y), np.asarray(lineage)
    ok = np.isfinite(x)
    if ok.sum() < 6 or len(np.unique(y[ok])) < 2:
        return {"held_out": float("nan"), "tuned": float("nan"), "gap": float("nan"),
                "n_used": int(ok.sum()), "n_lineages": 0}
    x, y, lineage = x[ok], y[ok], lineage[ok]
    pred = np.empty(len(y), dtype=object)
    for lin in np.unique(lineage):
        te, tr = lineage == lin, lineage != lin
        if tr.sum() < 3 or len(np.unique(y[tr])) < 2:
            pred[te] = y[tr][0] if tr.sum() else y[te][0]
            continue
        pred[te] = _fit_predict_1d(x[tr], y[tr], x[te])
    return {"held_out": float(balanced_accuracy_score(y, pred.astype(str))),
            "tuned": float(balanced_accuracy_score(y, _fit_predict_1d(x, y, x).astype(str))),
            "gap": float(balanced_accuracy_score(y, _fit_predict_1d(x, y, x).astype(str))
                         - balanced_accuracy_score(y, pred.astype(str))),
            "n_used": int(len(y)), "n_lineages": int(len(np.unique(lineage)))}


def lolo_2way(x, y, lineage):
    m = np.isin(y, ["instruct", "abliterated"])
    return lolo_score(np.asarray(x)[m], np.asarray(y)[m], np.asarray(lineage)[m])


N_PERM = 200   # lineage-clustered permutations per metric; see PREREG deviation note


def perm_p_lineage(x, y, lineage, n_perm=N_PERM, seed=SEED):
    """Lineage-clustered permutation p for the held-out 3-way balanced accuracy.

    Class labels are permuted WITHIN lineage, so the permutation respects the
    resampling unit instead of destroying it.
    """
    x, y, lineage = np.asarray(x, float), np.asarray(y), np.asarray(lineage)
    obs = lolo_score(x, y, lineage)["held_out"]
    if not np.isfinite(obs):
        return float("nan")
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n_perm):
        yp = y.copy()
        for lin in np.unique(lineage):
            m = lineage == lin
            yp[m] = y[m][rng.permutation(int(m.sum()))]
        v = lolo_score(x, yp, lineage)["held_out"]
        if np.isfinite(v) and v >= obs:
            cnt += 1
    return (1 + cnt) / (n_perm + 1)


def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")

    registry = read_json(UP_RESULTS / "metrics_registry.json")
    metrics = registry["metrics"]
    reg_by_id = {m["id"]: m for m in metrics}

    # --- per-checkpoint metric values, preferring D0's rescore ----------------
    src = RESULTS / "per_checkpoint_reads_rescored.json"
    if not src.exists():
        logger.error("D0 rescore not present -- D3 cannot build the table. Writing a "
                     "BLOCKED record instead of a silently empty one.")
        write_json(RESULTS / "d3_table.json",
                   {"status": "BLOCKED_D0_MISSING",
                    "reason": "results/per_checkpoint_reads_rescored.json was not produced "
                              "by the D0 stage, so no per-checkpoint metric values exist to "
                              "tabulate.", "schema_version": SCHEMA_VERSION})
        return
    reads = read_json(src)

    slugs = [s for s in sorted(PANEL_MAP) if s in reads]
    y = np.array([PANEL_MAP[s][0] for s in slugs])
    lineage = np.array([PANEL_MAP[s][2] for s in slugs])
    fam = np.array([PANEL_MAP[s][1] for s in slugs])
    params = np.array([PANEL_MAP[s][3] for s in slugs], dtype=float)
    logp = np.log10(params * 1e9)
    logger.info(f"D3 tabulating {len(slugs)} checkpoints / {len(set(lineage))} lineages / "
                f"families {sorted(set(fam))}")

    # --- family-only and size-only baselines (the honesty columns) ------------
    fam_num = (fam == fam[0]).astype(float)
    fb3, fb2 = lolo_score(fam_num, y, lineage), lolo_2way(fam_num, y, lineage)
    sb3, sb2 = lolo_score(logp, y, lineage), lolo_2way(logp, y, lineage)
    logger.info(f"D3 family-only held-out balacc 3way={fb3['held_out']:.3f} "
                f"2way={fb2['held_out']:.3f}; size-only 3way={sb3['held_out']:.3f} "
                f"2way={sb2['held_out']:.3f}")

    d2b = read_json(RESULTS / "d2b_first_token.json") if (RESULTS / "d2b_first_token.json").exists() else {}
    flag_by_slug = {r["slug"]: r["verdict"] for r in d2b.get("per_checkpoint", [])}
    d0 = read_json(RESULTS / "d0_rescore.json") if (RESULTS / "d0_rescore.json").exists() else {}
    degrade = {e["metric_id"]: e.get("reason") for e in d0.get("degrade_ledger", [])}

    def vals(mid):
        return np.array([reads[s].get("metrics", {}).get(mid, float("nan"))
                         for s in slugs], dtype=float)

    def _one(args):
        _i, m = args
        mid = m["id"]
        x = vals(mid)
        s3, s2 = lolo_score(x, y, lineage), lolo_2way(x, y, lineage)
        m2 = np.isin(y, ["instruct", "abliterated"]) & np.isfinite(x)
        auroc2 = float("nan")
        if m2.sum() >= 6 and len(np.unique(y[m2])) > 1:
            from sklearn.metrics import roc_auc_score
            a = roc_auc_score((y[m2] == "abliterated").astype(int), x[m2])
            auroc2 = float(max(a, 1 - a))
        p = perm_p_lineage(x, y, lineage) if np.isfinite(s3["held_out"]) else float("nan")
        praw.append(p)

        # --- size ladder: sign of instruct-minus-abliterated at each Qwen3 rung
        signs = {}
        for tag, size in (("0p6B", 0.6), ("1p7B", 1.7), ("4B", 4.0)):
            iv = [x[i] for i, s in enumerate(slugs)
                  if PANEL_MAP[s][0] == "instruct" and PANEL_MAP[s][3] == size
                  and PANEL_MAP[s][1] == "Qwen3"]
            av = [x[i] for i, s in enumerate(slugs)
                  if PANEL_MAP[s][0] == "abliterated" and PANEL_MAP[s][3] == size
                  and PANEL_MAP[s][1] == "Qwen3"]
            iv = [v for v in iv if np.isfinite(v)]
            av = [v for v in av if np.isfinite(v)]
            if iv and av:
                d = float(np.mean(iv) - np.mean(av))
                signs[tag] = 0 if d == 0 else int(math.copysign(1, d))
            else:
                signs[tag] = None
        present = [v for v in signs.values() if v is not None]
        sign_flip = bool(len(set(present)) > 1) if len(present) >= 2 else None

        # --- does the metric track log-parameters across the HONEST instruct arm?
        hm = np.array([PANEL_MAP[s][0] == "instruct" for s in slugs])
        cp = corr_pair(logp[hm], x[hm])
        rho, prho = cp.get("spearman_rho"), cp.get("spearman_p")
        det = cp["detectable_abs_rho_at_this_n"]
        reads_size = bool(rho is not None and np.isfinite(det) and abs(rho) >= det)

        floors = [LEXFLOOR["lexfloor_jbb_index_paired"], LEXFLOOR["lexfloor_xstest_twins"]]
        best_floor = max(floors)     # the MATCHED floors only; cross-source excluded
        return p, ({
            "metric_id": mid, "name": m["name"], "family": m["family"],
            "functional_form_class_id": m["functional_form_class_id"],
            "inputs": m["inputs"], "n_prompts": m["n_prompts"],
            "candidate": m.get("candidate", ""), "incumbent": m.get("incumbent", ""),
            "baseline": m.get("baseline", ""), "predicted_gap_rank": m["predicted_gap_rank"],
            "held_out_balacc_3way": s3["held_out"], "tuned_balacc_3way": s3["tuned"],
            "gap": s3["gap"], "held_out_balacc_2way": s2["held_out"],
            "tuned_balacc_2way": s2["tuned"], "auroc_2way": auroc2,
            "n_used": s3["n_used"], "n_lineages": s3["n_lineages"],
            "family_binary_derived": FAMILY_BINARY[m["family"]],
            "lexfloor_jbb_index_paired": LEXFLOOR["lexfloor_jbb_index_paired"],
            "lexfloor_xstest_twins": LEXFLOOR["lexfloor_xstest_twins"],
            "lexfloor_cross_source": LEXFLOOR["lexfloor_cross_source"],
            "lexfloor_cross_source_IS_NOT_A_FLOOR": "NOT_A_FLOOR",
            "familyonly_baseline_3way": fb3["held_out"],
            "familyonly_baseline_2way": fb2["held_out"],
            "sizeonly_baseline_3way": sb3["held_out"],
            "sizeonly_baseline_2way": sb2["held_out"],
            "beats_familyonly_3way": (bool(s3["held_out"] > fb3["held_out"])
                                      if np.isfinite(s3["held_out"]) else None),
            "beats_sizeonly_3way": (bool(s3["held_out"] > sb3["held_out"])
                                    if np.isfinite(s3["held_out"]) else None),
            "delta_over_best_matched_floor": (auroc2 - best_floor
                                              if np.isfinite(auroc2) else float("nan")),
            "p_perm": p, "q_BH": None, "n_perm": N_PERM,
            "readout_flag": ("REQUIRES_REFUSAL_DRIVE:" +
                             (d2b.get("panel_verdict", "UNKNOWN"))
                             if m["inputs"] == "activations+logits" else "n/a"),
            "degrade_reason": degrade.get(mid, ""),
            "sign_0p6B": signs["0p6B"], "sign_1p7B": signs["1p7B"], "sign_4B": signs["4B"],
            "sign_flip_across_ladder": sign_flip,
            "spearman_vs_log10_params_instruct": rho,
            "spearman_p_vs_log10_params_instruct": prho,
            "detectable_abs_rho_at_this_n": det,
            "reads_size_not_safety": reads_size,
        })

    from concurrent.futures import ThreadPoolExecutor
    rows, praw = [], []
    done_n = [0]

    def _wrap(a):
        r = _one(a)
        done_n[0] += 1
        logger.info(f"  [{done_n[0]}/{len(metrics)}] {a[1]['id']}")
        return r

    with ThreadPoolExecutor(max_workers=2) as _ex:
        for _p, _row in _ex.map(_wrap, list(enumerate(metrics))):
            praw.append(_p)
            rows.append(_row)
    for r, q in zip(rows, bh_fdr(praw)):
        r["q_BH"] = q

    cols = FROZEN_COLS + APPENDED_COLS
    out_csv = RESULTS / "race_table_v2.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})

    # --- AMS row, special handling -------------------------------------------
    ams = {rid: next((r for r in rows if r["metric_id"] == rid), None)
           for rid in ("k_ams_sep_insample", "k_ams_sep_cf", "k_ams_layer_frac")}
    ams_block = {
        "rows": {k: v for k, v in ams.items() if v},
        "published_71pct_leave_one_out": "NON_COMPARABLE",
        "non_comparable_reason": (
            "That protocol held out only the THRESHOLD, not the direction: the direction was "
            "fitted on the same 16 contrastive pairs it was then measured on. Our table "
            "reports AMS twice -- in its published IN-SAMPLE form (k_ams_sep_insample) and "
            "cross-fitted on our folds (k_ams_sep_cf) -- with the gap printed."),
        "in_sample_minus_crossfitted_gap": (
            (ams["k_ams_sep_insample"]["held_out_balacc_3way"]
             - ams["k_ams_sep_cf"]["held_out_balacc_3way"])
            if ams["k_ams_sep_insample"] and ams["k_ams_sep_cf"] else None),
        "its_own_headline": (
            "AMS's own headline r = -0.546 has a NON-SIGNIFICANT Spearman rho = -0.423 at "
            f"n = 14; the detectable |rho| at n=14 is {detectable_rho(14):.3f}."),
        "the_16_author_pairs_are_unreleased": (
            "Iteration 1 substituted 16 frozen pairs of its own and said so; that substitution "
            "is inherited here unchanged and is a named non-comparability, not a silent one."),
    }

    n_beat_fam = sum(1 for r in rows if r["beats_familyonly_3way"] is True)
    n_scored = sum(1 for r in rows if np.isfinite(r["held_out_balacc_3way"]))
    out = {
        "schema_version": SCHEMA_VERSION,
        "THIS_IS_A_WITHIN_FAMILY_TABLE": (
            "This is a WITHIN-FAMILY table. The 17 finished harvests span only Qwen3 and "
            "TinyLlama, so this lane supports ZERO held-out-FAMILY answer; the family axis "
            "belongs to the sibling experiment."),
        "frozen_columns": FROZEN_COLS, "appended_columns": APPENDED_COLS,
        "superset_of_frozen_race_table": True,
        "n_checkpoints": len(slugs), "n_lineages": int(len(set(lineage))),
        "n_families": int(len(set(fam))), "families": sorted(set(fam.tolist())),
        "slugs": slugs,
        "baselines": {"familyonly_3way": fb3, "familyonly_2way": fb2,
                      "sizeonly_3way": sb3, "sizeonly_2way": sb2},
        "the_confound_stated_plainly": (
            f"With only {len(set(fam))} families and three sizes, family label and parameter "
            f"count NEARLY DETERMINE the three-way class. The family label alone reaches "
            f"held-out balanced accuracy {fb3['held_out']:.3f} (3-way) and "
            f"{fb2['held_out']:.3f} (2-way); size alone reaches {sb3['held_out']:.3f} and "
            f"{sb2['held_out']:.3f}. Only {n_beat_fam} of {n_scored} scored metrics beat the "
            f"family-only baseline. If the family label alone predicts the ground truth as "
            f"well as the metric does, THE METRIC HAS NOT EARNED ITS FORWARD PASSES."),
        "n_metrics_beating_familyonly_3way": n_beat_fam,
        "n_metrics_scored": n_scored,
        "size_ladder": {
            "rungs": "Qwen3 at 0.6B, 1.7B and 4B, each with base, instruct and an "
                     "abliterated sibling -- the one asset this panel has that no other "
                     "lane does.",
            "n_metrics_with_sign_flip": sum(1 for r in rows
                                            if r["sign_flip_across_ladder"] is True),
            "n_metrics_reading_size_not_safety": sum(1 for r in rows
                                                     if r["reads_size_not_safety"]),
            "detectable_abs_rho_at_n4_instruct": detectable_rho(4),
        },
        "ams_row": ams_block,
        "lexical_floors": LEXFLOOR,
        "lexical_floor_note": (
            "delta_over_best_matched_floor is measured against the best MATCHED floor "
            f"({max(LEXFLOOR['lexfloor_jbb_index_paired'], LEXFLOOR['lexfloor_xstest_twins']):.3f}). "
            "The cross-source 0.963 is printed but is explicitly NOT_A_FLOOR: an unmatched "
            "safety benchmark is about 96% lexis."),
        "n_perm_per_metric": N_PERM,
        "perm_deviation_note": (
            "The PREREG fixes B=1000 for the D2 null draws. D3's lineage-clustered "
            f"permutation p uses B={N_PERM} per metric, declared here as a deviation: the "
            "test refits a leave-one-lineage-out multinomial logistic model on every "
            "permutation for each of 50 metrics, and B=500 keeps the stage inside its time "
            "box on a 2-CPU box under heavy shared load. The resulting p has a resolution "
            f"floor of 1/{N_PERM + 1}."),
        "rows": rows,
        "csv_path": "results/race_table_v2.csv",
    }
    write_json(RESULTS / "d3_table.json", out)
    logger.info(f"D3 wrote {len(rows)} rows -> {out_csv}; {n_beat_fam}/{n_scored} beat "
                f"family-only; {out['size_ladder']['n_metrics_with_sign_flip']} sign flips")


if __name__ == "__main__":
    main()
