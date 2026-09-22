#!/usr/bin/env python3
"""Smoke-test the POST-RACE stages against a finished trial's race and the metric cache.

The score stage runs ~25 min on 2 shared cores; its last stages (prompt-budget
curve, pole battery, shortlist, step-5 correlations, summary) were rewritten in
session 3 and must be exercised without paying for the race again. This rebuilds
the chosen readout's metric table from results/metric_cache and runs exactly
those stages, writing to results/<tag>_post/.

Run:  OMP_NUM_THREADS=2 venv_exp1/bin/python tests/post_race_smoke.py s3pre
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from screen.pipeline2 import (  # noqa: E402
    METRIC_CACHE_VERSION, SEED, _items, build_summary, correlate_top_metrics,
    prompt_budget_curve, shortlist, write_json,
)
from screen.poles2 import pole_battery_full  # noqa: E402
from screen.registry import METRICS  # noqa: E402,F401  (import check only)


def main(tag: str) -> None:
    src = ROOT / "results" / tag
    out = ROOT / "results" / f"{tag}_post"
    out.mkdir(parents=True, exist_ok=True)
    items = _items(ROOT)
    ckpt_rows = json.loads((src / "per_checkpoint.json").read_text())
    race = json.loads((src / "race.json").read_text())
    chosen = race["chosen_readout"]
    cache = ROOT / "results" / "metric_cache"
    table: dict[str, dict] = {}
    for r in ckpt_rows:
        c = sorted(cache.glob(f"{r['slug']}__{chosen}__*__{METRIC_CACHE_VERSION}.json"),
                   key=lambda p: p.stat().st_mtime)
        if c:
            table[r["slug"]] = json.loads(c[-1].read_text())
    print(f"chosen={chosen}; table rows={len(table)} of {len(ckpt_rows)}")
    jg = json.loads((ROOT / "results" / "judge_grades.json").read_text())["per_checkpoint"]

    t = time.time()
    budget = prompt_budget_curve(ROOT, ckpt_rows, items, jg, np.random.default_rng(SEED))
    write_json(out / "prompt_budget.json", budget)
    print(f"budget {time.time()-t:.0f}s crossover={budget.get('crossover_k')} "
          f"by_ba={budget.get('crossover_k_by_lofo_ba_2way')} ci={budget.get('crossover_k_bootstrap')}")
    for c in budget.get("curves", []):
        print("  k", c["k"], "int|rho|", round(c["internal_abs_spearman"]["mean"], 3),
              "bb|rho|", round(c["blackbox_abs_spearman"]["mean"], 3) if c["blackbox_abs_spearman"]["n"] else None,
              "intBA", round(c["internal_lofo_ba_2way"]["mean"], 3) if c["internal_lofo_ba_2way"]["n"] else None)

    t = time.time()
    poles = pole_battery_full(ROOT, ckpt_rows, items, table,
                              [r["metric_id"] for r in race["rows_primary"]])
    write_json(out / "poles.json", poles)
    print(f"poles {time.time()-t:.0f}s failing={poles['n_metrics_failing']} "
          f"passing={poles['n_metrics_passing']} wrapped={poles['n_wrapped_instruct_with_battery']}")
    print("  failing:", poles["metrics_failing_the_pole_rule"])
    print("  passing:", poles["metrics_passing_the_pole_rule"])

    registry = json.loads((ROOT / "inherited" / "metrics_registry.json").read_text())["metrics"]
    ship = shortlist(race, poles, registry)
    write_json(out / "shipped_metrics.json", ship)
    print("ship invariant:", ship["constrained_invariant_satisfied"],
          [z["metric_id"] for z in ship["shipped_satisfying_invariant"]])
    corr = correlate_top_metrics(race, budget.get("targets", {}), ckpt_rows, table)
    write_json(out / "step5_correlations.json", corr)
    for rr in corr["rows"]:
        print("  step5", rr["metric_id"], rr.get("checkpoint_level"), rr.get("lineage_level", rr.get("status")))
    summ = build_summary(ROOT, ckpt_rows, race, json.loads((src / "readout_bakeoff.json").read_text()),
                         budget, poles, json.loads((src / "class_trend.json").read_text()), [], time.time())
    write_json(out / "summary.json", summ)
    print("summary keys ok:", all(k in summ for k in (
        "n_families_scheduled", "n_families_harvested", "n_checkpoints_scheduled",
        "n_checkpoints_harvested", "n_dropped", "PARTIAL_PANEL", "n_safety_lineages",
        "readout_chosen", "readout_bar_met", "think_trap_confirmed", "crossover_k",
        "wall_clock_minutes", "judge_spend_usd")))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "s3pre")
