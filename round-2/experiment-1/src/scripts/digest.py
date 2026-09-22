#!/usr/bin/env python3
"""Print a markdown digest of the final results, every number read from results/.

    venv_exp1/bin/python scripts/digest.py [tag] > results/DIGEST.md

The README and RESULTS.md quote numbers from this digest, so a reader can
regenerate every table in them from the files alone.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def f(v, nd: int = 3) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return "n/a" if not math.isfinite(v) else f"{v:.{nd}f}"
    return str(v)


def rd(res: Path, name: str, default=None):
    p = res / name
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text())


def main(tag: str = "") -> None:
    res = ROOT / "results" / tag if tag else ROOT / "results"
    sm = rd(res, "summary.json")
    out: list[str] = ["# Digest of the final results", ""]
    out.append("## Panel counts (results/summary.json)")
    for k in ("n_families_scheduled", "n_families_harvested", "families_harvested",
              "n_checkpoints_scheduled", "n_checkpoints_harvested", "n_dropped", "PARTIAL_PANEL",
              "harvest_tiers", "n_families_with_instruct_abliterated_pair", "FAMILY_AXIS_DEGRADED",
              "n_safety_lineages", "readout_chosen", "readout_bar_met", "think_trap_confirmed",
              "crossover_k", "n_metrics_beating_null_p95", "n_metrics_failing_pole_rule",
              "wall_clock_minutes", "judge_spend_usd", "gates_fired"):
        out.append(f"- `{k}`: {f(sm.get(k)) if not isinstance(sm.get(k), (list, dict)) else json.dumps(sm.get(k))}")
    out.append("- not harvested: " + "; ".join(
        f"{x['repo']} ({x['reason']})" for x in sm.get("not_harvested", [])))

    bo = rd(res, "readout_bakeoff.json")
    out += ["", "## Readout bake-off (results/readout_bakeoff.json)", "",
            "| readout | n ckpt | min AUROC | mean AUROC | min on abliterated | n below chance | "
            "invariance min | invariance mean | judge calls |", "|---|---|---|---|---|---|---|---|---|"]
    for k, v in sorted(bo.get("summary", {}).items()):
        out.append(f"| `{k}` | {v.get('n_checkpoints_scored')} | {f(v.get('min_auroc'))} | "
                   f"{f(v.get('mean_auroc'))} | {f(v.get('min_auroc_abliterated'))} | "
                   f"{v.get('n_below_chance')} | {f(v.get('invariance_min'))} | "
                   f"{f(v.get('invariance_mean'))} | {f(v.get('judge_calls_total'), 0)} |")
    out.append(f"\nchosen = `{bo.get('chosen')}`, gate = `{bo.get('gate')}`")
    fams = sorted({r['family'] for r in bo.get('table', [])})
    out.append(f"bake-off families: {fams}")
    lc = bo.get("probe_learning_curve", {})
    if lc:
        out.append(f"learning curve (diff-in-means readout, AUROC vs labelled items): mean "
                   f"{json.dumps({k: round(v, 3) for k, v in lc['mean_over_checkpoints'].items()})}"
                   f", min {json.dumps({k: round(v, 3) for k, v in lc['min_over_checkpoints'].items()})}")
    out += ["", "per-checkpoint AUROC (signed):", "",
            "| checkpoint | class | family | base rate | " + " | ".join(
                sorted(bo.get("summary", {}).keys())) + " |",
            "|---|---|---|---|" + "---|" * len(bo.get("summary", {}))]
    by: dict[str, dict] = {}
    for r in bo.get("table", []):
        by.setdefault(r["repo"], {"cls": r["cls"], "family": r["family"],
                                  "br": r["base_rate"]})[r["readout"]] = r.get("auroc")
    for repo, d in sorted(by.items(), key=lambda z: (z[1]["family"], z[0])):
        out.append(f"| {repo} | {d['cls']} | {d['family']} | {f(d['br'])} | " + " | ".join(
            f(d.get(k)) for k in sorted(bo.get("summary", {}).keys())) + " |")

    race = rd(res, "race.json")
    out += ["", "## Race (results/race.json, chosen readout)",
            f"two-way checkpoints: {race.get('n_checkpoints_in_race')}; families: "
            f"{race.get('families')}; pair families: "
            f"{race.get('families_with_instruct_abliterated_pair')}; safety lineages: "
            f"{race.get('n_independent_safety_lineages')}", "",
            f"PRIMARY holdout: {race.get('primary_holdout')}", "",
            "| metric | class | n | PRIMARY BA | primary gap | null p95 | CI (lineage boot) | "
            "LOFO BA | LOLO BA | tuned BA | AUROC 2-way | fam-sep BA |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    rows = sorted(race.get("rows_primary", []),
                  key=lambda z: -(z["primary_ba"] if isinstance(z.get("primary_ba"), float) else -9))
    for z in rows:
        out.append(f"| `{z['metric_id']}` | {z['metric_class']} | {z['n_checkpoints_with_value']} | "
                   f"{f(z.get('primary_ba'))} | {f(z.get('primary_gap'))} | "
                   f"{f(z.get('null_null_p95'))} | {f(z.get('ci_lo'))}-{f(z.get('ci_hi'))} | "
                   f"{f(z.get('lofo_ba'))} | {f(z.get('lolo_ba'))} | {f(z.get('tuned_ba'))} | "
                   f"{f(z.get('auroc_2way'))} | {f(z.get('family_separability_ba'))} |")
    fo = race.get("family_label_only_baseline", {})
    cr = race.get("card_regex_text_floor", {})
    out.append(f"\nfamily-label-only: LOFO {f(fo.get('lofo_ba'))}, LOLO {f(fo.get('lolo_ba'))}; "
               f"card-regex text floor: LOFO {f(cr.get('lofo_ba'))}, LOLO {f(cr.get('lolo_ba'))}; "
               f"metrics beating their null p95: {race.get('n_metrics_beating_null_p95')}")
    ns = race.get("nested_selection_race", {})
    out.append(f"nested selection: per-fold choice {ns.get('readout_chosen_per_held_out_group')}, "
               f"max |diff| {f(ns.get('max_abs_difference_vs_global'))}, materially disagrees: "
               f"{ns.get('materially_disagrees')}")
    bs = race.get("bsa_published_threshold_check", {})
    out.append(f"BSA 0.35 threshold: {bs.get('n_unedited_above_threshold')}/{bs.get('n_unedited')} "
               f"unedited above (FPR {f(bs.get('false_positive_rate_on_unedited'))}), "
               f"{bs.get('n_abliterated_above_threshold')}/{bs.get('n_abliterated')} abliterated above")

    ct = rd(res, "class_trend.json")
    cs = ct.get("common_support", {})
    out += ["", "## Class trend (results/class_trend.json)",
            f"- own support: corr {f(ct.get('observed_trend_corr'))}, p {f(ct.get('p_value'))}, "
            f"n {ct.get('n_metrics')}, means {json.dumps(ct.get('mean_gap_by_class'))} {ct.get('status') or ''}",
            f"- COMMON support ({cs.get('n_families')} families): corr {f(cs.get('observed_trend_corr'))}, "
            f"p {f(cs.get('p_value'))}, one-sided {f(cs.get('p_value_one_sided_predicted'))}, "
            f"n {cs.get('n_metrics')}, means {json.dumps(cs.get('mean_gap_by_class'))} {cs.get('status') or ''}"]
    for ro, t in (ct.get("by_readout") or {}).items():
        out.append(f"- readout `{ro}`: corr {f(t.get('observed_trend_corr'))}, p {f(t.get('p_value'))}, "
                   f"n {t.get('n_metrics')} {t.get('status') or ''}")

    dn = rd(res, "direction_nulls.json")
    out += ["", "## Direction nulls (results/direction_nulls.json)",
            f"verdict {dn.get('verdict')}; fitted beats within-span p95 on "
            f"{dn.get('n_fitted_beats_within_span_p95')}/{dn.get('n_checkpoints')} "
            f"(win rate {f(dn.get('win_rate'))}); draws per tier {dn.get('n_draws_per_tier')}", "",
            "| checkpoint | fitted AUROC | isotropic p95 | covariance p95 | within-span p95 | "
            "fitted pct in within-span |", "|---|---|---|---|---|---|"]
    for p in dn.get("per_checkpoint", []):
        out.append(f"| {p['repo']} | {f(p.get('fitted_auroc'))} | {f(p['isotropic'].get('p95'))} | "
                   f"{f(p['covariance'].get('p95'))} | {f(p['within_span'].get('p95'))} | "
                   f"{f(p['within_span'].get('fitted_percentile'), 1)} |")

    lf = rd(res, "lexical_floor.json")
    out += ["", "## Lexical floor", json.dumps({k: v for k, v in lf.items()
                                                if isinstance(v, (int, float))})]

    bu = rd(res, "prompt_budget.json")
    out += ["", "## Prompt budget (results/prompt_budget.json)",
            f"checkpoints {bu.get('n_checkpoints')} (two-way {bu.get('n_checkpoints_two_way')}); "
            f"crossover k (|rho|) = {bu.get('crossover_k')}, by two-way LOFO BA = "
            f"{bu.get('crossover_k_by_lofo_ba_2way')}; bootstrap {json.dumps(bu.get('crossover_k_bootstrap'))}; "
            f"gap at k=64 {f(bu.get('gap_at_k64'))}", "",
            f"crossover k by two-way LOLO BA (primary) = {bu.get('crossover_k_by_lolo_ba_2way')}", "",
            "| k | internal |rho| | black-box |rho| | internal LOLO BA | black-box LOLO BA | "
            "internal LOFO BA | black-box LOFO BA |", "|---|---|---|---|---|---|---|"]
    for c in bu.get("curves", []):
        g = lambda key: f((c.get(key) or {}).get("mean"))
        out.append(f"| {c['k']} | {g('internal_abs_spearman')} | {g('blackbox_abs_spearman')} | "
                   f"{g('internal_lolo_ba_2way')} | {g('blackbox_lolo_ba_2way')} | "
                   f"{g('internal_lofo_ba_2way')} | {g('blackbox_lofo_ba_2way')} |")

    po = rd(res, "poles.json")
    out += ["", "## Poles (results/poles.json)",
            f"failing {po.get('n_metrics_failing')}, passing {po.get('n_metrics_passing')}, real refusers "
            f"{po.get('real_blanket_refuser_repos')} (with activations: {po.get('real_refusers_with_activations')}), "
            f"wrapped instruct with battery {po.get('n_wrapped_instruct_with_battery')}",
            f"failing: {po.get('metrics_failing_the_pole_rule')}",
            f"passing: {po.get('metrics_passing_the_pole_rule')}", "",
            "| checkpoint | condition | level | spread | coupling |", "|---|---|---|---|---|"]
    for r in po.get("rows", []):
        out.append(f"| {r['repo']} | {r['condition']} | {f(r['level'], 2)} | {f(r['spread'], 2)} | "
                   f"{f(r.get('coupling_ratio'), 2) if r.get('coupling_ratio') is not None else 'UNDEFINED'} |")

    sh = rd(res, "shipped_metrics.json")
    out += ["", "## Shipped (results/shipped_metrics.json)",
            f"constrained invariant satisfied: {sh.get('constrained_invariant_satisfied')}; "
            f"internal metrics available: {sh.get('n_internal_metrics_available')}; "
            f"reason: {sh.get('constraint_unmeetable_reason')}",
            f"constrained set: {[z['metric_id'] for z in sh.get('shipped_satisfying_invariant', [])]}",
            f"ranked: {[(z['metric_id'], round(z['primary_ba'], 3), z['beats_null_p95'], z['passes_pole_rule']) for z in sh.get('ranked', [])]}",
            f"best comparator: {(sh.get('best_comparator') or {}).get('metric_id')} "
            f"{f((sh.get('best_comparator') or {}).get('primary_ba'))}"]

    s5 = rd(res, "step5_correlations.json")
    out += ["", "## Step 5 correlations"]
    for r in s5.get("rows", []):
        out.append(f"- `{r['metric_id']}`: checkpoint-level {json.dumps(r.get('checkpoint_level'))}; "
                   f"lineage-level {json.dumps(r.get('lineage_level', r.get('status')))}")
    s1 = rd(res, "step1_anchor.json")
    out += ["", "## Step 1", json.dumps(s1.get("headline"))[:1500]]
    mm = rd(res, "metamodel.json")
    out += ["", "## Metamodel", json.dumps({k: mm.get(k) for k in (
        "status", "n_checkpoints", "n_features", "leave_one_lineage_out", "leave_one_family_out")})]
    tt = rd(res, "think_trap.json")
    out += ["", "## Think trap", json.dumps({k: tt.get(k) for k in ("think_trap_confirmed", "fired")})
            + f" checked={len(tt.get('checked', []))}"]
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
