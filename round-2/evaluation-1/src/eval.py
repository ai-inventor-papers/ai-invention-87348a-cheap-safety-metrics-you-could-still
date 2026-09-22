#!/usr/bin/env python3
"""Assemble every stage into eval_out.json (exp_eval_sol_out schema) + RESULTS.md.

Runs LAST.  It computes nothing new; it reads the per-stage JSON that each stage
persisted the moment its numbers existed, and reports MISSING for anything a
stage did not deliver rather than inventing it.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evallib.core import (  # noqa: E402
    LEXFLOOR, RESULTS, SURV_PREMISE_FAILS_MAX, SURV_SURVIVES_MIN, detectable_rho,
    read_json, sha256_file, write_json,
)

ARTIFACT_ID = "gen_plan_evaluation_1_idx1"
SCHEMA_VERSION = "race_table_v2.1"


def _load(name: str):
    p = RESULTS / name
    return read_json(p) if p.exists() else None


def _num(v, default=None):
    try:
        f = float(v)
        return f if np.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def main() -> None:                                                # noqa: PLR0915
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    t0 = time.time()

    s0 = _load("s0_setup.json") or {}
    prereg = _load("PREREG.json") or {}
    d0 = _load("d0_rescore.json")
    d1 = _load("d1_step1.json")
    d2 = _load("d2_controls.json") or _load("d2_controls_partial.json")
    d2b = _load("d2b_first_token.json")
    d3 = _load("d3_table.json")
    d4 = _load("d4_prior_art.json")

    panel = s0.get("panel", {})
    integ = s0.get("registry_integrity", {})
    reg_before = integ.get("registry_sha256_before")
    reg_after = sha256_file(Path(prereg.get("_registry_path", ""))) if False else None
    from evallib.core import UP_RESULTS
    reg_after = sha256_file(UP_RESULTS / "metrics_registry.json")

    # ---------------- verdicts ------------------------------------------
    verdicts: dict = {}
    agg = (d2 or {}).get("aggregate", {})
    prim = agg.get("content_last", {})
    twin = agg.get("twin_xstest", {})
    fitted_verdict = prim.get("verdict_band", "MISSING")
    verdicts["D2_fitted_direction_vs_own_within_span_null"] = {
        "band_cited": prereg.get("survival_bands_over_17_checkpoints"),
        "primary_readout": "content_last (harmful vs plain-benign, fixed depth 0.60)",
        "SURV": prim.get("SURV_span_of_n"), "wilson95": prim.get("SURV_span_wilson95"),
        "verdict": fitted_verdict,
        "matched_contrast_readout": "twin_xstest (XSTest positional twins, MATCHED)",
        "SURV_matched": twin.get("SURV_span_of_n"),
        "verdict_matched": twin.get("verdict_band", "MISSING"),
    }
    verdicts["D2b_first_generated_token"] = {
        "band_cited": prereg.get("d2b_first_token_bands"),
        "verdict": (d2b or {}).get("panel_verdict", "MISSING"),
        "histogram": (d2b or {}).get("verdict_histogram"),
        "contaminated_slugs": (d2b or {}).get("contaminated_slugs"),
    }
    verdicts["D1_step1_subspace"] = {
        "band_cited": prereg.get("d1_verdict_bands"),
        "verdict": (d1 or {}).get("verdict", "MISSING"),
        "judged_at": (d1 or {}).get("verdict_judged_at"),
        "positive_control_passes": ((d1 or {}).get("positive_control") or {})
        .get("control_passes"),
        "headline_numbers": (d1 or {}).get("headline_numbers"),
        "weight_limb": {k: v for k, v in ((d1 or {}).get("weight_limb") or {}).items()
                        if not isinstance(v, (list, dict))} or "MISSING",
        "highest_value_missing_harvest": (d1 or {}).get("highest_value_missing_harvest"),
    }
    verdicts["R1_frozen_gap_ordering"] = {
        "band_cited": prereg.get("r1_frozen_prediction"),
        "observed_corr": ((d0 or {}).get("R1_frozen_prediction") or {}).get("observed_corr"),
        "p_perm": ((d0 or {}).get("R1_frozen_prediction") or {}).get("p_perm"),
        "per_family_mean_gap": ((d0 or {}).get("R1_frozen_prediction") or {})
        .get("per_family_mean_gap"),
        "status": "COMPUTED" if d0 else "MISSING",
    }
    verdicts["registry_integrity"] = {
        "band_cited": "registry_sha256_before must equal registry_sha256_after and the "
                      "frozen literal; nothing in the registry may be edited, only computed.",
        "verdict": "INTACT" if (reg_before == reg_after and integ.get("registry_intact"))
                   else "MISMATCH",
    }

    # ---------------- metrics_agg (flat numbers only) ---------------------
    ma: dict[str, float] = {
        "n_checkpoints_done": _num(panel.get("n_done"), 0.0),
        "n_lineages": _num(panel.get("n_lineages"), 0.0),
        "n_families": _num(panel.get("n_families"), 0.0),
        "n_registry_metrics": _num(integ.get("n_metrics"), 0.0),
        "registry_intact": 1.0 if integ.get("registry_intact") else 0.0,
        "detectable_abs_rho_at_n17": detectable_rho(17),
        "detectable_abs_rho_at_n14": detectable_rho(14),
        "detectable_abs_rho_at_n4": detectable_rho(4),
        "lexfloor_jbb_index_paired": LEXFLOOR["lexfloor_jbb_index_paired"],
        "lexfloor_xstest_twins": LEXFLOOR["lexfloor_xstest_twins"],
        "lexfloor_cross_source_NOT_A_FLOOR": LEXFLOOR["lexfloor_cross_source"],
        "cost_usd": 0.0,
    }
    for rn, a in agg.items():
        pfx = f"D2_{rn}"
        ma[f"{pfx}_SURV_span_k"] = _num(a.get("SURV_span_k"), 0.0)
        ma[f"{pfx}_SURV_span_fraction"] = _num(a.get("SURV_span_fraction"))
        ma[f"{pfx}_SURV_perm_k"] = _num(a.get("SURV_perm_k"), 0.0)
        ma[f"{pfx}_SURV_iso_k"] = _num(a.get("SURV_iso_k"), 0.0)
        ma[f"{pfx}_SURV_aniso_k"] = _num(a.get("SURV_aniso_k"), 0.0)
        ma[f"{pfx}_SURV_white_k"] = _num(a.get("SURV_white_k"), 0.0)
        ma[f"{pfx}_SURV_joint_k"] = _num(a.get("SURV_joint_span_and_perm_k"), 0.0)
        ma[f"{pfx}_mean_AUROC_xf"] = _num(a.get("mean_AUROC_xf"))
        ma[f"{pfx}_mean_AUROC_in"] = _num(a.get("mean_AUROC_in"))
        ma[f"{pfx}_mean_inflation_in_minus_xf"] = _num(a.get("mean_inflation_in_minus_xf"))
        ma[f"{pfx}_mean_AUROC_white_xf"] = _num(a.get("mean_AUROC_white_xf"))
        ma[f"{pfx}_mean_delta_white_minus_raw"] = _num(a.get("mean_delta_white_minus_raw"))
        ci = a.get("delta_auroc_lineage_clustered_ci", {})
        ma[f"{pfx}_delta_auroc_point"] = _num(ci.get("point"))
        ma[f"{pfx}_delta_auroc_ci_lo"] = _num(ci.get("lo"))
        ma[f"{pfx}_delta_auroc_ci_hi"] = _num(ci.get("hi"))
        sc = a.get("per_checkpoint_scatter", [])
        ma[f"{pfx}_mean_null_span_mean"] = _num(
            np.nanmean([_num(r.get("null_span_mean"), np.nan) for r in sc]) if sc else None)
        ma[f"{pfx}_mean_null_iso_mean"] = _num(
            np.nanmean([_num(r.get("null_iso_mean"), np.nan) for r in sc]) if sc else None)
        ma[f"{pfx}_mean_null_span_max_first20"] = _num(
            np.nanmean([_num(r.get("null_span_max_first20"), np.nan) for r in sc]) if sc else None)
    if d0:
        ma["D0_n_cells_nan_before"] = _num(d0.get("n_cells_recovered_before"), 0.0)
        ma["D0_n_cells_nan_after"] = _num(d0.get("n_cells_nan_after"), 0.0)
        ma["D0_n_cells_recovered"] = _num(d0.get("n_cells_recovered"), 0.0)
        ma["D0_n_metrics_computable"] = _num(d0.get("n_metrics_computable"), 0.0)
        ma["D0_n_degraded"] = _num(len(d0.get("degrade_ledger", []) or []), 0.0)
        r1 = d0.get("R1_frozen_prediction") or {}
        ma["R1_observed_corr"] = _num(r1.get("observed_corr"))
        ma["R1_p_perm"] = _num(r1.get("p_perm"))
    if d2b:
        ma["D2b_n_contaminated"] = _num(len(d2b.get("contaminated_slugs", []) or []), 0.0)
        ma["D2b_n_clean"] = _num((d2b.get("verdict_histogram") or {}).get("CLEAN", 0), 0.0)
        ma["D2b_max_delimiter_share"] = _num(max(
            [_num(r.get("delimiter_share_over_items"), 0.0)
             for r in d2b.get("per_checkpoint", [])] or [0.0]))
    if d3 and d3.get("rows"):
        ma["D3_n_metrics_scored"] = _num(d3.get("n_metrics_scored"), 0.0)
        ma["D3_n_beating_familyonly"] = _num(d3.get("n_metrics_beating_familyonly_3way"), 0.0)
        b = d3.get("baselines", {})
        ma["D3_familyonly_balacc_3way"] = _num((b.get("familyonly_3way") or {}).get("held_out"))
        ma["D3_familyonly_balacc_2way"] = _num((b.get("familyonly_2way") or {}).get("held_out"))
        ma["D3_sizeonly_balacc_3way"] = _num((b.get("sizeonly_3way") or {}).get("held_out"))
        ma["D3_sizeonly_balacc_2way"] = _num((b.get("sizeonly_2way") or {}).get("held_out"))
        ma["D3_n_sign_flips"] = _num((d3.get("size_ladder") or {})
                                     .get("n_metrics_with_sign_flip"), 0.0)
        ma["D3_n_reading_size_not_safety"] = _num((d3.get("size_ladder") or {})
                                                  .get("n_metrics_reading_size_not_safety"), 0.0)
    if d1:
        for k in ("signed_cos_safe_vs_mlab", "signed_cos_safe_vs_heretic",
                  "disattenuated_overlap_safe_vs_mlab", "null_p95_at_verdict_band"):
            v = _num((d1.get("headline_numbers") or {}).get(k))
            if v is not None:
                ma[f"D1_{k}"] = v
    ma = {k: v for k, v in ma.items() if v is not None}

    # ---------------- datasets -------------------------------------------
    datasets = []

    # D2
    ex = []
    for ck in (d2 or {}).get("per_checkpoint", []):
        if "readouts" not in ck:
            continue
        for rn, r in ck["readouts"].items():
            spec = (prereg.get("d2_readout_specs") or {}).get(rn, {})
            ns = r["nulls"]["NULL_span"]
            na = r["nulls"]["NULL_aniso"]
            ni = r["nulls"]["NULL_iso"]
            e = {
                "input": (f"{ck['slug']} :: readout={rn} :: read_position={r['read_position']} "
                          f":: layer={r['layer_index']}/{ck['n_layer_slots'] - 1} "
                          f":: contrast={'+'.join(spec.get('pos_kinds', []))} vs "
                          f"{'+'.join(spec.get('neg_kinds', []))} :: n={r['n_items']} "
                          f"({r['n_pos']}/{r['n_neg']}) :: d={ck['hidden_size']}"),
                "output": ("PREMISE_UNDER_TEST: a difference-in-means direction fitted from "
                           "labelled harmful/benign items should beat an anisotropy-matched "
                           "random direction drawn from this checkpoint's own item span."),
                "predict_within_span_null_primary": ("CLEARS_P95" if ns.get(
                    "fitted_exceeds_null_p95") else "DOES_NOT_CLEAR_P95"),
                "predict_covariance_matched_null": ("CLEARS_P95" if na.get(
                    "fitted_exceeds_null_p95") else "DOES_NOT_CLEAR_P95"),
                "predict_isotropic_null": ("CLEARS_P95" if ni.get(
                    "fitted_exceeds_null_p95") else "DOES_NOT_CLEAR_P95"),
                "predict_label_permutation_null": ("CLEARS_P95" if r["perm_null"].get(
                    "fitted_exceeds_null_p95") else "DOES_NOT_CLEAR_P95"),
                "predict_whitened_refit_lda": ("CLEARS_ITS_OWN_SPAN_NULL" if r[
                    "white_span_null"].get("fitted_exceeds_null_p95")
                    else "DOES_NOT_CLEAR_ITS_OWN_SPAN_NULL"),
                "predict_best_of_20_null_replay": (
                    "FITTED_WINS" if _num(r["AUROC_xf"], -1) > _num(
                        ns.get("null_max_first_20_draws"), 9) else "BEST_OF_20_TIES_OR_WINS"),
                "metadata_slug": ck["slug"],
                "metadata_readout": rn,
                "metadata_matched_lexical_floor": r["matched_lexical_floor"],
                "metadata_matched_floor_is_a_floor": r["matched_floor_is_a_floor"],
                "metadata_registry_metrics_covered": r["registry_metrics_covered"],
                "eval_auroc_xf": _num(r["AUROC_xf"], float("nan")),
                "eval_auroc_in_sample": _num(r["AUROC_in"], float("nan")),
                "eval_inflation_in_minus_xf": _num(r["inflation_in_minus_xf"], float("nan")),
                "eval_null_span_mean": _num(ns.get("null_mean"), float("nan")),
                "eval_null_span_sd": _num(ns.get("null_sd"), float("nan")),
                "eval_null_span_p95": _num(ns.get("null_p95"), float("nan")),
                "eval_null_span_max": _num(ns.get("null_max"), float("nan")),
                "eval_null_span_max_first_20_draws": _num(
                    ns.get("null_max_first_20_draws"), float("nan")),
                "eval_fitted_percentile_in_span_null": _num(
                    ns.get("fitted_percentile_in_null"), float("nan")),
                "eval_p_one_sided_span": _num(ns.get("p_one_sided"), float("nan")),
                "eval_null_aniso_mean": _num(na.get("null_mean"), float("nan")),
                "eval_null_iso_mean": _num(ni.get("null_mean"), float("nan")),
                "eval_perm_null_mean": _num(r["perm_null"].get("null_mean"), float("nan")),
                "eval_perm_null_p95": _num(r["perm_null"].get("null_p95"), float("nan")),
                "eval_p_one_sided_perm": _num(r["perm_null"].get("p_one_sided"), float("nan")),
                "eval_auroc_white_xf": _num(r["AUROC_white_xf"], float("nan")),
                "eval_delta_white_minus_raw": _num(r["delta_white_minus_raw"], float("nan")),
                "eval_delta_auroc_vs_null_span_mean": _num(
                    r["delta_auroc_vs_null_span_mean"], float("nan")),
                "eval_auroc_xf_at_L_star": _num(
                    r["secondary_layer_swept"]["AUROC_xf_at_L_star"], float("nan")),
                "eval_L_star_depth_fraction": _num(
                    r["secondary_layer_swept"]["L_star_depth_fraction"], float("nan")),
                "eval_null_p95_with_matched_argmax": _num(
                    r["secondary_layer_swept"]["null_with_matched_argmax"].get("null_p95"),
                    float("nan")),
            }
            ex.append(e)
    if ex:
        datasets.append({"dataset": "D2_control_suite_per_checkpoint_readout", "examples": ex})

    # D2b
    ex = []
    for r in (d2b or {}).get("per_checkpoint", []):
        ex.append({
            "input": f"{r['slug']} :: first generated token over 160 items :: "
                     f"renderer={r.get('renderer')} thinking_supported={r.get('enable_thinking_supported')}",
            "output": ("EXPECTED_IF_THE_READOUT_IS_SOUND: the first generated token is a "
                       "CONTENT token, not a <think> or role delimiter."),
            "predict_audit_verdict": r["verdict"],
            "predict_modal_first_token": str(r.get("modal_first_token")),
            "metadata_cls": r["cls"], "metadata_family": r["family"],
            "metadata_top5_first_tokens": r["top5_first_tokens"],
            "metadata_generations_opening_on_delimiter": r[
                "stored_generations_opening_on_a_delimiter"],
            "eval_modal_first_token_share": _num(r["modal_first_token_share"], float("nan")),
            "eval_delimiter_share_over_items": _num(r["delimiter_share_over_items"], float("nan")),
            "eval_n_distinct_first_tokens": _num(r["n_distinct_first_tokens"], float("nan")),
            "eval_refusal_drive_vs_harm_label_auroc": _num(
                r["refusal_drive_vs_harm_label_auroc"], float("nan")),
        })
    if ex:
        datasets.append({"dataset": "D2b_first_generated_token_audit", "examples": ex})

    # D3
    ex = []
    for r in (d3 or {}).get("rows", []):
        ex.append({
            "input": f"{r['metric_id']} :: {r['name']} :: family={r['family']} :: "
                     f"inputs={r['inputs']} :: n_prompts={r['n_prompts']} :: "
                     f"form={r['functional_form_class_id']}",
            "output": f"FROZEN_PREDICTED_GAP_RANK={r['predicted_gap_rank']} "
                      f"(1=smallest held-out-minus-tuned gap, expected to transfer best)",
            "predict_beats_familyonly_baseline": str(r["beats_familyonly_3way"]),
            "predict_beats_sizeonly_baseline": str(r["beats_sizeonly_3way"]),
            "predict_sign_flip_across_size_ladder": str(r["sign_flip_across_ladder"]),
            "predict_reads_size_not_safety": str(r["reads_size_not_safety"]),
            "predict_degrade_reason": str(r["degrade_reason"] or "COMPUTED"),
            "predict_readout_flag": str(r["readout_flag"]),
            "metadata_candidate": r["candidate"], "metadata_incumbent": r["incumbent"],
            "metadata_baseline": r["baseline"],
            "metadata_family_binary_derived": r["family_binary_derived"],
            "eval_held_out_balacc_3way": _num(r["held_out_balacc_3way"], float("nan")),
            "eval_tuned_balacc_3way": _num(r["tuned_balacc_3way"], float("nan")),
            "eval_gap": _num(r["gap"], float("nan")),
            "eval_held_out_balacc_2way": _num(r["held_out_balacc_2way"], float("nan")),
            "eval_auroc_2way": _num(r["auroc_2way"], float("nan")),
            "eval_familyonly_baseline_3way": _num(r["familyonly_baseline_3way"], float("nan")),
            "eval_sizeonly_baseline_3way": _num(r["sizeonly_baseline_3way"], float("nan")),
            "eval_delta_over_best_matched_floor": _num(
                r["delta_over_best_matched_floor"], float("nan")),
            "eval_p_perm": _num(r["p_perm"], float("nan")),
            "eval_q_BH": _num(r["q_BH"], float("nan")),
            "eval_n_used": _num(r["n_used"], float("nan")),
            "eval_n_lineages": _num(r["n_lineages"], float("nan")),
            "eval_spearman_vs_log10_params_instruct": _num(
                r["spearman_vs_log10_params_instruct"], float("nan")),
            "eval_detectable_abs_rho_at_this_n": _num(
                r["detectable_abs_rho_at_this_n"], float("nan")),
        })
    if ex:
        datasets.append({"dataset": "D3_race_table_v2_within_family", "examples": ex})

    # D1 -- one example per judged cell, plus the positive control
    ex = []
    if d1:
        def _cell_example(tag, cell, question, extra=None):
            if not isinstance(cell, dict):
                return None
            dt = cell.get("detail", cell)
            e = {
                "input": (f"Qwen3-4B anchor :: {tag} :: pair={dt.get('pair')} "
                          f":: read={dt.get('read_position')} :: cell={dt.get('cell')} "
                          f":: layers={dt.get('layers')}"),
                "output": question,
                "predict_verdict": str(cell.get("verdict", d1.get("verdict"))),
                "predict_overlap_above_null_p95": str(dt.get("above_null_p95")),
                "predict_sign_of_rank1_cosine": str(dt.get("sign")),
                "metadata_nuance": cell.get("nuance"),
                "metadata_disattenuation": dt.get("disattenuated"),
                "eval_signed_rank1_cos": _num(dt.get("signed_rank1_cos"), float("nan")),
                "eval_abs_signed_rank1_cos": _num(dt.get("abs_signed_rank1_cos"), float("nan")),
                "eval_k1_null_p95": _num(dt.get("k1_null_p95"), float("nan")),
                "eval_k1_null_percentile": _num(dt.get("k1_null_percentile"), float("nan")),
                "eval_p_one_sided": _num(dt.get("p_one_sided"), float("nan")),
                "eval_k8_cos_first_principal_angle": _num(dt.get("k8_cos_first"), float("nan")),
                "eval_n_cells_scanned": _num(dt.get("n_cells_scanned_for_this_maximum"),
                                             float("nan")),
                "eval_bonferroni_p_over_cells": _num(dt.get("bonferroni_p_over_scanned_cells"),
                                                     float("nan")),
            }
            if extra:
                e.update(extra)
            return e

        Q = ("PRE-REGISTERED TWO-SIDED QUESTION: do official safety RL and community "
             "abliteration move the SAME subspace in OPPOSITE directions (a large NEGATIVE "
             "signed rank-1 cosine above the null), or DIFFERENT subspaces (overlap inside "
             "the matched-anisotropy null band)?")
        vj = d1.get("verdict_judged_at") or {}
        for tag, cell in (("verdict cell (hs_last)", vj),
                          ("strongest single layer (hs_last)",
                           vj.get("strongest_single_layer_supplementary")),
                          ("verdict cell (hs_first)", d1.get("verdict_hs_first"))):
            e = _cell_example(tag, cell, Q)
            if e:
                ex.append(e)
        pc = d1.get("positive_control") or {}
        for pos in ("hs_last", "hs_first"):
            sc = ((pc.get("activation_outcome") or {}).get(pos) or {}).get("strongest_cell")
            if not sc:
                continue
            blk = (pc.get("activation_outcome") or {}).get(pos) or {}
            ex.append({
                "input": (f"INTERNAL POSITIVE CONTROL :: mlabonne/Qwen3-4B-abliterated vs "
                          f"DreamFast/qwen3-4b-heretic :: two independent abliterations of "
                          f"ONE parent :: read={pos} :: cell={sc.get('cell')}"),
                "output": ("EXPECTED IF THE MEASUREMENT IS POWERED: two independent "
                           "abliterations of the same parent SHOULD share a subspace, i.e. "
                           "overlap above the matched-anisotropy null p95."),
                "predict_control_outcome": ("PASSES" if pc.get("control_passes")
                                            else "FAILS"),
                "predict_overlap_above_null_p95": str(sc.get("above_null_p95")),
                "metadata_weight_reading": (d1.get("verdict_judged_at") or {})
                .get("positive_control_weight_reading"),
                "eval_abs_signed_rank1_cos": _num(sc.get("abs_signed_rank1_cos"), float("nan")),
                "eval_k1_null_p95": _num(sc.get("k1_null_p95"), float("nan")),
                "eval_p_one_sided": _num(sc.get("p_one_sided"), float("nan")),
                "eval_n_cells_clearing_null_p95": _num(blk.get("n_cells_clearing_null_p95"),
                                                       float("nan")),
                "eval_n_cells": _num(blk.get("n_cells"), float("nan")),
                "eval_fraction_clearing": _num(blk.get("fraction_clearing"), float("nan")),
            })
    if not ex and d1:
        ex.append({
            "input": "Qwen3-4B anchor :: instruct-to-SafeRL vs instruct-to-abliterated "
                     "activation differences :: principal angles and signed rank-1 cosine",
            "output": ("PRE-REGISTERED TWO-SIDED QUESTION: do official safety RL and "
                       "community abliteration move the SAME subspace in OPPOSITE directions, "
                       "or DIFFERENT subspaces?"),
            "predict_verdict": str(d1.get("verdict", "MISSING")),
            "predict_verdict_hs_first": str(d1.get("verdict_hs_first", "MISSING")),
            "predict_positive_control": str((d1.get("positive_control") or {})
                                            .get("outcome", "MISSING")),
            "metadata_judged_at": d1.get("verdict_judged_at"),
            "metadata_anchor_resolution": d1.get("anchor_resolution"),
            "eval_n_anchor_members": _num(len((d1.get("anchor_resolution") or {})
                                              .get("resolved", {}) or {}), float("nan")),
        })
    if ex:
        datasets.append({"dataset": "D1_step1_principal_angles", "examples": ex})

    # D4
    ex = []
    for q in ("q1", "q2"):
        b = (d4 or {}).get(q)
        if not b:
            continue
        near = b.get("nearest", []) or []
        ex.append({
            "input": b.get("question", q),
            "output": "OPEN if no located paper reports this exact conjunction; otherwise "
                      "PARTIAL or CLOSED with the nearest paper named.",
            "predict_verdict": str(b.get("verdict")),
            "predict_nearest_paper": (f"{near[0].get('arxiv_id')} {near[0].get('title')} "
                                      f"{near[0].get('url')}" if near else "NONE_LOCATED"),
            "metadata_reason": b.get("reason"),
            "metadata_gap_we_fill": b.get("gap_we_fill"),
            "metadata_nearest": near,
            "eval_n_nearest_located": _num(len(near), 0.0),
        })
    if ex:
        datasets.append({"dataset": "D4_bounded_prior_art", "examples": ex})

    if not datasets:
        datasets = [{"dataset": "NO_STAGE_PRODUCED_OUTPUT",
                     "examples": [{"input": "n/a", "output": "n/a"}]}]

    # ---------------- handoff --------------------------------------------
    degraded = [{"metric_id": e.get("metric_id"), "reason": e.get("reason")}
                for e in ((d0 or {}).get("degrade_ledger") or [])]
    contaminated = (d2b or {}).get("contaminated_slugs", [])
    handoff = {
        "readout_contaminated": {
            "answer": "yes" if contaminated else "no",
            "per_checkpoint": {r["slug"]: r["verdict"]
                               for r in (d2b or {}).get("per_checkpoint", [])},
            "forces_three_way_readout_bakeoff": bool(contaminated),
            "statement": (d2b or {}).get("conclusion_for_the_sibling_gpu_experiment"),
        },
        "fitted_direction_verdict": {
            "verdict": fitted_verdict,
            "SURV": prim.get("SURV_span_of_n"),
            "wilson95": prim.get("SURV_span_wilson95"),
            "matched_contrast_verdict": twin.get("verdict_band", "MISSING"),
            "matched_contrast_SURV": twin.get("SURV_span_of_n"),
            "decision_for_the_family_panel": (
                "Fitted-direction metrics MAY be shipped: they clear their own "
                "anisotropy-matched null on enough checkpoints. BUT see "
                "mean_delta_white_minus_raw -- whitening removes much of the advantage, so "
                "the direction is partly riding residual-stream anisotropy."
                if fitted_verdict == "SURVIVES" else
                "Fitted-direction metrics MUST NOT be shipped on the strength of this panel "
                "alone; spend GPU time on the weight and behaviour families instead."
                if fitted_verdict == "PREMISE_FAILS" else
                f"AMBIGUOUS ({prim.get('SURV_span_of_n')}). Do not round the verdict in "
                "either direction; the family panel should carry the null with it."),
        },
        "step1_verdict": {
            "verdict": (d1 or {}).get("verdict", "MISSING"),
            "judged_at": (d1 or {}).get("verdict_judged_at"),
            "anchor_complete": bool(d1 and (d1.get("anchor_resolution") or {})
                                    .get("all_five_present")),
        },
        "degraded_metrics": {
            "n": len(degraded), "entries": degraded,
            "what_the_family_panel_must_reharvest_differently": (
                "Each entry names the reason in the pre-registered controlled vocabulary "
                "(MISSING_READ_POSITION / MISSING_LAYER / REQUIRES_REFUSAL_DRIVE / "
                "REQUIRES_GENERATION_NOT_STORED / REQUIRES_PARENT / CODE_ERROR). A metric "
                "that cannot be computed is a ROW WITH A REASON, never a silent omission."),
        },
        "schema_version": SCHEMA_VERSION,
        "table_merge_note": (
            "results/race_table_v2.csv is a STRICT SUPERSET of the frozen 18-column "
            "race_table.csv: the frozen columns come first, in their frozen order and with "
            "their frozen names and values, and the new columns are appended after them. The "
            "two merge by position as well as by name. The `family` column keeps the "
            "registry's own three values; the prose's LEVEL/ACROSS-ITEM binary is a NEW "
            "derived column, family_binary_derived."),
        "highest_value_missing_harvest": (d1 or {}).get("highest_value_missing_harvest"),
    }

    limitations = [
        "WITHIN-FAMILY ONLY. The 17 finished harvests span exactly two model families "
        "(Qwen3 and TinyLlama). This artifact supports ZERO held-out-FAMILY answer. Every "
        "number here is a within-family number and the family axis belongs to the sibling "
        "experiment.",
        f"ITEM BUDGET ~160 (harmful 64, benign_alarming 32, xstest_contrast 32, "
        f"plain_benign 32). Every AUROC is computed over at most 160 items, and the "
        f"within-span null is defined by that same span.",
        f"n_lineages = {panel.get('n_lineages')} . The resampling unit is the LINEAGE, so "
        f"every lineage-clustered bootstrap here resamples {panel.get('n_lineages')} "
        f"clusters. That is a SMALL resampling base and the intervals should be read as "
        f"indicative, not as precise coverage statements.",
        "PER-CHECKPOINT AXIS. Any negative result here is about a PER-CHECKPOINT score on "
        "OUR panel at OUR item budget. It is never a refutation of AMS, RAS, LatentBiopsy "
        "or any published PER-PROMPT number evaluated on its own panel.",
        "NO NEW COMPUTE. This artifact ran no model inference, downloaded nothing and used "
        "no GPU. It re-analyses the activation and weight tensors iteration 1 left on disk, "
        "so it inherits every harvesting choice iteration 1 made, including the 16 "
        "substituted AMS pairs and the four unpinned N-GLARE choices.",
        "THE FOUR INCUMBENTS WERE ALREADY NON-COMPARABLE for four different named reasons "
        "recorded in UP/INCUMBENTS.md; those named gaps are carried forward verbatim rather "
        "than re-derived, and this artifact does not close any of them.",
        "LAYER SELECTION. The primary D2 arm reads at a FIXED depth fraction of 0.60 and "
        "makes no per-checkpoint selection. The secondary L_star arm reproduces iteration "
        "1's argmax-over-layers, and there the same argmax is applied to every null draw; "
        "its null uses B=200 rather than the pre-registered B=1000, declared as a deviation.",
        "The base checkpoints use a different renderer and sit in their own stratum; they "
        "are a scale reference and are never mixed into the three-way class comparison.",
        f"The plan's printed detectable |rho| at n=17 was 0.472; the stated formula "
        f"tanh(1.96*sqrt(1.06/(n-3))) gives {detectable_rho(17):.3f}. This artifact "
        f"publishes the value its own formula produces and flags the discrepancy.",
    ]

    out = {
        "metadata": {
            "evaluation_name": "Do safety probes beat random directions?",
            "artifact_id": ARTIFACT_ID,
            "description": (
                "Offline, zero-new-compute evaluation of the 1.5 GB activation+weight harvest "
                "iteration 1 left orphaned on disk. Headline: the control the whole cheap-"
                "readout literature rests on -- does a fitted difference-in-means safety "
                "direction beat an ANISOTROPY-MATCHED random direction drawn from the same "
                "checkpoint's own item span, at n=17 with a 1000-draw null distribution "
                "instead of iteration 1's best-of-20 point estimate?"),
            "prereg_sha256": prereg.get("prereg_sha256"),
            "registry_sha256_before": reg_before,
            "registry_sha256_after": reg_after,
            "registry_intact": bool(reg_before == reg_after and integ.get("registry_intact")),
            "panel": {
                "n_dirs": panel.get("n_dirs"), "n_done": panel.get("n_done"),
                "slugs": panel.get("slugs"), "lineages": panel.get("lineages"),
                "n_lineages": panel.get("n_lineages"), "families": panel.get("families"),
                "class_counts": panel.get("class_counts"),
                "lineage_counts": panel.get("lineage_counts"),
                "assignment": panel.get("assignment"),
                "resampling_unit": panel.get("resampling_unit"),
            },
            "provenance": s0.get("provenance"),
            "folds": s0.get("folds"),
            "item_join": s0.get("item_join"),
            "registry_integrity": integ,
            "D0_rescore": d0 or {"status": "MISSING"},
            "D1_step1": d1 or {"status": "MISSING"},
            "D2_controls": {k: v for k, v in (d2 or {}).items() if k != "per_checkpoint"}
                           or {"status": "MISSING"},
            "D2b_first_token": {k: v for k, v in (d2b or {}).items()
                                if k != "per_checkpoint"} or {"status": "MISSING"},
            "D3_table": {k: v for k, v in (d3 or {}).items() if k != "rows"}
                        or {"status": "MISSING"},
            "D4_prior_art": d4 or {"status": "MISSING"},
            "verdicts": verdicts,
            "limitations": limitations,
            "cost_usd": 0.0,
            "cost_note": "Zero OpenRouter spend. No judge calls were made: judged labels "
                         "already existed in the iteration-1 outputs and cache.",
            "handoff": handoff,
            "prereg": prereg,
            "sealed_respected": (s0.get("inherited_context") or {})
            .get("how_this_artifact_honours_the_seal"),
            "runtime_minutes": round((time.time() - t0) / 60, 2),
        },
        "metrics_agg": ma,
        "datasets": datasets,
    }
    write_json(RESULTS.parent / "eval_out.json", out)
    logger.info(f"eval_out.json written: {len(ma)} agg metrics, "
                f"{len(datasets)} datasets, "
                f"{sum(len(d['examples']) for d in datasets)} examples")


if __name__ == "__main__":
    main()
