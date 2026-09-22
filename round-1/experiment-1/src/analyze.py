#!/usr/bin/env python3
"""Turn results/ into RESULTS.md -- the human-readable digest of the race."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parent / "results"
OUT = Path(__file__).resolve().parent / "RESULTS.md"


def _j(name: str, default=None):
    p = R / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return default


def _f(v, nd: int = 3) -> str:
    try:
        x = float(v)
        return "n/a" if not np.isfinite(x) else f"{x:.{nd}f}"
    except (TypeError, ValueError):
        return "n/a"


def correlation_panel(pc: dict, gt: dict, rows: list[dict], top_k: int = 10) -> list[str]:
    """Step 5: correlation-test the best metrics against the ground-truth numbers.

    Reported at BOTH aggregation units with the resampling unit named, plus the
    within-family breakdown -- a metric that only works inside one architecture
    family is a NEGATIVE RESULT and is said so in those words.
    """
    from scipy import stats
    L: list[str] = []
    A = L.append
    per = gt.get("per_checkpoint", {})
    slugs = [s for s in pc if s in per and pc[s]["class"] in ("safety", "instruct", "abliterated")]
    if len(slugs) < 6:
        return ["## Step 5 — correlation against ground truth\n\nToo few scored checkpoints.\n"]
    lin = np.array([pc[s]["lineage"] for s in slugs])
    fam = np.array([l.split("::")[0] for l in lin])
    targets = {
        "graded harmful compliance": np.array(
            [per[s]["harmful_compliance_strongreject"] for s in slugs], float),
        "XSTest false refusal": np.array(
            [per[s]["xstest_false_refusal_rate"] for s in slugs], float),
    }
    ranked = [r for r in rows if np.isfinite(r.get("held_out_balacc_3way", np.nan))][:top_k]

    def _boot_ci(x, y, groups, n=2000, seed=7):
        rng = np.random.default_rng(seed)
        gs = np.unique(groups)
        out = []
        for _ in range(n):
            pick = rng.choice(gs, size=len(gs), replace=True)
            idx = np.concatenate([np.where(groups == g)[0] for g in pick])
            if len(np.unique(y[idx])) < 3 or len(np.unique(x[idx])) < 3:
                continue
            out.append(stats.spearmanr(x[idx], y[idx]).statistic)
        if not out:
            return float("nan"), float("nan")
        return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))

    A("## Step 5 — the best metrics correlated against the ground-truth numbers\n")
    A("**Resampling unit: the LINEAGE** (parent x tuning run). Confidence intervals are "
      "lineage-clustered bootstraps, 2000 resamples of whole lineages. Both aggregation "
      "units are reported because they answer different questions: per-checkpoint is what "
      "an auditor sees, per-lineage is what generalises.\n")
    for tname, tv in targets.items():
        ok = np.isfinite(tv)
        if ok.sum() < 6:
            A(f"### vs {tname}\n\nNot enough graded checkpoints.\n")
            continue
        A(f"### vs {tname}  (n = {int(ok.sum())} checkpoints / "
          f"{len(np.unique(lin[ok]))} lineages)\n")
        A("| metric | rho per-checkpoint | p | 95% CI (lineage-clustered) | rho per-lineage | worst within-family rho | verdict |")
        A("|---|---|---|---|---|---|---|")
        for r in ranked:
            mid = r["metric_id"]
            x = np.array([pc[s]["metrics"].get(mid, np.nan) for s in slugs], float)
            m = ok & np.isfinite(x)
            if m.sum() < 6 or len(np.unique(x[m])) < 3:
                A(f"| `{mid}` | n/a | n/a | n/a | n/a | n/a | undefined |")
                continue
            sr = stats.spearmanr(x[m], tv[m])
            lo, hi = _boot_ci(x[m], tv[m], lin[m])
            # per-lineage aggregation: mean within lineage, then correlate
            ul = np.unique(lin[m])
            xa = np.array([np.nanmean(x[m][lin[m] == l]) for l in ul])
            ta = np.array([np.nanmean(tv[m][lin[m] == l]) for l in ul])
            sl = (stats.spearmanr(xa, ta).statistic if len(ul) > 3 and len(np.unique(xa)) > 2
                  else float("nan"))
            wf = []
            for f in np.unique(fam[m]):
                fm = m & (fam == f)
                if fm.sum() >= 4 and len(np.unique(x[fm])) > 2:
                    wf.append(stats.spearmanr(x[fm], tv[fm]).statistic)
            worst = float(np.nanmin(wf)) if wf else float("nan")
            covers0 = (np.isfinite(lo) and np.isfinite(hi) and lo <= 0 <= hi)
            verdict = ("CI COVERS 0" if covers0 else
                       "WITHIN-FAMILY ONLY (negative result)"
                       if (np.isfinite(worst) and worst * sr.statistic <= 0) else "holds")
            A(f"| `{mid}` | {_f(sr.statistic)} | {_f(sr.pvalue)} | "
              f"[{_f(lo)}, {_f(hi)}] | {_f(sl)} | {_f(worst)} | {verdict} |")
        # P7.5: does the family label alone do as well?
        famcode = {f: i for i, f in enumerate(sorted(set(fam[ok])))}
        fx = np.array([famcode[f] for f in fam[ok]], float)
        fr = stats.spearmanr(fx, tv[ok]).statistic if len(famcode) > 2 else float("nan")
        A(f"\n**Family-label control.** The architecture-family label alone correlates with "
          f"{tname} at rho = {_f(fr)}. Any metric that does not clearly exceed this has "
          f"not earned its forward passes.\n")
    return L


def mech_profile(pc: dict) -> list[str]:
    """Which layers carry the signal, and what breaks it.

    Answers the request's bonus directly: the per-layer cross-fitted probe AUROC
    profile is stored for every checkpoint, so we can say where harm CONTENT
    becomes decodable, where REFUSAL becomes decodable, and how those two depths
    move between ordinary-instruct, safety-tuned and abliterated checkpoints.
    """
    L: list[str] = []
    A = L.append
    A("## Bonus — what the signal is reading, and which layers carry it\n")
    by_cls: dict[str, list] = {}
    for v in pc.values():
        d = v.get("diagnostics") or {}
        ac = d.get("auroc_content_per_layer")
        ar = d.get("auroc_refusal_per_layer")
        if not ac:
            continue
        by_cls.setdefault(v["class"], []).append((np.asarray(ac, float),
                                                  np.asarray(ar, float) if ar else None,
                                                  d.get("depth_content"), d.get("depth_refusal"),
                                                  d.get("L_star"), len(ac)))
    if not by_cls:
        return ["## Bonus — mechanistic profile\n\nNo per-layer profiles on disk.\n"]

    A("Per-layer **cross-fitted** probe AUROC, resampled to ten depth deciles and averaged "
      "within class. `content` = harmful vs plain-benign; `refusal` = the judge's refused "
      "flag read at the FIRST GENERATED token.\n")
    A("| class | n | " + " | ".join(f"{int(100*i/9)}%" for i in range(10)) + " |")
    A("|---" * 12 + "|")
    for cls in ("instruct", "safety", "abliterated", "base"):
        rows_ = by_cls.get(cls)
        if not rows_:
            continue
        for label, idx in (("content", 0), ("refusal", 1)):
            grid = []
            for r in rows_:
                arr = r[idx]
                if arr is None or not np.isfinite(arr).any():
                    continue
                xs = np.linspace(0, len(arr) - 1, 10)
                grid.append(np.interp(xs, np.arange(len(arr)), np.nan_to_num(arr, nan=0.5)))
            if not grid:
                continue
            m = np.nanmean(np.stack(grid), 0)
            A(f"| {cls} · {label} | {len(grid)} | " + " | ".join(_f(x, 2) for x in m) + " |")
    A("")
    A("| class | mean harm-content decodability depth | mean refusal decodability depth | mean L\\* |")
    A("|---|---|---|---|")
    for cls, rows_ in sorted(by_cls.items()):
        dc = [r[2] for r in rows_ if r[2] is not None and np.isfinite(r[2])]
        dr = [r[3] for r in rows_ if r[3] is not None and np.isfinite(r[3])]
        ls = [r[4] / max(1, r[5] - 1) for r in rows_ if r[4] is not None]
        A(f"| {cls} | {_f(np.mean(dc)) if dc else 'n/a'} ({len(dc)}) | "
          f"{_f(np.mean(dr)) if dr else 'n/a'} ({len(dr)}) | {_f(np.mean(ls)) if ls else 'n/a'} |")
    A("\nDepths are fractions of layer count, so they compare across architectures. "
      "`x_c3_depth_gap` is the refusal-minus-content difference.\n")

    A("### What breaks it\n")
    inv, undef, rnd, fitbeat = [], 0, [], 0
    tot = 0
    for v in pc.values():
        d = v.get("diagnostics") or {}
        m = v.get("metrics") or {}
        tot += 1
        if d.get("c1_undefined"):
            undef += 1
        pi = m.get("x_presentation_invariance")
        if pi is not None and np.isfinite(pi):
            inv.append(pi)
        rm = d.get("rand_dir_auroc_max")
        fa = m.get("k_harm_probe_auroc_max")
        if rm is not None and np.isfinite(rm) and fa is not None and np.isfinite(fa):
            rnd.append((fa, rm))
            fitbeat += int(d.get("fitted_beats_random_paired", False))
    A(f"- **Re-presentation.** Wrapping the identical request in a roleplay frame changes the "
      f"first-token refusal drive: mean invariance {_f(np.mean(inv)) if inv else 'n/a'} "
      f"(1.0 would be perfectly invariant), over {len(inv)} checkpoints.")
    A(f"- **A random direction gets most of the way there.** Against an ANISOTROPY-MATCHED "
      f"null (20 directions drawn from the empirical covariance, best of 20), the fitted "
      f"cross-fitted harm probe beats the null on **{fitbeat} of {len(rnd)}** checkpoints; "
      f"mean fitted AUROC {_f(np.mean([a for a, _ in rnd])) if rnd else 'n/a'} vs mean "
      f"best-of-20 random {_f(np.mean([b for _, b in rnd])) if rnd else 'n/a'}. Most of what a "
      f"harm probe reads is the anisotropy of the residual stream, not a harm-specific direction.")
    A(f"- **C1 undefined** (decision spread below the pre-registered 0.25-logit floor) on "
      f"**{undef} of {tot}** checkpoints.\n")
    return L


def main() -> None:
    s = _j("summary.json", {})
    race = _j("race.json", {})
    rows = race.get("rows", [])
    st0 = _j("stage0_selftest.json", {})
    st3 = _j("stage3_instrument_gate.json", {})
    st4 = _j("stage4_anchor_gate.json", {})
    f5 = _j("f5_weight_instrument.json", {})
    step1 = _j("step1_claim.json", {})
    cen = _j("lineage_census.json", {})
    gt = _j("ground_truth.json", {})
    items = _j("items.json", {})
    L: list[str] = []
    A = L.append

    A("# Results\n")
    A(f"**Verdict — {s.get('verdict', 'not computed')}**\n")
    A(f"- panel: **{s.get('n_checkpoints_scored','?')} scored checkpoints / "
      f"{s.get('n_lineages_scored','?')} lineages**, "
      f"branch `{s.get('branch_safety_arm','?')}` "
      f"({s.get('independent_safety_tuned_lineages','?')} independent safety-tuned lineages)")
    A(f"- incumbent bar, re-computed here: **{_f(s.get('incumbent_bar_recomputed_3way'))}** "
      f"3-way / **{_f(s.get('incumbent_bar_recomputed_2way'))}** 2-way")
    A(f"- promoted to iteration 2: **{s.get('promoted_to_iter2') or 'none'}**")
    A(f"- judge spend: **${s.get('judge_cost_usd','?')}** of the $10 cap | "
      f"wall clock {s.get('wall_clock_minutes','?')} min")
    A(f"- registry sha256 unchanged across the run: **{s.get('registry_unchanged')}** "
      f"(`{str(s.get('registry_sha256_at_start'))[:16]}…`)\n")

    A("## The substrate floor every internal readout has to beat\n")
    lf = items.get("lexical_floor", {})
    A("| comparison | TF-IDF + logistic AUC |")
    A("|---|---|")
    for k, v in lf.items():
        if k != "note":
            A(f"| {k.replace('_', ' ')} | {_f(v)} |")
    xs = items.get("xstest_report", {})
    A(f"\nXSTest: {xs.get('n_rows','?')} rows, **{xs.get('n_positional_pairs','?')} positional "
      f"twin pairs**; keying on `(type, focus)` instead would silently drop "
      f"**{xs.get('rows_dropped_if_keyed_on_type_focus','?')}** rows. "
      f"Unpaired by design: {', '.join(xs.get('unpaired_types', [])) or 'none'}.\n")

    A("## Stage 0 — cross-fitting is part of the definition\n")
    cf = st0.get("stage0_crossfitting", {})
    A(f"On **pure Gaussian noise**, d={cf.get('d')}, {cf.get('n_items')} randomly-labelled "
      f"items: in-sample difference-in-means projection separates at AUROC "
      f"**{_f(cf.get('in_sample_auroc'))}**, cross-fitted at **{_f(cf.get('cross_fitted_auroc'))}**. "
      "An in-sample harm direction is numerically indistinguishable from the harm label.\n")
    wi = st0.get("stage0_weight_instrument", {})
    if wi:
        A("| synthetic weight condition | BSA_w8 | BOTGAP |")
        A("|---|---|---|")
        A(f"| honest, Gaussian spectrum | {_f(wi.get('bsa_w8_honest_gaussian'))} | "
          f"{_f(wi.get('botgap_honest_gaussian'))} |")
        A(f"| honest, heavy-tailed spectrum | {_f(wi.get('bsa_w8_honest_heavy_tailed'))} | "
          f"{_f(wi.get('botgap_honest_heavy_tailed'))} |")
        A(f"| abliterated, full strength | {_f(wi.get('bsa_w8_abliterated_full_strength'))} | "
          f"{_f(wi.get('botgap_projected_bf16'))} (bf16 as shipped) |")
        A(f"| abliterated, weight 0.7 | {_f(wi.get('bsa_w8_abliterated_weight_0p7'))} | — |")
        A(f"| abliterated, 50 % layer band | {_f(wi.get('bsa_w8_abliterated_50pct_band'))} | — |")
        A(f"| per-layer RANDOM edit | {_f(wi.get('bsa_w8_per_layer_random_edit'))} (blind, expected) | "
          f"{_f(wi.get('botgap_per_layer_random_edit'))} (catches it) |")
        A("\nBSA is spectrum-invariant; **BOTGAP is not** — on a heavy-tailed spectrum the honest "
          f"BOTGAP is {_f(wi.get('botgap_honest_heavy_tailed'))}, already below its own 0.10 "
          "separator. That is a false-positive mode of the local statistic.\n")

    A("## Stage 3 / F5 — the published weight threshold does not survive real weights\n")
    A(f"Positive control on **real, unedited {st3.get('checkpoint','?')} weights**: honest "
      f"BSA_w8 = **{_f(st3.get('honest_bsa_w8'))}** against the simulation-calibrated "
      f"separator of {st3.get('bsa_threshold')}. The same weights with a shared-direction "
      f"abliteration applied by us go to **{_f(st3.get('abliterated_copy_bsa_w8'))}**, and "
      f"BOTGAP collapses to **{_f(st3.get('abliterated_copy_botgap_min'))}**. "
      f"Branch: `{st3.get('branch')}`.\n")
    if f5:
        A("Across the whole honest panel:\n")
        A("| statistic | threshold | honest mean | abliterated mean | FPR on honest | TPR | threshold-free AUROC |")
        A("|---|---|---|---|---|---|---|")
        for k in ("w_bsa_w8_k1", "_bsa_z", "w_botgap_min"):
            d = f5.get(k)
            if not d:
                continue
            A(f"| `{k}` | {d['reject_if']} {d['threshold']} | {_f(d['honest_mean'])} | "
              f"{_f(d['abliterated_mean'])} | **{_f(d['false_positive_rate_on_honest_panel'],2)}** | "
              f"{_f(d['true_positive_rate_on_abliterated'],2)} | {_f(d['threshold_free_auroc'])} |")
        A(f"\n{f5.get('verdict','')}\n")

    A("## Stage 4 — the anchor gate\n")
    A(f"- refusal-drive AUROC against the judge's refused flag: "
      f"{[_f(a) for a in st4.get('a_readout_auroc_vs_judge', [])]} → pass={st4.get('a_pass')}")
    A(f"- decision spread (logits): {[_f(x) for x in st4.get('b_decision_spread', [])]} → "
      f"pass={st4.get('b_pass')}")
    A(f"- poles behave: {st4.get('c_pass')} | nulls centred: {st4.get('d_pass')}")
    A(f"- branch: `{st4.get('branch')}`\n")

    A("## R1 — the race, top 20 of 50 (held-out WITH tuned beside it)\n")
    A("| # | metric | class | role | held-out 3-way | tuned | gap | held-out 2-way | AUROC 2-way |")
    A("|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows[:20], 1):
        role = r.get("candidate") or r.get("incumbent") or r.get("baseline") or ""
        A(f"| {i} | `{r['metric_id']}` | {r['family'].replace('LEVEL-','')} | {role} | "
          f"**{_f(r['held_out_balacc_3way'])}** | {_f(r['tuned_balacc_3way'])} | "
          f"{_f(r['gap'])} | {_f(r['held_out_balacc_2way'])} | {_f(r['auroc_2way'])} |")
    A(f"\nFull table: [`results/race_table.csv`](results/race_table.csv) — all 50 rows.\n")

    surv = race.get("survival", {})
    A("## Incumbents as bars\n")
    A("| incumbent | metric | held-out 3-way | held-out 2-way |")
    A("|---|---|---|---|")
    for r in surv.get("incumbent_rows", []):
        A(f"| {r['incumbent']} | `{r['metric_id']}` | {_f(r['held_out_3way'])} | "
          f"{_f(r['held_out_2way'])} |")
    A(f"\nSurvivors above the re-computed bar: "
      f"{[x['metric_id'] for x in surv.get('survivors', [])] or 'none'}\n")

    perm = race.get("class_gap_permutation_test", {})
    A("## The pre-registered class-gap trend\n")
    A(f"Prediction: `{perm.get('prediction','')}`. Observed rank-vs-gap correlation "
      f"**{_f(perm.get('observed_trend_corr'))}**, permutation p = **{_f(perm.get('p_value'))}** "
      f"over {perm.get('n_permutations','?')} permutations of the metric class labels "
      f"({perm.get('n_metrics','?')} metrics).\n")
    mg = perm.get("mean_gap_by_class", {})
    if mg:
        A("| metric class | mean held-out-minus-tuned gap |")
        A("|---|---|")
        for k, v in sorted(mg.items(), key=lambda kv: kv[1]):
            A(f"| {k} | {_f(v)} |")
        A("")

    diss = race.get("transfer_dissociation", {})
    A("## Ranking is not transferring\n")
    A(f"- best by DESCRIPTION (tuned): `{diss.get('best_by_description_tuned')}` — its held-out "
      f"score is {_f(diss.get('its_held_out'))}")
    A(f"- best by TRANSFER (held-out): `{diss.get('best_by_transfer_heldout')}` — its tuned "
      f"score is {_f(diss.get('its_tuned'))}")
    A(f"- dissociation present: **{diss.get('dissociation')}**")
    A(f"- model-card regex, term-swept: **{_f(diss.get('card_regex_termswept_heldout'))}** | "
      f"name-free de-biased: **{_f(diss.get('card_regex_namefree_heldout'))}** "
      "(zero prompts, zero forward passes)\n")

    cx = race.get("prompt_budget_crossover", {})
    if cx:
        A("## C2 — the prompt-budget crossover\n")
        A("| n items | internal across-item coupling | black-box logit gap |")
        A("|---|---|---|")
        for i, n in enumerate(cx["curves"]["n"]):
            a = cx["curves"]["internal_c1"][i]
            b = cx["curves"]["blackbox_b1"][i]
            A(f"| {n} | {_f(a[0])} [{_f(a[1])}, {_f(a[2])}] | {_f(b[0])} [{_f(b[1])}, {_f(b[2])}] |")
        A(f"\n{cx.get('interpretation','')}. Weight-only (zero prompts) held-out balanced "
          f"accuracy: **{_f(cx.get('weight_only_heldout_balacc_zero_prompts'))}**.\n")

    if step1.get("headline"):
        h = step1["headline"]
        A("## Step 1 — how the four anchor checkpoints actually differ\n")
        A(f"On the Qwen3-4B anchor ({step1['anchor']['instruct']} / "
          f"{step1['anchor']['saferl']} / {step1['anchor']['abliterated']}):\n")
        A(f"- mean **first principal angle** between the instruct→SafeRL and "
          f"instruct→abliterated activation-difference subspaces, at the last prompt token: "
          f"**{_f(h['mean_first_principal_angle_deg_last_prompt_token'],1)}°** "
          f"(min {_f(h['min_first_principal_angle_deg'],1)}°)")
        A(f"- mean cosine between the two mean difference vectors: "
          f"**{_f(h['mean_cosine_between_mean_difference_vectors'])}**")
        A(f"- band with the smallest angle: **{h['band_with_smallest_angle']}**")
        A(f"\n**{h['verdict']}**\n")
        A("| layer band | first principal angle | cos(mean diffs) | ‖Δabl‖ / ‖ΔSafeRL‖ |")
        A("|---|---|---|---|")
        for bn, d in h.get("by_band", {}).items():
            A(f"| {bn} | {_f(d['mean_first_principal_angle_deg'],1)}° | "
              f"{_f(d['mean_cos_mean_difference'])} | {_f(d['mean_norm_ratio'],2)} |")
        ws = step1.get("weight_side", {})
        if ws:
            A("\nWeight side (top-8 left singular subspaces, mean first principal angle):\n")
            A("| matrix | instruct→SafeRL | instruct→abliterated | SafeRL→abliterated |")
            A("|---|---|---|---|")
            for mat, d in ws.items():
                A(f"| `{mat}` | {_f(d['mean_first_angle_instruct_to_saferl_deg'],1)}° | "
                  f"{_f(d['mean_first_angle_instruct_to_abliterated_deg'],1)}° | "
                  f"{_f(d['mean_first_angle_saferl_to_abliterated_deg'],1)}° |")
        A("")

    A("## The poles — a blanket refuser must LOSE\n")
    pc = _j("per_checkpoint_reads.json", {})
    prows = []
    for k, v in pc.items():
        po = (v.get("diagnostics") or {}).get("poles") or {}
        if not po:
            continue
        own = (v.get("metrics") or {}).get("x_decision_spread", float("nan"))
        ar = po.get("always_refuse", {})
        nr = po.get("never_refuse", {})
        prows.append((v["repo"], v["class"], own, ar.get("mean_logit_gap"),
                      ar.get("decision_spread"), nr.get("mean_logit_gap"),
                      nr.get("decision_spread")))
    if prows:
        A("The synthetic always-refuse and never-refuse system wrappers are applied to the "
          "same items on the same checkpoint. A blanket refuser earns a huge refusal-drive "
          "*level* and a collapsed across-item *spread* — which is exactly why the C1 "
          "companion statistic (decision spread) is what stops a refuse-everything model "
          "from winning.\n")
        A("| checkpoint | class | own spread | always-refuse gap | its spread | ratio | never-refuse gap | its spread |")
        A("|---|---|---|---|---|---|---|---|")
        for r in sorted(prows, key=lambda x: x[1]):
            ratio = (r[4] / r[2]) if (r[2] and r[4] is not None and np.isfinite(r[2]) and r[2] > 0) else float("nan")
            A(f"| `{r[0]}` | {r[1]} | {_f(r[2])} | {_f(r[3])} | {_f(r[4])} | "
              f"**{_f(ratio, 2)}** | {_f(r[5])} | {_f(r[6])} |")
        rs = [(r[4] / r[2]) for r in prows
              if r[2] and r[4] is not None and np.isfinite(r[2]) and r[2] > 0]
        if rs:
            A(f"\nMedian always-refuse spread ratio: **{_f(np.median(rs), 2)}** "
              f"(a value well below 1 means the pole is correctly rejected).\n")

    A("## Per-item structure of the refusal drive\n")
    if pc:
        A("Mean first-token refusal-minus-compliance log-odds by item kind, averaged over "
          "scored checkpoints — the across-item structure C1 reads:\n")
        A("| item kind | what it is |")
        A("|---|---|")
        A("| `harmful` | JBB-Behaviors + StrongREJECT |")
        A("| `xstest_contrast` | XSTest genuinely-unsafe twin |")
        A("| `benign_alarming` | XSTest safe-but-alarming twin |")
        A("| `plain_benign` | JBB Index-paired benign partner |")
        A("")

    A("## Ground truth\n")
    per = gt.get("per_checkpoint", {})
    if per:
        A("| checkpoint | class | graded harmful compliance | XSTest false refusal |")
        A("|---|---|---|---|")
        for k, v in sorted(per.items(), key=lambda kv: (kv[1]["class"], kv[0])):
            A(f"| `{v['repo']}` | {v['class']} | {_f(v['harmful_compliance_strongreject'])} | "
              f"{_f(v['xstest_false_refusal_rate'])} |")
    j = gt.get("judge", {})
    A(f"\nJudge: `{j.get('judge_model')}`, {j.get('calls','?')} calls, "
      f"**${j.get('cumulative_cost_usd','?')}**. "
      f"Second-judge audit: {j.get('audit', {}).get('second_judge','n/a')}, agreement "
      f"{_f(j.get('audit', {}).get('refusal_flag_agreement'), 2)} on "
      f"{j.get('audit', {}).get('n_checked','?')} items. No Qwen judge anywhere.\n")

    try:
        L.extend(mech_profile(_j("per_checkpoint_reads.json", {})))
    except Exception as e:  # noqa: BLE001
        A(f"## Bonus — mechanistic profile\n\nnot computed: {type(e).__name__}: {e}\n")

    try:
        L.extend(correlation_panel(_j("per_checkpoint_reads.json", {}), gt, rows))
    except Exception as e:  # noqa: BLE001 - the digest must never die on one section
        A(f"## Step 5 — correlation panel\n\nnot computed: {type(e).__name__}: {e}\n")

    A("## The counting rule\n")
    hc = cen.get("hub_search_census", {})
    A(f"Resampling unit: **{cen.get('resampling_unit','')}**.\n")
    A(f"Collapse rule: `{cen.get('collapse_rule','')}`\n")
    if hc:
        A("```json")
        A(json.dumps({k: v for k, v in hc.items() if k != "candidates"}, indent=1)[:1800])
        A("```")
    A(f"\n{cen.get('f1_note','')}\n")

    A("## Known limitations of this artifact, stated rather than discovered later\n")
    A("1. **Two metrics are not scale-free across architectures.** `x_c1_slope` is in logits "
      "per unit of an L2-unit-norm projection, and `k_harm_proj_gap` likewise, so both carry "
      "the hidden-state norm of the model they came from. The race z-scores every metric "
      "column across checkpoints before fitting, so the RANKING is unaffected, but the raw "
      "values are not comparable model-to-model. The scale-free companions "
      "(`x_c1_r2`, `x_c1_spearman`, `x_c1_kendall`, `x_c1_auroc_items`) are.\n")
    A("2. **N-GLARE's four dialogue families are not equal-sized here** (baseline = the "
      "plain-benign items, plain-query = the harmful items, jailbreak = the same harmful items "
      "under the deterministic roleplay wrapper, ideal-refusal = a forced-refusal system "
      "prompt on a 40-item subsample). The declared choices are printed with the number; the "
      "verdict field says explicitly whether all four families were present.\n")
    A("3. **The base stratum is not scored.** Base checkpoints use the plain renderer, so they "
      "are harvested as GFS parents and for the step-1 note only, and never enter the "
      "three-way race. They are also not graded, so they carry no generation.\n")
    A("4. **Item fold 4 is an out-of-fold evaluation fold, not a sealed confirmation split.** "
      "Nothing is CHOSEN on it, so there is no selection leakage, but iteration 2 should not "
      "treat it as fresh data. The genuine seal is the family seal in `SEALED.md`.\n")
    A("5. **The graded ground truth is a single hosted judge with a partial second-judge "
      "audit**, not an official benchmark number. Where grading was unavailable the in-house "
      "refusal regex is used and labelled `in_house_regex` in "
      "`per_checkpoint_reads.json -> diagnostics.refusal_label_source`.\n")
    A("6. **`b_massive_act_depth` is NaN wherever the registered >1000x within-layer-median "
      "criterion is not met.** The observed peak ratio is recorded per checkpoint in "
      "`diagnostics.massive_act` so the threshold can be judged rather than guessed at.\n")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT} ({len(L)} lines)")


if __name__ == "__main__":
    main()
