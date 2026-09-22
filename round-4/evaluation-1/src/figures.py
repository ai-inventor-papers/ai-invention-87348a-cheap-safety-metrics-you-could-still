#!/usr/bin/env python3
"""STEP I: figures (vector PDF with Type-42 fonts + 200-dpi PNG), Okabe-Ito palette, n in every panel."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS)); sys.path.insert(0, str(WS / "sections"))
from io_utils import EXP1, SEED, dump, fast_spearman, get  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs/figures.log"), rotation="30 MB", level="DEBUG")

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 9, "axes.titlesize": 9.5,
                     "axes.labelsize": 9, "legend.fontsize": 7.5, "axes.spines.top": False,
                     "axes.spines.right": False})
OI = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73", "yellow": "#F0E442",
      "blue": "#0072B2", "verm": "#D55E00", "purple": "#CC79A7", "grey": "#999999"}
FIG = WS / "figures"
FIG.mkdir(exist_ok=True)
MANIFEST: dict = {}
RES = WS / "results"


def save(fig, name: str, caption: str, sources: list[str], n: dict) -> None:
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    MANIFEST[name] = {"pdf": f"figures/{name}.pdf", "png": f"figures/{name}.png", "caption": caption,
                      "data_sources": sources, "n": n}
    logger.info(f"saved {name}")


def rj(name: str):
    return json.loads((RES / name).read_text())


# ------------------------------------------------------------------ fig1 ROSI dose
def fig1():
    D = rj("D_rosi.json")
    rows = D["dose_table"]
    host0 = "Qwen2.5-0.5B-Instruct"
    main = sorted([r for r in rows if host0 in r["host"] and r.get("arm", "rosi") in ("rosi", "none", "base", "baseline", None)
                   and r.get("mult") is not None], key=lambda r: r["mult"])
    hid = [r for r in rows if host0 in r["host"] and "hidden" in str(r.get("arm", ""))]
    q3 = [r for r in rows if "Qwen3-0.6B" in r["host"] and r.get("mult") not in (None, 0)
          and "hidden" not in str(r.get("arm", ""))]
    q3b = [r for r in rows if "Qwen3-0.6B" in r["host"] and r.get("mult") == 0]
    xpos = {0: 0, 1: 1, 4: 2, 16: 3, 64: 4}
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.2))
    fig.subplots_adjust(wspace=0.28)
    ax = axs[0]
    for key, lab, col, mk in (("B", "balanced B (stored D2)", OI["blue"], "o"), ("P", "product P", OI["verm"], "s")):
        xs = [xpos.get(r["mult"], np.nan) for r in main]
        ys = [r[f"D2_{key}"] for r in main]
        ax.plot(xs, ys, marker=mk, color=col, label=lab, lw=1.4, ms=4)
        # CI band from paired dD2 CI shifted by the x0 value
        base = ys[0]
        lo = [base + (r[f"dD2_{key}"]["ci"][0] if r.get(f"dD2_{key}") and r[f"dD2_{key}"].get("ci") else 0) for r in main]
        hi = [base + (r[f"dD2_{key}"]["ci"][1] if r.get(f"dD2_{key}") and r[f"dD2_{key}"].get("ci") else 0) for r in main]
        ax.fill_between(xs, lo, hi, color=col, alpha=0.15, lw=0)
    for r in hid:
        x = xpos.get(r["mult"], 2) + 0.12
        v = main[0]["D2_B"] + r["dD2_B"]["val"]
        ci = r["dD2_B"]["ci"]
        ax.errorbar([x], [v], yerr=[[v - (main[0]["D2_B"] + ci[0])], [(main[0]["D2_B"] + ci[1]) - v]],
                    fmt="D", color=OI["grey"], ms=4, capsize=2, label=f"hidden-direction control x{r['mult']} (B)")
    for r in q3:
        base3 = q3b[0]["D2_B"] if q3b else r["D2_B"] - r["dD2_B"]["val"]
        x = xpos.get(r["mult"], 2) - 0.12
        v = base3 + r["dD2_B"]["val"]
        ci = r["dD2_B"]["ci"]
        ax.errorbar([x], [v], yerr=[[v - (base3 + ci[0])], [(base3 + ci[1]) - v]], fmt="^", color=OI["green"],
                    ms=4, capsize=2, label=f"Qwen3-0.6B x{r['mult']} (B)")
    ax.axhline(0.5, color="k", lw=0.6, ls=":")
    ax.text(1.6, 0.455, "blanket refuser scores 0.5 on B", fontsize=6.5)
    ax.set_xticks(list(range(4))); ax.set_xticklabels(["x0", "x1", "x4", "x16"])
    ax.set_xlabel("ROSI edit multiplier (log2-spaced)"); ax.set_ylabel("two-sided score")
    nh = main[0].get("n_items_h"); nt = main[0].get("n_items_t")
    ax.set_title(f"{host0} dose response\nn={nh} harmful + {nt} twin items")
    ax.legend(frameon=False, loc="lower left")
    ax = axs[1]
    for key, lab, col in (("harm_refusal", "refusal on harmful", OI["blue"]),
                          ("false_refusal", "false refusal on benign twins", OI["verm"])):
        xs = [xpos.get(r["mult"], np.nan) for r in main]
        ys = [r[key]["val"] for r in main]
        lo = [r[key]["ci95"][0] for r in main]; hi = [r[key]["ci95"][1] for r in main]
        ax.plot(xs, ys, marker="o", color=col, label=lab, ms=4)
        ax.fill_between(xs, lo, hi, color=col, alpha=0.15, lw=0)
    ax.set_xticks(list(range(4))); ax.set_xticklabels(["x0", "x1", "x4", "x16"])
    ax.set_ylim(-0.02, 1.02); ax.set_xlabel("ROSI edit multiplier"); ax.set_ylabel("rate (95% CI)")
    ax.set_title(f"components, n={nh} / {nt} items\n20-token greedy continuations")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "fig1_rosi_dose",
         f"ROSI dose response on {host0}. Left: balanced B (stored D2) and product P vs multiplier with paired "
         "item-bootstrap 95% CI bands (dD2 CI added to the x0 value), the hidden-direction control and a Qwen3-0.6B x4 "
         "point. Right: harm refusal and benign-twin false refusal separately. 20-token continuations, gpt-5-mini "
         "stance judge, 2 hosts only.",
         ["results/D_rosi.json:dose_table"], {"n_items_harmful": nh, "n_items_twin": nt, "n_hosts": 2})


# ------------------------------------------------------------------ fig2 race scatter
def fig2():
    A = rj("A_targets.json")
    comp = A["components"]
    race = get(EXP1 / "results/race.json", "rows_primary")
    poles = get(EXP1 / "results/poles.json", "metrics_failing_the_pole_rule")
    beats = {r["metric_id"] for r in race if r.get("primary_ba") is not None and r.get("null_null_p95") is not None
             and r["primary_ba"] > r["null_null_p95"]}
    from a_targets import metric_file
    jg = get(EXP1 / "results/judge_grades.json", "per_checkpoint")
    tables = {s: json.loads(metric_file(s, jg.get(s))[0].read_text()) for s in comp}
    pts = []
    for r in race:
        mid = r["metric_id"]
        if r.get("primary_ba") is None or mid.startswith("z_"):
            continue
        xs, b, p = [], [], []
        for s, c in comp.items():
            v = tables[s].get(mid)
            if isinstance(v, (int, float)) and np.isfinite(v):
                xs.append(v); b.append(c["B"]); p.append(c["P_stored"])
        if len(xs) < 6:
            continue
        pts.append({"metric_id": mid, "cls": r.get("metric_class"), "ba": r["primary_ba"], "n": len(xs),
                    "rhoB": fast_spearman(np.array(xs), np.array(b)), "rhoP": fast_spearman(np.array(xs), np.array(p)),
                    "pole_fail": mid in poles, "beats_null": mid in beats})
    pts = [q for q in pts if np.isfinite(q["rhoB"]) and np.isfinite(q["rhoP"])]
    colors = {"ACROSS-ITEM": OI["blue"], "LEVEL-KNOWLEDGE": OI["green"], "LEVEL-BEHAVIOUR-STRUCTURE": OI["orange"]}
    fig, axs = plt.subplots(1, 2, figsize=(8.2, 3.4), sharey=True)
    fig.subplots_adjust(wspace=0.12)
    for ax, key, ttl in ((axs[0], "rhoB", "balanced target B"), (axs[1], "rhoP", "product P (arrows P->B)")):
        for q in pts:
            col = colors.get(q["cls"], OI["grey"])
            if q["beats_null"]:
                ax.scatter(q["ba"], q[key], marker="*", s=90, color=col, edgecolor="k", lw=0.5, zorder=4)
            else:
                ax.scatter(q["ba"], q[key], marker="o", s=22, facecolors="none" if q["pole_fail"] else col,
                           edgecolors=col, lw=1.0, zorder=3)
            if key == "rhoP" and abs(q["rhoB"] - q["rhoP"]) > 0.02:
                ax.annotate("", xy=(q["ba"], q["rhoB"]), xytext=(q["ba"], q["rhoP"]),
                            arrowprops=dict(arrowstyle="->", color=col, lw=0.6, alpha=0.7))
            if q["metric_id"] == "x_presentation_invariance":
                ax.annotate("presentation\ninvariance", (q["ba"], q[key]), xytext=(-75, 6),
                            textcoords="offset points", fontsize=6.5)
        ax.axhline(0, color="k", lw=0.5); ax.axvline(0.5, color="k", lw=0.4, ls=":")
        ax.set_xlabel("LOLO balanced accuracy (instruct vs abliterated)")
        ax.set_title(f"{ttl}\n{len(pts)} metrics, n={min(q['n'] for q in pts)}-{max(q['n'] for q in pts)} ckpts each")
    axs[0].set_ylabel("checkpoint-level Spearman with target")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", color=c, label=k.title()) for k, c in colors.items()]
    h += [Line2D([], [], marker="o", ls="", mfc="none", mec="k", label="fails pole rule"),
          Line2D([], [], marker="*", ls="", color="k", ms=9, label="beats within-lineage perm. null p95")]
    axs[0].legend(handles=h, frameon=False, loc="lower left", fontsize=6.5)
    save(fig, "fig2_race_scatter",
         "Race under the corrected target. One point per registry metric: x = leave-one-lineage-out BA, y = checkpoint-"
         "level Spearman with the two-sided target (15 judged checkpoints, 3 families, 6 lineages; Josiefied excluded, "
         "D12). Open markers fail the blanket-refuser pole rule; stars beat the within-lineage label-permutation null "
         "p95. Right panel: product target with arrows to the balanced value.",
         ["iter_2 exp1 results/race.json:rows_primary", "results/poles.json:metrics_failing_the_pole_rule",
          "results/A_targets.json:components", "metric_cache probe_cf files"],
         {"n_metrics": len(pts), "n_checkpoints_max": max(q["n"] for q in pts)})
    return pts


# ------------------------------------------------------------------ fig3 grader refusal
def fig3():
    F = rj("F_grader.json")
    cal = F["step1_calibration"]["per_judge_per_framing"]["stance"]
    fc = F["step2_framing_comparison"]
    fig, ax = plt.subplots(figsize=(5.8, 3.0))
    fig.subplots_adjust(right=0.78)
    labels, vals, errs, cols = [], [], [], []
    for j, jl in (("gpt5mini", "gpt-5-mini"), ("gemini25flash", "gemini-2.5\n-flash")):
        for m, ml, c in (("accuracy", "accuracy", OI["blue"]),
                         ("degenerate_grade_rate_on_known_compliant", "degenerate rate", OI["verm"])):
            e = cal[j][m]
            labels.append(f"{jl}\nstance\n{ml}\n(n={e['n']})"); vals.append(e["value"])
            errs.append([e["value"] - e["wilson95"][0], e["wilson95"][1] - e["value"]]); cols.append(c)
    for key, ml in (("rate_111_overall", "1,1,1 rate\nall"), ("rate_111_on_harmful_items", "1,1,1 rate\nharmful")):
        e = fc[key]
        labels.append(f"gpt-5-mini\nStrongREJECT\n{ml}\n(n={e['n']})"); vals.append(e["value"])
        errs.append([e["value"] - e["wilson95"][0], e["wilson95"][1] - e["value"]]); cols.append(OI["orange"])
    x = np.arange(len(vals))
    ax.bar(x, vals, color=cols, yerr=np.array(errs).T, capsize=2)
    ax.axhline(0.9, color="k", lw=0.6, ls="--"); ax.text(len(vals) - 0.5, 0.91, "gate 0.90", fontsize=6.5, ha="right")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=5.8); ax.set_ylim(0, 1.05)
    ax.set_ylabel("rate (Wilson 95% CI)")
    ax.set_title("Grader-side refusal: calibration (60+60 known items) and framing effect")
    t = fc["two_by_two_table"]
    ins = ax.inset_axes([1.12, 0.35, 0.3, 0.45])
    k = list(t.values())
    M = np.array([[k[0], k[1]], [k[2], k[3]]])
    ins.imshow(M, cmap="Greys", vmin=0, vmax=M.max() * 1.6)
    for i in range(2):
        for jj in range(2):
            ins.text(jj, i, str(M[i, jj]), ha="center", va="center", fontsize=7,
                     color=OI["verm"] if (i, jj) in ((0, 1), (1, 0)) else "k")
    ins.set_xticks([0, 1]); ins.set_xticklabels(["stance\nrefused", "stance\nengaged"], fontsize=5.5)
    ins.set_yticks([0, 1]); ins.set_yticklabels(["SR refused", "SR engaged"], fontsize=5.5)
    ins.set_title(f"n={fc['n_paired_items']} pairs, McNemar p={fc['mcnemar_exact_p_binomtest']:.1e}", fontsize=5.8)
    save(fig, "fig3_grader_refusal",
         "Grader-side refusal. Bars: accuracy and degenerate-grade rate per judge on the iter-3 calibration set (60 "
         "known-compliant + 60 known-refusal, stance framing; the only framing stored), and the StrongREJECT-framing "
         "1,1,1 rate on 1,040 iter-2 replies. Inset: StrongREJECT vs stance refusal labels (328 vs 67 discordant). "
         "1,1,1 is also the legitimate output for a true refusal, so the asymmetry is an upper bound on grader-side "
         "refusal, not a measurement.",
         ["results/F_grader.json:step1_calibration", "results/F_grader.json:step2_framing_comparison"],
         {"n_calibration": 120, "n_pairs": fc["n_paired_items"]})


# ------------------------------------------------------------------ fig4 kappa band
def fig4():
    K = rj("C_kappa_points.json")
    pts = K["points"] if isinstance(K, dict) and "points" in K else K
    tk = np.array([p["kappa_true"] for p in pts], float)
    kh = np.array([p["kappa_hat"] for p in pts], float)
    inb = np.array([bool(p["in_band"]) for p in pts])
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    lim = [min(np.nanmin(tk), np.nanmin(kh), 0) - 0.05, max(np.nanmax(tk), np.nanmax(kh), 1.5) + 0.05]
    ax.plot(lim, lim, color="k", lw=0.6, ls=":")
    ax.scatter(tk[~inb], kh[~inb], s=7, color=OI["verm"], alpha=0.6, label=f"outside band (n={int((~inb).sum())})")
    ax.scatter(tk[inb], kh[inb], s=7, color=OI["blue"], alpha=0.7, label=f"inside band (n={int(inb.sum())})")
    ax.set_xlabel("true kappa (parent-based)"); ax.set_ylabel("down_proj kappa_hat (parent-free)")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_title(f"n={len(tk)} edited layer-matrices; band = per-layer\n|1-kappa| < sigma_min/sigma_rms", fontsize=8.5)
    ax.legend(frameon=False, loc="upper left")
    save(fig, "fig4_kappa_band",
         "Parent-free realised-strength estimate kappa_hat vs parent-based true kappa for every edited layer-matrix of "
         "real published edits. Blue = inside the validity band |1-kappa| < sigma_min/sigma_rms (the read is exact "
         "there), vermilion = outside (the read is blind). Dotted = identity.",
         ["results/C_kappa_points.json (from iter_2 exp3 results/true_kappa/)"], {"n_points": int(len(tk)),
                                                                                  "n_in_band": int(inb.sum())})


# ------------------------------------------------------------------ fig5 prompt budget
def fig5():
    pb = EXP1 / "results/prompt_budget.json"
    curves = get(pb, "curves")
    raw = get(EXP1 / "results/budget_raw.json", "rows")
    A = rj("A_targets.json")
    comp = {c["repo"]: c for c in A["components"].values()}
    ks = [c["k"] for c in curves if c["k"] > 0]
    rng = np.random.default_rng(SEED)
    rec = {}
    for tgt in ("B", "P"):
        rec[tgt] = {}
        for k in ks:
            rows = [r for r in raw if r["k"] == k and r["repo"] in comp]
            seeds = sorted({r["seed"] for r in rows})
            repos = sorted({r["repo"] for r in rows})
            lin = {rp: comp[rp]["lineage"] for rp in repos}
            L = sorted(set(lin.values()))
            arr = {s: {r["repo"]: r for r in rows if r["seed"] == s} for s in seeds}

            def stat(sel_repos):
                vi, vb = [], []
                for s in seeds:
                    rr = [arr[s][rp] for rp in sel_repos if rp in arr[s]]
                    t = np.array([comp[r["repo"]][tgt if tgt == "B" else "P_stored"] for r in rr])
                    xi = np.array([r["internal"] for r in rr], float)
                    xb = np.array([np.nan if r["blackbox"] is None else r["blackbox"] for r in rr], float)
                    m = np.isfinite(xb)
                    vi.append(abs(fast_spearman(xi, t))); vb.append(abs(fast_spearman(xb[m], t[m])))
                return np.nanmean(vi), np.nanmean(vb)
            pi, pbb = stat(repos)
            bi, bb = [], []
            for _ in range(300):
                pick = rng.integers(0, len(L), len(L))
                sel = [rp for i in pick for rp in repos if lin[rp] == L[i]]
                if len(set(sel)) < 4:
                    continue
                a, b = stat(sel); bi.append(a); bb.append(b)
            rec[tgt][k] = {"internal": pi, "blackbox": pbb, "internal_ci": np.nanpercentile(bi, [2.5, 97.5]).tolist(),
                           "blackbox_ci": np.nanpercentile(bb, [2.5, 97.5]).tolist(), "n_ckpt": len(repos),
                           "n_lineages": len(L), "n_seeds": len(seeds)}
    fig, axs = plt.subplots(1, 3, figsize=(8.8, 2.9))
    fig.subplots_adjust(wspace=0.38)
    ax = axs[0]
    for key, lab, col in (("internal_lolo_ba_2way", "internal readout", OI["blue"]),
                          ("blackbox_lolo_ba_2way", "black-box logit margin", OI["verm"])):
        m = [c[key]["mean"] for c in curves if c["k"] > 0]
        lo = [c[key]["lo"] for c in curves if c["k"] > 0]; hi = [c[key]["hi"] for c in curves if c["k"] > 0]
        ax.plot(ks, m, marker="o", color=col, label=lab, ms=3.5)
        ax.fill_between(ks, lo, hi, color=col, alpha=0.15, lw=0)
    ax.axhline(0.5, color="k", lw=0.5, ls=":"); ax.set_xscale("log", base=2)
    ax.set_xlabel("prompt budget k"); ax.set_ylabel("LOLO BA (2-way)"); ax.legend(frameon=False, fontsize=6.5)
    ax.set_title("LOLO BA (stored, 200 item draws)", fontsize=8)
    for ax, tgt in ((axs[1], "B"), (axs[2], "P")):
        for key, lab, col in (("internal", "internal readout", OI["blue"]), ("blackbox", "black-box logit margin", OI["verm"])):
            m = [rec[tgt][k][key] for k in ks]
            lo = [rec[tgt][k][f"{key}_ci"][0] for k in ks]; hi = [rec[tgt][k][f"{key}_ci"][1] for k in ks]
            ax.plot(ks, m, marker="o", color=col, label=lab, ms=3.5)
            ax.fill_between(ks, lo, hi, color=col, alpha=0.15, lw=0)
        ax.set_xscale("log", base=2); ax.set_xlabel("prompt budget k"); ax.set_ylabel("|Spearman| with target")
        n0 = rec[tgt][ks[0]]
        ax.set_title(f"target {tgt}: n={n0['n_ckpt']} ckpts, {n0['n_lineages']} lineages", fontsize=8)
    save(fig, "fig5_prompt_budget",
         "Prompt budget. Left: leave-one-lineage-out BA of the internal readout (cross-fitted harm-vs-benign separation "
         "at 60% depth) and the black-box first-token logit margin vs k (stored means and 200-draw bands). Middle/right: "
         "mean |Spearman| with the balanced (B) and product (P) targets over 20 item draws per k, with 300-draw "
         "lineage-cluster bootstrap bands recomputed from budget_raw.json. Panel: 15 judged checkpoints, 3 families, "
         "6 lineages (Josiefied excluded, D12).",
         [f"iter_2 exp1 results/prompt_budget.json:curves", "results/budget_raw.json:rows",
          "results/A_targets.json:components"], {"n_checkpoints": rec["B"][ks[0]]["n_ckpt"],
                                                  "n_lineages": rec["B"][ks[0]]["n_lineages"]})
    return rec


# ------------------------------------------------------------------ fig6 power
def fig6():
    H = rj("H_power_sim.json")
    ns = sorted(int(n) for n in H["MDE"])
    fig, ax = plt.subplots(figsize=(4.6, 3.1))
    for key, lab, col, mk in (("single_2s", "single Spearman, two-sided", OI["blue"], "o"),
                              ("single_1s", "single Spearman, one-sided", OI["sky"], "s"),
                              ("partial_c0.3", "partial Spearman S1 (c_XG=0.3)", OI["green"], "^"),
                              ("diff_c0.3", "difference |rho_X|-|rho_G| (S1 rule)", OI["verm"], "D")):
        ys = [H["MDE"][str(n)].get(key) for n in ns]
        ys = [np.nan if y is None else y for y in ys]
        ax.plot(ns, ys, marker=mk, color=col, label=lab, ms=4)
        for n, y in zip(ns, ys):
            if not np.isfinite(y):
                ax.scatter([n], [0.97], marker="x", color=col, s=14)
    ax.set_ylim(0.3, 1.0); ax.set_xlabel("panel size n (6 lineage clusters)"); ax.set_ylabel("MDE |rho| at 80% power")
    ax.set_title(f"ICC {H['config']['ICC']:.3f}; {H['config']['n_mc']} MC x {H['config']['B']} boot", fontsize=8)
    ax.legend(frameon=False, fontsize=6.5, loc="lower left")
    ax.text(ns[-1], 0.975, "x = not reached by 0.95", fontsize=6, ha="right")
    save(fig, "fig6_power",
         "Minimum detectable effect (80% power) vs panel size under the lineage-cluster simulation of iter-3 power.py "
         "(ICC 0.617, lineage-cluster percentile bootstrap). Crosses: MDE not reached on the grid (rho <= 0.95).",
         ["results/H_power_sim.json:MDE"], {"n_list": ns})


@logger.catch(reraise=True)
def main(which: list[str]):
    out = {}
    for name, fn in (("fig1", fig1), ("fig2", fig2), ("fig3", fig3), ("fig4", fig4), ("fig5", fig5), ("fig6", fig6)):
        if which and name not in which:
            continue
        try:
            out[name] = fn()
        except (FileNotFoundError, KeyError, ValueError, TypeError, IndexError) as exc:
            logger.exception(f"{name} FAILED: {exc}")
            MANIFEST[name] = {"status": f"FAILED: {type(exc).__name__}: {exc}"}
    old = {}
    mp = FIG / "figures_manifest.json"
    if mp.exists():
        old = json.loads(mp.read_text())
    old.update(MANIFEST)
    dump(old, mp)
    if out.get("fig5") is not None:
        dump(out["fig5"], RES / "I_fig5_budget_recomputed.json")
    if out.get("fig2") is not None:
        dump(out["fig2"], RES / "I_fig2_points.json")


if __name__ == "__main__":
    main(sys.argv[1:])
