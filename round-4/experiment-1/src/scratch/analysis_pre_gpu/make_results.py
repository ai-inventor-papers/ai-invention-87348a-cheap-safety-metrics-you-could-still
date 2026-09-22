#!/usr/bin/env python3
"""Compose RESULTS.md from candidates_live.json, analysis_tables.md, rosi_128tok.json and the bookkeeping files.

Every sentence that states a result is generated from the measured numbers (no hand-typed values), so the
text cannot drift from the JSON.  Nulls are written as 'not detectable at n=X (MDE=Y)', never as absence.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from pathlib import Path
from typing import Any

from loguru import logger

WS = Path(__file__).resolve().parent
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "make_results.log", rotation="30 MB", level="DEBUG")

INTERNAL = ["C1", "C2", "C3", "C7", "C8", "C11"]
ALL = ["C1", "C2", "C3", "C7", "C8", "C9", "C11", "C16", "logit_gap", "refusal_mass", "C1_oracle", "C2_oracle",
       "C16_oracle"]


def f(x: Any, nd: int = 3) -> str:
    if x is None:
        return "–"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int,)):
        return str(x)
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    return "–" if not math.isfinite(v) else f"{v:.{nd}f}"


IN_DIR = WS
OUT_DIR = WS


def find(name: str) -> Path | None:
    """Resolve `name` against --in-dir first, falling back to WS (the live run root) if absent there."""
    p = IN_DIR / name
    if p.exists():
        return p
    p = WS / name
    return p if p.exists() else None


def load(name: str) -> Any:
    p = find(name)
    return json.loads(p.read_text()) if p else None


def get(d: Any, *ks: str) -> Any:
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def rule(c: dict, s: str) -> tuple[bool | None, str]:
    r = c.get(s) or {}
    return r.get("pass"), str(r.get("reason", ""))


def main() -> None:
    global IN_DIR, OUT_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default=str(WS), help="dir to read candidates_live.json/analysis_tables.md/etc from (default WS)")
    ap.add_argument("--out-dir", default=str(WS), help="dir to write RESULTS.md into (default WS)")
    args = ap.parse_args()
    IN_DIR = Path(args.in_dir).resolve()
    OUT_DIR = Path(args.out_dir).resolve()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cl = load("candidates_live.json") or {}
    rosi = load("rosi_128tok.json")
    devs = load("DEVIATIONS.json") or []
    skips = load("skips.json") or []
    spend = load("spend.json") or {}
    prereg_hash_p = find("PREREG_hash.txt")
    prereg_hash = prereg_hash_p.read_text().split() if prereg_hash_p else ["–", "–"]
    rows_dir = IN_DIR / "rows" if (IN_DIR / "rows").exists() else WS / "rows"
    rows = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(rows_dir / "*.json")))]
    ps = cl.get("panel_summary", {})
    C = cl.get("candidates", {})
    n = ps.get("n_graded")
    mde = get(ps, "mde", "mde_rho")
    L: list[str] = []
    L.append("# RESULTS: live causal-gain safety screen (iteration 4, CPU fallback `LIVE_TIER_NO_CUDA`)\n")
    L.append(f"PREREG sha256 `{prereg_hash[0]}` (hashed {prereg_hash[1]}), fixed before any panel model was scored. "
             f"Measured checkpoints: **{len(rows)}** rows. Graded chat set G: **n = {n}**, "
             f"**{ps.get('n_families')} families**, **{ps.get('n_lineages')} lineages**, "
             f"**{ps.get('n_blanket_refusers')} blanket refusers**. Lineage ICC of the BALANCED target = "
             f"{f(get(ps, 'icc', 'icc'))}; one-sided minimum detectable Spearman at this n and ICC: "
             f"**MDE_rho = {f(mde)}**. OpenRouter spend: ${f(spend.get('total_usd'), 4)}.\n")
    prereg_j = load("PREREG.json") or {}
    sub = set(prereg_j.get("cpu_subpanel") or [])
    base_rows = [r["repo"] for r in rows if r.get("stratum") == "base"]
    lite = [r["repo"] for r in rows if any(fl.get("code") == "ANCHOR_LITE" for fl in r.get("flags", []))
            and r["repo"] not in base_rows]
    full_rows = [r["repo"] for r in rows if r["repo"] not in lite and r["repo"] not in base_rows]
    full_sub = [x for x in full_rows if x in sub]
    full_out = [x for x in full_rows if x not in sub]
    graded_repos = {r["repo"] for r in rows if r.get("graded")}
    full_out_graded = [x for x in full_out if x in graded_repos]
    ungraded_rows = [r["repo"] for r in rows if r["repo"] not in graded_repos and r.get("stratum") != "base"]
    n_offset_models = get(cl, "constant_offset_control", "n_models")
    L.append("**Scope honesty.** There was no CUDA (`LIVE_TIER_NO_CUDA`); every checkpoint was measured CPU-only in bf16 "
             "(the cpuset size changed across sessions -- see `HARDWARE_SESSION3` -- so no single thread count is quoted here). "
             f"{len(full_sub)} checkpoints of the pre-registered CPU sub-panel (every model <= 2B parameters) and "
             f"{len(full_out)} checkpoint(s) outside it (2-4B; {len(full_out_graded)} of them graded: "
             f"{', '.join(full_out_graded) or 'none'}) got the full candidate set: "
             f"poles, k=8, direction nulls, oracle rows and, on {f(n_offset_models)} model(s) (`constant_offset_control.n_models`), "
             "the constant-offset control. "
             + (f"{len(lite)} chat checkpoint(s) were measured in `ANCHOR_LITE` mode ({', '.join(lite)}): plain-condition "
                "candidates, oracle rows C1/C2 and the logit bars, but no nulls, k8, pole values or offset control. They enter "
                "the correlations but not S2(b) or the S3 pole checks. " if lite else
                "No chat checkpoint was measured in `ANCHOR_LITE` mode. ")
             + (f"The base-stratum row(s) {', '.join(base_rows)} (ANCHOR_LITE, plain `User:/Assistant:` renderer) are reported "
                "in the step-1 anchor table but excluded from every correlation. " if base_rows else "")
             + (f"{len(ungraded_rows)} checkpoint(s) were measured but are **ungraded (iteration-5 join)**: "
                f"{', '.join(ungraded_rows)}. They carry no BALANCED/PRODUCT label, so they are excluded from every "
                "correlation, poles table and S1-S6 rule, but their raw candidate values are in `candidate_values_live.json`. "
                if ungraded_rows else "")
             + "Every panel repo without a row is in `skips.json` with a reason code. "
             "S5 (under 120 s per 4B model on a GPU) is not measurable. "
             "Every row was measured with the v2 code, after an independent review (`CODE_FIXES_POST_REVIEW_V2`). See `DEVIATIONS.json` ("
             + ", ".join(sorted({d.get('code', '?') for d in devs})) + ").\n")
    # ---------------- verdict table
    L.append("## 1. Selection rules S1-S6 (BALANCED target, mechanical)\n")
    L.append("| candidate | role | n | undef | rho_ckpt [95% lineage CI] | rho_family | partial rho (one-sided 5% bound) | S1 | S2 | S3 | S4 | S6 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    passes = {}
    for k in ALL:
        c = C.get(k)
        if not c:
            continue
        rb = get(c, "rho", "BALANCED") or {}
        bt = rb.get("rho_ckpt_boot") or {}
        par = c.get("partial_rho") or {}
        pb = par.get("boot") or {}
        s = {r: rule(c, r)[0] for r in ("S1", "S2", "S3", "S4", "S6")}
        passes[k] = s
        L.append(f"| {k} | {c.get('role')} | {c.get('n')} | {c.get('n_undefined')} | {f(rb.get('rho_ckpt'))} "
                 f"[{f(bt.get('ci_lo'))}, {f(bt.get('ci_hi'))}] | {f(rb.get('rho_family'))} (n_fam={rb.get('n_families_used')}) | "
                 f"{f(par.get('point'))} ({f(pb.get('ci_lo_one_sided'))}) | "
                 + " | ".join(f(s[r]) for r in ("S1", "S2", "S3", "S4", "S6")) + " |")
    L.append("")
    # ---------------- verdict sentences generated from the numbers
    L.append("## 2. Verdicts (generated from the table)\n")
    shipped = [k for k in INTERNAL if all(passes.get(k, {}).get(r) for r in ("S1", "S2", "S3", "S4", "S6"))]
    s1_only = [k for k in INTERNAL if passes.get(k, {}).get("S1")]
    if n is not None and n < 12:
        L.append(f"- Graded n = {n} < 12: every verdict reads **not detectable at this n** (MDE_rho = {f(mde)}).")
    if shipped:
        L.append(f"- Internal candidates passing ALL of S1, S2, S3, S4, S6: **{', '.join(shipped)}**. These are screen "
                 "CANDIDATES only; the sealed confirmation has not run.")
    else:
        L.append("- **No internal candidate passes all of S1, S2, S3, S4 and S6.** The leading conjecture (a causal "
                 "gain beats the first-token logit gap across families) is **not supported by this screen** at "
                 f"n = {n} (MDE_rho = {f(mde)}). This is a negative screen result on a CPU sub-panel, not a proof of "
                 "absence.")
    if s1_only and not shipped:
        L.append(f"- Passing S1 (partial rho > 0 given logit gap and size) but failing another rule: {', '.join(s1_only)}.")
    for k in INTERNAL + ["C9", "C16"]:
        c = C.get(k) or {}
        fails = [r for r in ("S1", "S2", "S3", "S4", "S6") if passes.get(k, {}).get(r) is False]
        if fails:
            reasons = "; ".join(f"{r}: {rule(c, r)[1][:160]}" for r in fails)
            L.append(f"- {k} fails {', '.join(fails)}: {reasons}")
    wf = [k for k in ALL if "one family only" in json.dumps((C.get(k) or {}).get("within_family", {})).lower()]
    for k in wf:
        L.append(f"- {k}: **works within one family only: NEGATIVE**.")
    und = [k for k in ALL if (C.get(k) or {}).get("flag_undefined_majority")]
    for k in und:
        L.append(f"- {k} is **undefined at this item budget** (undefined on more than half the panel).")
    L.append("")
    # ---------------- product target
    L.append("## 3. Same rules under the PRODUCT target (P2 = harm refusal x benign compliance; blanket refuser = 0)\n")
    L.append("| candidate | rho_ckpt [CI] | rho_family | partial rho (bound) |")
    L.append("|---|---|---|---|")
    for k in ALL:
        c = C.get(k)
        if not c:
            continue
        rp = get(c, "rho", "PRODUCT") or {}
        bt = rp.get("rho_ckpt_boot") or {}
        L.append(f"| {k} | {f(rp.get('rho_ckpt'))} [{f(bt.get('ci_lo'))}, {f(bt.get('ci_hi'))}] | {f(rp.get('rho_family'))} | "
                 f"(partial rho is computed on the primary BALANCED target only) |")
    L.append("")
    # ---------------- poles table (per plan sec 4: candidate value vs its two wrapped poles vs CensorTune refusers)
    poles = cl.get("poles") or {}
    if poles:
        L.append("## 3b. Poles: honest-instruct plain vs wrapped poles vs CensorTune blanket refusers\n")
        L.append("| candidate | repo | role | plain | pole_refuse | pole_comply |")
        L.append("|---|---|---|---|---|---|")
        for k in ALL:
            for row in poles.get(k, []):
                L.append(f"| {k} | {row.get('repo')} | {row.get('role')} | {f(row.get('plain'))} | "
                         f"{f(row.get('pole_refuse'))} | {f(row.get('pole_comply'))} |"
                         + (f" (vs {row['vs_instruct']})" if row.get("vs_instruct") else ""))
        L.append("")
    # ---------------- oracle-row comparison + readout validity (per plan sec 4)
    oc = cl.get("oracle_comparison") or {}
    if oc:
        L.append("## 3c. Oracle-row comparison and readout validity\n")
        L.append("For C1/C2/C16, `rho_readout_vs_oracle` is the Spearman correlation between the internal-readout "
                 "value and the judge-graded (64-token generation) oracle value on the same checkpoints -- how much "
                 "the cheap readout agrees with what the model actually says.\n")
        L.append("| candidate | n (both defined) | rho(readout, oracle) |")
        L.append("|---|---|---|")
        for k in ("C1", "C2", "C16"):
            row = oc.get(k) or {}
            if row:
                L.append(f"| {k} | {row.get('n_both_defined')} | {f(row.get('rho_readout_vs_oracle'))} |")
        rv = oc.get("readout_validity_auroc") or {}
        if rv:
            L.append(f"\n**Readout validity AUROC** (harmful-vs-twin separation of the readout used for the oracle "
                     f"item split), across {rv.get('n')} checkpoints: median {f(rv.get('median'))}, "
                     f"min {f(rv.get('min'))}.\n")
    # ---------------- analysis tables verbatim
    at = find("analysis_tables.md")
    if at:
        L.append("## 4. Full analysis tables (analyze_live.py)\n")
        L.append(at.read_text())
    # ---------------- C9 AtP reliability switch
    cj = json.dumps(cl)
    if "ATP_UNRELIABLE" in cj:
        atp = cl.get("C9_atp_reliability") or cl.get("atp_reliability") or get(cl, "candidates", "C9", "atp_reliability") or {}
        L.append("\n**C9 AtP reliability rule.** " + (json.dumps(atp)[:600] if atp else "ATP_UNRELIABLE appears in candidates_live.json; see C9 there.") + "\n")
    # ---------------- post-hoc diagnostics (exploratory)
    ph = find("posthoc_live.md")
    if ph:
        L.append("\n## 4b. Post-hoc diagnostics (EXPLORATORY, not pre-registered, never used by S1-S6)\n")
        L.append(ph.read_text().split("\n", 1)[1])
    # ---------------- ROSI
    L.append("\n## 5. ROSI side arm: 128-token regeneration of the iteration-2 reversal\n")
    if rosi:
        pc = rosi.get("per_cell", {})
        L.append("Qwen2.5-0.5B-Instruct, greedy 128 new tokens, gemini-2.5-flash stance judge. The item set is the one iteration 2 "
                 "actually generated: " + str(get(rosi, "provenance", "item_set") or "64 harmful + 32 benign twins")[:300] + ".\n")
        L.append("| cell | harm refusal | twin false refusal | D2_balanced | D2_product | D2 (iter-2 formula) |")
        L.append("|---|---|---|---|---|---|")
        for cell, v in pc.items():
            L.append(f"| {cell} | {f(v.get('harm_refusal_rate'))} | {f(v.get('twin_false_refusal_rate'))} | "
                     f"{f(v.get('D2_balanced'))} | {f(v.get('D2_product'))} | {f(v.get('D2_iter2_own_definition'))} |")
        L.append("")
        L.append("| contrast | target | dD2 | 95% paired bootstrap CI |")
        L.append("|---|---|---|---|")
        for ck, cv in (rosi.get("dD2") or {}).items():
            for tg in ("balanced", "product", "iter2"):
                if isinstance(cv.get(tg), dict):
                    ci = cv[tg].get("ci95") or [None, None]
                    L.append(f"| {ck} | {tg} | {f(cv[tg].get('point'))} | [{f(ci[0])}, {f(ci[1])}] |")
        xm = rosi.get("x4_minus_hidden") or {}
        for tg in ("balanced", "product", "iter2"):
            if isinstance(xm.get(tg), dict):
                ci = xm[tg].get("ci95") or [None, None]
                L.append(f"| x4 minus hidden (generic-perturbation share removed) | {tg} | {f(xm[tg].get('point'))} | "
                         f"[{f(ci[0])}, {f(ci[1])}] |")
        L.append("")
        ref_x4 = rosi.get("reference_iter2_20tok_x4_dD2") or {}
        ref_hid = rosi.get("reference_iter2_20tok_hidden_x4_dD2") or {}
        ref_ci = ref_x4.get("ci95") or [None, None]
        L.append("Pre-registered verdict sentences (balanced target): " +
                 "; ".join(f"**{v}**" for v in (rosi.get("verdicts") or [])) +
                 f". Iteration-2 reference at 20 tokens: x4 dD2 {f(ref_x4.get('point'))} "
                 f"[{f(ref_ci[0])}, {f(ref_ci[1])}], hidden {f(ref_hid.get('point'))}.")
        pr = get(rosi, "dD2", "F2b_rosi_x4_vs_x0", "product") or {}
        ci = pr.get("ci95") or [None, None]
        if ci[1] is not None and ci[1] < 0:
            L.append(f"Under the PRODUCT target the x4 reversal remains significant at 128 tokens (dD2 = {f(pr.get('point'))} "
                     f"[{f(ci[0])}, {f(ci[1])}]). The false-refusal cost survives the longer generation, and the balanced "
                     "target dilutes it by averaging with the harm-refusal gain.")
        kap = rosi.get("kappa_primary_vs_secondary_25pct_sample")
        L.append(f"Secondary judge (gpt-5-mini, seeded 25%): {json.dumps(kap)[:200]}.")
        L.append("\nLength vs judge agreement (Cohen kappa per cell):\n")
        L.append("| cell | iter-2 20tok vs new 128tok | new 20tok vs new 128tok | iter-2 20tok vs new 20tok |")
        L.append("|---|---|---|---|")
        for cell, v in (rosi.get("agreement_table") or {}).items():
            L.append(f"| {cell} | {f(get(v, 'iter2_20tok_vs_new_128tok', 'kappa'))} | "
                     f"{f(get(v, 'new_20tok_vs_new_128tok', 'kappa'))} | {f(get(v, 'iter2_20tok_vs_new_20tok', 'kappa'))} |")
        L.append("")
    else:
        L.append("rosi_128tok.json not present (arm not finished); see logs/rosi128.log.\n")
    # ---------------- skips (a repo that already has a row in rows/ is authoritative over a stale skip entry)
    row_repos = {r["repo"] for r in rows}
    live_skips = [s_ for s_ in skips if s_.get("repo") not in row_repos]
    stale_skips = [s_ for s_ in skips if s_.get("repo") in row_repos]
    L.append("## 6. Coverage: every panel repo is in rows/ or skips.json\n")
    L.append("| repo | code |")
    L.append("|---|---|")
    for s_ in live_skips:
        L.append(f"| {s_['repo']} | {s_['code']} |")
    L.append("")
    if stale_skips:
        L.append(f"({len(stale_skips)} skip entr{'y' if len(stale_skips) == 1 else 'ies'} in `skips.json` "
                 f"({', '.join(sorted({s_['repo'] for s_ in stale_skips}))}) are superseded by a row in `rows/` "
                 "and are omitted above; 'has a row' is authoritative over a skip entry.)\n")
    # ---------------- analysis conventions (fixed by the session-3 audit of analyze_live.py, before the final run)
    L.append("## 7. Analysis conventions where the plan text left a choice\n")
    L.append("An independent audit of `analyze_live.py` (session 3) checked S1-S6, the MDE and the LOFO code against the plan. "
             "It fixed one defect: S3 on the oracle rows used to pass vacuously, because no oracle pole values exist. Those rows "
             "now read 'not assessable' and count as an S3 failure. The audit also checked every choice below against the "
             "plan wording. The choices were then fixed before the final analysis run:\n")
    L.append("- **S1 worst-value rule.** An undefined candidate value is replaced by the worst observed panel value under the "
             "declared orientation, for S1 and S3 only. The number of substitutions is reported (`partial_rho.n_worst_value_"
             "substituted`). S2 leaves undefined values out rather than worst-valuing them.")
    L.append("- **S2(a).** The one-sided checkpoint-label permutation p-value uses (1 + #{null >= observed}) / (1 + 2000), so "
             "it is never exactly 0.")
    L.append("- **S2(b).** The denominator is the graded chat models that have both a defined value and a direction-null p95. "
             "ANCHOR_LITE, base-stratum and ungraded rows are left out rather than counted as failures.")
    L.append("- **S3.** When a pole value is missing, it is worst-valued against the other pole values of the same kind. It is "
             "never compared with plain values. A rule with no pole value anywhere on the panel is 'not assessable', which "
             "counts as a fail.")
    L.append("- **S6.** Following the plan, every LOFO row, including the size-only row, is an out-of-fold 1-D map fit on the "
             "other families. For the family-only row, the held-out family gets the training grand mean. Under that "
             "definition the family-only Spearman is negative by construction: high-target families always get a lower "
             "training mean. So in practice S6 comes down to beating the out-of-fold log-size map.")
    L.append("- **Within-family NEGATIVE label.** 'works within one family only: NEGATIVE' is printed when exactly one family "
             "(of those with at least 3 graded checkpoints) has a within-family permutation p < 0.05 while S1 fails.")
    L.append("- **Oracle rows** (C1_oracle, C2_oracle, C16_oracle) use the model's own judged SCREEN16 refusals. SCREEN16 is "
             "not in the outcome item set, so this does not leak into the target. They have no pole values, so their S3 is "
             "not assessable.\n")
    (OUT_DIR / "RESULTS.md").write_text("\n".join(L))
    logger.info(f"RESULTS.md written ({len(L)} lines) to {OUT_DIR / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
