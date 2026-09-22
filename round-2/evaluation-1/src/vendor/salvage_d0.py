#!/usr/bin/env python3
"""SALVAGE ROUTE for the D0 rescore.

The full vendored make_outputs.py path was wedged behind gfs_reference_anchored
(dense per-layer eigsh over every parent-anchored pair) on a machine at load
average ~280-360 shared with other pipeline runs.  This script re-runs ONLY the
cheap, load-bearing path: p4_reads (judge_on=False, ~2 minutes end to end) ->
build_metric_table (with gfs={}, so gfs_parent_anchored degrades honestly with
reason REQUIRES_PARENT) -> run_race (incl. the C5 metamodel, which is cheap:
PCA+logistic on 13 points) -> class_gap_permutation_test.

It explicitly SKIPS: gfs_reference_anchored (the wedged eigsh loop), M.c2_crossover,
M.p8_output, and M.step1_claim.  It writes its outputs to its OWN results
directory (results_d0_salvage) so it can never race with the still-running
vendored process, which writes to results_d0.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

import method as M
from screen.common import HARVEST, read_json, setup_logging, slugify, write_json
from screen.race import (
    CLASSES, class_gap_permutation_test, run_race, survival_rule, transfer_dissociation,
)
from screen import panel as PN

SALVAGE_RESULTS = Path(__file__).resolve().parent.parent / "results_d0_salvage"
SALVAGE_RESULTS.mkdir(parents=True, exist_ok=True)
# Redirect every write inside method.py to the salvage directory so this run
# can never collide with the concurrently-running vendored make_outputs.py,
# which still targets results_d0.
M.RESULTS = SALVAGE_RESULTS


def main() -> None:
    setup_logging("salvage_d0")
    t0 = time.time()
    items = read_json(SALVAGE_RESULTS / "items.json")["items"]
    M._ITEMS = items
    rows_all = [e for e in PN.active_panel()]
    rows = [r for r in rows_all if (HARVEST / slugify(r["repo"]) / "DONE").exists()]
    logger.info(f"SALVAGE: scoring {len(rows)} harvested checkpoints of {len(rows_all)} in the panel")
    if not rows:
        sys.exit("nothing harvested yet")

    cards = read_json(M.ROOT / "data" / "model_cards.json") if (M.ROOT / "data" / "model_cards.json").exists() else {}
    reads, gtinfo = M.p4_reads(rows, items, cards, judge_on=False)
    logger.info(f"SALVAGE: p4_reads done at {time.time() - t0:.1f}s, {len(reads)} reads")

    slugs = [s for s in reads if reads[s]["class"] in CLASSES]
    y = np.array([reads[s]["class"] for s in slugs])
    lineage = np.array([reads[s]["lineage"] for s in slugs])
    logger.info(f"SALVAGE: {len(slugs)} scored checkpoints / {len(set(lineage))} lineages / "
                f"classes {sorted(set(y.tolist()))}")

    # gfs_reference_anchored is the SKIPPED, wedged step: it needs a dense per-layer
    # eigsh (2560x2560, ~37 layers x every parent-anchored pair) which is exactly
    # what stalled the vendored run under load average ~280-360.  gfs={} makes
    # build_metric_table degrade gfs_parent_anchored to NaN honestly instead of
    # blocking everything else.
    gfs: dict[str, float] = {}
    tbl = M.build_metric_table(reads, slugs, gfs)
    feats = np.array([reads[s]["features"] for s in slugs], dtype=float)

    race_rows = run_race(tbl, y, lineage, feats)
    logger.info(f"SALVAGE: run_race done at {time.time() - t0:.1f}s")
    perm = class_gap_permutation_test(race_rows)
    inc = [r for r in race_rows if r["incumbent"] and np.isfinite(r["held_out_balacc_3way"])]
    bar = max((r["held_out_balacc_3way"] for r in inc), default=float("nan"))
    surv = survival_rule(race_rows, bar if np.isfinite(bar) else 0.0)
    diss = transfer_dissociation(race_rows)
    M._write_race_csv(race_rows)
    write_json(SALVAGE_RESULTS / "race.json", {"rows": race_rows, "survival": surv,
                                               "class_gap_permutation_test": perm,
                                               "transfer_dissociation": diss})
    per_ckpt = {s: {"repo": reads[s]["repo"], "class": reads[s]["class"],
                     "lineage": reads[s]["lineage"], "metrics": reads[s]["metrics"],
                     "diagnostics": reads[s]["diagnostics"]} for s in reads}
    write_json(SALVAGE_RESULTS / "per_checkpoint_reads.json", per_ckpt)

    census = read_json(SALVAGE_RESULTS / "lineage_census.json") if (SALVAGE_RESULTS / "lineage_census.json").exists() else {}
    summary = {
        "route": "salvage_p4reads_only",
        "verdict": "SALVAGE_ROUTE -- gfs_reference_anchored, c2_crossover, p8_output and "
                   "step1_claim were SKIPPED for time; see degrade_ledger",
        "branch_safety_arm": census.get("branch"),
        "independent_safety_tuned_lineages": census.get("independent_safety_tuned_lineages"),
        "n_checkpoints_scored": len(slugs),
        "n_lineages_scored": int(len(set(lineage))),
        "n_checkpoints_harvested": len(rows),
        "n_panel_total": len(rows_all),
        "PARTIAL_PANEL": len(rows) < len(rows_all),
        "incumbent_bar_recomputed_3way": bar,
        "promoted_to_iter2": surv["promoted_to_iter2"],
        "judge_cost_usd": gtinfo["judge"]["cumulative_cost_usd"],
        "skipped_steps": ["gfs_reference_anchored", "M.c2_crossover", "M.p8_output", "step1_claim"],
        "wall_clock_minutes": round((time.time() - t0) / 60, 1),
    }
    write_json(SALVAGE_RESULTS / "summary.json", summary)
    logger.info(f"SALVAGE DONE in {summary['wall_clock_minutes']} min")
    for k, v in summary.items():
        logger.info(f"  {k}: {v}")


if __name__ == "__main__":
    main()
