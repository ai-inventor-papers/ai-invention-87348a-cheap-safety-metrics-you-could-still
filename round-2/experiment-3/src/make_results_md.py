#!/usr/bin/env python3
"""Render RESULTS.md - every headline number this artifact measured, with its n, in one place."""
from __future__ import annotations
import json, sys
from pathlib import Path
WS = Path(__file__).resolve().parent
R = WS / "results"

def j(p, d=None):
    try:
        return json.loads((R / p).read_text())
    except (OSError, json.JSONDecodeError):
        return d if d is not None else {}

def f(x, nd=3):
    if x is None: return "n/a"
    try:
        v = float(x)
        return "n/a" if v != v else f"{v:.{nd}g}"
    except (TypeError, ValueError):
        return str(x)

def main() -> None:
    g0, g1 = j("gate0_eigensolver.json"), j("gate1_estimator.json")
    a3, a4b = j("stage3_analysis.json"), j("stage4b_strata.json")
    a5, hw = j("stage5_bonus.json"), j("hardware.json")
    spend, thr = j("spend.json", {"usd": 0}), j("throughput.json")
    L = ["# Results\n",
         f"**VERDICT: {a3.get('VERDICT','n/a')}** — {a3.get('VERDICT_SENTENCE','')}\n",
         "## Hardware actually available\n",
         f"- GPU: {hw.get('gpu','n/a')}",
         f"- CPU: {hw.get('cpu_affinity_n','?')} logical (`{hw.get('cpuset_cpus','?')}`) — "
         f"two hyperthreads of ONE physical core; host load average "
         f"{hw.get('host_loadavg_at_start')}",
         f"- Dense eigh cost measured: {hw.get('measured_dense_eigh_seconds')}",
         f"- OpenRouter spend: ${f(spend.get('usd'),4)} of an $8.00 hard cap "
         f"({spend.get('calls','?')} calls)\n",
         "## Gates\n",
         f"- GATE 0 eigensolver: **{g0.get('verdict','n/a')}** "
         f"({g0.get('n_pass')}/{g0.get('n_checks')})",
         f"- GATE 1 estimator: **{g1.get('verdict','n/a')}** "
         f"({g1.get('n_pass')}/{g1.get('n_checks')})"]
    rc = g1.get("real_constructed") or {}
    if rc.get("variants"):
        L += ["\n### Gate 1 — real weights, constructed edit at KNOWN kappa\n",
              f"Real spectrum: sigma_min/sigma_rms = **{f(rc.get('real_sigma_min_over_median'))}**, "
              f"so a bottom-spectrum RANK read can only see |1-kappa| < "
              f"**{f(rc.get('predicted_rank_read_operating_range_abs1mk'))}**.\n",
              "| variant | kappa_hat | BOTGAP_min | BSA | XLC | RQ | cos(r_hat, r_true) |",
              "|---|---|---|---|---|---|---|"]
        for k, v in rc["variants"].items():
            L.append(f"| {k} | {f(v.get('kappa_hat_mean'))} | {f(v.get('BOTGAP_min'))} | "
                     f"{f(v.get('BSA_w'))} | {f(v.get('XLC'))} | {f(v.get('RQ_pooled'))} | "
                     f"{f(v.get('cos_rhat_rtrue'))} |")
    L += ["\n## Part 1 — parent-free recipe recovery on the real panel\n",
          f"- checkpoints read: **{a3.get('n_ckpt_with_recipe','?')}** "
          f"({a3.get('n_edited','?')} edited / {a3.get('n_honest','?')} honest, "
          f"{a3.get('n_families','?')} architecture families)",
          f"- median seconds per checkpoint: {f(thr.get('median_seconds_per_ckpt'),4)}\n"]
    pa = a3.get("prereg_threshold_audit") or {}
    if pa:
        L += ["### The pre-registered thresholds, measured on REAL trained weights\n",
              f"- BSA_w8 > 0.35 flag: FPR on the honest panel = **{f(pa.get('BSA_flag_0.35_FPR_on_real_honest_panel'))}**, "
              f"TPR on the edited arm = {f(pa.get('BSA_flag_0.35_TPR_on_edited'))} "
              f"(honest mean BSA_w8 = {f(pa.get('honest_BSA_w8_mean'))})",
              f"- BOTGAP_min < 0.1 flag: FPR = **{f(pa.get('BOTGAP_0.1_FPR_on_real_honest_panel'))}**, "
              f"TPR = {f(pa.get('BOTGAP_0.1_TPR_on_edited'))}",
              f"- {pa.get('note','')}\n"]
    sv = a3.get("structural_validity_of_the_bottom_read") or {}
    if sv:
        L += ["\n### The structural precondition of a parent-free bottom read\n",
              f"- sites with `d_in > d_out` (valid): **{sv.get('n_valid_d_in_gt_d_out')}**; "
              f"invalid: **{sv.get('n_invalid')}**",
              f"- honest BOTGAP_min on VALID sites: {sv.get('honest_BOTGAP_min_on_VALID_sites')}",
              f"- honest BOTGAP_min on INVALID sites: "
              f"{sv.get('honest_BOTGAP_min_on_INVALID_sites')}",
              f"- {sv.get('rule','')}\n"]
    dv = a3.get("part1_detection_VALID_SITES_ONLY") or {}
    if dv:
        L += ["#### Detection restricted to structurally valid sites\n",
              "| statistic | pooled AUROC | held-out-family TPR @5% FPR | Cohen's d | n |",
              "|---|---|---|---|---|"]
        for k, v in dv.items():
            L.append(f"| {k} | {f(v.get('auroc_pooled'))} | "
                     f"{f(v.get('heldout_family_TPR_at_5pct_FPR'))} | {f(v.get('cohens_d'))} | "
                     f"{v.get('n','?')} |")
    det = a3.get("part1_detection") or {}
    if det:
        L += ["### Detection, edited vs honest, threshold re-derived with each family held out\n",
              "| statistic | pooled AUROC | held-out-family TPR @5% FPR | realised FPR | Cohen's d | n |",
              "|---|---|---|---|---|---|"]
        for k, v in det.items():
            L.append(f"| {k} | {f(v.get('auroc_pooled'))} | "
                     f"{f(v.get('heldout_family_TPR_at_5pct_FPR'))} | "
                     f"{f(v.get('heldout_family_realised_FPR'))} | {f(v.get('cohens_d'))} | "
                     f"{v.get('n','?')} |")
    cen = j("card_census.json")
    if cen:
        L += ["\n### Recipe-coverage census over every model card in the panel\n",
              f"- cards read: **{cen.get('n_cards')}** (all {cen.get('n_with_card_text')} had text)",
              f"- scope stated: {json.dumps(cen.get('scope_class_pct'))}",
              f"- cards naming a tool: **{cen.get('n_with_a_named_tool')}**",
              f"- cards stating a NUMERIC ablation strength: "
              f"**{cen.get('n_with_a_stated_strength')}**",
              f"- prior census for comparison (n=37): "
              f"{json.dumps(cen.get('prior_census_for_comparison'))}\n"]
    cf = a3.get("part1_stated_vs_recovered_confusion") or {}
    if cf:
        L += ["\n### Stated recipe (model card) x recovered recipe (weights)\n",
              "Where the card and the weights disagree, **the weights are the measurement and the "
              "card is the claim.**\n", "```", json.dumps(cf, indent=1), "```"]
    lin = j("lineage_qwen3_4b.json")
    if lin.get("rows"):
        L += ["\n### The request's step-1 lineage, read parent-free (identical architecture)\n",
              "| member | kappa_hat | BOTGAP_min | BSA_w8 | XLC | cross-family cosine |",
              "|---|---|---|---|---|---|"]
        for r0 in lin["rows"]:
            d0 = r0.get("down_proj") or {}
            L.append(f"| {r0['role']} | {f(d0.get('kappa_hat'))} | {f(d0.get('BOTGAP_min'))} | "
                     f"{f(d0.get('BSA_w8'))} | {f(d0.get('XLC'))} | "
                     f"{f(r0.get('cross_family_cosine'))} |")
        L += ["", "Read across: the realised-strength estimate barely moves and the cross-LAYER "
                  "cosine moves the wrong way, while the CROSS-FAMILY cosine - how far o_proj's and "
                  "down_proj's bottom directions agree at the same layer - separates the abliterated "
                  "member from both unedited siblings. Statistics are from `down_proj`, the site "
                  f"with `d_in > d_out` on every family. Members read: {lin.get('n_read')}/4"
                  + (f", missing {lin.get('missing')}" if lin.get("missing") else "") + ".\n"]
    L += ["\n## Part 2 — the graded test\n",
          f"- graded checkpoints: **{a3.get('n_graded_total','?')}** "
          f"(edited: **{a3.get('n_edited_graded','?')}**)"]
    prim = a3.get("PRIMARY_within_edited") or {}
    cps = a3.get("coordinate_prespecification") or {}
    if cps:
        L.append(f"- coordinates pre-specified: PRIMARY=`{cps.get('PRIMARY')}`, "
                 f"CO_PRIMARY=`{cps.get('CO_PRIMARY')}`; exploratory never drives the verdict")
    if isinstance(prim, dict) and "status" not in prim:
        L += ["\n| coordinate | rho (per checkpoint) | 95% CI | n | families | rho (per family) | achieved MDE |",
              "|---|---|---|---|---|---|---|"]
        for k, v in prim.items():
            if not isinstance(v, dict) or "per_checkpoint" not in v: continue
            pc = v["per_checkpoint"]; pf = v.get("per_family_mean") or {}
            ciq = (f"[{f(pc.get('ci_lo'))}, {f(pc.get('ci_hi'))}]"
                   if pc.get("ci_lo") is not None else "n/a")
            L.append(f"| {k} | {f(pc.get('rho'))} | {ciq} | {pc.get('n','?')} | "
                     f"{pc.get('n_clusters','?')} | {f(pf.get('rho'))} | "
                     f"{f(v.get('achieved_MDE_rho'))} |")
    else:
        L.append(f"- {prim.get('reason','the graded claim was not testable at the achieved n')}")
    bars = a3.get("bars") or {}
    if bars:
        L += ["\n### Bars\n", "```", json.dumps(
            {k: ({kk: vv for kk, vv in v.items() if kk not in ("preds", "abs_err")}
                 if isinstance(v, dict) else v) for k, v in bars.items()},
            indent=1, default=float)[:6000], "```"]
    L += ["\n## Part 3 — the external limb (published safety numbers)\n"]
    s1 = a4b.get("S1_sub4B_with_published_safety") or {}
    s2 = a4b.get("S2_open_weight_helm_subset") or {}
    ic = a4b.get("identical_weights_ceiling") or {}
    rc2 = a4b.get("resolution_counts") or {}
    L += [f"- HELM models: {rc2.get('n_models_total','?')}; resolved to a HF repo: "
          f"{rc2.get('n_resolved','?')}; closed-API by construction: "
          f"{rc2.get('n_closed_api_by_construction','?')}; unresolved: {rc2.get('n_unresolved','?')}",
          f"- feasible open-weight pool (<=14B, readable): **{s2.get('n_feasible_open_weight','?')}**",
          f"- **sub-4.5B checkpoints with ANY published safety number: "
          f"{s1.get('n','?')}** — {s1.get('ecosystem_finding','')}",
          f"- **identical-weights ceiling**: {ic.get('n_pairs','?')} same-weights pairs; the largest "
          f"wrapper-induced gap is **{f(ic.get('headline_max_share_of_across_model_variance'))}x** "
          f"the entire across-model variance ({json.dumps(ic.get('headline_ref'))}).",
          f"  {ic.get('interpretation','')}\n",
          f"- CAVEAT: {a4b.get('caveat','')}\n"]
    if a5:
        L += ["## Part 4 — mechanism, null and forgery\n"]
        fg = a5.get("forgery") or {}
        if fg and "rows" in fg:
            L += [f"- cheapest forgery that heals the detector: eps = "
                  f"**{f(fg.get('cheapest_healing_eps'))}**, "
                  f"{fg.get('labelled_examples_needed','?')} labelled examples, "
                  f"{fg.get('prompts_needed','?')} prompts, "
                  f"{f(fg.get('compute_seconds'))} s of compute",
                  f"- detector is forgeable: **{fg.get('detector_is_forgeable')}**",
                  f"- {fg.get('PREREGISTERED_PREDICTION','')}\n",
                  "| eps | BOTGAP_min | BSA_w8 | detector healed |", "|---|---|---|---|"]
            for r in fg["rows"]:
                L.append(f"| {f(r.get('eps'))} | {f(r.get('BOTGAP_min'))} | {f(r.get('BSA_w8'))} | "
                         f"{r.get('detector_healed')} |")
        an = (a5.get("anisotropy_matched_null") or {}).get("per_family") or {}
        if an:
            L += ["\n### Anisotropy-matched random-direction null (NOT isotropic)\n",
                  "| family | anisotropic null BSA | isotropic null BSA | observed edited | observed honest | p (edited vs aniso) |",
                  "|---|---|---|---|---|---|"]
            for k, v in an.items():
                L.append(f"| {k} | {f((v.get('anisotropic_BSA') or {}).get('mean'))} | "
                         f"{f((v.get('isotropic_BSA') or {}).get('mean'))} | "
                         f"{f(v.get('observed_edited_BSA_mean'))} | "
                         f"{f(v.get('observed_honest_BSA_mean'))} | "
                         f"{f(v.get('p_edited_vs_anisotropic_null'))} |")
        lp = a5.get("layer_and_component_profile") or {}
        if lp:
            L += ["\n### Which layers and components carry it\n", "```",
                  json.dumps(lp, indent=1, default=float)[:2500], "```"]
    # ---- what this means for the request that started the run --------------------------
    rc = (g1.get("real_constructed") or {})
    sv = a3.get("structural_validity_of_the_bottom_read") or {}
    pa = a3.get("prereg_threshold_audit") or {}
    ic = a4b.get("identical_weights_ceiling") or {}
    cen = j("card_census.json")
    L += ["\n---\n\n## What to do with a random HuggingFace checkpoint\n",
          "The request was for a cheap safety read on a single model with no parent and no "
          "reference. Here is what this artifact's measurements actually license.\n",
          "**1. Read `down_proj`, not `o_proj`.** A bottom-spectrum read needs `d_in > d_out` "
          "strictly. Every Qwen2/Qwen3/Llama `o_proj` on this panel is square and Gemma3-1B's is "
          "wider than tall, so on those sites the honest bottom edge is not bounded away from zero "
          f"and the flag fires on untouched weights. Valid sites here: "
          f"{sv.get('n_valid_d_in_gt_d_out','?')}, invalid: {sv.get('n_invalid','?')}.\n",
          "**2. Do not use a rank-deficiency flag as a strength meter.** Measured on a real "
          "checkpoint abliterated at KNOWN strength, the rank read is blind outside "
          f"|1-kappa| < {f(rc.get('predicted_rank_read_operating_range_abs1mk'))}: at kappa=0.3 and "
          "0.7 the recovered strength was indistinguishable from unedited, and only at kappa=1 did "
          "it recover (0.985). A rank flag answers 'was one direction fully projected out', not "
          "'how unsafe is this'.\n",
          "**3. The sharing statistics carry the grade, not the rank statistic.** Over the same "
          "known-kappa sweep, BSA moved 0.346 -> 0.555 -> 1.000 and XLC 0.202 -> 0.327 -> 1.000, "
          "while the rank read stayed flat until kappa=1.\n",
          f"**4. Calibrate the threshold on YOUR OWN honest panel.** The pre-registered BSA > 0.35 "
          f"flag has a measured false-positive rate of "
          f"{f(pa.get('BSA_flag_0.35_FPR_on_real_honest_panel'))} on real honest weights here "
          f"(honest mean BSA_w8 = {f(pa.get('honest_BSA_w8_mean'))}); it was derived from "
          "simulation, and real trained networks carry shared bottom directions of their own.\n",
          "**5. Use an anisotropy-matched null, never an isotropic one.** They differ by about 3x "
          "here, and the isotropic null would make almost anything look significant.\n",
          f"**6. Expect no published number to check yourself against.** Of "
          f"{cen.get('n_cards','?')} model cards in this panel, "
          f"{(cen.get('scope_class_pct') or {}).get('STATED_NOTHING','?')}% state nothing about the "
          f"recipe and {cen.get('n_with_a_stated_strength','?')} state a numeric ablation strength. "
          f"Of the models in a published safety table, "
          f"{(a4b.get('S1_sub4B_with_published_safety') or {}).get('n','?')} are sub-4.5B open "
          f"checkpoints with any published safety score at all.\n",
          f"**7. Know the ceiling.** Two HELM entries that are the SAME WEIGHTS with a different "
          f"safety wrapper differ in published score by up to "
          f"{f(ic.get('headline_max_share_of_across_model_variance'))}x the entire across-model "
          f"variance. Any weights-only readout scores such a pair identically, so that gap is a "
          f"ceiling on how much published safety variance weights alone can ever explain. Weight "
          f"identity within a pair is INFERRED from HELM's naming (a wrapper or a decoding setting "
          f"on the same served model), not verified by comparing checkpoints - the "
          f"reasoning-budget pairs, where a decoding setting cannot change weights at all, still "
          f"show mean |delta| 0.008-0.014.\n"]
    (WS / "RESULTS.md").write_text("\n".join(L) + "\n")
    print(f"RESULTS.md written ({len('\n'.join(L))} chars)")

if __name__ == "__main__":
    main()
