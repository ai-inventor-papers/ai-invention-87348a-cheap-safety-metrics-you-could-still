#!/usr/bin/env python3
"""CPU-ONLY deliverable builder: harvest on disk -> reads -> race -> output contract.

Identical analysis path to `method.py` (it imports the very same functions), but
it never touches the GPU, never re-harvests and never runs the stage gates, so it
can run alongside a live harvest without contending for the card. Re-run it at
any time; it always scores whatever checkpoints currently carry a DONE marker.
"""

from __future__ import annotations

import sys
import time

import numpy as np
from loguru import logger

import method as M
from screen.common import HARVEST, RESULTS, read_json, setup_logging, sha256_file, slugify, write_json
from screen.race import (
    CLASSES, class_gap_permutation_test, run_race, survival_rule, transfer_dissociation,
)
from screen import panel as PN


def main() -> None:
    setup_logging("make_outputs")
    t0 = time.time()
    items = read_json(RESULTS / "items.json")["items"]
    M._ITEMS = items
    rows_all = [e for e in PN.active_panel()]
    rows = [r for r in rows_all if (HARVEST / slugify(r["repo"]) / "DONE").exists()]
    logger.info(f"scoring {len(rows)} harvested checkpoints of {len(rows_all)} in the panel")
    if not rows:
        sys.exit("nothing harvested yet")

    cards = read_json(M.ROOT / "data" / "model_cards.json") if (M.ROOT / "data" / "model_cards.json").exists() else {}
    reads, gtinfo = M.p4_reads(rows, items, cards, judge_on=True)
    st4 = M.stage4_gate(reads)
    write_json(RESULTS / "stage4_anchor_gate.json", st4)

    slugs = [s for s in reads if reads[s]["class"] in CLASSES]
    y = np.array([reads[s]["class"] for s in slugs])
    lineage = np.array([reads[s]["lineage"] for s in slugs])
    logger.info(f"{len(slugs)} scored checkpoints / {len(set(lineage))} lineages / "
                f"classes {sorted(set(y.tolist()))}")

    f5 = M.f5_weight_instrument_report(reads)
    write_json(RESULTS / "f5_weight_instrument.json", f5)
    gfs = M.gfs_reference_anchored(reads, rows)
    tbl = M.build_metric_table(reads, slugs, gfs)
    feats = np.array([reads[s]["features"] for s in slugs], dtype=float)

    step1 = {}
    need = {k: (slugify(k) if (HARVEST / slugify(k) / "DONE").exists() else None)
            for k in ("Qwen/Qwen3-4B", "Qwen/Qwen3-4B-SafeRL", "DreamFast/qwen3-4b-heretic",
                      "Qwen/Qwen3-4B-Base")}
    if all(need[k] for k in ("Qwen/Qwen3-4B", "Qwen/Qwen3-4B-SafeRL", "DreamFast/qwen3-4b-heretic")):
        from screen.step1 import step1_claim
        step1 = step1_claim(need["Qwen/Qwen3-4B"], need["Qwen/Qwen3-4B-SafeRL"],
                            need["DreamFast/qwen3-4b-heretic"], need["Qwen/Qwen3-4B-Base"])
        h = step1["headline"]
        logger.info(f"STEP-1 CLAIM: {h['mean_first_principal_angle_deg_last_prompt_token']:.1f} deg "
                    f"cos {h['mean_cosine_between_mean_difference_vectors']:.3f} -> {h['verdict']}")
    else:
        step1 = {"status": "anchor lineage incomplete", "resolved": need}
    write_json(RESULTS / "step1_claim.json", step1)

    race_rows = run_race(tbl, y, lineage, feats)
    inc = [r for r in race_rows if r["incumbent"] and np.isfinite(r["held_out_balacc_3way"])]
    bar = max((r["held_out_balacc_3way"] for r in inc), default=float("nan"))
    bar2 = max((r["held_out_balacc_2way"] for r in inc
                if np.isfinite(r["held_out_balacc_2way"])), default=float("nan"))
    surv = survival_rule(race_rows, bar if np.isfinite(bar) else 0.0)
    surv["incumbent_rows"] = [{"metric_id": r["metric_id"], "incumbent": r["incumbent"],
                               "held_out_3way": r["held_out_balacc_3way"],
                               "held_out_2way": r["held_out_balacc_2way"]} for r in inc]
    surv["incumbent_bar_2way"] = bar2
    perm = class_gap_permutation_test(race_rows)
    diss = transfer_dissociation(race_rows)
    cross = M.c2_crossover(reads, y, lineage, slugs)
    M._write_race_csv(race_rows)
    write_json(RESULTS / "race.json", {"rows": race_rows, "survival": surv,
                                       "class_gap_permutation_test": perm,
                                       "transfer_dissociation": diss,
                                       "prompt_budget_crossover": cross})
    write_json(RESULTS / "per_checkpoint_reads.json",
               {s: {"repo": reads[s]["repo"], "class": reads[s]["class"],
                    "lineage": reads[s]["lineage"], "metrics": reads[s]["metrics"],
                    "diagnostics": reads[s]["diagnostics"]} for s in reads})

    census = read_json(RESULTS / "lineage_census.json") if (RESULTS / "lineage_census.json").exists() else {}
    summary = {
        "verdict": M._verdict(st4, surv, diss),
        "branch_safety_arm": census.get("branch"),
        "independent_safety_tuned_lineages": census.get("independent_safety_tuned_lineages"),
        "n_checkpoints_scored": len(slugs),
        "n_lineages_scored": int(len(set(lineage))),
        "n_checkpoints_harvested": len(rows),
        "n_panel_total": len(rows_all),
        "PARTIAL_PANEL": len(rows) < len(rows_all),
        "incumbent_bar_recomputed_3way": bar,
        "incumbent_bar_recomputed_2way": bar2,
        "promoted_to_iter2": surv["promoted_to_iter2"],
        "lexical_floor": read_json(RESULTS / "items.json").get("lexical_floor"),
        "stage3_branch": (read_json(RESULTS / "stage3_instrument_gate.json").get("branch")
                          if (RESULTS / "stage3_instrument_gate.json").exists() else None),
        "stage3_honest_bsa_on_real_weights": (
            read_json(RESULTS / "stage3_instrument_gate.json").get("honest_bsa_w8")
            if (RESULTS / "stage3_instrument_gate.json").exists() else None),
        "f5_bsa_false_positive_rate_honest_panel":
            f5.get("w_bsa_w8_k1", {}).get("false_positive_rate_on_honest_panel"),
        "f5_bsa_threshold_free_auroc": f5.get("w_bsa_w8_k1", {}).get("threshold_free_auroc"),
        "stage4_branch": st4["branch"],
        "crossover_n": cross["crossover_n"],
        "judge_cost_usd": gtinfo["judge"]["cumulative_cost_usd"],
        "registry_sha256_at_end": sha256_file(RESULTS / "metrics_registry.json"),
        "step1_verdict": step1.get("headline", {}).get("verdict", "not computed"),
        "wall_clock_minutes": round((time.time() - t0) / 60, 1),
    }
    reg = (RESULTS / "metrics_registry.sha256")
    if reg.exists():
        summary["registry_sha256_at_start"] = reg.read_text().strip()
        summary["registry_unchanged"] = (summary["registry_sha256_at_start"]
                                         == summary["registry_sha256_at_end"])
    write_json(RESULTS / "summary.json", summary)

    M.p8_output(race_rows=race_rows, tbl=tbl, slugs=slugs, reads=reads, y=y, lineage=lineage,
                gtruth=gtinfo["ground_truth"],
                extras={"step1": step1, "crossover": cross, "summary": summary})
    for k, v in summary.items():
        logger.info(f"  {k}: {v}")


if __name__ == "__main__":
    main()
