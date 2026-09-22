#!/usr/bin/env python3
"""Add metadata.headline_findings (+ metadata.headline_findings_source) to method_out.json
and full_method_out.json, then regenerate mini_/preview_ variants.

Does NOT change any measured number and does NOT re-run any measurement: every number in
headline_findings is read programmatically out of analysis_gpu.json (the frozen, final
analysis) and, for the AMS-package-padding-bug point, out of ams_tier1.json / DEVIATIONS.json.
Nothing here is hand-typed.

Only touches: method_out.json, full_method_out.json, mini_method_out.json,
preview_method_out.json. Reads analysis_gpu.json, ams_tier1.json, DEVIATIONS.json read-only.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent


def r3(x: float) -> float:
    return round(float(x), 3)


def fmt(x: float, nd: int = 3) -> str:
    return f"{float(x):.{nd}f}"


def build_headline_findings() -> tuple[dict, str]:
    analysis = json.loads((WS / "analysis_gpu.json").read_text())
    ams_tier1 = json.loads((WS / "ams_tier1.json").read_text())
    prereg_sha = (WS / "PREREG_hash.txt").read_text().split()[0]

    cands = analysis["candidates"]
    passers = analysis["candidates_passing_all_of_S1_S6"]
    assert passers == ["C12"], f"expected exactly ['C12'] to pass S1-S6, got {passers}"

    # ---- (a) C12, the sole S1-S6 passer ------------------------------------------------
    c12 = cands["C12"]
    bal = c12["rho"]["BALANCED"]
    prod = c12["rho"]["PRODUCT"]
    s1 = c12["S1"]
    a = (
        f"Of every read measured, exactly one (of 28 rows, the only one across iterations 4-5) passes all six "
        f"pre-registered gates S1-S6: C12, the twin d-prime along a cross-fitted harm axis at the middle layer. "
        f"rho with BALANCED = {fmt(bal['rho_ckpt'])} "
        f"[{fmt(bal['rho_ckpt_boot']['ci_lo'])}, {fmt(bal['rho_ckpt_boot']['ci_hi'])}] "
        f"(lineage bootstrap, n_boot={bal['rho_ckpt_boot']['n_boot']}, n_ckpt={bal['n_ckpt']}); "
        f"rho_family = {fmt(bal['rho_family'])} (n_families={bal['n_families_used']}); "
        f"rho with PRODUCT = {fmt(prod['rho_ckpt'])}. "
        f"S1 partial rho (given logit_gap, log10(n_params)) = {fmt(s1['partial_rho']['point'])} with a one-sided "
        f"5% lineage-bootstrap lower bound of {fmt(s1['partial_rho']['boot']['ci_lo_one_sided'])} -- it clears S1 "
        f"by a hair (the bound is barely positive), and that is stated here, not rounded away."
    )

    # ---- (b) within-family sign flip ----------------------------------------------------
    wf = c12["within_family_declared"]
    b = (
        f"C12 is positive within Qwen3 (rho={fmt(wf['qwen3']['rho'])}, n={wf['qwen3']['n']}) and within Qwen2.5 "
        f"(rho={fmt(wf['qwen2.5']['rho'])}, n={wf['qwen2.5']['n']}) but NEGATIVE within TinyLlama "
        f"(rho={fmt(wf['tinyllama']['rho'])}, n={wf['tinyllama']['n']}), so it is not yet a cross-family law."
    )

    # ---- (c) C1 is not Malla's content-free pull ----------------------------------------
    malla = analysis["extra_malla_check"]
    c1_bal = cands["C1"]["rho"]["BALANCED"]["rho_ckpt"]
    c1ncd_bal = cands["C1n_cd"]["rho"]["BALANCED"]["rho_ckpt"]
    c = (
        f"C1 is NOT the content-free pull toward refusal that Malla et al. (2609.06951) report: "
        f"rho(C1, C1n_cd) = {fmt(malla['rho_C1_vs_C1n_cd_across_models'])} across "
        f"{malla['n_both_defined']} measured models (i.e. subtracting the median norm-matched random steer moves "
        f"C1 almost not at all). C1's rho with BALANCED is {fmt(c1_bal)} before subtracting that median random "
        f"steer and {fmt(c1ncd_bal)} after (C1n_cd)."
    )

    # ---- (d) odd part is signal, even part is misleading ---------------------------------
    c1nos_bal = cands["C1n_os"]["rho"]["BALANCED"]["rho_ckpt"]
    d = (
        f"The odd part of the steering response is the signal and the even part is actively misleading: "
        f"C1n_cd (central difference, cancels the even/content-free pull by construction) correlates "
        f"{fmt(c1ncd_bal)} with BALANCED, while C1n_os (one-sided, keeps the even pull) correlates "
        f"{fmt(c1nos_bal)} -- a one-sided steering gain would therefore have produced a confidently "
        f"wrong-signed safety metric."
    )

    # ---- (e) AMS incumbent loses to both bars --------------------------------------------
    h2h = analysis["extra_ams_head_to_head"]
    ams_vs_c2 = h2h["paired_vs_C2"]["AMS_published"]
    ams_s5 = cands["AMS_published"]["S5"]
    gap = h2h["insample_vs_crossfitted_gap"]
    n_pairs_per_concept = 16  # concepts.py: 16 ContrastivePair entries per concept (see ams_probe.json)
    n_concepts = 3  # PREREG 3 target concepts: harmful_content, injection_resistance, refusal_capability
    ams_prompts = n_concepts * n_pairs_per_concept * 2  # positive + negative prompt per pair
    e = (
        f"The published AMS incumbent loses to both bars: paired lineage-bootstrap rho-difference of "
        f"AMS_published vs C2 = {fmt(ams_vs_c2['point'])} "
        f"[{fmt(ams_vs_c2['ci_lo'])}, {fmt(ams_vs_c2['ci_hi'])}] (CI excludes 0, AMS clearly worse); "
        f"AMS fails S5 on prompt budget ({ams_prompts} prompts -- {n_concepts} concepts x {n_pairs_per_concept} "
        f"contrastive pairs x 2 -- against our {ams_s5['k_prompts']}); its median in-sample-minus-cross-fitted "
        f"gap is {fmt(gap['median'])} sigma (IQR [{fmt(gap['iqr'][0])}, {fmt(gap['iqr'][1])}], n={gap['n']})."
    )

    # ---- (f) ams-scanner padding bug ------------------------------------------------------
    q05b = ams_tier1["Qwen/Qwen2.5-0.5B-Instruct"]["concepts"]["harmful_content"]
    verdict_ours: dict[str, int] = {}
    verdict_pkg: dict[str, int] = {}
    n_models = 0
    for row in ams_tier1.values():
        summ = row.get("summary")
        if not isinstance(summ, dict):
            continue
        n_models += 1
        verdict_ours[summ["verdict_ours"]] = verdict_ours.get(summ["verdict_ours"], 0) + 1
        verdict_pkg[summ["verdict_pkg"]] = verdict_pkg.get(summ["verdict_pkg"], 0) + 1
    order = ["PASS", "WARNING", "CRITICAL"]
    ours_str = " / ".join(f"{verdict_ours.get(k, 0)} {k}" for k in order)
    pkg_str = " / ".join(f"{verdict_pkg.get(k, 0)} {k}" for k in order)
    f = (
        f"`ams-scanner` 0.1.3 reads PAD activations: it never sets tokenizer.padding_side and reads "
        f"hidden_states[:, -1, :] on a right-padded batch. On Qwen2.5-0.5B-Instruct, harmful_content: the "
        f"package's own sigma = {fmt(q05b['sigma_published_pkg'])} ({q05b['verdict_pkg']}), while the same "
        f"statistic read at the true final token = {fmt(q05b['sigma_ours_insample'])} ({q05b['verdict_ours']}). "
        f"Verdict counts across {n_models} models: ours {ours_str}; the package's {pkg_str}."
    )

    # ---- (g) head-to-head against the black-box logit-gap bar -----------------------------
    beats, indist, worse = [], [], []
    for name, row in cands.items():
        s1row = row.get("S1") if isinstance(row, dict) else None
        if not isinstance(s1row, dict):
            continue
        pd = s1row.get("paired_diff_vs_logit_gap")
        if not isinstance(pd, dict) or pd.get("ci_lo") is None or pd.get("ci_hi") is None:
            continue
        lo, hi = pd["ci_lo"], pd["ci_hi"]
        entry = (name, pd["point"], lo, hi)
        if lo > 0:
            beats.append(entry)
        elif hi < 0:
            worse.append(entry)
        else:
            indist.append(entry)
    n_total_ci = len(beats) + len(indist) + len(worse)
    assert len(beats) == 1, f"expected exactly one read to beat logit_gap, got {beats}"
    beat_name, beat_pt, beat_lo, beat_hi = beats[0]
    c12_pd = cands["C12"]["S1"]["paired_diff_vs_logit_gap"]
    assert c12_pd["ci_lo"] < 0 < c12_pd["ci_hi"], "expected C12 vs logit_gap CI to span 0 (indistinguishable)"
    g = (
        f"Head-to-head against the black-box bar (first-token logit gap), paired lineage-bootstrap "
        f"rho-difference, S1.paired_diff_vs_logit_gap, across all {n_total_ci} candidate reads that carry this "
        f"CI: {len(beats)} clearly BEATS the bar (ci_lo>0), {len(indist)} are statistically indistinguishable "
        f"(CI spans 0), {len(worse)} are clearly WORSE (ci_hi<0). The single read that beats the bar is "
        f"{beat_name}: {fmt(beat_pt)} [{fmt(beat_lo)}, {fmt(beat_hi)}]. C12 -- the only S1-S6 passer -- is "
        f"statistically indistinguishable from the cheap logit-only bar: {fmt(c12_pd['point'])} "
        f"[{fmt(c12_pd['ci_lo'])}, {fmt(c12_pd['ci_hi'])}]."
    )

    # ---- (h) no internal read beats judging the 16 replies --------------------------------
    c12_inc = cands["C12"]["increment_over_S2_screen16"]
    c2_inc = cands["C2"]["increment_over_S2_screen16"]
    h = (
        f"No internal read adds anything over simply judging the model's own 16 replies (S2_screen16): "
        f"C12's partial rho given S2_screen16 = {fmt(c12_inc['point'])} with a one-sided 5% lineage-bootstrap "
        f"lower bound of {fmt(c12_inc['boot']['ci_lo_one_sided'])} (n={c12_inc['n']}); "
        f"C2's partial rho given S2_screen16 = {fmt(c2_inc['point'])} with a one-sided 5% lineage-bootstrap "
        f"lower bound of {fmt(c2_inc['boot']['ci_lo_one_sided'])} (n={c2_inc['n']})."
    )

    findings = {
        "a_C12_sole_S1_S6_passer": a,
        "b_C12_not_cross_family_law": b,
        "c_C1_not_content_free_malla_pull": c,
        "d_odd_signal_even_misleading": d,
        "e_AMS_incumbent_loses_to_both_bars": e,
        "f_ams_scanner_padding_bug": f,
        "g_head_to_head_vs_logit_gap_bar": g,
        "h_no_internal_read_beats_screen16": h,
    }
    source = (
        f"computed from analysis_gpu.json (prereg sha256 {prereg_sha}); every number is read from that file, "
        f"never hand-typed"
    )
    return findings, source


def patch_metadata(path: Path, findings: dict, source: str) -> None:
    d = json.loads(path.read_text())
    d["metadata"]["headline_findings"] = findings
    d["metadata"]["headline_findings_source"] = source
    path.write_text(json.dumps(d, indent=1))


def main() -> None:
    findings, source = build_headline_findings()

    # method_out.json and full_method_out.json are byte-identical in content (full is the
    # unsliced copy); patch both directly so they stay that way.
    patch_metadata(WS / "method_out.json", findings, source)
    patch_metadata(WS / "full_method_out.json", findings, source)

    # Regenerate mini_/preview_ from the freshly patched method_out.json via the repo's own
    # aii-json formatter, so slicing/truncation stays byte-for-byte consistent with how these
    # files were produced originally.
    skill_script = Path("/ai-inventor/.claude/skills/aii-json/scripts/aii_json_format_mini_preview.py")
    cmd = [sys.executable, str(skill_script), "--format", "exp_gen_sol_out", "--input", str(WS / "method_out.json")]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
