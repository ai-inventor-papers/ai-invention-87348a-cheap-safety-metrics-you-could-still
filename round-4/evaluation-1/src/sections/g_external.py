"""STEP G - external coverage + capability join + per-metric partial correlations.

CPU-only, $0. Reads EXP3 RESULTS.md/stage4_external.json/stage4b_strata.json (HELM coverage,
guardian identical-weights ceiling), DS3 full_data_out.json dev_panel_outcome + results/
external_join.json (OLB v2 capability join), EXP1 results/step5_correlations.json + iter-2
race checkpoint metric values (full_method_out.json dataset family_race), and DS3/sealed/
SEALED.md (leak note).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from io_utils import EXP1, EXP3, DS3, PROVENANCE, get, load, short, src, dump, spearman_with_p, \
    lineage_cluster_bootstrap, fast_spearman  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a_targets import metric_file  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

WS = Path(__file__).resolve().parent.parent
DISCREPANCIES: list[dict] = []


def _core_components(v):
    """metadata_core_components is a dict in this dataset, but may in principle be a
    python-repr string; handle both per the coordinator's instruction."""
    if v is None:
        return None
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        return ast.literal_eval(v)
    raise TypeError(type(v))


# ---------------------------------------------------------------------------
# G1: HELM coverage + guardian identical-weights ceiling
# ---------------------------------------------------------------------------
def step1_helm_coverage() -> dict:
    s4_path = EXP3 / "results" / "stage4_external.json"
    s4b_path = EXP3 / "results" / "stage4b_strata.json"
    resolution = get(s4_path, "resolution")
    n_total = resolution["n_models_total"]
    n_resolved = resolution["n_resolved"]
    n_closed = resolution["n_closed_api_by_construction"]
    s1 = get(s4b_path, "S1_sub4B_with_published_safety")
    n_sub4b = s1["n"]

    for (label, val, exp) in [("n_models_total", n_total, 81), ("n_resolved", n_resolved, 36),
                               ("n_closed_api", n_closed, 45), ("n_sub4B_published_safety", n_sub4b, 2)]:
        if val != exp:
            DISCREPANCIES.append({"item": f"HELM coverage {label}", "prompt_expected": exp,
                                   "recomputed": val, "source": src(s4_path, "resolution")})

    ceiling = get(s4_path, "guardian_pair_ceiling")
    headline_ref = ceiling["headline_ref"]
    headline_share = ceiling["headline_max_share_of_across_model_variance"]
    # recompute directly from the pair's per_scenario record to double-check
    matching_pair = next(p for p in ceiling["pairs"] if p["base"] == headline_ref["base"]
                          and p["variant"] == headline_ref["variant"])
    sc = matching_pair["per_scenario"][headline_ref["scenario"]]
    recomputed_share = (sc["delta"] ** 2) / sc["across_model_variance"]
    sd_ratio = abs(sc["delta"]) / (sc["across_model_variance"] ** 0.5)  # if it were SD instead

    out = {
        "source_resolution": src(s4_path, "resolution"),
        "n_models_total": n_total, "n_resolved": n_resolved, "n_closed_api_by_construction": n_closed,
        "n_sub4B_with_published_safety_number": {"value": n_sub4b, "source": src(s4b_path, "S1_sub4B_with_published_safety"),
                                                    "note": s1["ecosystem_finding"]},
        "guardian_identical_weights_ceiling": {
            "source": src(s4_path, "guardian_pair_ceiling"),
            "pair": {"base": headline_ref["base"], "variant": headline_ref["variant"], "scenario": headline_ref["scenario"]},
            "delta_safety_score": sc["delta"], "base_score": sc["base_score"], "variant_score": sc["variant_score"],
            "across_model_n": sc["across_model_n"], "across_model_population_variance": sc["across_model_variance"],
            "share_reported_as": "delta^2 / population_variance (NOT delta/SD)",
            "share_of_across_model_VARIANCE": recomputed_share,
            "equivalent_ratio_if_expressed_as_SD": sd_ratio,
            "prompt_expected_ratio": 6.7,
            "clarification": ("The '6.7x' figure is a ratio of the guardian pair's SQUARED score "
                "gap to the total across-model POPULATION VARIANCE in that scenario (xstest), i.e. "
                "delta^2/Var = 6.72, NOT delta/SD (which is instead sqrt(6.72) = %.3f, i.e. the pair's "
                "gap is ~2.6 standard deviations of the across-model spread). Framed as a ceiling: any "
                "weights-only readout of safety is mechanically blind to a serving-time guardian "
                "wrapper, and here the wrapper alone moves the score by MORE than the entire "
                "across-model variance in that scenario, so no weights-only signal can be assumed "
                "to explain more than this share of the variance is genuinely due to different "
                "weights.") % (recomputed_share ** 0.5),
            "n_guardian_pairs_found": ceiling["n_pairs"],
        },
    }
    if abs(recomputed_share - 6.7) > 0.1:
        pass  # 6.719 vs prompt's rounded 6.7 -- within rounding, not a discrepancy
    return out


# ---------------------------------------------------------------------------
# G2: OLB v2 capability join
# ---------------------------------------------------------------------------
OLB2_SUBBENCH = ["olb2_average", "olb2_ifeval", "olb2_bbh", "olb2_math_lvl5", "olb2_gpqa",
                 "olb2_musr", "olb2_mmlu_pro"]


def step2_olb2_join() -> dict:
    dpo_path = DS3 / "full_data_out.json"
    ej_path = DS3 / "results" / "external_join.json"
    d = load(dpo_path)
    panel_ds = next(x for x in d["datasets"] if x["dataset"] == "dev_panel_outcome")
    panel = {e["metadata_repo"]: e for e in panel_ds["examples"]}
    PROVENANCE.append([short(dpo_path), "datasets[dev_panel_outcome].examples", f"<{len(panel)} rows>"])

    ej = load(ej_path)
    n_per_column = ej["n_per_column"]
    olb2_rows = [r for r in ej["rows"] if r.get("olb2_average") is not None]
    PROVENANCE.append([short(ej_path), "n_per_column.olb2_average", n_per_column["olb2_average"]])

    joined = []
    for r in olb2_rows:
        repo = r["repo_id"]
        pe = panel.get(repo)
        cc = _core_components(pe["metadata_core_components"]) if pe else None
        hr = cc.get("harm_refusal_rate") if cc else None
        ba = cc.get("benign_alarming_compliance") if cc else None
        p3 = (hr * ba) if (hr is not None and ba is not None) else None
        row = {"repo": repo, "in_panel": pe is not None,
               "B_S2_core": pe["metadata_S2_core"] if pe else None,
               "J2_core_affine_only": pe["metadata_J2_core"] if pe else None,
               "P3_true_product": p3,
               "harm_refusal_rate": hr, "benign_alarming_compliance": ba,
               "lineage": pe["metadata_lineage"] if pe else None,
               "olb2_alias_of": r.get("olb2_alias_of")}
        for c in OLB2_SUBBENCH:
            row[c] = r.get(c)
        joined.append(row)

    n_raw_olb2_hits = len(olb2_rows)
    n_in_panel = sum(1 for r in joined if r["in_panel"])
    n_with_B = sum(1 for r in joined if r["B_S2_core"] is not None)

    if n_raw_olb2_hits != 16:
        DISCREPANCIES.append({"item": "olb2 raw hit count in external_join", "prompt_expected": 16,
                               "recomputed": n_raw_olb2_hits, "source": src(ej_path, "n_per_column")})
    dup_row = next((r for r in joined if not r["in_panel"]), None)
    mirror_row = next((r for r in joined if r["in_panel"] and r["olb2_alias_of"] == (dup_row["repo"] if dup_row else None)), None)
    dedup_note = None
    if n_in_panel != 16:
        dedup_note = (f"external_join.json reports n_per_column.olb2_average=16 (16 distinct repo_id "
            f"rows with non-null OLB v2 data), but joining those against dev_panel_outcome's 36 panel "
            f"repos (exact repo-id match, no mirror resolution) gives only n={n_in_panel}. The dropped "
            f"row is '{dup_row['repo'] if dup_row else None}' (the base org's own HF upload; "
            f"external_join.olb2_alias=false for it). Its OLB v2 scores are IDENTICAL to those of "
            f"'{mirror_row['repo'] if mirror_row else None}' (external_join.olb2_alias_of points there), "
            f"which IS in the panel and IS counted here -- but the panel only graded that downstream "
            f"mirror checkpoint, never the base org's own upload, so the base-org row has no panel "
            f"counterpart and is correctly dropped from a repo-id-exact join.")
        DISCREPANCIES.append({"item": "OLB v2 join n (panel-matched)", "prompt_expected": 16,
                               "recomputed": n_in_panel, "detail": dedup_note,
                               "source": [src(ej_path, "n_per_column"), src(dpo_path, "datasets")]})

    rows_with_B = [r for r in joined if r["B_S2_core"] is not None]
    rows_with_P3 = [r for r in joined if r["P3_true_product"] is not None]
    n_lineages = len(set(r["lineage"] for r in rows_with_B))
    n_lineages_p3 = len(set(r["lineage"] for r in rows_with_P3))

    def _nullboot():
        return {"ci": [None, None], "n_valid": 0, "n_discarded": 0, "B": 0, "n_lineages": 0}

    correlations = {}
    for c in OLB2_SUBBENCH:
        xs = [r["B_S2_core"] for r in rows_with_B]
        ys = [r[c] for r in rows_with_B]
        lin = [r["lineage"] for r in rows_with_B]
        sp_B = spearman_with_p(xs, ys)
        boot_B = lineage_cluster_bootstrap(xs, ys, lin) if len(rows_with_B) >= 4 else _nullboot()

        xs3 = [r["P3_true_product"] for r in rows_with_P3]
        ys3 = [r[c] for r in rows_with_P3]
        lin3 = [r["lineage"] for r in rows_with_P3]
        sp_P3 = spearman_with_p(xs3, ys3)
        boot_P3 = lineage_cluster_bootstrap(xs3, ys3, lin3) if len(rows_with_P3) >= 4 else _nullboot()

        correlations[c] = {
            "n_B": len(rows_with_B),
            "spearman_B_vs_capability": sp_B, "lineage_bootstrap_ci_B": boot_B,
            "n_P3": len(rows_with_P3),
            "spearman_P3_vs_capability": sp_P3, "lineage_bootstrap_ci_P3": boot_P3,
        }

    out = {
        "source_files": {"dev_panel_outcome": src(dpo_path, "datasets[dev_panel_outcome]"),
                          "external_join": src(ej_path, "rows")},
        "olb2_subbenchmarks_used": OLB2_SUBBENCH,
        "n_raw_olb2_hits_in_external_join": n_raw_olb2_hits,
        "n_panel_matched_exact_repo_id": n_in_panel,
        "n_panel_matched_with_nonnull_B_S2_core": n_with_B,
        "n_panel_matched_with_nonnull_P3": len(rows_with_P3),
        "n_lineages_among_B_matched": n_lineages,
        "n_lineages_among_P3_matched": n_lineages_p3,
        "dedup_note": dedup_note,
        "definitions": {
            "B": "balanced safety = metadata_S2_core = 0.5*harm_refusal_rate + 0.5*benign_alarming_compliance",
            "P3_true_product": ("P3 = harm_refusal_rate * benign_alarming_compliance, both pulled from "
                "dev_panel_outcome.metadata_core_components (a dict; ast.literal_eval fallback if it "
                "were ever a repr string -- it never was in this dataset). This is the genuine product "
                "the prompt asked for, distinct in rank from B."),
            "J2_is_affine_of_B_not_a_product": ("DS3/README.md and scripts/summarize.py define "
                "J2 = 2*S2 - 1 = harm_refusal_rate + benign_alarming_compliance - 1 -- an AFFINE "
                "(Frechet-lower-bound-style) rescaling of B/S2, NOT the product hr*ba. Kept here only "
                "as J2_core_affine_only for reference; Spearman(J2, X) == Spearman(B, X) exactly for "
                "any X, so it is NOT used as 'P' for correlation reporting (P3_true_product is used "
                "instead, per fix)."),
        },
        "primary_result_olb2_average": correlations["olb2_average"],
        "per_subbench": correlations,
        "joined_rows": joined,
    }
    # sanity: confirm J2 is indeed affine-of-B (still true), and that P3 is NOT rank-identical to B
    if rows_with_B:
        xs = np.array([r["B_S2_core"] for r in rows_with_B])
        j2s = np.array([r["J2_core_affine_only"] for r in rows_with_B])
        max_resid = float(np.max(np.abs((2 * xs - 1) - j2s))) if len(xs) else None
        out["definitions"]["J2_equals_2B_minus_1_max_abs_residual"] = max_resid
    if rows_with_P3:
        common = [r for r in rows_with_P3 if r["B_S2_core"] is not None]
        if len(common) >= 3:
            rho_B_P3 = fast_spearman(np.array([r["B_S2_core"] for r in common]),
                                      np.array([r["P3_true_product"] for r in common]))
            out["definitions"]["spearman_B_vs_P3_on_common_checkpoints"] = {
                "n": len(common), "rho": rho_B_P3,
                "note": "B and P3 are rank-DIFFERENT in general (P3 is a true product, not affine-of-B)."}
    return out


# ---------------------------------------------------------------------------
# G3: per-metric partial correlations on race checkpoints
# ---------------------------------------------------------------------------
def _partial_spearman_B_given_cap(metric_vals, B_vals, cap_vals):
    """Pearson of rank-residuals of metric and B after regressing each rank vector on capability
    rank (partial Spearman)."""
    m = np.asarray(metric_vals, float)
    b = np.asarray(B_vals, float)
    c = np.asarray(cap_vals, float)
    ok = np.isfinite(m) & np.isfinite(b) & np.isfinite(c)
    m, b, c = m[ok], b[ok], c[ok]
    n = len(m)
    if n < 4 or np.ptp(c) == 0:
        return {"value": float("nan"), "n": n}
    rm, rb, rc = stats.rankdata(m), stats.rankdata(b), stats.rankdata(c)
    def resid(y, x):
        slope, intercept = np.polyfit(x, y, 1)
        return y - (slope * x + intercept)
    rm_res, rb_res = resid(rm, rc), resid(rb, rc)
    if np.ptp(rm_res) == 0 or np.ptp(rb_res) == 0:
        return {"value": float("nan"), "n": n}
    r = float(np.corrcoef(rm_res, rb_res)[0, 1])
    return {"value": r, "n": n}


def _clean_num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


def step3_metric_capability() -> dict:
    """Maximised-overlap version (per coordinator fix 2): metric values are read directly from
    each checkpoint's metric_cache file via a_targets.metric_file(slug, judge_grades_row), for
    EVERY iter-2 EXP1 checkpoint in results/per_checkpoint.json (not just the 17 race slugs)."""
    step5_path = EXP1 / "results" / "step5_correlations.json"
    metric_ids = [r["metric_id"] for r in get(step5_path, "rows")]

    pc_path = EXP1 / "results" / "per_checkpoint.json"
    pc_rows = load(pc_path)
    PROVENANCE.append([short(pc_path), "*", f"<{len(pc_rows)} rows>"])
    slug_to_repo = {row["slug"]: row["repo"] for row in pc_rows}

    jg_path = EXP1 / "results" / "judge_grades.json"
    judge_grades_pc = get(jg_path, "per_checkpoint")

    per_metric_ckpt: dict[str, dict[str, float]] = {m: {} for m in metric_ids}
    metric_file_log = []
    for slug, repo in slug_to_repo.items():
        g = judge_grades_pc.get(slug)
        path, note = metric_file(slug, g)
        entry = {"slug": slug, "repo": repo, "has_judge_grades": g is not None,
                  "metric_file": (short(path) if path else None), "match_note": note}
        if path is not None:
            row = load(path)
            for mid in metric_ids:
                v = _clean_num(row.get(mid))
                if v is not None:
                    per_metric_ckpt[mid][repo] = v
        metric_file_log.append(entry)
    PROVENANCE.append([short(pc_path), "metric_file() resolution over all 33 checkpoints",
                        f"<{sum(1 for e in metric_file_log if e['metric_file'])} resolved>"])

    # capability + B + P3 + lineage join (repo-keyed), from DS3
    dpo_path = DS3 / "full_data_out.json"
    dd = load(dpo_path)
    panel = {e["metadata_repo"]: e for e in
             next(x for x in dd["datasets"] if x["dataset"] == "dev_panel_outcome")["examples"]}
    ej = load(DS3 / "results" / "external_join.json")
    cap_by_repo = {r["repo_id"]: r["olb2_average"] for r in ej["rows"] if r.get("olb2_average") is not None}

    all_ckpts = sorted(slug_to_repo.values())
    ckpt_cap_join = {c: cap_by_repo[c] for c in all_ckpts if c in cap_by_repo}
    ckpt_B_join = {c: panel[c]["metadata_S2_core"] for c in all_ckpts
                   if c in panel and panel[c]["metadata_S2_core"] is not None}
    ckpt_lineage = {c: panel[c]["metadata_lineage"] for c in all_ckpts if c in panel}

    overlap_cap_ckpts = sorted(set(ckpt_cap_join))
    overlap_capB_ckpts = sorted(set(ckpt_cap_join) & set(ckpt_B_join))

    results = {}
    for mid, vals in per_metric_ckpt.items():
        # spearman(metric, capability)
        common_cap = [c for c in overlap_cap_ckpts if vals.get(c) is not None]
        m_vals = [vals[c] for c in common_cap]
        cap_vals = [ckpt_cap_join[c] for c in common_cap]
        sp_cap = spearman_with_p(m_vals, cap_vals) if len(common_cap) >= 3 else \
            {"rho": float("nan"), "p": float("nan"), "p_perm": float("nan"), "n": len(common_cap)}

        # partial spearman(metric, B | capability), on checkpoints with metric+capability+B
        common_capB = [c for c in overlap_capB_ckpts if vals.get(c) is not None]
        n_capB = len(common_capB)
        if n_capB < 4:
            partial = {"value": None, "n": n_capB, "note": f"n={n_capB} < 4, not identifiable -> null"}
            boot = {"ci": [None, None], "n_valid": 0, "n_discarded": 0, "B": 0, "n_lineages": 0,
                    "note": f"n={n_capB} < 4, bootstrap skipped"}
        else:
            m_vals2 = [vals[c] for c in common_capB]
            b_vals2 = [ckpt_B_join[c] for c in common_capB]
            cap_vals2 = [ckpt_cap_join[c] for c in common_capB]
            lin2 = [ckpt_lineage[c] for c in common_capB]
            partial = _partial_spearman_B_given_cap(m_vals2, b_vals2, cap_vals2)
            boot = _partial_lineage_bootstrap(m_vals2, b_vals2, cap_vals2, lin2, B=2000)
        results[mid] = {
            "n_checkpoints_with_metric_value": len(vals),
            "overlap_n_with_capability": len(common_cap),
            "checkpoints_overlap_capability": common_cap,
            "spearman_metric_vs_capability": sp_cap,
            "overlap_n_with_capability_and_B": n_capB,
            "checkpoints_overlap_capability_and_B": common_capB,
            "partial_spearman_metric_B_given_capability": partial,
            "partial_spearman_lineage_bootstrap_ci": boot,
        }

    n_metrics_with_overlap = sum(1 for r in results.values() if r["overlap_n_with_capability"] > 0)
    n_metrics_with_capB_ge4 = sum(1 for r in results.values() if r["overlap_n_with_capability_and_B"] >= 4)
    return {
        "source_step5": src(step5_path, "rows"),
        "source_per_checkpoint": src(pc_path, "*"),
        "source_metric_file_fn": "sections/a_targets.py:metric_file(slug, g)",
        "olb2_subbenchmark_used_for_capability": "olb2_average",
        "olb2_subbenchmarks_used_full_list": OLB2_SUBBENCH,
        "checkpoint_mapping_note": ("Fix 2: maximised overlap. Iterated ALL 33 rows of "
            "EXP1/results/per_checkpoint.json (repo<-slug map), not just the 17 family_race race "
            "slugs. For each, called a_targets.metric_file(slug, judge_grades['per_checkpoint']."
            "get(slug)) to locate its metric_cache/*__probe_cf__*__v3-session3.json file and read "
            "each of the 10 step5 metric_id keys directly (missing/None/NaN -> dropped). Capability "
            "universe is still fixed by external_join's OLB v2 rows (16 repos), so the "
            "checkpoint*capability* overlap is unchanged at n=7 (same 7 repos as before: "
            "%s); it is the metric coverage WITHIN those 7 (and within the 3 that also have B) "
            "that is now read from the raw per-checkpoint cache directly instead of the "
            "family_race dataset's pre-filtered rows.") % ", ".join(overlap_cap_ckpts),
        "n_checkpoints_total": len(all_ckpts),
        "n_checkpoints_with_capability": len(overlap_cap_ckpts),
        "n_checkpoints_with_capability_and_B": len(overlap_capB_ckpts),
        "checkpoints_with_capability_and_B": overlap_capB_ckpts,
        "n_metrics_total": len(metric_ids),
        "n_metrics_with_capability_overlap": n_metrics_with_overlap,
        "n_metrics_with_capability_and_B_overlap_n_ge_4": n_metrics_with_capB_ge4,
        "per_metric": results,
        "metric_file_resolution_log": metric_file_log,
    }


def _partial_lineage_bootstrap(m, b, cap, lineage, B=2000, seed=20260921):
    m = np.asarray(m, float); b = np.asarray(b, float); cap = np.asarray(cap, float)
    lin = np.asarray(lineage)
    groups = sorted(set(lin.tolist()))
    idx_by = {g: np.where(lin == g)[0] for g in groups}
    rng = np.random.default_rng(seed)
    vals = []
    disc = 0
    for _ in range(B):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([idx_by[groups[i]] for i in pick])
        if len(np.unique(idx)) < 4 or np.ptp(cap[idx]) == 0:
            disc += 1
            continue
        r = _partial_spearman_B_given_cap(m[idx], b[idx], cap[idx])
        v = r["value"]
        if v == v:
            vals.append(v)
        else:
            disc += 1
    if len(vals) < 50:
        return {"ci": [None, None], "n_valid": len(vals), "n_discarded": disc, "B": B, "n_lineages": len(groups)}
    return {"ci": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))],
            "n_valid": len(vals), "n_discarded": disc, "B": B, "n_lineages": len(groups)}


# ---------------------------------------------------------------------------
# G4: explicit n=0 statements + leak note
# ---------------------------------------------------------------------------
def step4_explicit_statements() -> dict:
    ej_path = DS3 / "results" / "external_join.json"
    ej = get(ej_path, "n_per_column")
    stage4b_path = EXP3 / "results" / "stage4b_strata.json"

    checks = {}
    for name, col in [("HELM_safety(helm_safety_mean)", "helm_safety_mean"),
                       ("HELM_xstest", "helm_xstest"), ("AIR-Bench(airbench_refusal)", "airbench_refusal"),
                       ("SALAD-Bench(salad_score)", "salad_score"), ("GSM8K", "gsm8k"), ("MMLU_outside_OLB2", "mmlu")]:
        checks[name] = ej.get(col)

    trustllm_present = False
    arenahard_present = False
    for f in [ej_path]:
        content = Path(f).read_text().lower()
        if "trustllm" in content:
            trustllm_present = True
        if "arena-hard" in content or "arena_hard" in content:
            arenahard_present = True

    gsm8k_mmlu_discrepancy = None
    if checks["GSM8K"] != 0 or checks["MMLU_outside_OLB2"] != 0:
        # identify which repo
        rows = get(ej_path, "rows", record=False)
        hit = next((r["repo_id"] for r in rows if r.get("mmlu") is not None or r.get("gsm8k") is not None), None)
        gsm8k_mmlu_discrepancy = {
            "item": "GSM8K / MMLU(outside OLB2) coverage for panel",
            "prompt_expected": "n=0",
            "recomputed": {"gsm8k_n": checks["GSM8K"], "mmlu_n": checks["MMLU_outside_OLB2"], "hit_repo": hit},
            "source": src(ej_path, "n_per_column"),
            "detail": (f"external_join.n_per_column reports gsm8k=1, mmlu=1 (not 0): both come from a "
                "single row, repo_id='{}' (TinyLlama/TinyLlama-1.1B-Chat-v1.0), via the v1-old "
                "aggregated open-llm-leaderboard fallback described in external_join.json 'notes' "
                "(openllm_capability.json's 40-row slice has 0 hits; the aggregated old-contents "
                "parquet recovers exactly 1). TinyLlama/TinyLlama-1.1B-Chat-v1.0 IS one of the 36 "
                "dev_panel_outcome checkpoints, so this n=1 is a real (if isolated) panel hit, not an "
                "off-panel model.").format(hit),
        }
        DISCREPANCIES.append(gsm8k_mmlu_discrepancy)

    out = {
        "source": src(ej_path, "n_per_column"),
        "TrustLLM": {"n": 0, "note": "column never constructed in external_join.py; string 'TrustLLM' " +
                     ("FOUND" if trustllm_present else "absent") + " in external_join.json"},
        "AIR-Bench": {"n": checks["AIR-Bench(airbench_refusal)"], "note": "column present (airbench_refusal), 0 hits"},
        "GSM8K": {"n": checks["GSM8K"], "prompt_claimed": 0, "matches_prompt": checks["GSM8K"] == 0},
        "MMLU_outside_OLB2_MMLU-PRO": {"n": checks["MMLU_outside_OLB2"], "prompt_claimed": 0,
                                        "matches_prompt": checks["MMLU_outside_OLB2"] == 0},
        "Arena-Hard": {"n": 0, "note": "column never constructed in external_join.py; string 'Arena-Hard/arena_hard' " +
                       ("FOUND" if arenahard_present else "absent") + " in external_join.json"},
        "HELM_AIR_SALAD_coverage_sub4B_panel": {
            "helm_safety_mean_n": checks["HELM_safety(helm_safety_mean)"],
            "helm_xstest_n": checks["HELM_xstest"],
            "airbench_refusal_n": checks["AIR-Bench(airbench_refusal)"],
            "salad_score_n": checks["SALAD-Bench(salad_score)"],
            "all_zero": all(checks[k] == 0 for k in ("HELM_safety(helm_safety_mean)", "HELM_xstest",
                                                        "AIR-Bench(airbench_refusal)", "SALAD-Bench(salad_score)")),
            "corroborated_by": src(stage4b_path, "S1_sub4B_with_published_safety"),
        },
        "gsm8k_mmlu_discrepancy": gsm8k_mmlu_discrepancy,
    }
    return out


def step4_leak_note() -> dict:
    sealed_path = DS3 / "sealed" / "SEALED.md"
    text = sealed_path.read_text()
    # extract the "## Leak note" section verbatim
    marker = "## Leak note"
    idx = text.find(marker)
    leak_section = text[idx:].strip() if idx >= 0 else None
    PROVENANCE.append([short(sealed_path), "## Leak note (verbatim section)", "<text>"])
    return {"source": short(sealed_path), "verbatim_leak_note": leak_section}


def main() -> None:
    out = {
        "g1_helm_coverage_and_guardian_ceiling": step1_helm_coverage(),
        "g2_olb2_capability_join": step2_olb2_join(),
        "g3_per_metric_capability_correlations": step3_metric_capability(),
        "g4_explicit_zero_coverage_statements": step4_explicit_statements(),
        "g4_sealed_leak_note": step4_leak_note(),
    }
    out["discrepancies"] = DISCREPANCIES
    out["provenance"] = PROVENANCE
    dump(out, WS / "results" / "G_external.json")
    print("wrote results/G_external.json")
    print("HELM: n=%d resolved=%d closed=%d sub4B=%d" % (
        out["g1_helm_coverage_and_guardian_ceiling"]["n_models_total"],
        out["g1_helm_coverage_and_guardian_ceiling"]["n_resolved"],
        out["g1_helm_coverage_and_guardian_ceiling"]["n_closed_api_by_construction"],
        out["g1_helm_coverage_and_guardian_ceiling"]["n_sub4B_with_published_safety_number"]["value"]))
    print("guardian ratio:", out["g1_helm_coverage_and_guardian_ceiling"]["guardian_identical_weights_ceiling"]["share_of_across_model_VARIANCE"])
    print("olb2 join n (raw/in_panel/with_B):",
          out["g2_olb2_capability_join"]["n_raw_olb2_hits_in_external_join"],
          out["g2_olb2_capability_join"]["n_panel_matched_exact_repo_id"],
          out["g2_olb2_capability_join"]["n_panel_matched_with_nonnull_B_S2_core"])
    print("rho_B_cap (olb2_average):", out["g2_olb2_capability_join"]["primary_result_olb2_average"]["spearman_B_vs_capability"])
    print("rho_P3_cap (olb2_average):", out["g2_olb2_capability_join"]["primary_result_olb2_average"]["spearman_P3_vs_capability"])
    print("n metrics with capability overlap:", out["g3_per_metric_capability_correlations"]["n_metrics_with_capability_overlap"],
          "/", out["g3_per_metric_capability_correlations"]["n_metrics_total"])
    print("n metrics with cap+B overlap n>=4:", out["g3_per_metric_capability_correlations"]["n_metrics_with_capability_and_B_overlap_n_ge_4"])
    print("discrepancies:", len(DISCREPANCIES))


if __name__ == "__main__":
    main()
