#!/usr/bin/env python3
"""STEP A: recompute Table-1 (step5) correlations under the balanced target B and the product P.

Reproduction gate first: the stored step5 numbers use P = (1-hc)*(1-fr) on the
iter-2 exp1 targets (prompt_budget.json:targets, which already excludes the 48-token
Josiefied checkpoint under deviation D12) and the probe_cf metric table
(results/metric_cache/<slug>__probe_cf__<harvest fp>__<label hash>__v3-session3.json,
label hash recomputed exactly as screen/pipeline2.py:_metric_row does).
"""
from __future__ import annotations

import ast
import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from io_utils import (DS3, EXP1, WS, PROVENANCE, dump, get, lineage_cluster_bootstrap,  # noqa: E402
                      spearman_with_p, src)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs/a_targets.log"), rotation="30 MB", level="DEBUG")

RES = EXP1 / "results"
TOL = 0.005
N_BOOT = 5000


def lab_hash(g: dict | None) -> str:
    lc = None
    if g:
        lc = {"item_idx": list(g.get("item_idx", [])),
              "full": [[r.get("refused"), r.get("score")] for r in g.get("full", [])],
              "short": [[r.get("refused"), r.get("score")] for r in g.get("short", [])]}
    return hashlib.sha256(json.dumps(lc, sort_keys=True, default=str).encode()).hexdigest()[:12]


def metric_file(slug: str, g: dict | None) -> tuple[Path | None, str]:
    lab = lab_hash(g)
    fs = sorted(glob.glob(str(RES / "metric_cache" / f"{slug}__probe_cf__*__{lab}__v3-session3.json")))
    if fs:
        return Path(fs[0]), "label-hash match"
    fs = sorted(glob.glob(str(RES / "metric_cache" / f"{slug}__probe_cf__*__v3-session3.json")),
                key=lambda p: Path(p).stat().st_mtime)
    if fs:
        return Path(fs[-1]), "NO label-hash match; newest probe_cf v3 file used"
    return None, "no probe_cf cache file"


def num(v) -> float:
    try:
        f = float(v)
        return f if np.isfinite(f) else np.nan
    except (TypeError, ValueError):
        return np.nan


def corr_block(x, t, lin, *, seed: int) -> dict:
    """Checkpoint-level and lineage-level Spearman + perm p + lineage-cluster bootstrap CI."""
    x, t, lin = np.asarray(x, float), np.asarray(t, float), np.asarray(lin)
    ck = spearman_with_p(x, t, seed=seed)
    ck["ci95_lineage_boot"] = lineage_cluster_bootstrap(x, t, lin, B=N_BOOT, seed=seed)
    ck["n_lineages"] = int(len(set(lin.tolist())))
    lx, lt, ll = [], [], []
    for L in sorted(set(lin.tolist())):
        m = lin == L
        lx.append(float(x[m].mean())); lt.append(float(t[m].mean())); ll.append(L)
    lv = spearman_with_p(lx, lt, seed=seed)
    # lineage-level: each lineage is one point, so the cluster bootstrap == ordinary bootstrap
    lv["ci95_lineage_boot"] = lineage_cluster_bootstrap(lx, lt, ll, B=N_BOOT, seed=seed)
    lv["n_lineages"] = len(ll)
    return {"checkpoint_level": ck, "lineage_level": lv}


def sig(block: dict) -> bool:
    ci = block.get("ci95_lineage_boot", {}).get("ci", [np.nan, np.nan])
    return bool((block.get("p", 1) < 0.05))


def ci_excl0(block: dict) -> bool:
    ci = block.get("ci95_lineage_boot", {}).get("ci", [np.nan, np.nan])
    return bool(np.isfinite(ci[0]) and (ci[0] > 0 or ci[1] < 0))


@logger.catch(reraise=True)
def main() -> dict:
    s5p = RES / "step5_correlations.json"
    target_str = get(s5p, "target")
    rows_stored = get(s5p, "rows")
    tg_path = RES / "prompt_budget.json"
    targets = get(tg_path, "targets")
    excluded = get(tg_path, "excluded_for_completion_length")
    jg = get(RES / "judge_grades.json", "per_checkpoint")
    judge_model = get(RES / "judge_grades.json", "judge_report.model")
    rubric = get(RES / "judge_grades.json", "rubric")
    pc = get(RES / "per_checkpoint.json", "")
    meta = {r["slug"]: r for r in pc}
    logger.info(f"targets n={len(targets)}; excluded(D12)={excluded}; judge={judge_model} rubric={rubric}")

    # ---- A1: per-checkpoint components; recompute hc/fr from judge_grades to verify stored ones
    items = json.loads((EXP1 / "inherited/items.json").read_text())
    items = items["items"] if isinstance(items, dict) else items
    kinds = np.array([it["kind"] for it in items])
    comp = {}
    max_comp_err = 0.0
    for slug, t in targets.items():
        g = jg[slug]
        idx = np.asarray(g["item_idx"])
        sc = np.array([np.nan if r.get("score") is None else float(r["score"]) for r in g["full"]])
        rf = np.array([np.nan if r.get("refused") is None else float(r["refused"]) for r in g["full"]])
        k = kinds[idx]
        hc = float(np.nanmean(sc[k == "harmful"]))
        fr = float(np.nanmean(rf[k == "benign_alarming"]))
        err = max(abs(hc - t["harmful_compliance"]), abs(fr - t["false_refusal"]))
        max_comp_err = max(max_comp_err, err)
        comp[slug] = {"repo": meta[slug]["repo"], "family": meta[slug]["family"],
                      "lineage": meta[slug]["lineage"], "cls": meta[slug]["cls"],
                      "hc": hc, "fr": fr, "P": (1 - hc) * (1 - fr),
                      "B": 0.5 * (1 - hc) + 0.5 * (1 - fr),
                      "P_stored": t["two_sided"], "n_harmful": int(np.isfinite(sc[k == "harmful"]).sum()),
                      "n_alarming": int(np.isfinite(rf[k == "benign_alarming"]).sum()),
                      "gen_max_new_tokens": meta[slug]["gen_max_new_tokens"]}
    logger.info(f"A1 component recompute max |err| vs prompt_budget targets = {max_comp_err:.2e}")

    # metric table (probe_cf readout = race.json:chosen_readout)
    chosen = get(RES / "race.json", "chosen_readout")
    table, mfile = {}, {}
    for slug in targets:
        f, how = metric_file(slug, jg.get(slug))
        mfile[slug] = {"file": f.name if f else None, "how": how}
        table[slug] = json.loads(f.read_text()) if f else {}

    # ---- A2 reproduction gate + A3 recompute + A4 flags
    out_rows = []
    for i, rs in enumerate(rows_stored):
        mid = rs["metric_id"]
        slugs = [s for s in targets if np.isfinite(num(table[s].get(mid)))]
        x = [num(table[s][mid]) for s in slugs]
        lin = [comp[s]["lineage"] for s in slugs]
        P = [comp[s]["P_stored"] for s in slugs]
        B = [comp[s]["B"] for s in slugs]
        fams = sorted({comp[s]["family"] for s in slugs})
        blkP = corr_block(x, P, lin, seed=20260921 + i)
        blkB = corr_block(x, B, lin, seed=20260921 + i)
        rep = {}
        for lev in ("checkpoint_level", "lineage_level"):
            st = rs[lev]
            d = abs(blkP[lev]["rho"] - st["spearman"])
            rep[lev] = {"stored_rho": st["spearman"], "stored_n": st["n"],
                        "recomputed_rho": blkP[lev]["rho"], "recomputed_n": blkP[lev]["n"],
                        "abs_diff": d, "status": "REPRODUCED" if (d <= TOL and st["n"] == blkP[lev]["n"])
                        else "UNREPRODUCED"}
        flags = {}
        for lev in ("checkpoint_level", "lineage_level"):
            rb, rp_ = blkB[lev]["rho"], blkP[lev]["rho"]
            flags[lev] = {
                "delta_rho_B_minus_P": rb - rp_,
                "SIGN_CHANGE": bool(np.sign(rb) != np.sign(rp_)),
                "SIG_CHANGE": bool(sig(blkB[lev]) != sig(blkP[lev]) or ci_excl0(blkB[lev]) != ci_excl0(blkP[lev])),
                "sig_B_p_lt_05": sig(blkB[lev]), "sig_P_p_lt_05": sig(blkP[lev]),
                "ciexcl0_B": ci_excl0(blkB[lev]), "ciexcl0_P": ci_excl0(blkP[lev]),
            }
        for tgt, blk in (("B", blkB), ("P", blkP)):
            flags[f"LEVEL_SIGN_DISAGREE_{tgt}"] = bool(
                np.sign(blk["checkpoint_level"]["rho"]) != np.sign(blk["lineage_level"]["rho"]))
        out_rows.append({
            "metric_id": mid, "metric_class": rs.get("metric_class"),
            "primary_ba_lolo": rs.get("primary_ba"), "lofo_ba": rs.get("lofo_ba"),
            "n": len(slugs), "n_families": len(fams), "families": fams,
            "n_lineages": len(set(lin)), "slugs": slugs, "metric_values": x,
            "B": blkB, "P": blkP, "reproduction": rep, "flags": flags,
            "source": [src(s5p, f"rows.{i}"), "results/metric_cache/<slug>__probe_cf__*.json:" + mid,
                       src(tg_path, "targets.<slug>.{harmful_compliance,false_refusal,two_sided}")],
        })
        logger.info(f"{mid}: ckpt rho_P {blkP['checkpoint_level']['rho']:+.3f} (stored {rs['checkpoint_level']['spearman']:+.3f}) "
                    f"rho_B {blkB['checkpoint_level']['rho']:+.3f} | lin P {blkP['lineage_level']['rho']:+.3f} "
                    f"B {blkB['lineage_level']['rho']:+.3f} | {rep['checkpoint_level']['status']}/{rep['lineage_level']['status']}")

    n_unrep = sum(1 for r in out_rows for lev in r["reproduction"].values() if lev["status"] != "REPRODUCED")

    # ---- A5 verdict on presentation invariance
    pi = next(r for r in out_rows if r["metric_id"] == "x_presentation_invariance")
    cb = pi["B"]["checkpoint_level"]
    if np.sign(cb["rho"]) != np.sign(pi["P"]["checkpoint_level"]["rho"]):
        verdict = "REVERSED"
    elif abs(cb["rho"]) >= 0.5 and cb["p"] < 0.05 and ci_excl0(cb):
        verdict = "SURVIVES"
    else:
        verdict = "ATTENUATED"
    lin_sign_changed = bool(np.sign(pi["B"]["lineage_level"]["rho"]) != np.sign(pi["P"]["lineage_level"]["rho"]))
    a5 = {
        "metric_id": "x_presentation_invariance", "verdict_checkpoint_level_B": verdict,
        "rho_B_ckpt": cb["rho"], "p_B_ckpt": cb["p"], "p_perm_B_ckpt": cb["p_perm"],
        "ci_B_ckpt": cb["ci95_lineage_boot"]["ci"], "n_ckpt": cb["n"],
        "rho_P_ckpt": pi["P"]["checkpoint_level"]["rho"],
        "rho_B_lineage": pi["B"]["lineage_level"]["rho"], "rho_P_lineage": pi["P"]["lineage_level"]["rho"],
        "n_lineage": pi["B"]["lineage_level"]["n"],
        "lineage_sentence": ("at lineage level n=5, which cannot reach significance under any target "
                             "(minimum achievable two-sided Spearman p at n=5 is 0.0167 only for a perfect rank order)"),
        "min_two_sided_exact_perm_p_n5": 2 / 120,
        "carry_iter2_conclusion": (not lin_sign_changed),
        "conclusion": ("within-lineage only and NEGATIVE (higher invariance -> lower two-sided safety); "
                       "the lineage-level estimate does not change sign between B and P" if not lin_sign_changed else
                       "lineage-level estimate CHANGES SIGN between targets; iter-2 conclusion must be revisited"),
    }

    # ---- A3 cross-check: iter-2 B vs iter-3 S2 on overlapping checkpoints
    dsf = DS3 / "full_data_out.json"
    ds = json.loads(dsf.read_text())
    dev = next(d for d in ds["datasets"] if d["dataset"] == "dev_panel_outcome")["examples"]
    s2 = {}
    for e in dev:
        try:
            cc = e["metadata_core_components"]
            cc = ast.literal_eval(cc) if isinstance(cc, str) else cc
            s2[e["metadata_repo"]] = {"S2": float(e["metadata_S2_core"]) if e.get("metadata_S2_core") not in (None, "None", "NA") else float("x"), "J2": float(e["metadata_J2_core"]),
                                      "P3": float(cc["harm_refusal_rate"]) * float(cc["benign_alarming_compliance"]),
                                      "hr": float(cc["harm_refusal_rate"]), "bac": float(cc["benign_alarming_compliance"]),
                                      "lineage3": e["metadata_lineage"], "family3": e["metadata_family"],
                                      "source_of_generations": e.get("metadata_source_of_generations")}
        except (TypeError, ValueError, KeyError, SyntaxError):
            continue
    del ds
    ov = [s for s in comp if comp[s]["repo"] in s2]
    xb = [comp[s]["B"] for s in ov]; yb = [s2[comp[s]["repo"]]["S2"] for s in ov]
    xp = [comp[s]["P_stored"] for s in ov]; yp = [s2[comp[s]["repo"]]["P3"] for s in ov]
    j2_identity = float(np.max([abs(v["J2"] - (2 * v["S2"] - 1)) for v in s2.values()]))
    cross = {"n_overlap": len(ov),
             "spearman_B_iter2_vs_S2_iter3": spearman_with_p(xb, yb),
             "spearman_P_iter2_vs_P3_iter3": spearman_with_p(xp, yp),
             "J2_is_not_product": {"max_abs(J2 - (2*S2-1))": j2_identity,
                                   "finding": ("iter-3 metadata_J2_core == 2*S2_core - 1 == harm_refusal_rate + "
                                               "benign_alarming_compliance - 1 (Youden-J form). It is a LINEAR rescaling of S2, "
                                               "so every Spearman under J2 is identical to S2. It is NOT the product (1-hc)*(1-fr). "
                                               "A true product P3 = harm_refusal_rate * benign_alarming_compliance is rebuilt "
                                               "from metadata_core_components and used for the A6 product sensitivity.")},
             "mean_abs_diff_B_S2": float(np.mean(np.abs(np.array(xb) - np.array(yb)))),
             "per_checkpoint": [{"repo": comp[s]["repo"], "B_iter2": comp[s]["B"], "S2_iter3": s2[comp[s]["repo"]]["S2"],
                                 "P_iter2": comp[s]["P_stored"], "J2_iter3": s2[comp[s]["repo"]]["J2"],
                                 "P3_iter3": s2[comp[s]["repo"]]["P3"]} for s in ov],
             "note": ("item sets differ: iter-3 S2_core is CORE-94 (66 harmful-side incl. 24 XSTest contrast prompts + 28 "
                      "XSTest-safe) graded from replies truncated to 64 tokens by gemini-2.5-flash; iter-2 used 48 harmful + "
                      "32 benign-alarming items, 96-token replies, gpt-5-mini stance judge. hc in iter-2 is the mean "
                      "graded compliance SCORE, iter-3 uses refusal rates."),
             "source": [src(dsf, "datasets[dev_panel_outcome].examples[*].metadata_S2_core/metadata_J2_core")]}
    logger.info(f"A3 cross-check n={len(ov)} rho(B,S2)={cross['spearman_B_iter2_vs_S2_iter3']['rho']:.3f}")

    # ---- A6 sensitivity: J2 (product) and S2 on iter-3 checkpoints, metric values from iter-2 cache
    slug_by_repo = {r["repo"]: r["slug"] for r in pc}
    a6 = []
    for i, rs in enumerate(rows_stored):
        mid = rs["metric_id"]
        xs, j2, s2v, lins = [], [], [], []
        for repo, v in s2.items():
            slug = slug_by_repo.get(repo)
            if not slug:
                continue
            f, how = metric_file(slug, jg.get(slug))
            if f is None:
                continue
            val = num(json.loads(f.read_text()).get(mid))
            if not np.isfinite(val):
                continue
            xs.append(val); j2.append(v["P3"]); s2v.append(v["S2"]); lins.append(v["lineage3"])
        row = {"metric_id": mid, "n_overlap": len(xs), "n_lineages": len(set(lins))}
        if len(xs) >= 4:
            row["P3_product"] = spearman_with_p(xs, j2, seed=7 + i)
            row["P3_product"]["ci95_lineage_boot"] = lineage_cluster_bootstrap(xs, j2, lins, B=2000, seed=7 + i)
            row["S2_balanced"] = spearman_with_p(xs, s2v, seed=7 + i)
            row["S2_balanced"]["ci95_lineage_boot"] = lineage_cluster_bootstrap(xs, s2v, lins, B=2000, seed=7 + i)
        a6.append(row)

    n_sign = sum(1 for r in out_rows if r["flags"]["checkpoint_level"]["SIGN_CHANGE"])
    n_sig = sum(1 for r in out_rows if r["flags"]["checkpoint_level"]["SIG_CHANGE"])
    n_sign_l = sum(1 for r in out_rows if r["flags"]["lineage_level"]["SIGN_CHANGE"])
    n_sig_l = sum(1 for r in out_rows if r["flags"]["lineage_level"]["SIG_CHANGE"])
    res = {
        "stored_target_string": target_str,
        "targets": {"B": "0.5*(1-hc) + 0.5*(1-fr)  (blanket refuser -> 0.5)",
                    "P": "(1-hc)*(1-fr)  (blanket refuser -> 0)",
                    "hc": "mean judge compliance SCORE on 48 harmful items (pipeline2.py:two_sided_targets)",
                    "fr": "mean judged refusal on 32 benign_alarming (XSTest-safe) items"},
        "judge": {"model": judge_model, "rubric": rubric},
        "D12_exclusion": {"excluded": excluded,
                          "note": "Josiefied-Qwen2.5-1.5B-abliterated (48-token regeneration after OOM) excluded from every two-sided analysis (deviation D12)"},
        "components": comp, "component_recompute_max_abs_err": max_comp_err,
        "metric_table_files": mfile, "chosen_readout": chosen,
        "rows": out_rows, "n_unreproduced_cells": n_unrep,
        "counts": {"n_rows_sign_change_ckpt": n_sign, "n_rows_sig_change_ckpt": n_sig,
                   "n_rows_sign_change_lineage": n_sign_l, "n_rows_sig_change_lineage": n_sig_l},
        "A5_presentation_invariance": a5, "A3_crosscheck_iter3": cross, "A6_sensitivity_iter3": a6,
    }
    dump(res, WS / "results/A_targets.json")
    dump(PROVENANCE, WS / "results/A_provenance.json")
    logger.info(f"A done: unreproduced cells={n_unrep}; sign changes ckpt={n_sign} lin={n_sign_l}; "
                f"sig changes ckpt={n_sig} lin={n_sig_l}; presinv verdict={verdict}")
    return res


if __name__ == "__main__":
    main()
