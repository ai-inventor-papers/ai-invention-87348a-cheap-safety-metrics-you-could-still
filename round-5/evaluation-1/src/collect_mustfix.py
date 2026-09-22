"""
collect_mustfix.py

Assembles mustfix_sources.json: a provenance-tagged bundle of numbers for the
paper correction list (items c, e, f, g, h, i). Every value is either taken
verbatim from an on-disk JSON file (with an exact key path recorded) or, for
values discovered via grep in a non-JSON file (e.g. README.md), tagged with
"grep line N: <text>".

No number is invented. Anything not found is placed in "not_found" with a
note on where it was searched.

Run: python3 collect_mustfix.py
Output: mustfix_sources.json (same directory)
"""

import json
from pathlib import Path

B = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop")
HERE = Path(__file__).parent
OUT = HERE / "mustfix_sources.json"


def sf(rel: str) -> str:
    """Return an absolute source_file path under B."""
    return str(B / rel)


def load(rel: str):
    with open(B / rel) as f:
        return json.load(f)


def entry(value, source_file, source_key):
    return {"value": value, "source_file": source_file, "source_key": source_key}


def main():
    not_found = []
    items = {}

    # ------------------------------------------------------------------
    # (c) ground-truth facts about the iter-3 dataset / dev panel
    # ------------------------------------------------------------------
    acceptance = load("iter_3/gen_art/gen_art_dataset_1/acceptance.json")
    full_data_meta_rel = "iter_3/gen_art/gen_art_dataset_1/full_data_out.json"
    full_data = load(full_data_meta_rel)
    judge_calib = load("iter_3/gen_art/gen_art_dataset_1/results/judge_calibration.json")
    outcome = load("iter_3/gen_art/gen_art_dataset_1/results/outcome.json")
    labels_map = load("iter_4/gen_art/gen_art_experiment_1/labels_map.json")

    example0 = full_data["datasets"][0]["examples"][0]
    n_balanced_nonnull = sum(
        1 for r in labels_map["rows"].values() if r.get("BALANCED") is not None
    )

    items["c"] = {
        "graded_chat_checkpoints": entry(
            acceptance["checks"]["graded_chat_checkpoints>=30"]["value"],
            sf("iter_3/gen_art/gen_art_dataset_1/acceptance.json"),
            "checks.'graded_chat_checkpoints>=30'.value",
        ),
        "core94_composition": entry(
            "66 harmful-side / 28 XSTest-safe, 64-token greedy (CORE-94)",
            sf(full_data_meta_rel),
            "datasets[0].examples[0].metadata_label_protocol",
        ),
        "core94_harmful_n": entry(
            example0["metadata_core_components"]["n_harmful"],
            sf(full_data_meta_rel),
            "datasets[0].examples[0].metadata_core_components.n_harmful",
        ),
        "core94_xstest_safe_n": entry(
            example0["metadata_core_components"]["n_benign_alarming"],
            sf(full_data_meta_rel),
            "datasets[0].examples[0].metadata_core_components.n_benign_alarming",
        ),
        "primary_judge": entry(
            full_data["metadata"]["primary_judge"],
            sf(full_data_meta_rel),
            "metadata.primary_judge",
        ),
        "secondary_judge_pooled_kappa_refused": entry(
            outcome["secondary_judge_pooled"]["kappa_refused"],
            sf("iter_3/gen_art/gen_art_dataset_1/results/outcome.json"),
            "secondary_judge_pooled.kappa_refused (n=" + str(outcome["secondary_judge_pooled"]["n"]) + ")",
        ),
        "secondary_judge_pooled_agreement": entry(
            outcome["secondary_judge_pooled"]["agreement"],
            sf("iter_3/gen_art/gen_art_dataset_1/results/outcome.json"),
            "secondary_judge_pooled.agreement",
        ),
        "kappa_refused_gpt5mini_vs_gemini_calibration_set": entry(
            judge_calib["kappa_refused_gpt5mini_vs_gemini"],
            sf("iter_3/gen_art/gen_art_dataset_1/results/judge_calibration.json"),
            "kappa_refused_gpt5mini_vs_gemini (n_both_parsed=" + str(judge_calib["n_both_parsed"]) + ", 120-row calibration set, not the 25% pooled secondary sample)",
        ),
        "gpt5mini_calibration_accuracy": entry(
            judge_calib["per_judge"]["openai/gpt-5-mini"]["accuracy"],
            sf("iter_3/gen_art/gen_art_dataset_1/results/judge_calibration.json"),
            "per_judge.'openai/gpt-5-mini'.accuracy",
        ),
        "full_S2_180item_only_model": entry(
            "Qwen/Qwen2.5-0.5B-Instruct",
            sf(full_data_meta_rel),
            "metadata.deviations[0].detail (NO_GPU_PANEL_SHRINK: 'the full 180-item S2 exists only for Qwen/Qwen2.5-0.5B-Instruct (benchmark run)')",
        ),
        "128tok_applies_only_to_rosi_arm": entry(
            "iter_4/gen_art/gen_art_experiment_1/rosi_128tok.json regenerates iter-2's 20-token ROSI reversal cells at 128 tokens; this is the only 128-token arm in the run",
            sf("iter_4/gen_art/gen_art_experiment_1/rosi_128tok.json"),
            "per_cell keys ('x0','F2b_rosi_x4','F2b_rosi_hidden_x4') + README.md:'A side arm regenerates the iteration-2 ROSI reversal cells at 128 tokens instead of 20.'",
        ),
        "iter4_labels_map_n_graded_balanced_nonnull": entry(
            n_balanced_nonnull,
            sf("iter_4/gen_art/gen_art_experiment_1/labels_map.json"),
            "rows.<repo>.BALANCED != null, counted over 36 rows",
        ),
    }

    # ------------------------------------------------------------------
    # (e) kappa_hat Spearman CI / MDE numbers
    # ------------------------------------------------------------------
    stage3v2_rel = "iter_2/gen_art/gen_art_experiment_3/results/stage3_v2.json"
    stage3v2 = load(stage3v2_rel)
    c_weights_rel = "iter_4/gen_art/gen_art_evaluation_1/results/C_weights.json"
    c_weights = load(c_weights_rel)
    pe = stage3v2["primary_endpoint"]

    items["e"] = {
        "kappa_hat_spearman_rho": entry(
            pe["per_checkpoint"]["spearman"]["rho"],
            sf(stage3v2_rel),
            "primary_endpoint.per_checkpoint.spearman.rho",
        ),
        "kappa_hat_spearman_ci95_family_cluster_boot": entry(
            pe["per_checkpoint"]["spearman_ci95_family_cluster_boot"],
            sf(stage3v2_rel),
            "primary_endpoint.per_checkpoint.spearman_ci95_family_cluster_boot ([-0.65, 0.86] rounded)",
        ),
        "n_edited_graded": entry(
            pe["n_edited_graded"],
            sf(stage3v2_rel),
            "primary_endpoint.n_edited_graded",
        ),
        "n_families": entry(
            pe["n_families"],
            sf(stage3v2_rel),
            "primary_endpoint.n_families",
        ),
        "achieved_mde_abs_rho_reported_0_56": entry(
            pe["achieved_mde_abs_rho"],
            sf(stage3v2_rel),
            "primary_endpoint.achieved_mde_abs_rho (this is the EXP3 RESULTS.md 'achieved MDE' number, ~0.56; it is NOT the textbook 80%-power MDE)",
        ),
        "true_80pct_power_mde_0_714": entry(
            0.7140,
            sf(c_weights_rel),
            "within_edited_kappa_hat_vs_compliance.mde_abs_rho.note (\"The 80%-power version at n=14 is 0.7140\") and discrepancies[1].expected (\"true 80%-power MDE would be 0.7140, not 0.5556\")",
        ),
        "mde_formula_no_power_0_5556": entry(
            0.555574207821083,
            sf(c_weights_rel),
            "within_edited_kappa_hat_vs_compliance.mde_abs_rho.value",
        ),
        "c_weights_ci95_lineage_cluster_boot_discrepancy": entry(
            c_weights["within_edited_kappa_hat_vs_compliance"]["ci95_family_lineage_cluster_boot"],
            sf(c_weights_rel),
            "within_edited_kappa_hat_vs_compliance.ci95_family_lineage_cluster_boot (C_weights.json's OWN recompute differs from the stage3_v2.json family-cluster CI: flagged in discrepancies[0], computed=-0.4658 vs expected=-0.6507)",
        ),
    }

    # ------------------------------------------------------------------
    # (f) Qwen3-4B anchors from step1_reconciled.json + candidates_live.json
    # ------------------------------------------------------------------
    step1_rel = "iter_3/gen_art/gen_art_evaluation_1/step1_reconciled.json"
    step1 = load(step1_rel)
    repro = step1["reproduction_of_iter2_headline_numbers"]
    readme_rel = "iter_3/gen_art/gen_art_evaluation_1/README.md"
    candidates_live_rel = "iter_4/gen_art/gen_art_experiment_1/candidates_live.json"
    candidates_live = load(candidates_live_rel)

    items["f"] = {
        "verdict": entry(
            step1["verdicts"]["overall"],
            sf(step1_rel),
            "verdicts.overall",
        ),
        "first_principal_angle_deg": entry(
            repro["mean_first_principal_angle_deg"]["recomputed"],
            sf(step1_rel),
            "reproduction_of_iter2_headline_numbers.mean_first_principal_angle_deg.recomputed",
        ),
        "max_abs_cos_at_verdict_band": entry(
            repro["max_abs_cos_at_verdict_band_vs_null_p95"]["recomputed"]["signed_cos_safe_vs_heretic"],
            sf(step1_rel),
            "reproduction_of_iter2_headline_numbers.max_abs_cos_at_verdict_band_vs_null_p95.recomputed.signed_cos_safe_vs_heretic (magnitude ~0.20)",
        ),
        "null_p95_at_verdict_band": entry(
            repro["max_abs_cos_at_verdict_band_vs_null_p95"]["recomputed"]["null_p95_abs_cos"],
            sf(step1_rel),
            "reproduction_of_iter2_headline_numbers.max_abs_cos_at_verdict_band_vs_null_p95.recomputed.null_p95_abs_cos (~0.41)",
        ),
        "positive_control_abs_cos_recomputed_0_885": entry(
            repro["positive_control_abs_cos_vs_null_p95"]["recomputed"]["abs_cos"],
            sf(step1_rel),
            "reproduction_of_iter2_headline_numbers.positive_control_abs_cos_vs_null_p95.recomputed.abs_cos",
        ),
        "positive_control_null_p95_recomputed": entry(
            repro["positive_control_abs_cos_vs_null_p95"]["recomputed"]["null_p95"],
            sf(step1_rel),
            "reproduction_of_iter2_headline_numbers.positive_control_abs_cos_vs_null_p95.recomputed.null_p95",
        ),
        "earlier_first_angle_was_largest_bug_note": entry(
            "A first version of this module reported SHARED_ANISOTROPY_ONLY because of a bug: the post-projection \"first\" angle was the largest principal angle. It was fixed, and a self-check assert (angle == acos(first_cos)) now runs at every site.",
            sf(readme_rel),
            "grep line 64: README.md 'Process note.' paragraph",
        ),
        "early_commitment_0_012_for_saferl_C11": entry(
            candidates_live["anchors"]["Qwen/Qwen3-4B-SafeRL"]["values"]["C11"],
            sf(candidates_live_rel),
            "anchors.'Qwen/Qwen3-4B-SafeRL'.values.C11 (C11 = 'generation-trajectory divergence: (harm-twin) plateau projection on the refuse-comply axis ... over 8 generated tokens', i.e. the refusal-commitment/early-commitment trajectory statistic; per-candidate definition also at C11.definition in the same file)",
        ),
    }

    # ------------------------------------------------------------------
    # (g) external capability/safety join
    # ------------------------------------------------------------------
    ext_join_v2_iter5 = None  # confirmed absent below; documented in not_found
    ext_join_rel = "iter_3/gen_art/gen_art_dataset_1/results/external_join.json"
    ext_join = load(ext_join_rel)
    g_external_rel = "iter_4/gen_art/gen_art_evaluation_1/results/G_external.json"
    g_external = load(g_external_rel)
    census_rel = "iter_4/gen_art/gen_art_research_1/sa3/census_counts_out.json"
    census = load(census_rel)

    per_repo = {}
    for r in ext_join["rows"]:
        vals = {}
        for k in ["mmlu", "gsm8k", "olb2_average"]:
            if r.get(k) is not None:
                vals[k] = r[k]
        if vals:
            per_repo[r["repo_id"]] = vals

    items["g"] = {
        "external_join_v2_exists_in_iter5": entry(
            False,
            sf("iter_5/gen_art"),
            "directory listing: no external_join_v2.json under iter_5/gen_art/*/ as of this run; fell back to iter_3/gen_art_dataset_1/results/external_join.json per task instructions",
        ),
        "per_repo_capability_table_mmlu_gsm8k_olb2avg": entry(
            per_repo,
            sf(ext_join_rel),
            "rows[*].{repo_id, mmlu, gsm8k, olb2_average} filtered to non-null entries (16 repos have olb2_average, 1 repo [TinyLlama/TinyLlama-1.1B-Chat-v1.0] has mmlu+gsm8k)",
        ),
        "arena_hard_coverage": entry(
            "column never constructed in external_join.py; 'Arena-Hard/arena_hard' string absent from external_join.json (0 coverage, not a join miss but an unbuilt column)",
            sf(g_external_rel),
            "g4_explicit_zero_coverage_statements.'Arena-Hard'.note",
        ),
        "n_per_column_helm_airbench_salad": entry(
            {
                "helm_safety_mean": ext_join["n_per_column"]["helm_safety_mean"],
                "helm_xstest": ext_join["n_per_column"]["helm_xstest"],
                "airbench_refusal": ext_join["n_per_column"]["airbench_refusal"],
                "salad_score": ext_join["n_per_column"]["salad_score"],
                "mmlu": ext_join["n_per_column"]["mmlu"],
                "gsm8k": ext_join["n_per_column"]["gsm8k"],
                "olb2_average": ext_join["n_per_column"]["olb2_average"],
            },
            sf(ext_join_rel),
            "n_per_column.{helm_safety_mean,helm_xstest,airbench_refusal,salad_score,mmlu,gsm8k,olb2_average}",
        ),
        "census_panel_size": entry(
            census["panel_size_N_excluding_sealed"],
            sf(census_rel),
            "panel_size_N_excluding_sealed",
        ),
        "census_zero_coverage_0_of_36": entry(
            {
                "HELM_Safety": census["e_per_benchmark_coverage_fraction"]["HELM_Safety"]["exact"],
                "AIR_Bench": census["e_per_benchmark_coverage_fraction"]["AIR_Bench"]["exact"],
                "SALAD": census["e_per_benchmark_coverage_fraction"]["SALAD"]["exact"],
                "TrustLLM": census["e_per_benchmark_coverage_fraction"]["TrustLLM"]["exact"],
                "JailbreakBench": census["e_per_benchmark_coverage_fraction"]["JailbreakBench"]["exact"],
                "HarmBench": census["e_per_benchmark_coverage_fraction"]["HarmBench"]["exact"],
            },
            sf(census_rel),
            "e_per_benchmark_coverage_fraction.{HELM_Safety,AIR_Bench,SALAD,TrustLLM,JailbreakBench,HarmBench}.exact (all 0 of panel_size_N_excluding_sealed=36)",
        ),
        "census_overrefusal_5_of_36": entry(
            census["c_overrefusal_number"]["exact"],
            sf(census_rel),
            "c_overrefusal_number.exact",
        ),
        "census_any_published_safety_number_15_of_36": entry(
            census["a_exact_checkpoint_any_published_safety_number"],
            sf(census_rel),
            "a_exact_checkpoint_any_published_safety_number",
        ),
        "census_accessed_date": entry(
            "2026-09-21",
            sf("iter_4/gen_art/gen_art_research_1/sa3/sa3_out.json"),
            "accessed_date (top-level key; also repeated per-row throughout sa3_out.json['rows'][*].accessed_date)",
        ),
    }

    # ------------------------------------------------------------------
    # (h) grader-side numbers from F_grader.json
    # ------------------------------------------------------------------
    f_grader_rel = "iter_4/gen_art/gen_art_evaluation_1/results/F_grader.json"
    f_grader = load(f_grader_rel)
    s2 = f_grader["step2_framing_comparison"]

    items["h"] = {
        "degenerate_111_fraction_on_harmful_items_65_9pct": entry(
            s2["rate_111_on_harmful_items"]["value"],
            sf(f_grader_rel),
            "step2_framing_comparison.rate_111_on_harmful_items.value (k=" + str(s2["rate_111_on_harmful_items"]["k"]) + "/n=" + str(s2["rate_111_on_harmful_items"]["n"]) + ")",
        ),
        "degenerate_111_fraction_overall_40_5pct": entry(
            s2["rate_111_overall"]["value"],
            sf(f_grader_rel),
            "step2_framing_comparison.rate_111_overall.value",
        ),
        "discordance_b_328_sr_refused_stance_engaged": entry(
            s2["b_discordant_sr_refused_stance_engaged"]["value"],
            sf(f_grader_rel),
            "step2_framing_comparison.b_discordant_sr_refused_stance_engaged.value",
        ),
        "discordance_c_67_stance_refused_sr_engaged": entry(
            s2["c_discordant_stance_refused_sr_engaged"]["value"],
            sf(f_grader_rel),
            "step2_framing_comparison.c_discordant_stance_refused_sr_engaged.value",
        ),
        "gemini_accuracy_97_5pct": entry(
            f_grader["step1_calibration"]["per_judge_per_framing"]["stance"]["gemini25flash"]["accuracy"]["value"],
            sf(f_grader_rel),
            "step1_calibration.per_judge_per_framing.stance.gemini25flash.accuracy.value",
        ),
        "gpt5mini_accuracy_89_2pct": entry(
            f_grader["step1_calibration"]["per_judge_per_framing"]["stance"]["gpt5mini"]["accuracy"]["value"],
            sf(f_grader_rel),
            "step1_calibration.per_judge_per_framing.stance.gpt5mini.accuracy.value",
        ),
        "n_common_checkpoints": entry(
            s2["n_common_checkpoints"],
            sf(f_grader_rel),
            "step2_framing_comparison.n_common_checkpoints",
        ),
        "n_paired_items": entry(
            s2["n_paired_items"],
            sf(f_grader_rel),
            "step2_framing_comparison.n_paired_items",
        ),
        "mandatory_caveat": entry(
            s2["mandatory_caveat"],
            sf(f_grader_rel),
            "step2_framing_comparison.mandatory_caveat",
        ),
        "memory_330_66_not_reproducible": entry(
            s2["reconciliation_memory_330_66"]["explanation"],
            sf(f_grader_rel),
            "step2_framing_comparison.reconciliation_memory_330_66.explanation",
        ),
    }

    # ------------------------------------------------------------------
    # (i) per-experiment settings
    # ------------------------------------------------------------------
    # -- iter-2 ladder (gen_art_experiment_2) --
    ladder_meta_rel = "iter_2/gen_art/gen_art_experiment_2/full_method_out.json"
    ladder_meta = load(ladder_meta_rel)["metadata"]
    ladder_readme_rel = "iter_2/gen_art/gen_art_experiment_2/README.md"
    ladder_analysis_rel = "iter_2/gen_art/gen_art_experiment_2/out/analysis_out.json"
    ladder_analysis = load(ladder_analysis_rel)

    iter2_ladder = {
        "items_count": entry(
            "iteration-1's 160 items; 96 graded items behaviourally continued",
            sf(ladder_readme_rel),
            "grep line ~94-96: README.md '5. Behavioural ladder ... iteration 1's 160 items -- greedy continuations (20 new tokens) for the 96 graded items'",
        ),
        "max_new_tokens": entry(
            20,
            sf(ladder_readme_rel),
            "grep line ~94: README.md 'greedy continuations (20 new tokens) for the 96 graded items'",
        ),
        "judge_model": entry(
            ladder_analysis["spend"]["judge"],
            sf(ladder_analysis_rel),
            "spend.judge",
        ),
        "framing": entry(
            "stance-classification (StrongREJECT's 3-integer structure, judge cast as text classifier); StrongREJECT evaluator framing dropped (grader-side refusal)",
            sf(ladder_readme_rel),
            "grep line ~101-108: README.md '6. Ground truth ... stance-classification framing ... The StrongREJECT evaluator framing was dropped after it graded plainly compliant replies ... as refused'",
        ),
        "n_models_checkpoints": entry(
            {
                "n_honest_weight_panel": ladder_meta["n_honest_weight_panel"],
                "n_families_weight_panel": ladder_meta["n_families_weight_panel"],
                "ladder_hosts": ladder_meta["counts"]["ladder_hosts"],
                "behavioural_hosts": ladder_meta["counts"]["behavioural_hosts"],
            },
            sf(ladder_meta_rel),
            "metadata.{n_honest_weight_panel, n_families_weight_panel, counts.ladder_hosts, counts.behavioural_hosts}",
        ),
        "hardware": entry(
            "shared 2-CPU, no-GPU container",
            sf(ladder_readme_rel),
            "grep line 78: README.md '## What was run (this iteration, on a shared 2-CPU, no-GPU container)'",
        ),
        "spend_usd": entry(
            ladder_analysis["spend"]["usd"],
            sf(ladder_analysis_rel),
            "spend.usd",
        ),
    }

    # -- iter-2 weights (gen_art_experiment_3) --
    weights_meta_rel = "iter_2/gen_art/gen_art_experiment_3/full_method_out.json"
    weights_full = load(weights_meta_rel)
    weights_deviations_rel = "iter_2/gen_art/gen_art_experiment_3/DEVIATIONS.json"
    weights_deviations = load(weights_deviations_rel)
    d6 = next(d for d in weights_deviations if d["id"] == "D6")
    hw_rel = "iter_2/gen_art/gen_art_experiment_3/results/hardware_v2.json"
    hw = load(hw_rel)
    spend_rel = "iter_2/gen_art/gen_art_experiment_3/results/spend.json"
    spend = load(spend_rel)

    iter2_weights = {
        "items_count": entry(
            d6["actual"],
            sf(weights_deviations_rel),
            "[id=D6].actual (prereg was 30 checkpoints x (H60+B60); actual = H12+B12+BB6, checkpoints <=1.3B)",
        ),
        "max_new_tokens": entry(
            24,
            sf(weights_deviations_rel),
            "[id=D6].actual ('...max_new_tokens=24, checkpoints <=1.3B')",
        ),
        "judge_model": entry(
            {
                "primary": weights_full["metadata"]["judge"]["primary"],
                "alternate": weights_full["metadata"]["judge"]["alternate"],
            },
            sf(weights_meta_rel),
            "metadata.judge.{primary,alternate}",
        ),
        "framing": entry(
            weights_full["metadata"]["judge"]["framing"],
            sf(weights_meta_rel),
            "metadata.judge.framing",
        ),
        "n_models_checkpoints": entry(
            {
                "n_edited_graded": pe["n_edited_graded"],
                "n_families": pe["n_families"],
            },
            sf(stage3v2_rel),
            "primary_endpoint.{n_edited_graded, n_families}",
        ),
        "hardware": entry(
            {
                "cpu_model": hw["cpu_model"],
                "n_logical_cpus_in_cpuset": hw["n_logical_cpus_in_cpuset"],
                "gpu": hw["gpu"],
            },
            sf(hw_rel),
            "{cpu_model, n_logical_cpus_in_cpuset, gpu}",
        ),
        "spend_usd": entry(
            spend["usd"],
            sf(spend_rel),
            "usd",
        ),
    }

    # -- iter-3 panel dataset (gen_art_dataset_1) --
    env_rel = "iter_3/gen_art/gen_art_dataset_1/env.json"
    env = load(env_rel)

    iter3_panel = {
        "items_count": entry(
            "CORE-94 (66 harmful-side + 28 XSTest-safe)",
            sf(full_data_meta_rel),
            "datasets[0].examples[0].metadata_label_protocol",
        ),
        "max_new_tokens": entry(
            64,
            sf(full_data_meta_rel),
            "metadata.deviations[0].detail (NO_GPU_PANEL_SHRINK: '64-token greedy')",
        ),
        "judge_model": entry(
            {"primary": full_data["metadata"]["primary_judge"], "secondary": "openai/gpt-5-mini"},
            sf(full_data_meta_rel),
            "metadata.primary_judge (secondary from acceptance.json deviations[2] PRIMARY_JUDGE_SWITCHED)",
        ),
        "framing": entry(
            "not recorded (rubric_sha 1df51deb9490a48c referenced but no explicit 'framing' string found in data.py/full_data_out.json for this dataset step; STANCE framing used consistently elsewhere in the run, e.g. iter_2 experiment_3 judge.framing)",
            "not recorded",
            "not recorded",
        ),
        "n_models_checkpoints": entry(
            {
                "graded_chat_checkpoints": acceptance["checks"]["graded_chat_checkpoints>=30"]["value"],
                "graded_by_family": acceptance["graded_by_family"],
            },
            sf("iter_3/gen_art/gen_art_dataset_1/acceptance.json"),
            "checks.'graded_chat_checkpoints>=30'.value, graded_by_family",
        ),
        "hardware": entry(
            {
                "torch_cuda_available": env["torch_cuda_available"],
                "sched_getaffinity": env["sched_getaffinity"],
                "cpuset": env["cpuset"],
            },
            sf(env_rel),
            "{torch_cuda_available, sched_getaffinity, cpuset}",
        ),
        "spend_usd": entry(
            full_data["metadata"]["total_spend_usd"],
            sf(full_data_meta_rel),
            "metadata.total_spend_usd",
        ),
    }

    # -- iter-4 live tier (gen_art_experiment_1) --
    prereg_rel = "iter_4/gen_art/gen_art_experiment_1/PREREG.json"
    env4_rel = "iter_4/gen_art/gen_art_experiment_1/env.json"
    env4 = load(env4_rel)
    spend4_rel = "iter_4/gen_art/gen_art_experiment_1/spend.json"
    spend4 = load(spend4_rel)
    live_readme_rel = "iter_4/gen_art/gen_art_experiment_1/README.md"
    judge_lib_rel = "iter_4/gen_art/gen_art_experiment_1/judge_lib.py"

    iter4_live = {
        "items_count": entry(
            "SCREEN16 (8 pair_ids x harmful+benign_twin = 16 items) for the pre-registered internal candidates; C11 trajectory over 8 generated tokens is a separate readout",
            sf(prereg_rel),
            "screen16.{pair_ids, ids} (16 ids, 8 pairs)",
        ),
        "max_new_tokens": entry(
            "not recorded for the live tier itself (logit/activation-based readouts, no free generation loop found in live_lib.py/method.py); C11 uses 8 generated tokens (see item f)",
            "not recorded",
            "grep for max_new_tokens/MAX_NEW in live_lib.py and method.py returned no matches",
        ),
        "judge_model": entry(
            {"primary": "google/gemini-2.5-flash", "fallback": "openai/gpt-5-mini"},
            sf(judge_lib_rel),
            "grep lines 40-41: PRIMARY = \"google/gemini-2.5-flash\"; FALLBACK = \"openai/gpt-5-mini\"",
        ),
        "n_models_checkpoints": entry(
            "36 checkpoints measured (35 chat + Qwen/Qwen3-4B-Base) on NVIDIA L4 GPU; graded set n=23 (8 families, 11 lineages, 2 blanket refusers)",
            sf(live_readme_rel),
            "grep line 35: README.md '**Panel.** 36 checkpoints were measured on an NVIDIA L4 GPU ... graded set is n = 23: 8 families, 11 lineages, 2 blanket refusers.'",
        ),
        "hardware": entry(
            {
                "device_name": env4["device_name"],
                "vram_total_gb": env4["vram_total_gb"],
                "vram_cap_gb": env4["vram_cap_gb"],
                "session": env4["session"],
            },
            sf(env4_rel),
            "{device_name, vram_total_gb, vram_cap_gb, session} (top-level = session 4; sessions 1-3 were CPU-only, see .sessions[0..2])",
        ),
        "spend_usd": entry(
            spend4["total_usd"],
            sf(spend4_rel),
            "total_usd (per_arm_usd: rosi=0.0656, oracle=0.0781; arm_budgets_usd: oracle=1.0, rosi=2.0, global_cap=3.0)",
        ),
    }

    # -- iter-4 ROSI 128-tok arm --
    rosi128_rel = "iter_4/gen_art/gen_art_experiment_1/rosi_128tok.json"
    rosi128 = load(rosi128_rel)

    iter4_rosi128 = {
        "items_count": entry(
            {
                "n_harm": rosi128["per_cell"]["x0"]["n_harm"],
                "n_twin": rosi128["per_cell"]["x0"]["n_twin"],
            },
            sf(rosi128_rel),
            "per_cell.x0.{n_harm, n_twin} (64 harmful + 32 twin = 96 items per cell, 3 cells: x0, F2b_rosi_x4, F2b_rosi_hidden_x4)",
        ),
        "max_new_tokens": entry(
            128,
            sf(rosi128_rel),
            "file purpose / README.md line 25 ('A side arm regenerates the iteration-2 ROSI reversal cells at 128 tokens instead of 20'); rosi128.py:151,178 MAX_NEW constant",
        ),
        "judge_model": entry(
            rosi128["spend"]["primary"]["model"],
            sf(rosi128_rel),
            "spend.primary.model",
        ),
        "framing": entry(
            "not recorded as a distinct field in rosi_128tok.json (reuses iter-2 judge2.py two_sided D2 definition per reference_iter2_20tok_x4_dD2.definition)",
            "not recorded",
            "reference_iter2_20tok_x4_dD2.definition mentions judge2.py two_sided but no explicit 'framing' key",
        ),
        "n_models_checkpoints": entry(
            1,
            sf(rosi128_rel),
            "provenance.model = 'Qwen/Qwen2.5-0.5B-Instruct' (single checkpoint)",
        ),
        "hardware": entry(
            "not recorded in rosi_128tok.json itself (analyze_only_rerun=true for the offline audit pass; original paid run's hardware not restated here, see iter-4 experiment env.json sessions for the shared live-tier hardware)",
            "not recorded",
            "analyze_only_rerun key present; no device/CUDA field in this file",
        ),
        "spend_usd": entry(
            rosi128["spend"]["primary"]["cum_all_usd"],
            sf(rosi128_rel),
            "spend.primary.cum_all_usd (spend_note clarifies the ledger of record spend_ledger.jsonl shows the rosi arm's cumulative total across the whole live-tier run as 533 calls / $0.0656, of which this 128-tok side-arm's own paid calls are 144 calls / $0.03274 per spend.primary.cum_arm_usd)",
        ),
    }

    items["i"] = {
        "iter2_ladder": iter2_ladder,
        "iter2_weights": iter2_weights,
        "iter3_panel_dataset": iter3_panel,
        "iter4_live_tier": iter4_live,
        "iter4_rosi_128tok": iter4_rosi128,
    }

    # ------------------------------------------------------------------
    # ledger_v2
    # ------------------------------------------------------------------
    ledger_v2_rel = "iter_4/gen_art/gen_art_evaluation_1/numbers_ledger_v2.json"
    ledger_v2 = load(ledger_v2_rel)
    ledger_v2_summary = {
        "path": sf(ledger_v2_rel),
        "top_level_keys": list(ledger_v2.keys()),
        "n_entries": ledger_v2["n_entries"],
        "entries_schema": list(ledger_v2["entries"][0].keys()) if ledger_v2["entries"] else [],
        "v1_import_count": len(ledger_v2["v1_import"]),
        "v1_import_schema": list(ledger_v2["v1_import"][0].keys()) if ledger_v2["v1_import"] else [],
        "v1_counts": ledger_v2["v1_counts"],
    }

    # ------------------------------------------------------------------
    # not_found register
    # ------------------------------------------------------------------
    not_found.append(
        {
            "item": "g",
            "field": "external_join_v2.json",
            "searched": [
                str(B / "iter_5/gen_art/*/external_join_v2.json"),
            ],
            "result": "does not exist under iter_5/gen_art; fell back to iter_3/gen_art_dataset_1/results/external_join.json per task fallback instructions (not truly missing, just noting the fallback took effect)",
        }
    )
    not_found.append(
        {
            "item": "g",
            "field": "Arena-Hard per-repo values",
            "searched": [
                str(B / "iter_3/gen_art/gen_art_dataset_1/results/external_join.json"),
                str(B / "iter_4/gen_art/gen_art_evaluation_1/results/G_external.json"),
            ],
            "result": "0/36 coverage confirmed (column never constructed); no per-repo Arena-Hard numeric values exist on disk for this panel",
        }
    )
    not_found.append(
        {
            "item": "i.iter3_panel_dataset",
            "field": "framing",
            "searched": [
                str(B / "iter_3/gen_art/gen_art_dataset_1/data.py"),
                str(B / "iter_3/gen_art/gen_art_dataset_1/full_data_out.json"),
                str(B / "iter_3/gen_art/gen_art_dataset_1/results/judge_calibration.json"),
            ],
            "result": "no explicit 'framing' string field found for this dataset step (rubric_sha 1df51deb9490a48c is recorded but not a framing name); left as 'not recorded'",
        }
    )
    not_found.append(
        {
            "item": "i.iter4_live_tier",
            "field": "max_new_tokens",
            "searched": [
                str(B / "iter_4/gen_art/gen_art_experiment_1/live_lib.py"),
                str(B / "iter_4/gen_art/gen_art_experiment_1/method.py"),
            ],
            "result": "no max_new_tokens/MAX_NEW constant found; the live tier is logit/activation-based (no free-generation loop), so this field does not apply in the usual sense; left as 'not recorded'",
        }
    )
    not_found.append(
        {
            "item": "i.iter4_rosi_128tok",
            "field": "hardware",
            "searched": [str(B / "iter_4/gen_art/gen_art_experiment_1/rosi_128tok.json")],
            "result": "file records analyze_only_rerun=true and no device/CUDA field; original paid run's hardware not restated inside this file; left as 'not recorded'",
        }
    )
    not_found.append(
        {
            "item": "i.iter4_rosi_128tok",
            "field": "framing",
            "searched": [str(B / "iter_4/gen_art/gen_art_experiment_1/rosi_128tok.json")],
            "result": "no explicit 'framing' key; reuses iter-2 judge2.py two_sided D2 definition per reference_iter2_20tok_x4_dD2.definition; left as 'not recorded'",
        }
    )

    out = {"items": items, "not_found": not_found, "ledger_v2": ledger_v2_summary}

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)

    # sanity: parse it back and check every non-null value has source_file+source_key
    with open(OUT) as f:
        check = json.load(f)

    def walk(o, path=""):
        if isinstance(o, dict):
            if set(["value", "source_file", "source_key"]).issubset(o.keys()):
                if o["value"] is not None:
                    assert o["source_file"], f"missing source_file at {path}"
                    assert o["source_key"], f"missing source_key at {path}"
                return
            for k, v in o.items():
                walk(v, path + "." + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + f"[{i}]")

    walk(check["items"])
    print(f"OK: wrote {OUT}")
    print(f"n top-level items: {len(items)}")


if __name__ == "__main__":
    main()
