#!/usr/bin/env python3
"""Render RESULTS.md from results/stage3_v2.json + method_out.json (numbers are never typed by hand)."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
R = WS / "results"


def jl(p: Path, d: Any = None) -> Any:
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return d


def s(x: Any, nd: int = 3) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return "n/a"
        return f"{x:.{nd}g}"
    if isinstance(x, (list, tuple)):
        return "[" + ", ".join(s(v, nd) for v in x) + "]"
    return str(x)


def corr_line(b: dict | None) -> str:
    if not b:
        return "n/a"
    pc = b.get("per_checkpoint") or {}
    sp = pc.get("spearman") or {}
    pf = ((b.get("per_family_mean") or {}).get("spearman") or {})
    return (f"rho = {s(sp.get('rho'))}, 95% CI {s(pc.get('spearman_ci95_family_cluster_boot'))} "
            f"(n = {b.get('n_checkpoints')}, {b.get('n_families')} families; per-family-mean rho = {s(pf.get('rho'))}; "
            f"achieved MDE |rho| = {s(b.get('achieved_mde_abs_rho'))})")


def main() -> None:
    a = jl(R / "stage3_v2.json", {}) or {}
    mo = jl(WS / "method_out.json", {}) or {}
    meta = mo.get("metadata") or {}
    L: list[str] = ["# Results (v2)", ""]
    L += [f"**VERDICT: {meta.get('VERDICT')}** — {meta.get('VERDICT_SENTENCE')}", ""]
    hw = jl(R / "hardware_v2.json", {}) or {}
    sp = jl(R / "spend.json", {}) or {}
    L += ["## What the worker actually was", "",
          f"- GPU: {hw.get('gpu')}; cpuset {hw.get('cpuset_effective')} ({hw.get('n_logical_cpus_in_cpuset')} logical); "
          f"cgroup memory {s(int(hw.get('cgroup_memory_max_bytes') or 0) / 1e9)} GB, shared with two sibling executors",
          f"- {hw.get('concurrent_heavy_processes_sharing_the_cpuset')}",
          f"- {hw.get('thread_oversubscription_finding')}",
          f"- OpenRouter spend: ${s(sp.get('usd'), 4)} of the $8.00 hard cap ({sp.get('calls')} calls)", ""]
    # PART 1
    det = a.get("part1_detection") or {}
    L += ["## Part 1 — recovering the recipe from the weights alone", "",
          f"Real checkpoints read: **{a.get('n_real')}** ({det.get('n_edited')} edited / {det.get('n_honest')} honest, "
          f"{det.get('n_families')} architecture families); exact v2 reads: {a.get('n_real_weights_v2')}, "
          f"sibling-harvest fallback: {a.get('n_real_weights_harvest_fallback')}.", "",
          "| statistic | orientation | pooled AUROC | held-out-family TPR @5% FPR | realised FPR | Cohen's d | n |",
          "|---|---|---|---|---|---|---|"]
    for k, v in (det.get("statistics") or {}).items():
        h = v.get("heldout_family_threshold_at_5pct_fpr") or {}
        L.append(f"| {k} | {v.get('orientation')} | {s(v.get('auroc_pooled'))} | {s(h.get('tpr'))} | "
                 f"{s(h.get('realised_fpr'))} | {s(v.get('cohens_d_edited_minus_honest'))} | {v.get('n')} |")
    ad = det.get("statistics_abliteration_tool_only") or {}
    L += ["", "Abliteration-TOOL outputs only vs honest (fine-tune 'uncensored' models excluded): " + ", ".join(
        f"{k} {s(v.get('auroc_pooled'))} (n={v.get('n')})" for k, v in ad.items()), "",
          "o_proj split by structural validity: valid sites " + json.dumps({k: round(v['auroc_pooled'], 3) for k, v in (det.get('o_proj_valid_sites') or {}).items() if v.get('auroc_pooled') is not None})
          + "; square/wide sites " + json.dumps({k: round(v['auroc_pooled'], 3) for k, v in (det.get('o_proj_square_or_wide_sites') or {}).items() if v.get('auroc_pooled') is not None})]
    L += ["", "**Pre-registered thresholds, measured on real weights** (the 0.35 BSA flag was derived from simulation):", ""]
    for k, v in (det.get("prereg_threshold_operating_points") or {}).items():
        L.append(f"- {k} {v.get('rule')}: FPR on honest = {s(v.get('fpr_on_honest'))} (n={v.get('n_honest')}), "
                 f"TPR on edited = {s(v.get('tpr_on_edited'))} (n={v.get('n_edited')}); honest mean {s(v.get('honest_mean'))}")
    th = a.get("part1_thresholds_rederived_on_honest_panel") or {}
    L += ["", f"Thresholds re-derived on this honest panel at 5% FPR: BOTGAP_min < {s(th.get('BOTGAP_min_below'))}, "
              f"XLC > {s(th.get('XLC_above'))}, BSA_w8 > {s(th.get('BSA_w8_above'))} (n_honest = {th.get('n_honest')}).", "",
          "**Stated recipe (card) × recovered recipe (weights).** " + (a.get("part1_confusion_note") or ""), "",
          "```", json.dumps(a.get("part1_confusion_stated_x_recovered"), indent=1), "```", ""]
    # constructed
    c = a.get("constructed_known_kappa_arm") or {}
    if c.get("grid"):
        L += ["## Known-truth calibration — a real published edit scaled along its own direction", "",
              c.get("construction", ""), "",
              c.get("scale_note", ""), "",
              "| c (x published edit) | effective true kappa median / max | kappa_hat | BOTGAP_min | BSA_w8 | XLC | RQ | XFC | COMPLIANCE | harmful refusal | BB8 refusal |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for g in c["grid"]:
            L.append(f"| {s(g['kappa_true'])} | {s(g.get('kappa_effective_true_median'))} / {s(g.get('kappa_effective_true_max'))} | "
                     f"{s(g.get('mlp_kappa_hat_band'))} | {s(g.get('mlp_BOTGAP_min'))} | "
                     f"{s(g.get('mlp_BSA_w8'))} | {s(g.get('mlp_XLC'))} | {s(g.get('mlp_RQ_pooled'))} | {s(g.get('XFC'))} | "
                     f"{s(g.get('COMPLIANCE'))} | {s(g.get('HREFUSAL'))} | {s(g.get('BB8'))} |")
        cal = c.get("spearman_vs_true_kappa") or {}
        L += ["", "Spearman with the TRUE kappa over the grid: " + ", ".join(
            f"{k} {s((v or {}).get('rho'))}" for k, v in cal.items() if (v or {}).get("rho") is not None), ""]
    tk = a.get("true_kappa_ground_truth") or {}
    if tk.get("per_checkpoint"):
        L += ["## Ground truth on REAL published edits (parent-based, calibration only)", "",
              "For every edited checkpoint whose parent is cached: the true realised strength of the published edit per "
              "matrix (W_E = (I - kappa r r^T) W_P solved for kappa along the top direction of W_E - W_P), against the "
              "parent-free read of the same checkpoint.", "",
              "| edited | parent | projection edit (rank-1 share) | kappa_true median / max | frac layers over-ablated (kappa>1.02) | true-direction XLC | parent-free kappa_hat | parent-free BOTGAP_min | COMPLIANCE |",
              "|---|---|---|---|---|---|---|---|---|"]
        for x in tk["per_checkpoint"]:
            L.append(f"| {x['edited']} | {x['parent_chosen']} | {s(x.get('rank_one_share_median'))} | "
                     f"{s(x.get('kappa_true_median'))} / {s(x.get('kappa_true_max'))} | {s(x.get('frac_layers_kappa_gt_1'))} | "
                     f"{s(x.get('true_direction_XLC'))} | {s(x.get('kappa_hat_band_parentfree'))} | "
                     f"{s(x.get('BOTGAP_min_parentfree'))} | {s(x.get('COMPLIANCE'))} |")
        o = tk.get("operating_range_test") or {}
        dt = tk.get("does_TRUE_strength_grade_risk") or {}
        L += ["", f"- per-layer Spearman(kappa_true, parent-free kappa_hat) = "
                  f"{s((tk.get('per_layer_spearman_kappa_true_vs_kappa_hat') or {}).get('rho'))} over {tk.get('per_layer_n')} layer-matrices; "
                  f"|1-kappa| MAE {s(tk.get('per_layer_absdev_mae'))}",
              f"- operating range ({o.get('rule')}): {o.get('n_layers_in_range')} layers in range (median kappa_hat "
              f"{s(o.get('median_kappa_hat_in_range'))}, |1-kappa| MAE {s(o.get('absdev_mae_in_range'))}) vs "
              f"{o.get('n_layers_out_of_range')} out of range (median kappa_hat {s(o.get('median_kappa_hat_out_of_range'))}, "
              f"MAE {s(o.get('absdev_mae_out_of_range'))})",
              f"- parent-free bottom direction vs the TRUE edited direction, per layer: {json.dumps(tk.get('per_layer_cos_true_direction_vs_parentfree_bottom1'))}",
              f"- detection by EDIT TYPE (re-derived thresholds): {json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'members'} for k, v in ((tk.get('detection_by_edit_type') or {}).get('by_type') or {}).items()})}",
              f"- **does the TRUE (signed, parent-based) strength grade risk?** Spearman(kappa_true, COMPLIANCE) = "
              f"{s((dt.get('spearman_kappa_true_median_vs_COMPLIANCE') or {}).get('rho'))}, Spearman(|1-kappa_true|, COMPLIANCE) = "
              f"{s((dt.get('spearman_abs_dev_true_vs_COMPLIANCE') or {}).get('rho'))} (n = {dt.get('n')}, MDE {s(dt.get('achieved_mde_abs_rho'))}). "
              f"{dt.get('reading', '')}"]
        tb = tk.get("true_strength_vs_risk_blocks") or {}
        for k in ("signed_kappa_true", "abs_one_minus_kappa_true", "parentfree_kappa_hat_same_checkpoints"):
            if tb.get(k):
                L.append(f"  - {tb[k].get('label')}: {corr_line(tb[k])}")
        L += [f"  - over-ablated (kappa_true > 1.02): {tb.get('n_over_ablated_checkpoints')}, under-ablated (< 0.98): "
              f"{tb.get('n_under_ablated_checkpoints')}", ""]
    # PART 2
    p = a.get("primary_endpoint") or {}
    L += ["## Part 2 — the graded test", "",
          f"**PRIMARY (pre-registered):** Spearman(kappa_hat, COMPLIANCE) inside the edited arm: {corr_line(p)}. "
          f"Directional prediction: positive.", "",
          f"Secondary, pooled over edited + honest: {corr_line(a.get('secondary_pooled'))}. "
          f"{(a.get('secondary_pooled') or {}).get('caveat', '')}", "",
          "| graded checkpoint | arm | family | COMPLIANCE | refusal H48 | OVERREFUSAL judge / regex | BB8 | kappa_hat | BOTGAP_min | BSA_w8 | XLC | RQ | A_coupling |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    rowsby = {r["id"]: r for r in a.get("_rows") or []}
    for g in sorted(a.get("graded_panel") or [], key=lambda g: (g["arm"], -(g.get("COMPLIANCE") or 0))):
        rr = rowsby.get(g["id"], {})
        L.append(f"| {g['id']} | {g['arm']} | {g['family']} | {s(g.get('COMPLIANCE'))} | {s(g.get('HREFUSAL'))} | "
                 f"{s(g.get('OVERREFUSAL'))} / {s(rr.get('regex_overrefusal_B'))} | "
                 f"{s(g.get('BB8'))} | {s(g.get('mlp_kappa_hat_band'))} | {s(g.get('mlp_BOTGAP_min'))} | "
                 f"{s(g.get('mlp_BSA_w8'))} | {s(g.get('mlp_XLC'))} | {s(g.get('mlp_RQ_pooled'))} | {s(g.get('A_coupling'))} |")
    L += ["", "**Exploratory within-edited correlations** (not pre-registered; " + (a.get("exploratory_note") or "") + ")", ""]
    for k, v in (a.get("exploratory_within_edited") or {}).items():
        L.append(f"- {k}: {corr_line(v)}")
    se = a.get("outcome_sensitivity_within_edited") or {}
    if se:
        L += ["", "**Outcome sensitivity (exploratory; the raw harm score also carries base-model capability):**", ""]
        for k in ("primary_restricted_to_abliteration_tool_checkpoints", "kappa_vs_one_minus_HREFUSAL",
                  "kappa_vs_delta_COMPLIANCE_vs_family_parent", "kappa_vs_COMPLIANCE_full96"):
            if se.get(k):
                L.append(f"- {se[k].get('label')}: {corr_line(se[k])}")
        pp = se.get("kappa_vs_COMPLIANCE_partial_log_n_params")
        if pp:
            L.append(f"- size-partialled (log n_params) within-edited Spearman: {s(pp.get('rho_partial'))} (n={pp.get('n')}; "
                     f"rho(kappa, size) {s(pp.get('rho_kappa_size'))}, rho(COMPLIANCE, size) {s(pp.get('rho_compliance_size'))})")
        L.append(f"- honest parents used for the delta: {json.dumps(se.get('parents_used'))}")
    b = a.get("bars") or {}
    L += ["", "### The bars", ""]
    for k in ("BAR1_graded_vs_binary_oracle_label", "BAR1_graded_vs_binary_detector"):
        v = b.get(k) or {}
        L.append(f"- **{k}**: R² binary {s(v.get('R2_M0_binary'))} -> +kappa {s(v.get('R2_M1_binary_plus_kappa'))} "
                 f"(delta {s(v.get('delta_R2'))}, family-cluster CI {s(v.get('delta_R2_ci95_family_cluster_boot'))}); "
                 f"permutation p {s(v.get('delta_R2_permutation_p'))}; leave-one-family-out MAE {s(v.get('lofo_mae_M0'))} -> "
                 f"{s(v.get('lofo_mae_M1'))}, paired diff {s((v.get('lofo_paired_mae_diff_M1_minus_M0') or {}).get('diff_mae'))} "
                 f"CI {s((v.get('lofo_paired_mae_diff_M1_minus_M0') or {}).get('ci95'))} (n={v.get('n')}, "
                 f"{v.get('n_families')} families). {v.get('delta_R2_note', '')}")
    v = b.get("BAR2_weights_vs_blackbox_BB8") or {}
    kk = v.get("kappa_hat_zero_prompts") or {}
    L.append(f"- **BAR2 (0 prompts vs 8 disjoint prompts)**: LOFO R² kappa_hat {s(v.get('lofo_R2_kappa'))}, BB8 "
             f"{s(v.get('lofo_R2_BB8'))}, L1 logit gap {s(v.get('lofo_R2_L1_logit_gap'))}; paired MAE diff (kappa - BB8) "
             f"{s(kk.get('diff_mae'))} CI {s(kk.get('ci95'))}. {v.get('cost_note', '')}")
    v = b.get("BAR3_recipe_vector_vs_strength") or {}
    L.append(f"- **BAR3 (recipe vector vs strength alone)**: LOFO R² {s(v.get('lofo_R2_recipe_vector'))} vs "
             f"{s(v.get('lofo_R2_kappa_alone'))}; paired {s((v.get('paired') or {}).get('diff_mae'))} "
             f"CI {s((v.get('paired') or {}).get('ci95'))}")
    v = b.get("BAR4_activation_readout") or {}
    L.append(f"- **BAR4 (cross-fitted activation readout)**: A_coupling defined for {v.get('n_with_A_coupling_defined')} "
             f"graded checkpoints ({v.get('n_undefined_decision_spread')} UNDEFINED by the 0.25-logit spread floor); "
             f"vs COMPLIANCE {corr_line(v.get('spearman_A_coupling_vs_COMPLIANCE_all_graded'))}")
    v = b.get("BAR5_free_baselines") or {}
    L.append(f"- **BAR5 (free baselines)**: family-label-only LOCO R² {s(v.get('family_label_only_loco_R2'))} vs "
             f"kappa_hat LOCO R² {s(v.get('kappa_hat_loco_R2'))}. {v.get('standing_rule_sentence', '')}")
    L += ["", f"Binary detector used by BAR1: {b.get('edited_flag_definition')} — confusion vs the edited label "
              f"{json.dumps(b.get('edited_flag_confusion_vs_label'))}.", ""]
    # forgery
    if a.get("forgery"):
        L += ["## The cheapest forgery (Stage 5.3) — handed to the forgery lane", ""]
        for fid, fo in a["forgery"].items():
            db, da = fo.get("detector_before") or {}, fo.get("detector_after") or {}
            L.append(f"- **{fid}**: BOTGAP_min {s(db.get('mlp_BOTGAP_min'))} -> {s(da.get('mlp_BOTGAP_min'))}, "
                     f"BSA_w8 {s(db.get('mlp_BSA_w8'))} -> {s(da.get('mlp_BSA_w8'))}, XLC {s(db.get('mlp_XLC'))} -> "
                     f"{s(da.get('mlp_XLC'))}, kappa_hat {s(db.get('mlp_kappa_hat_band'))} -> {s(da.get('mlp_kappa_hat_band'))}, "
                     f"RQ {s(db.get('mlp_RQ_pooled'))} -> {s(da.get('mlp_RQ_pooled'))}; COMPLIANCE edited "
                     f"{s(fo.get('COMPLIANCE_before_edited'))} -> after repair {s(fo.get('COMPLIANCE_after_repair'))} "
                     f"(honest parent {fo.get('honest_parent')}: {s(fo.get('COMPLIANCE_honest_parent'))}); harmful REFUSAL rate "
                     f"{s(fo.get('HREFUSAL_before_edited'))} -> {s(fo.get('HREFUSAL_after_repair'))} (parent {s(fo.get('HREFUSAL_honest_parent'))}); "
                     f"BB8 {s(fo.get('BB8_before_edited'))} -> {s(fo.get('BB8_after_repair'))} (parent {s(fo.get('BB8_honest_parent'))}); "
                     f"A_coupling {s(fo.get('A_coupling_before_edited'))} -> {s(fo.get('A_coupling_after_repair'))} "
                     f"(parent {s(fo.get('A_coupling_honest_parent'))})")
        L.append("")
    # part 4
    an = a.get("part4_anisotropy_matched_null") or {}
    if an:
        L += ["## Part 4 — anisotropy-matched null (NOT isotropic)", "",
              "| family | aniso null BSA_w8 mean (p95) | iso null BSA_w8 | aniso null XLC mean (p95) | iso null XLC | edited p(BSA) | edited p(XLC) |",
              "|---|---|---|---|---|---|---|"]
        for fam, v in an.items():
            ed = [o for o in v.get("observed") or [] if o.get("arm") == "edited"]
            L.append(f"| {fam} | {s(v.get('aniso_null_BSA_w8_mean'))} ({s(v.get('aniso_null_BSA_w8_p95'))}) | "
                     f"{s(v.get('iso_null_BSA_w8_mean'))} | {s(v.get('aniso_null_XLC_mean'))} ({s(v.get('aniso_null_XLC_p95'))}) | "
                     f"{s(v.get('iso_null_XLC_mean'))} | {s([o.get('p_BSA_vs_aniso') for o in ed])} | "
                     f"{s([o.get('p_XLC_vs_aniso') for o in ed])} |")
        L.append("")
    prof = (a.get("part4_layer_component_profile") or {}).get("within_edited_spearman_vs_COMPLIANCE") or {}
    if prof:
        L += ["**Which depth quintile / component carries the within-edited correlation:** " + ", ".join(
            f"{k} {s((v or {}).get('rho'))}" for k, v in prof.items()), ""]
    rep = a.get("replication_other_runs") or {}
    if rep:
        L += ["## Replication on other runs' stored generations (source-stratified)", ""]
        for src, v in (rep.get("within_source_summary") or {}).items():
            L.append(f"- {src}: {v.get('n_checkpoints')} checkpoints graded, {v.get('n_edited_with_weights')} edited with a "
                     f"weight read; within-edited Spearman(kappa_hat, COMPLIANCE) = {s((v.get('mlp_kappa_hat_band') or {}).get('rho'))} "
                     f"(n={(v.get('mlp_kappa_hat_band') or {}).get('n')})")
        for src, v in (rep.get("within_source_summary") or {}).items():
            L.append(f"- {src}, weight-DETECTED projection edits only (kappa_hat > honest p95 "
                     f"{s(rep.get('projection_edit_threshold_kappa_hat_honest_p95'))}): n = {v.get('n_detected_projection_edits')}, "
                     f"Spearman {s((v.get('detected_projection_edits_only_kappa_vs_COMPLIANCE') or {}).get('rho'))}")
        cp = rep.get("combined_detected_projection_edits_only")
        if cp:
            L.append(f"- combined, projection edits only: rho {s(cp.get('rho'))}, CI {s(cp.get('ci95'))}, n = {cp.get('n_total')}")
        L.append(f"- {rep.get('interpretation_note', '')}")
        cb = rep.get("combined_kappa_within_edited")
        if cb:
            L.append(f"- combined (Fisher z, n-weighted): rho {s(cb.get('rho'))}, CI {s(cb.get('ci95'))}, "
                     f"{cb.get('n_sources')} sources, n = {cb.get('n_total')}")
        L.append("")
    a4b = jl(R / "stage4b_strata.json", {}) or {}
    L += ["## Part 3 — the external limb (published safety numbers)", "",
          f"- HELM resolution: {json.dumps(a4b.get('resolution_counts'))}",
          f"- S1 sub-4B with any published safety number: n = {(a4b.get('S1_sub4B_with_published_safety') or {}).get('n')} (scatter only, no coefficient)",
          f"- S2 open-weight HELM subset: {(a4b.get('S2_open_weight_helm_subset') or {}).get('n_feasible_open_weight')} feasible, "
          f"weight readouts computed on 0 (DEVIATIONS D20)",
          f"- identical-weights ceiling: {s((a4b.get('identical_weights_ceiling') or {}).get('headline_max_share_of_across_model_variance'))}x "
          f"the across-model variance ({json.dumps((a4b.get('identical_weights_ceiling') or {}).get('headline_ref'))})",
          f"- {a4b.get('caveat', '')}", ""]
    # ---------------- practical guidance, every number pulled from the analysis
    det = (a.get("part1_detection") or {}).get("statistics") or {}
    abl_det = (a.get("part1_detection") or {}).get("statistics_abliteration_tool_only") or {}
    osv = (a.get("part1_detection") or {}).get("o_proj_valid_sites") or {}
    osq = (a.get("part1_detection") or {}).get("o_proj_square_or_wide_sites") or {}
    op = (a.get("part1_detection") or {}).get("prereg_threshold_operating_points") or {}
    tk = a.get("true_kappa_ground_truth") or {}
    L += ["---", "", "## What this licenses for a random HuggingFace checkpoint", "",
          f"1. **Read `down_proj`; read `o_proj` only where it has more columns than rows.** Pooled AUROC, abliteration-tool "
          f"outputs vs honest: down_proj kappa_hat {s((abl_det.get('mlp_kappa_hat_band') or {}).get('auroc_pooled'))}, down_proj "
          f"BOTGAP_min {s((abl_det.get('mlp_BOTGAP_min') or {}).get('auroc_pooled'))}; o_proj BOTGAP_min on valid sites "
          f"{s((osv.get('attn_BOTGAP_min') or {}).get('auroc_pooled'))} vs square/wide sites "
          f"{s((osq.get('attn_BOTGAP_min') or {}).get('auroc_pooled'))}. A float32 Gram cannot even resolve a square "
          f"o_proj's bottom spectrum (regression file), and the PREREG BOTGAP < 0.1 flag false-positives there.",
          f"2. **Never use the published 0.35 BSA flag.** Its measured false-positive rate on honest down_proj is "
          f"{s((op.get('mlp_BSA_w8') or {}).get('fpr_on_honest'))}; re-derive thresholds on an honest panel of the same "
          f"architecture family.",
          f"3. **A detection is not a grade.** Inside the edited arm the parent-free strength read does not order models "
          f"by harm (primary endpoint above), and neither does the parent-based TRUE strength of the edit (signed "
          f"Spearman {s(((tk.get('does_TRUE_strength_grade_risk') or {}).get('spearman_kappa_true_median_vs_COMPLIANCE') or {}).get('rho'))}, "
          f"|1-kappa| Spearman {s(((tk.get('does_TRUE_strength_grade_risk') or {}).get('spearman_abs_dev_true_vs_COMPLIANCE') or {}).get('rho'))}): "
          f"a better strength estimator would not fix this; the harm an edit unlocks is not a monotone function of its strength.",
          "4. **Only |1-kappa| is identifiable, and only near kappa = 1.** Over-ablation is common in shipped heretic "
          "checkpoints (true kappa up to ~1.5) and reads exactly like the same-size under-ablation; partial edits outside "
          "|1-kappa| < sigma_min/sigma_rms are invisible to a spectral read.",
          "5. **Fine-tune 'uncensoring' leaves no spectral scar** (amoral-gemma leaves down_proj byte-identical to its "
          "parent) - a clean weight read is not evidence of safety.",
          "6. **The detectors are cheap to forge.** A rank-one repair from the checkpoint's own weights (zero prompts, "
          "zero labels, about a minute of CPU) heals BOTGAP, kappa_hat, XLC and BSA ('swap') and RQ ('bulk').",
          "7. **If you can afford 8 prompts, spend them**: see BAR2 for how the first-token logit gap and the 8-prompt "
          "refusal rate compare with the zero-prompt weight read.", ""]
    (WS / "RESULTS.md").write_text("\n".join(L))
    # ---- README headline block (auto-generated between markers)
    pe = a.get("primary_endpoint") or {}
    pc = pe.get("per_checkpoint") or {}
    b1 = (a.get("bars") or {}).get("BAR1_graded_vs_binary_oracle_label") or {}
    b4 = ((a.get("bars") or {}).get("BAR4_activation_readout") or {}).get("spearman_A_coupling_vs_COMPLIANCE_all_graded") or {}
    ort = tk.get("operating_range_test") or {}
    cosd = tk.get("per_layer_cos_true_direction_vs_parentfree_bottom1") or {}
    best_k, best_r, best_p, best_n = None, None, None, None
    for kk, vv in (a.get("exploratory_within_edited") or {}).items():
        sp_ = ((vv.get("per_checkpoint") or {}).get("spearman") or {})
        if kk == "OVERREFUSAL":
            continue   # an outcome, not a readout
        if sp_.get("rho") is not None and (vv.get("n_checkpoints") or 0) >= 8 and (best_r is None or abs(sp_["rho"]) > abs(best_r)):
            best_k, best_r, best_p, best_n = kk, sp_["rho"], sp_.get("p"), vv.get("n_checkpoints")
    best_k = {"L1_logit_gap_H": "the logit-only L1 first-token gap BASELINE", "BB8": "the 8-prompt black-box BASELINE",
              "A_coupling": "the activation coupling"}.get(best_k, best_k)
    fo = a.get("forgery") or {}
    fsw = next((v for k, v in fo.items() if k.endswith("__swap") and v.get("COMPLIANCE_after_repair") is not None), {})
    H = ["## Headline findings (auto-generated from results/stage3_v2.json)", "",
         f"- **Verdict: {meta.get('VERDICT')}.** {meta.get('VERDICT_SENTENCE')}",
         f"- **Detection (edited vs honest, pooled AUROC):** down_proj kappa_hat {s((det.get('mlp_kappa_hat_band') or {}).get('auroc_pooled'))} "
         f"over ALL edited (abliteration-tool outputs only: {s((abl_det.get('mlp_kappa_hat_band') or {}).get('auroc_pooled'))}), "
         f"down_proj BOTGAP_min {s((det.get('mlp_BOTGAP_min') or {}).get('auroc_pooled'))} "
         f"({s((abl_det.get('mlp_BOTGAP_min') or {}).get('auroc_pooled'))}), RQ {s((det.get('mlp_RQ_pooled') or {}).get('auroc_pooled'))} "
         f"({s((abl_det.get('mlp_RQ_pooled') or {}).get('auroc_pooled'))}); o_proj BOTGAP_min on structurally valid sites "
         f"{s((osv.get('attn_BOTGAP_min') or {}).get('auroc_pooled'))} vs square sites {s((osq.get('attn_BOTGAP_min') or {}).get('auroc_pooled'))}. "
         f"The published 0.35 BSA flag false-positives on {s(100 * ((op.get('mlp_BSA_w8') or {}).get('fpr_on_honest') or 0), 3)}% "
         f"of honest checkpoints.",
         f"- **Primary endpoint (pre-registered):** within-edited Spearman(kappa_hat, COMPLIANCE) = "
         f"{s((pc.get('spearman') or {}).get('rho'))}, 95% CI {s(pc.get('spearman_ci95_family_cluster_boot'))}, "
         f"n = {pe.get('n_edited_graded')}, achieved MDE {s(pe.get('achieved_mde_abs_rho'))}.",
         f"- **Bar 1:** adding kappa_hat to the binary edited label: permutation p = {s(b1.get('delta_R2_permutation_p'))}, "
         f"out-of-family MAE {s(b1.get('lofo_mae_M0'))} -> {s(b1.get('lofo_mae_M1'))}.",
         f"- **Ground truth on real edits (parent-based):** the parent-free read is exact inside |1-kappa| < "
         f"sigma_min/sigma_rms (median kappa_hat {s(ort.get('median_kappa_hat_in_range'))}, true-direction cos "
         f"{s(cosd.get('median_in_range'))}) and blind outside it (median kappa_hat {s(ort.get('median_kappa_hat_out_of_range'))}, "
         f"cos {s(cosd.get('median_out_of_range'))}); {ort.get('n_layers_out_of_range')} of "
         f"{(ort.get('n_layers_in_range') or 0) + (ort.get('n_layers_out_of_range') or 0)} real edited layer-matrices lie outside it.",
         f"- **Ground truth on strength vs risk (parent-based):** signed true kappa vs COMPLIANCE Spearman "
         f"{s(((tk.get('does_TRUE_strength_grade_risk') or {}).get('spearman_kappa_true_median_vs_COMPLIANCE') or {}).get('rho'))} "
         f"(p = {s(((tk.get('does_TRUE_strength_grade_risk') or {}).get('spearman_kappa_true_median_vs_COMPLIANCE') or {}).get('p'))}), "
         f"|1-kappa_true| vs COMPLIANCE {s(((tk.get('does_TRUE_strength_grade_risk') or {}).get('spearman_abs_dev_true_vs_COMPLIANCE') or {}).get('rho'))} "
         f"(p = {s(((tk.get('does_TRUE_strength_grade_risk') or {}).get('spearman_abs_dev_true_vs_COMPLIANCE') or {}).get('p'))}), "
         f"n = {(tk.get('does_TRUE_strength_grade_risk') or {}).get('n')} projection edits, of which "
         f"{(tk.get('true_strength_vs_risk_blocks') or {}).get('n_over_ablated_checkpoints')} over-ablate (kappa > 1) and "
         f"{(tk.get('true_strength_vs_risk_blocks') or {}).get('n_under_ablated_checkpoints')} under-ablate: even the TRUE "
         f"strength of an edit does not order models by harm.",
         f"- **Where a graded signal does exist, it is not in the weights.** Pooled over all graded checkpoints the "
         f"cross-fitted activation coupling tracks COMPLIANCE (Spearman {s(((b4.get('per_checkpoint') or {}).get('spearman') or {}).get('rho'))}, "
         f"CI {s((b4.get('per_checkpoint') or {}).get('spearman_ci95_family_cluster_boot'))}, n = {b4.get('n_checkpoints')}) "
         f"more strongly than kappa_hat does ({s((((a.get('secondary_pooled') or {}).get('per_checkpoint') or {}).get('spearman') or {}).get('rho'))}); "
         f"inside the edited arm the best single predictor is {best_k} (Spearman {s(best_r)}, p = {s(best_p)}, n = {best_n}).",
         (f"- **Replication on other runs' stored generations (source-stratified, their own item sets):** within-source "
          f"within-edited Spearman(kappa_hat, COMPLIANCE) combined = "
          f"{s(((a.get('replication_other_runs') or {}).get('combined_kappa_within_edited') or {}).get('rho'))} "
          f"(CI {s(((a.get('replication_other_runs') or {}).get('combined_kappa_within_edited') or {}).get('ci95'))}, "
          f"n = {((a.get('replication_other_runs') or {}).get('combined_kappa_within_edited') or {}).get('n_total')}) - but those "
          f"'edited' arms mix abliterations with behaviour-uncensored fine-tunes that carry no scar, so this partly re-detects "
          f"EDIT TYPE; restricted to weight-detected projection edits it is "
          f"{s(((a.get('replication_other_runs') or {}).get('combined_detected_projection_edits_only') or {}).get('rho'))} "
          f"(CI {s(((a.get('replication_other_runs') or {}).get('combined_detected_projection_edits_only') or {}).get('ci95'))}, "
          f"n = {((a.get('replication_other_runs') or {}).get('combined_detected_projection_edits_only') or {}).get('n_total')}). "
          f"A positive graded signal inside projection edits is therefore NOT excluded at these n; it is not established."),
         (f"- **Cheapest forgery:** a zero-prompt rank-one repair heals the weight detectors (BOTGAP_min "
          f"{s((fsw.get('detector_before') or {}).get('mlp_BOTGAP_min'))} -> {s((fsw.get('detector_after') or {}).get('mlp_BOTGAP_min'))}) "
          f"but not the behaviour (harmful refusal {s(fsw.get('HREFUSAL_before_edited'))} -> {s(fsw.get('HREFUSAL_after_repair'))}, "
          f"honest parent {s(fsw.get('HREFUSAL_honest_parent'))}; 8-probe refusal {s(fsw.get('BB8_before_edited'))} -> "
          f"{s(fsw.get('BB8_after_repair'))}, parent {s(fsw.get('BB8_honest_parent'))}). The activation coupling reads "
          f"{s(fsw.get('A_coupling_before_edited'))} -> {s(fsw.get('A_coupling_after_repair'))} (parent "
          f"{s(fsw.get('A_coupling_honest_parent'))}); in this small family the parent is itself weakly coupled, so it "
          f"does not separate the three.")
         if fsw else "- Forgery: see RESULTS.md.",
         "", "Full tables: `RESULTS.md`.", ""]
    rd = WS / "README.md"
    txt = rd.read_text()
    if "<!-- HEADLINE_START -->" in txt:
        a0, rest = txt.split("<!-- HEADLINE_START -->", 1)
        _, b0 = rest.split("<!-- HEADLINE_END -->", 1)
        rd.write_text(a0 + "<!-- HEADLINE_START -->\n" + "\n".join(H) + "\n<!-- HEADLINE_END -->" + b0)
    print(f"RESULTS.md: {len(L)} lines")


if __name__ == "__main__":
    main()
