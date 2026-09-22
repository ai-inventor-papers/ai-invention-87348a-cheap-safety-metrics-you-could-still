#!/usr/bin/env python3
"""Append the session-3 pre-registration deviations to results/prereg_deviations.json.

PREREG.json is hashed and never edited; every departure from it is recorded in
results/prereg_deviations.json with what was pre-registered, what was actually
done, why, and the evidence. Idempotent: re-running replaces entries by id.

    venv_exp1/bin/python scripts/record_deviations.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def _tier_g_evidence() -> dict:
    out: dict = {"tier_g_checkpoints": []}
    for d in sorted((ROOT / "harvest").glob("*/")):
        if not (d / "DONE_G").exists():
            continue
        try:
            meta = json.loads((d / "meta.json").read_text())
        except (OSError, json.JSONDecodeError):
            continue
        out["tier_g_checkpoints"].append({
            "repo": meta.get("repo_id", d.name), "profile": meta.get("profile"),
            "timings_s": meta.get("timings_s_tier_g"),
            "think_trap_fired": meta.get("think_trap_fired"),
            "system_prompt_merged_into_user_turn":
                meta.get("system_prompt_merged_into_user_turn")})
    bench = RES / "bench_cpu.json"
    if bench.exists():
        out["cpu_benchmark"] = json.loads(bench.read_text())
    return out


def main() -> None:
    path = RES / "prereg_deviations.json"
    doc = json.loads(path.read_text())
    new = [
        {
            "id": "D6_TIER_G_CPU_GENERATION",
            "prereg_said": "harvest.no_generation_on_new_checkpoints: greedy generation is NOT "
                           "attempted on new checkpoints; judged-refusal labels exist only for "
                           "tier-I checkpoints (and D2/D5 above).",
            "actually_done": "Sessions 2-3 ran a TIER-G CPU harvest (bf16, 2 threads, "
                             "screen/harvest_cpu_gen.py) on a prioritised queue of new-family "
                             "checkpoints: activations schema-identical to the inherited GPU "
                             "harvests, plus 80 greedy completions at max_new_tokens=96 on the SAME "
                             "gen_item_idx, graded by the same stance judge (the 24 probe prompts "
                             "only under profile=full; lite/min skip them, so b_refusal_rate_probe "
                             "is NaN there). Every such checkpoint carries harvest_tier=G and its "
                             "profile in meta.json and is flagged in results/per_checkpoint.json.",
            "why": "The pre-registered infeasibility was measured on a host at load ~290 where "
                   "eigh(1536) took 25-34 s. The same box, re-measured, runs eigh(1536) in 0.65 s "
                   "and a batch-80 greedy generation of a 0.5B model in ~32 s, so the degradation "
                   "was no longer forced. Tier G only ADDS checkpoints to the bake-off and the "
                   "race; no pre-registered bar, rule, statistic, grid or threshold changed.",
            "evidence": _tier_g_evidence(),
        },
        {
            "id": "D7_PROBE_READOUT_V2_FULL_COVERAGE",
            "prereg_said": "readout.definitions: three fixed definitions (logitgap, refmass, "
                           "greedy24). Plan variation V2 (a cross-fitted hidden-state probe) was "
                           "listed as an optional alternative.",
            "actually_done": "V2 is raced as a FOURTH readout `probe_cf` under the SAME bars and "
                             "the SAME tiebreak. Session 3 made it full-coverage and fully nested: "
                             "for each outer item fold the probe LAYER is chosen by an inner CV on "
                             "the judged items of the other folds, the logistic probe is fitted "
                             "there, and every item of the held-out fold is scored (judged or "
                             "not). Its presentation-invariance column applies the SAME per-fold "
                             "probes to the roleplay-wrapped hidden states. Every R-dependent "
                             "metric is computed under all four readouts.",
            "why": "Session 1 chose the probe layer on all labels (a mild selection leak) and "
                   "scored only the 80 judged items, mean-imputing the rest, and re-fitted a NEW "
                   "probe on the wrapped states for its invariance test -- which tests a different "
                   "readout. The nested version removes all three.",
            "evidence": {"code": "screen/analysis2.py:crossfit_probe_full"},
        },
        {
            "id": "D8_READOUT_SUBSTITUTION_FIXES",
            "prereg_said": "Across-item metrics are PARAMETRIC over R(.); compute every "
                           "R-dependent metric under all readouts.",
            "actually_done": "(a) x_presentation_invariance now compares R(plain) with R(wrapped) "
                             "for the SAME readout R (NaN where R cannot be computed under the "
                             "wrapper, i.e. greedy24); (b) the black-box baselines b_logit_gap_* "
                             "are PINNED to the true first-token logit gap under every readout; "
                             "(c) a readout unavailable on a checkpoint NaNs the R-dependent "
                             "metrics instead of silently falling back to the logit gap.",
            "why": "Session 1 substituted R on the plain side only, so under refmass/greedy24 the "
                   "invariance metric compared two different readouts; and under a probe readout "
                   "the 'black-box' rows would have become hidden-state statistics, corrupting the "
                   "requester's <=2-logit-only invariant.",
            "evidence": {"code": "screen/pipeline2.py:compute_all_metrics, R_DEPENDENT_METRICS"},
        },
        {
            "id": "D9_POLE_RULE_ON_OWN_SAFE_DIRECTION_FULL_BATTERY",
            "prereg_said": "poles.rejection_rule: a metric FAILS if it scores either real blanket "
                           "refuser or the synthetic always-refuse wrapper above the MEDIAN honest "
                           "instruct checkpoint ON ITS OWN SAFE DIRECTION.",
            "actually_done": "Implemented as written, on EVERY metric: the safe direction is "
                             "sign(median instruct - median abliterated) from the two-way race; "
                             "real poles are compared on the full battery; the synthetic wrapper "
                             "is scored by the unmodified registry code on the 48 pole items and "
                             "compared item-matched to the same 48 items under the plain "
                             "condition. Metrics a wrapper cannot move (weights, card) or that "
                             "need arrays the wrapper pass did not store are NOT_APPLICABLE to the "
                             "synthetic pole and are judged on the real poles alone.",
            "why": "Session 1 applied the rule to the weight metrics only and assumed higher = "
                   "safer for every metric, which is not the pre-registered rule.",
            "evidence": {"code": "screen/poles2.py:pole_battery_full"},
        },
        {
            "id": "D10_PROMPT_BUDGET_INTERNAL_READOUT_CROSSFIT",
            "prereg_said": "budget: internal = the leading internal readout restricted to the k "
                           "items; black-box on the identical k items; crossover k as a number "
                           "with a bootstrap CI.",
            "actually_done": "Internal = LEAVE-ONE-OUT cross-fitted harm-vs-benign separation of "
                             "last-prompt-token hidden states at 60% depth on the k items; "
                             "black-box = first-token logit-gap margin (harmful minus benign) on "
                             "the SAME items. Base checkpoints excluded. Crossover reported on "
                             "|Spearman| vs the two-sided target with a LINEAGE-cluster bootstrap "
                             "CI, and separately on two-way LOFO balanced accuracy.",
            "why": "An in-sample difference-in-means direction at hidden size >> k separates "
                   "pure noise perfectly, so an in-sample internal readout would win the budget "
                   "curve by construction. A greedy-refusal-rate black box would be graded on "
                   "the same generations as the target and is excluded for the same reason as "
                   "greedy24.",
            "evidence": {"code": "screen/pipeline2.py:prompt_budget_curve, _loo_gap"},
        },
        {
            "id": "D11_G2_PRIMARY_HOLDOUT_APPLIED",
            "prereg_said": "gates.G2_FAMILY_AXIS_DEGRADED: if fewer than 5 families survive with "
                           "a usable instruct/abliterated PAIR, run leave-one-LINEAGE-out instead "
                           "of leave-one-family-out and say so in those words.",
            "actually_done": "Applied as written (not a departure from PREREG, a departure from "
                             "session 1's code, which recorded the gate but kept leave-one-FAMILY-"
                             "out as the column every downstream step used). The race's PRIMARY "
                             "holdout is leave-one-LINEAGE-out (lineage = parent model; a "
                             "lineage's instruct and abliterated siblings are held out together); "
                             "the label-permutation null, the lineage bootstrap, the class trend, "
                             "the nested check and the shortlist all use it; leave-one-FAMILY-out "
                             "is printed beside it on every row (lofo_ba).",
            "why": "Only 3 families carry an instruct/abliterated pair (2 of them with "
                   "activations), so leave-one-family-out is undefined for every activation "
                   "metric: holding out Qwen3 leaves fewer than 4 two-way training checkpoints.",
            "evidence": {"code": "screen/pipeline2.py:run_race_tables (prim_grp)"},
        },
        {
            "id": "D12_JOSIEFIED_OOM_RERUN_48_TOKENS",
            "prereg_said": "harvest: one pass per checkpoint; generation parity with iteration 1 "
                           "(greedy, 96 new tokens on the 80 gen items).",
            "actually_done": "Goekdeniz-Guelmez/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1 "
                             "(the ONLY non-Qwen3 abliterated checkpoint with activations, i.e. the "
                             "second pair family for the activation metrics) was OOM-KILLED at "
                             "10:32 UTC at the start of generation, after its roleplay-wrapped and "
                             "N-GLARE passes had been saved. It was re-run at profile=min (plain "
                             "activation pass, persisted immediately) with max_new_tokens=48 on "
                             "the same 80 items. Its judged REFUSAL FLAGS enter the bake-off; the "
                             "checkpoint is EXCLUDED from the two-sided-target analyses (prompt-"
                             "budget curve, step-5 correlations), because a 48-token completion "
                             "earns a lower detail grade than a 96-token one.",
            "why": "The kill was caused by memory pressure in the SHARED 16 GB cgroup, to which "
                   "this artifact's own concurrent cache warm-up and smoke test contributed. "
                   "A full re-run would not fit the remaining clock.",
            "evidence": {"log": "logs/harvest_g5.log ('Killed'), logs/harvest_g6_josiefied.log"},
        },
    ]
    ids = {d["id"] for d in new}
    doc["deviations"] = [d for d in doc["deviations"] if d["id"] not in ids] + new
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, default=str))
    tmp.replace(path)
    print(f"recorded {len(new)} session-3 deviations; total {len(doc['deviations'])}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
