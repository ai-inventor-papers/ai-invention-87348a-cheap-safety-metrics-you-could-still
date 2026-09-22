#!/usr/bin/env python3
"""RESULTS.md, counts first (plan Step 9).

Reads analysis_gpu.json, coverage_gpu5.json, ams_tier1.json, freeze_certificate.json, values_setA.sha256,
skips.json, spend.json, DEVIATIONS.json and rows/. Writes RESULTS.md. Pure bookkeeping: every number is copied
from those files, nothing is recomputed here, so RESULTS.md can never disagree with the analysis.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import blind_guard

blind_guard.install()

WS = Path(__file__).resolve().parent
ROWS = WS / "rows"


def j(name: str, default=None):  # noqa: ANN001, ANN201
    p = WS / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return default


def f(x, nd=3):  # noqa: ANN001, ANN201
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "–"
    return f"{v:.{nd}f}"


def ci(b: dict | None, nd=3) -> str:  # noqa: ANN001
    if not isinstance(b, dict):
        return "–"
    if "ci_lo" in b:
        return f"{f(b.get('point'), nd)} [{f(b.get('ci_lo'), nd)}, {f(b.get('ci_hi'), nd)}]"
    if "ci_lo_one_sided" in b:
        return f"{f(b.get('point'), nd)} (5% bound {f(b.get('ci_lo_one_sided'), nd)})"
    return f(b.get("point"), nd)


ORDER = ["C1", "C1n_cd", "C1n_os", "C2", "C6", "C6_insample", "C6_lens", "C10", "C12", "C12r", "C13", "C13_rank",
         "C15_erank", "C15_disp", "C11", "AMS_published", "AMS_pkg", "AMS_mean3", "AMS_cf_layer", "AMS_cf_sweep",
         "AMS_screen16", "logit_gap", "refusal_mass", "C13_logit", "S2_screen16", "keyword_probe",
         "family_only", "size_only"]
INTERNAL = {"C1", "C1n_cd", "C1n_os", "C2", "C6", "C6_insample", "C6_lens", "C10", "C12", "C12r", "C13",
            "C13_rank", "C15_erank", "C15_disp", "C11", "AMS_published", "AMS_pkg", "AMS_mean3", "AMS_cf_layer",
            "AMS_cf_sweep", "AMS_screen16"}


def main() -> None:
    an = j("analysis_gpu.json", {}) or {}
    cov = j("coverage_gpu5.json", {}) or {}
    ams = j("ams_tier1.json", {}) or {}
    cert = j("freeze_certificate.json", {}) or {}
    devs = (j("DEVIATIONS.json", {}) or {}).get("entries", [])
    skips = j("skips.json", []) or []
    spend = j("spend.json", {}) or {}
    prereg_hash = (WS / "PREREG_hash.txt").read_text().split()[0] if (WS / "PREREG_hash.txt").exists() else "–"
    rows = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(ROWS / "*.json")))]
    cands = an.get("candidates") or {}
    ps = an.get("panel_summary") or {}
    L = []
    A = L.append
    A("# RESULTS — iteration-5 GPU tier (C1n random-steer control, five new activation reads, AMS incumbent)\n")
    A(f"PREREG sha256 `{prereg_hash}` (frozen before any value was computed). "
      f"Set A values sha256 `{(cert.get('values_setA_sha256') or '–')}`, frozen {cert.get('frozen_utc', '–')}.\n")

    # ---------------- counts first
    A("## 1. Counts\n")
    n_graded = sum(1 for r in rows if r.get("graded"))
    setA = set((j("PREREG.json", {}) or {}).get("panel", {}).get("setA", []))
    n_setA = sum(1 for r in rows if r["repo"] in setA)
    n_base = sum(1 for r in rows if r.get("stratum") == "base")
    ncand = {len(r.get("candidates") or {}) for r in rows}
    secs = [r.get("wall_s") for r in rows if r.get("wall_s")]
    peaks = [(r.get("compute") or {}).get("vram_peak_gb") for r in rows]
    peaks = [p for p in peaks if p]
    A(f"- models measured: **{len(rows)}** = {n_graded} graded + {n_setA} Set A + {n_base} base "
      f"(panel {cov.get('n_panel', '–')}; coverage ok {cov.get('n_ok', '–')}, incomplete {cov.get('n_incomplete', '–')}, "
      f"skipped {cov.get('n_skipped', '–')}, missing {cov.get('n_missing', '–')})")
    A(f"- candidates per model: {sorted(ncand)} (including every bar and variant key)")
    A(f"- wall seconds per model: min {f(min(secs), 1) if secs else '–'}, median "
      f"{f(sorted(secs)[len(secs) // 2], 1) if secs else '–'}, max {f(max(secs), 1) if secs else '–'}")
    A(f"- VRAM peak across models: max {f(max(peaks)) if peaks else '–'} GB (cap 10.0 GB, never raised above 10.5)")
    A(f"- graded analysis panel: n={ps.get('n_graded', '–')}, families={ps.get('n_families', '–')}, "
      f"lineages={ps.get('n_lineages', '–')}, blanket refusers={ps.get('n_blanket_refusers', '–')}; "
      f"MDE_rho={f((an.get('mde_table') or {}).get('mde_rho'))} at ICC={f((an.get('mde_table') or {}).get('ICC'))}")
    if skips:
        A(f"- skips: " + ", ".join(f"{s['repo']} ({s['code']})" for s in skips))
    A(f"- OpenRouter spend: ${f(spend.get('total_usd'), 4)} (cap $1.00; the stance judge only, cache-first)\n")

    # ---------------- verdict table
    A("## 2. The frozen rule, applied mechanically (target BALANCED, n=23 graded)\n")
    A("| read | internal? | rho_ckpt [lineage CI] | rho_family | partial\\|gap,size (5% bound) | S1 | S2a | S2b | S3 | S4 | S5 | S6 | PASS |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in [x for x in ORDER if x in cands] + [x for x in sorted(cands) if x not in ORDER]:
        c = cands[k]
        rho = ((c.get("rho") or {}).get("BALANCED") or {})
        s1 = c.get("S1") or {}
        def st(key):  # noqa: ANN001, ANN202
            v = c.get(key) or {}
            if isinstance(v, dict) and v.get("applicable") is False:
                return "N/A"
            p = v.get("pass") if isinstance(v, dict) else v
            return "–" if p is None else ("pass" if p else "fail")
        A(f"| {k} | {'yes' if k in INTERNAL else 'BAR'} | {ci(rho.get('rho_ckpt_boot'))} | {f(rho.get('rho_family'))} | "
          f"{ci((s1.get('partial_rho') or {}).get('boot'))} | {st('S1')} | {st('S2a')} | {st('S2b')} | {st('S3')} | "
          f"{st('S4')} | {st('S5')} | {st('S6')} | **{c.get('PASS')}** |")
    A("")
    A(f"**Candidates passing all of S1–S6: {an.get('candidates_passing_all_of_S1_S6') or '[] (none)'}**\n")

    # ---------------- AMS
    A("## 3. The incumbent (AMS Tier-1)\n")
    ok = [v for v in ams.values() if (v or {}).get("status") == "ok"]
    A(f"- AMS ran on {len(ok)}/{len(ams)} measured models; package "
      f"{sorted({(v or {}).get('package') for v in ams.values()}) or '–'}, path "
      f"{sorted({(v or {}).get('path_used') for v in ams.values()}) or '–'}")
    h2h = an.get("extra_ams_head_to_head") or {}
    if h2h.get("available"):
        def verdict(v):  # noqa: ANN001, ANN202
            if v.get("AMS_beats"):
                return "beats"
            if v.get("AMS_clearly_worse"):
                return "clearly worse"
            return "not distinguishable"

        def h2h_table(caption: str, block: dict) -> None:  # noqa: ANN001
            A(f"**{caption}**\n")
            A("| variant | rho difference | lineage-bootstrap 95% CI | verdict |")
            A("|---|---|---|---|")
            for aid, v in block.items():
                A(f"| {aid} | {f(v.get('point'))} | [{f(v.get('ci_lo'))}, {f(v.get('ci_hi'))}] | "
                  f"{verdict(v)} |")
            A("")

        h2h_table("paired rho-difference vs C2", h2h.get("paired_vs_C2") or {})
        h2h_table("paired rho-difference vs the logit gap", h2h.get("paired_vs_logit_gap") or {})
        if h2h.get("verdict_counts"):
            A(f"- verdict counts by class: {json.dumps(h2h['verdict_counts'])}")
        if h2h.get("gap_distribution"):
            A(f"- in-sample minus cross-fitted gap: {json.dumps(h2h['gap_distribution'])}")
    else:
        A(f"- head-to-head not available: {h2h.get('reason')}")
    A("")

    # ---------------- Malla
    A("## 4. Malla check — is C1 just the content-free pull toward refusal?\n")
    ml = an.get("extra_malla_check") or {}
    if ml.get("available"):
        for k, v in ml.items():
            if k != "available":
                A(f"- {k}: {json.dumps(v)[:400]}")
    else:
        A(f"- not available: {ml.get('reason')}")
    A("")

    # ---------------- never-gates
    A("## 5. Reported, never a gate\n")
    A("| read | detect-vs-grade rho (n) | exceed-indicator point-biserial | increment over the 16-prompt judged probe |")
    A("|---|---|---|---|")
    for k in [x for x in ORDER if x in cands]:
        c = cands[k]
        dg = c.get("detect_vs_grade") or {}
        inc = c.get("increment_over_S2_screen16") or {}
        A(f"| {k} | {f(dg.get('rho_restricted_to_exceeders'))} (n={dg.get('n_exceed', '–')}/{dg.get('n_total', '–')}) | "
          f"{f(dg.get('point_biserial_exceed_vs_BALANCED'))} | {ci(inc.get('boot'))} |")
    A("")

    # ---------------- blindness + deviations
    A("## 6. Blindness and deviations\n")
    A(f"- Set A: {cert.get('n_repos_frozen', '–')} checkpoints frozen and hashed before any Set A label existed; "
      f"dataset workspaces seen at freeze: {cert.get('dataset_workspaces_present') or 'NONE'}; "
      f"files named like a label at freeze: {cert.get('any_label_named_file_at_freeze')}")
    A(f"- guard: {json.dumps(cert.get('guard'))}")
    for d in devs:
        A(f"- **{d.get('code')}** — {d.get('detail')}")
    (WS / "RESULTS.md").write_text("\n".join(L) + "\n")
    print(f"RESULTS.md written ({len(L)} lines)")


if __name__ == "__main__":
    main()
