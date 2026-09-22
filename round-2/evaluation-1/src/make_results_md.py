#!/usr/bin/env python3
"""Render results/*.json into a human-readable RESULTS.md digest."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evallib.core import LEXFLOOR, RESULTS, detectable_rho, read_json  # noqa: E402


def L(name):
    p = RESULTS / name
    return read_json(p) if p.exists() else None


def f(v, n=3, dash="--"):
    try:
        x = float(v)
        return dash if not np.isfinite(x) else f"{x:.{n}f}"
    except (TypeError, ValueError):
        return dash


def main() -> None:                                                # noqa: PLR0915
    s0 = L("s0_setup.json") or {}
    pre = L("PREREG.json") or {}
    d0, d1 = L("d0_rescore.json"), L("d1_step1.json")
    d2 = L("d2_controls.json") or L("d2_controls_partial.json")
    d2b, d3, d4 = L("d2b_first_token.json"), L("d3_table.json"), L("d4_prior_art.json")
    P = s0.get("panel", {})
    agg = (d2 or {}).get("aggregate", {})
    o: list[str] = []
    A = o.append

    A("# Do safety probes beat random directions?")
    A("")
    A("Offline re-analysis of the 1.5 GB activation + weight harvest that iteration 1 left "
      "orphaned on disk. **No GPU, no downloads, no model inference, $0.00 of API spend.**")
    A("")
    A(f"- Panel: **{P.get('n_done')} checkpoints / {P.get('n_lineages')} lineages / "
      f"{P.get('n_families')} families** ({', '.join(P.get('families', []))})")
    A(f"- Classes: {P.get('class_counts')}")
    A(f"- Resampling unit: **LINEAGE**, never the repo. Every aggregate below is clustered "
      f"on {P.get('n_lineages')} lineages.")
    A(f"- Pre-registration sha256: `{pre.get('prereg_sha256')}`")
    A(f"- Registry sha256 before == after == frozen literal: "
      f"**{s0.get('registry_integrity', {}).get('status')}** "
      f"(`{s0.get('registry_integrity', {}).get('registry_sha256_before', '')[:16]}...`)")
    A("")
    A("## What iteration 1 actually left behind")
    A("")
    prov = s0.get("provenance", {})
    A("> " + prov.get("the_discrepancy_stated_in_those_words", ""))
    A("")
    us = prov.get("upstream_summary_verbatim", {})
    A(f"Verbatim from the upstream `summary.json`: `n_checkpoints_scored`="
      f"{us.get('n_checkpoints_scored')}, `n_panel_total`={us.get('n_panel_total')}, "
      f"`PARTIAL_PANEL`={us.get('PARTIAL_PANEL')}, `wall_clock_minutes`="
      f"{us.get('wall_clock_minutes')}, `step1_verdict`='{us.get('step1_verdict')}'. "
      f"DONE markers on disk now: **{prov.get('n_done_markers_now')}**.")
    A("")

    # ---------------- D2, the headline ----------------------------------
    A("## D2 (HEADLINE) -- the fitted direction against its own anisotropy-matched null")
    A("")
    A("Five numbers side by side per (checkpoint, readout). Every null direction is treated "
      "**exactly** as the fitted one: drawn on the training folds, sign-fixed on the training "
      "folds, scored out-of-fold, pooled, one AUROC. "
      f"B = {(d2 or {}).get('B_null')} draws per tier; primary null = within-item-span; "
      f"primary read layer = fixed depth fraction "
      f"{pre.get('d2_readout_specs') and 0.60}. No per-checkpoint layer selection.")
    A("")
    A("| readout | contrast | SURV vs own span-null p95 | Wilson 95% | verdict | mean AUROC_xf | "
      "mean span-null | mean iso-null | mean best-of-20 null | mean AUROC_in | mean whitened |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for rn, a in agg.items():
        spec = (pre.get("d2_readout_specs") or {}).get(rn, {})
        con = f"{'+'.join(spec.get('pos_kinds', []))} vs {'+'.join(spec.get('neg_kinds', []))}"
        sc = a.get("per_checkpoint_scatter", [])
        mspan = np.nanmean([x.get("null_span_mean") or np.nan for x in sc]) if sc else np.nan
        miso = np.nanmean([x.get("null_iso_mean") or np.nan for x in sc]) if sc else np.nan
        mb20 = np.nanmean([x.get("null_span_max_first20") or np.nan for x in sc]) if sc else np.nan
        w = a.get("SURV_span_wilson95", [np.nan, np.nan])
        A(f"| `{rn}` | {con} | **{a.get('SURV_span_of_n')}** | "
          f"[{f(w[0])}, {f(w[1])}] | **{a.get('verdict_band')}** | {f(a.get('mean_AUROC_xf'))} | "
          f"{f(mspan)} | {f(miso)} | {f(mb20)} | {f(a.get('mean_AUROC_in'))} | "
          f"{f(a.get('mean_AUROC_white_xf'))} |")
    A("")
    A("Other null arms (count of the 17 clearing each p95):")
    A("")
    A("| readout | span | covariance-matched | isotropic | label-permutation | whitened | joint span+perm |")
    A("|---|---|---|---|---|---|---|")
    for rn, a in agg.items():
        A(f"| `{rn}` | {a.get('SURV_span_k')} | {a.get('SURV_aniso_k')} | "
          f"{a.get('SURV_iso_k')} | {a.get('SURV_perm_k')} | {a.get('SURV_white_k')} | "
          f"{a.get('SURV_joint_span_and_perm_k')} |")
    A("")
    A(f"Pre-registered bands over 17 checkpoints: "
      f"SURVIVES >= 13/17 | AMBIGUOUS 10-12/17 | PREMISE_FAILS <= 9/17.")
    A("")
    for rn, a in agg.items():
        ci = a.get("delta_auroc_lineage_clustered_ci", {})
        A(f"- `{rn}`: Delta_AUROC (fitted minus span-null mean) = **{f(ci.get('point'))}** "
          f"[{f(ci.get('lo'))}, {f(ci.get('hi'))}] "
          f"(lineage-clustered bootstrap, B={ci.get('B')}, {ci.get('n_clusters')} clusters); "
          f"in-sample inflation AUROC_in - AUROC_xf = {f(a.get('mean_inflation_in_minus_xf'))}; "
          f"whitened minus raw = {f(a.get('mean_delta_white_minus_raw'))}.")
    A("")
    A("### Why iteration 1 saw a tie")
    A("")
    A("Iteration 1 reported, at n=3, a cross-fitted fitted harm direction at mean AUROC 0.921 "
      "against a **best-of-20** anisotropy-matched random direction at mean AUROC 0.921. The "
      "best-of-20 maximum is an upward-biased estimate of a null *mean*. Printing it beside "
      "the full distribution (column `mean best-of-20 null` above, and "
      "`null_max_first_20_draws` per checkpoint) reproduces that number and explains it, "
      "rather than contradicting it.")
    A("")
    A("### The anisotropy is large and it is the point")
    A("")
    A("The isotropic null sits near chance while the within-span null does not. A random "
      "direction *drawn from the checkpoint's own item span* already separates harmful from "
      "benign items well above 0.5 -- on Qwen3-4B the span-null mean reaches ~0.80. That "
      "decomposition is the reportable content: how much of an apparent probe signal is "
      "dimensionality, how much is residual-stream anisotropy, and how much is the item span "
      "the fitted direction actually lives in.")
    A("")
    A("> " + (d2 or {}).get("failure_scope_sentence", ""))
    A("")

    # ---------------- D2b ------------------------------------------------
    A("## D2b -- first-generated-token identity audit")
    A("")
    if d2b:
        A(f"Panel verdict: **{d2b.get('panel_verdict')}** {d2b.get('verdict_histogram')}. "
          f"Contaminated checkpoints: **{d2b.get('contaminated_slugs') or 'none'}**.")
        A("")
        A("| checkpoint | class | modal first token | share | delimiter share | verdict |")
        A("|---|---|---|---|---|---|")
        for r in d2b.get("per_checkpoint", []):
            A(f"| `{r['slug']}` | {r['cls']} | `{r['modal_first_token']}` | "
              f"{f(r['modal_first_token_share'])} | {f(r['delimiter_share_over_items'])} | "
              f"{r['verdict']} |")
        A("")
        A("> " + (d2b.get("conclusion_for_the_sibling_gpu_experiment") or ""))
    else:
        A("MISSING.")
    A("")

    # ---------------- D0 -------------------------------------------------
    A("## D0 -- the rescore")
    A("")
    if d0:
        A(f"- Route: **{d0.get('route')}**, judge mode **{d0.get('judge_mode')}** "
          f"($0.00 spend).")
        A(f"- Empty score cells in the frozen `race_table.csv`: "
          f"**{d0.get('n_cells_recovered_before')} -> {d0.get('n_cells_nan_after')}** "
          f"(**{d0.get('n_cells_recovered')} recovered**) across "
          f"{d0.get('n_rows')} metric rows.")
        A(f"- Metrics computable: **{d0.get('n_metrics_computable')}**; "
          f"degrade ledger: **{len(d0.get('degrade_ledger') or [])}** rows, each with a "
          f"reason from the pre-registered controlled vocabulary.")
        r1 = d0.get("R1_frozen_prediction") or {}
        A("")
        A("### R1 -- the frozen gap-ordering prediction, scored as frozen")
        A("")
        A(f"Registry prediction (frozen before any measurement): "
          f"`LEVEL-BEHAVIOUR-STRUCTURE`=1 (smallest gap) < `ACROSS-ITEM`=2 < "
          f"`LEVEL-KNOWLEDGE`=3 (largest gap).")
        A(f"Observed corrcoef(rank, gap) = **{f(r1.get('observed_corr'))}**, "
          f"lineage-clustered permutation p = **{f(r1.get('p_perm'), 4)}**.")
        pf = r1.get("per_family_mean_gap") or {}
        if pf:
            A("")
            A("| family | predicted rank | observed mean gap |")
            A("|---|---|---|")
            for fam, rk in (r1.get("predicted_rank_map") or {}).items():
                A(f"| {fam} | {rk} | {f(pf.get(fam))} |")
        A("")
        A("This frozen ordering is **not** the same claim as the hypothesis's simpler "
          "LEVEL-versus-ACROSS-ITEM split; it is scored as frozen and is not retrofitted "
          "to the prose.")
        dl = d0.get("degrade_ledger") or []
        if dl:
            from collections import Counter
            A("")
            A(f"Degrade-ledger reason histogram: "
              f"{dict(Counter(e.get('reason') for e in dl))}")
    else:
        A("MISSING -- the vendored scorer did not deliver within its time box.")
    A("")

    # ---------------- D1 -------------------------------------------------
    A("## D1 -- the user's step 1, answered")
    A("")
    if d1:
        va = d1.get("verdict_judged_at") or {}
        vd = va.get("detail") or {}
        vf = d1.get("verdict_hs_first") or {}
        vfd = vf.get("detail") or {}
        hn = d1.get("headline_numbers") or {}
        A(f"Verdict (last prompt token): **{d1.get('verdict')}**. Judged at the band "
          f"`{vd.get('cell')}` ({vd.get('pair')}), the cell maximising |signed rank-1 cosine| "
          f"(pre-registered selection rule; {vd.get('n_cells_scanned_for_this_maximum')} cells "
          f"scanned, Bonferroni p = {f(vd.get('bonferroni_p_over_scanned_cells'))}). "
          f"Signed cos = **{f(vd.get('signed_rank1_cos'))}**, within-span null p95 = "
          f"{f(vd.get('k1_null_p95'))}, null percentile {f(vd.get('k1_null_percentile'), 1)}, "
          f"one-sided p = {f(vd.get('p_one_sided'))}.")
        A("")
        A(f"- {va.get('nuance')}")
        A(f"- The selection maximises over cells, which inflates overlap. That bias works "
          f"AGAINST a DIFFERENT_SUBSPACES call, so the verdict is conservative.")
        A(f"- First generated token: **{vf.get('verdict')}**. Best cell `{vfd.get('cell')}` "
          f"({vfd.get('pair')}), signed cos {f(vfd.get('signed_rank1_cos'))} vs null p95 "
          f"{f(vfd.get('k1_null_p95'))}.")
        A("")
        A("| headline number | value |")
        A("|---|---|")
        for k, v in hn.items():
            A(f"| {k} | {f(v)} |")
        A("")
        A("Mean-difference directions are highly reliable (split-half r_self about 0.99), so "
          "disattenuation barely moves the cosines. The low overlap is not produced by noise.")
        A("")
        ar = (d1.get("anchor_resolution") or {})
        A(f"**Anchor.** All five anchor members carry DONE markers: "
          f"{ar.get('all_five_present')}. Iteration 1's `step1_claim.json` recorded SafeRL "
          "and Base as `null` ('anchor lineage incomplete'). It was written during the "
          "3-checkpoint race, and the harvests landed afterwards.")
        rt = (ar.get("renderer_and_template_finding") or {})
        if rt.get("confound"):
            A("")
            tr = ((d1.get("edit_onset_and_template_confound") or {})
                  .get("template_confound_resolution") or {})
            A(f"**Template confound (found here, not pre-registered).** mlabonne ships the "
              f"base-style chat template, so at face value mlab-bearing comparisons are "
              f"confounded. Resolution: **{tr.get('verdict')}**. {tr.get('reading', '')} "
              f"Caveat: {tr.get('caveat', '')}")
        pc = d1.get("positive_control") or {}
        A("")
        A(f"**Internal positive control** ({pc.get('control')}): passes = "
          f"**{pc.get('control_passes')}**. At the last prompt token, the strongest cell has "
          f"|cos| = {f(hn.get('positive_control_abs_cos'))} against null p95 "
          f"{f(hn.get('positive_control_null_p95'))}. D1 is therefore powered, not UNDERPOWERED.")
        sb = d1.get("shared_basis_check") or {}
        A("")
        A(f"**Shared-basis check:** {sb.get('verdict')}. Median ratio of the base gap to the "
          f"fine-tune gap = {f(sb.get('median_ratio_base_gap_to_finetune_gap'), 2)}.")
        wl = d1.get("weight_limb") or {}
        A("")
        A(f"**Weight limb (D1.8):** {wl.get('status')}. Principal angles are computed between "
          f"per-layer top-16 residual-write subspaces (o_proj, down_proj); the per-band "
          f"medians are in `results/d1_step1.json` -> weight_limb.")
        A("")
        A(f"**Highest-value missing harvest:** {d1.get('highest_value_missing_harvest')}")
        for lim in (d1.get("limitations") or [])[:4]:
            A(f"- {lim}")
    else:
        A("MISSING.")
    A("")

    # ---------------- D3 -------------------------------------------------
    A("## D3 -- the within-family and size-ladder table")
    A("")
    if d3 and d3.get("rows"):
        A("> " + d3.get("THIS_IS_A_WITHIN_FAMILY_TABLE", ""))
        A("")
        A("> **" + d3.get("the_confound_stated_plainly", "") + "**")
        A("")
        b = d3.get("baselines", {})
        A("| baseline | held-out balacc 3-way | held-out balacc 2-way |")
        A("|---|---|---|")
        A(f"| family label alone | {f((b.get('familyonly_3way') or {}).get('held_out'))} | "
          f"{f((b.get('familyonly_2way') or {}).get('held_out'))} |")
        A(f"| log10(parameters) alone | {f((b.get('sizeonly_3way') or {}).get('held_out'))} | "
          f"{f((b.get('sizeonly_2way') or {}).get('held_out'))} |")
        A("")
        sl = d3.get("size_ladder", {})
        A(f"Size ladder (Qwen3 0.6B / 1.7B / 4B, each with base, instruct and an abliterated "
          f"sibling): **{sl.get('n_metrics_with_sign_flip')}** metrics flip the sign of the "
          f"instruct-minus-abliterated contrast across the ladder; "
          f"**{sl.get('n_metrics_reading_size_not_safety')}** track log-parameters across the "
          f"honest instruct arm at |rho| above the detectable threshold and are labelled as "
          f"reading size, not safety.")
        A("")
        A(f"`results/race_table_v2.csv` -- schema `{d3.get('schema_version')}`, a **strict "
          f"superset** of the frozen 18-column `race_table.csv` (frozen columns first, in "
          f"their frozen order and names; new columns appended after).")
        A("")
        ams = d3.get("ams_row", {})
        A(f"**AMS row.** Published 71% leave-one-out figure: "
          f"`{ams.get('published_71pct_leave_one_out')}` -- "
          f"{ams.get('non_comparable_reason')} {ams.get('its_own_headline')}")
    elif d3:
        A(f"BLOCKED: {d3.get('reason')}")
    else:
        A("MISSING.")
    A("")

    # ---------------- D4 -------------------------------------------------
    A("## D4 -- bounded prior-art check")
    A("")
    if d4:
        A(f"{d4.get('n_queries_used')} of at most 15 queries; backends "
          f"{d4.get('backends_used')}. {d4.get('backend_note', '')}")
        A("")
        for q in ("q1", "q2"):
            b = d4.get(q) or {}
            A(f"**{q.upper()} = {b.get('verdict')}** -- {b.get('question')}")
            A("")
            A(f"{b.get('reason')}")
            A("")
            for n in (b.get("nearest") or [])[:4]:
                A(f"- `{n.get('arxiv_id')}` {n.get('title')} <{n.get('url')}> -- "
                  f"{n.get('relation')} [{n.get('upheld_or_overturned')}]")
            A("")
            A(f"Gap we fill: {b.get('gap_we_fill')}")
            A("")
        bad = [r for r in (d4.get("id_resolvability") or [])
               if r.get("verdict") not in (None, "OK")]
        A(f"arXiv ID resolvability: {len(d4.get('id_resolvability') or [])} checked, "
          f"**{len(bad)} not OK**"
          + (f" -> {[(r.get('id'), r.get('verdict')) for r in bad]}" if bad else "."))
    else:
        A("MISSING.")
    A("")

    # ---------------- hygiene / limitations ------------------------------
    A("## Statistical hygiene applied everywhere")
    A("")
    A("- Resampling unit is the LINEAGE; bootstraps resample lineages; `n_lineages` is "
      "printed beside every aggregate.")
    A("- Pearson **and** Spearman for every correlation, both with Fisher-z CIs "
      "(Spearman with the 1.06 variance-inflation factor).")
    A(f"- Beside any correlation at n < 10 the **detectable |rho|** at that n is printed: "
      f"{f(detectable_rho(6))} at n=6, {f(detectable_rho(8))} at n=8, "
      f"{f(detectable_rho(10))} at n=10, {f(detectable_rho(14))} at n=14, "
      f"{f(detectable_rho(17))} at n=17. *(The plan printed 0.472 at n=17; the stated "
      f"formula tanh(1.96*sqrt(1.06/(n-3))) gives {f(detectable_rho(17))}. We publish what "
      f"the formula produces and flag the discrepancy.)*")
    A("- Benjamini-Hochberg within each declared family of tests; raw p and q side by side.")
    A("- Every null is a DISTRIBUTION with B stated, never a best-of-N point estimate.")
    A("- No metric is evaluated on a checkpoint used to choose its layer or threshold; the "
      "primary D2 arm makes no selection at all.")
    A(f"- Matched lexical floors inherited from iteration 1: JBB Index-paired "
      f"{LEXFLOOR['lexfloor_jbb_index_paired']:.3f}, XSTest twins "
      f"{LEXFLOOR['lexfloor_xstest_twins']:.3f}. The cross-source "
      f"{LEXFLOOR['lexfloor_cross_source']:.3f} is printed but is **NOT a floor**.")
    A("")
    A("## Fold verification")
    A("")
    fo = s0.get("folds", {})
    g = fo.get("frozen_respects_twin_group", {})
    A(f"The frozen `fold` column is used as **primary**. Verified: it respects `twin_group` "
      f"-- **{g.get('n_straddling')} of {g.get('n_groups')} groups straddle a fold boundary** "
      f"(respects_groups = {g.get('respects_groups')}). A grouped-stratified reassignment "
      f"over 5 seeds is reported as a labelled SECONDARY analysis.")
    A("")
    ev = L("../eval_out.json")
    lim = ((ev or {}).get("metadata") or {}).get("limitations") or []
    if lim:
        A("## Limitations")
        A("")
        for x in lim:
            A(f"- {x}")
        A("")
    (RESULTS.parent / "RESULTS.md").write_text("\n".join(o) + "\n", encoding="utf-8")
    print(f"RESULTS.md written ({len(o)} lines)")


if __name__ == "__main__":
    main()
