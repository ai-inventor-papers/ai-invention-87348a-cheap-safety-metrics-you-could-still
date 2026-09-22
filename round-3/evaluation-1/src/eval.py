"""Single entry point: re-scoring iteration-2 safety reads without new runs.

    venv_eval/bin/python eval.py all          # power (background) -> oracle -> scatter -> step1 -> ledger -> finalize
    venv_eval/bin/python eval.py oracle|scatter|power|step1|ledger|finalize

CPU only, no model is loaded, no LLM is called ($0). Everything iteration 2 wrote
is read-only; every output lands in this directory.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from common import WS, logger, read_json, setup_logging, write_json

PY = sys.executable


def _run_module(name: str) -> None:
    t = time.time()
    if name == "oracle":
        import oracle
        oracle.run()
    elif name == "scatter":
        import scatter
        scatter.run()
    elif name == "step1":
        import step1
        step1.run()
    elif name == "ledger":
        import ledger
        ledger.run()
    elif name == "power":
        import power
        power.run(WS)
    logger.info(f"{name} finished in {time.time()-t:.1f}s")


# ---------------------------------------------------------------------------
# FINALIZE: power-aware verdicts, aggregate, full/mini/preview eval outputs
# ---------------------------------------------------------------------------
def _icc_key(power: dict) -> str:
    icc = power["config"]["primary_cell"]["ICC"]
    return next(k for k in power["MDE_single"]["15"] if abs(float(k) - icc) < 1e-6)


def mde_single(power: dict, n: int) -> tuple[float, str]:
    """MDE of a single lineage-cluster Spearman at the observed (primary) ICC.

    power.json stores null when 80% power is not reached by rho_X = 0.9 (the top of
    the grid); that is recorded as MDE = 1.0 ('> 0.9'), so every |rho| is below it.
    """
    try:
        ik = _icc_key(power)
        v = power["MDE_single"][str(n)][ik]
        if isinstance(v, (int, float)):
            return float(v), f"power.json MDE_single[{n}][ICC={ik}] (simulated, lineage-cluster bootstrap)"
        return 1.0, (f"power.json MDE_single[{n}][ICC={ik}] = not reached by rho_X=0.9 "
                     f"(recorded as 1.0, i.e. > 0.9)")
    except (KeyError, TypeError, StopIteration):
        v = float(min(0.999, np.tanh((1.96 + 0.84) / np.sqrt(n - 3)) * 1.06))
        return v, "analytic Fisher-z x1.06 (power.json unreadable)"


def apply_power(orc: dict, power: dict) -> dict:
    """Re-derive the oracle verdicts with the SIMULATED MDE (rule fixed in oracle.verdict_of)."""
    from oracle import verdict_of

    n = int(orc["n_checkpoints"])
    mde, src = mde_single(power, n)
    counts: dict[str, dict[str, int]] = {}
    for r in orc["metrics"]:
        for tkey in ("two_sided", "balanced"):
            for oname, v in r[f"verdict_{tkey}"].items():
                vv = verdict_of(v["oracle_pass"], v["probe_cf_pass"],
                                v["rho_oracle_split_half"] if v["rho_oracle_split_half"] is not None else np.nan, mde)
                v["verdict"], v["tagged"], v["mde_single_at_n"] = vv, f"{vv} | SCATTER_ONLY_n<24", mde
                if not r["reference_row"]:
                    c = counts.setdefault(f"{tkey}__{oname}", {})
                    c[vv] = c.get(vv, 0) + 1
    orc["verdict_counts"] = counts
    orc["mde_single_used"], orc["mde_source"] = mde, src
    prim = counts.get("two_sided__oracle", {})
    n_ora_pass = prim.get("BOTH_PASS", 0) + prim.get("READOUT_FAILED", 0)
    if n_ora_pass == 0 and prim.get("CONSTRUCT_FAILS", 0) == 0:
        orc["cause_B_answer"] = (
            f"neither can be distinguished at n={n}: no R-dependent metric passes under the judged "
            f"oracle and every failing oracle |rho| is below the MDE ({mde:.2f})")
    elif n_ora_pass == 0:
        orc["cause_B_answer"] = (
            f"the construct: {prim.get('CONSTRUCT_FAILS', 0)} metric(s) fail under the judged oracle "
            f"with |rho| >= MDE ({mde:.2f}); {prim.get('CONSTRUCT_UNTESTABLE_AT_n', 0)} are untestable at n={n}")
    elif prim.get("READOUT_FAILED", 0) > 0:
        orc["cause_B_answer"] = (f"the readout: {prim['READOUT_FAILED']} metric(s) pass with judged refusal "
                                 f"but fail through probe_cf")
    else:
        orc["cause_B_answer"] = "neither: metrics that pass under the oracle also pass under probe_cf"
    return orc


def _f(v: Any) -> float:
    try:
        f = float(v)
        return f if np.isfinite(f) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _ex(inp: str, out: str, **kw) -> dict:
    e = {"input": inp, "output": out}
    for k, v in kw.items():
        if k.startswith("eval_"):
            f = _f(v)
            if np.isfinite(f):
                e[k] = f
        elif k.startswith("predict_"):
            e[k] = "" if v is None else str(v)
        else:
            e[k] = v
    return e


def finalize() -> dict:
    orc = read_json(WS / "oracle_rescore.json")
    power = read_json(WS / "power.json")
    sc = read_json(WS / "early_scatter.json")
    st1 = read_json(WS / "step1_reconciled.json")
    led = read_json(WS / "numbers_ledger.json")
    orc = apply_power(orc, power)
    write_json(WS / "oracle_rescore.json", orc)

    agg: dict[str, float] = {}
    for key, c in orc["verdict_counts"].items():
        for v, n in c.items():
            agg[f"oracle_verdicts__{key}__{v}"] = n
    agg["oracle_n_checkpoints"] = orc["n_checkpoints"]
    agg["oracle_n_lineages"] = orc["n_lineages"]
    agg["oracle_mde_single_used"] = orc["mde_single_used"]
    agg["warmup_checks_ok_fraction"] = orc["warmup"]["n_ok"] / max(1, orc["warmup"]["n_checks"])
    agg["reimplementation_checks_ok_fraction"] = (orc["reimplementation_validation"]["n_ok"]
                                                  / max(1, orc["reimplementation_validation"]["n_checks"]))
    # MDE table (primary cell: observed ICC and observed rho_G)
    ik = _icc_key(power)
    rg = next(k for k in power["MDE_diff"]["15"]["0.0"][ik]
              if abs(float(k) - power["config"]["primary_cell"]["rho_G"]) < 1e-6)
    for n in ("15", "24", "30", "38"):
        v = power["MDE_single"][n][ik]
        agg[f"power_mde_single_n{n}_primaryICC"] = v if isinstance(v, (int, float)) else 1.0
        agg[f"power_mde_single_n{n}_ICC0"] = (power["MDE_single"][n]["0.0"]
                                             if isinstance(power["MDE_single"][n]["0.0"], (int, float)) else 1.0)
        agg[f"power_mde_analytic_n{n}"] = power["analytic_fisher_z_MDE"][n]
        for cxg in ("0.0", "0.3", "0.6"):
            curve = power["power_curves"]["diff"][n][cxg][ik][rg]
            agg[f"power_S1diff_maxpower_n{n}_cXG{cxg}"] = max(x["power"] for x in curve)
            vv = power["MDE_diff"][n][cxg][ik][rg]
            agg[f"power_mde_diff_n{n}_cXG{cxg}"] = vv if isinstance(vv, (int, float)) else 1.0
        sz = power["size_check"]["single_rho_X_equals_0"][n][ik]
        agg[f"power_size_single_n{n}"] = sz
    agg["power_ICC_obs"] = power["observed"]["ICC_obs"]
    agg["power_rho_G_obs"] = power["observed"]["rho_G_obs"]
    # step 1
    ov = st1.get("verdicts", {}).get("overall", {})
    ov_v = ov.get("verdict") if isinstance(ov, dict) else ov
    for lab in ("SHARED_ANISOTROPY_ONLY", "SHARED_SUBSPACE_DIFFERENT_DIRECTIONS", "SAME_AXIS", "UNRELATED"):
        agg[f"step1_verdict_is_{lab}"] = float(ov_v == lab)
    rep = st1.get("reproduction_of_iter2_headline_numbers", {})
    agg["step1_iter2_numbers_reproduced"] = sum(bool(v.get("reproduced")) for v in rep.values() if isinstance(v, dict))
    agg["step1_iter2_numbers_checked"] = sum(1 for v in rep.values() if isinstance(v, dict))
    # scatter
    for rd, c in sc["correlations"].items():
        r = c["two_sided"]["spearman"]
        if r is not None:
            agg[f"scatter_rho_two_sided__{rd}"] = r
    agg["scatter_family_only_anova_R2"] = _f(sc["family_and_size_rows"]["two_sided"]["family_only"]["anova_R2"])
    # ledger
    for k, v in led.get("summary", {}).items():
        if isinstance(v, (int, float)):
            agg[f"ledger_{k}"] = v
    agg["ledger_n_inconsistencies"] = len(led.get("inconsistencies", []))
    agg = {k: float(v) for k, v in agg.items() if np.isfinite(_f(v))}
    agg = {k.replace("-", "_").replace("<", "lt").replace(".", "p"): v for k, v in agg.items()}

    datasets = []
    # --- 1. per metric oracle rows
    exs = []
    for r in orc["metrics"]:
        v2 = r["verdict_two_sided"]["oracle"]
        ho = r["target_two_sided"]["oracle"]["headline"]
        hp = r["target_two_sided"]["probe_cf"]["headline"]
        exs.append(_ex(
            f"Registry metric {r['metric_id']} (R-dependent={not r['reference_row']}): does it track the "
            f"two-sided target when R is judged refusal (oracle) vs the probe_cf readout? split-half, n={ho['n_checkpoints']}",
            v2["tagged"],
            predict_verdict_two_sided_binary_oracle=v2["tagged"],
            predict_verdict_two_sided_graded_oracle=r["verdict_two_sided"]["oracle_graded"]["tagged"],
            predict_verdict_balanced_binary_oracle=r["verdict_balanced"]["oracle"]["tagged"],
            predict_headline_form=r["target_two_sided"]["oracle"]["headline_form"],
            eval_rho_oracle_split_half=ho["rho_split_half"],
            eval_rho_oracle_LEAKY_same_item=ho.get("LEAKY_same_item_rho"),
            eval_rho_probe_cf_split_half=hp["rho_split_half"],
            eval_rho_oracle_lineage_level=ho["lineage_level_rho"],
            eval_oracle_boot_ci_lo=(ho["boot95_lineage_cluster"] or [None])[0],
            eval_oracle_boot_ci_hi=(ho["boot95_lineage_cluster"] or [None, None])[1],
            eval_oracle_perm_null_p95=ho["perm_null"]["p95_abs_rho"],
            eval_rank_agreement_oracle_vs_probe=r["rank_agreement_oracle_vs_probe_cf"]["pipeline"],
            eval_oracle_pole_pass=float(bool(r["poles"]["oracle"]["pass"])),
            metadata_metric_id=r["metric_id"], metadata_reference_row=r["reference_row"]))
    datasets.append({"dataset": "oracle_rescore_metrics", "examples": exs})
    # --- 2. per checkpoint oracle / target rows
    exs = []
    for s, p in orc["per_checkpoint"].items():
        fo = p["forms"]["oracle__restricted"]["metrics"]
        fp = p["forms"]["probe_cf__pipeline"]["metrics"]
        exs.append(_ex(f"checkpoint {p['repo']} ({p['cls']}, {p['family']}): judged two-sided target and "
                       f"oracle vs probe_cf R-dependent reads",
                       f"two_sided={_f(p['target_full']['two_sided']):.3f}",
                       predict_cls=p["cls"],
                       eval_two_sided=p["target_full"]["two_sided"], eval_balanced=p["target_full"]["balanced"],
                       eval_harmful_compliance=p["target_full"]["harmful_compliance"],
                       eval_false_refusal=p["target_full"]["false_refusal"],
                       eval_oracle_x_c1_spearman=fo.get("x_c1_spearman"),
                       eval_probe_cf_x_c1_spearman=fp.get("x_c1_spearman"),
                       eval_oracle_x_decision_spread=fo.get("x_decision_spread"),
                       eval_probe_cf_x_decision_spread=fp.get("x_decision_spread"),
                       eval_probe_cf_x_presentation_invariance=fp.get("x_presentation_invariance"),
                       metadata_slug=s, metadata_lineage=p["lineage"], metadata_family=p["family"]))
    datasets.append({"dataset": "oracle_rescore_checkpoints", "examples": exs})
    # --- 3. early scatter per checkpoint
    exs = []
    gset = set(sc["graded_slugs"])
    tg = {s: None for s in gset}
    for s, p in orc["per_checkpoint"].items():
        tg[s] = p["target_full"]["two_sided"]
    for s, r in sc["per_checkpoint"].items():
        exs.append(_ex(f"checkpoint {s}: SCREEN16 reads (C12/C13/C15/bars); graded={s in gset}",
                       "SCATTER ONLY, no survival verdict (n<24 rule)",
                       predict_cls=r.get("cls"),
                       eval_C12_twin_discrimination=r.get("C12_twin_discrimination"),
                       eval_C12_null_p95=r.get("null_p95"),
                       eval_C13_presentation_invariance_logitgap=r.get("C13_presentation_invariance_logitgap"),
                       eval_C15_late_effective_rank=r.get("C15_late_effective_rank"),
                       eval_C15_late_dispersion=r.get("C15_late_dispersion"),
                       eval_BAR_logit_gap_harm_minus_twin=r.get("BAR_logit_gap_harm_minus_twin"),
                       eval_BAR_log_refusal_mass16=r.get("BAR_log_refusal_mass16"),
                       eval_two_sided_target=tg.get(s),
                       metadata_slug=s, metadata_family=r.get("family"), metadata_graded=s in gset))
    datasets.append({"dataset": "early_scatter_screen16", "examples": exs})
    # --- 4. power: one example per (test, n, c_XG) curve at the primary ICC / rho_G
    exs = []
    for n in ("15", "24", "30", "38"):
        c = power["power_curves"]["single"][n][ik]
        v = power["MDE_single"][n][ik]
        exs.append(_ex(f"SINGLE test (H0 rho_X=0, lineage-cluster bootstrap CI), n={n}, ICC={ik}: smallest |rho| with power>=0.80",
                       "not reached by 0.9" if v is None else str(v),
                       eval_mde_single=v, eval_mde_analytic=power["analytic_fisher_z_MDE"][n],
                       eval_power_at_rho_0p6=[x["power"] for x in c if abs(x["rho_X"] - 0.6) < 1e-9][0],
                       eval_power_at_rho_0p9=[x["power"] for x in c if abs(x["rho_X"] - 0.9) < 1e-9][0],
                       eval_size_at_rho_0=[x["power"] for x in c if abs(x["rho_X"]) < 1e-9][0],
                       metadata_n=int(n), metadata_test="single"))
        for cxg in ("0.0", "0.3", "0.6"):
            c = power["power_curves"]["diff"][n][cxg][ik][rg]
            vv = power["MDE_diff"][n][cxg][ik][rg]
            exs.append(_ex(f"S1 DIFFERENCE rule (|rho_XT|-|rho_GT| CI excludes 0 AND >= 0.15), n={n}, corr(X,G)={cxg}, "
                           f"ICC={ik}, rho_G={rg}: smallest rho_X-rho_G with power>=0.80",
                           "not reached by rho_X=0.9" if vv is None else str(vv),
                           eval_mde_diff=vv, eval_max_power=max(x["power"] for x in c),
                           eval_power_at_rho_0p9=[x["power"] for x in c if abs(x["rho_X"] - 0.9) < 1e-9][0],
                           metadata_n=int(n), metadata_test="S1_diff", metadata_c_XG=float(cxg)))
    datasets.append({"dataset": "power_mde", "examples": exs})
    # --- 5. step 1 per layer (primary combo)
    exs = []
    for combo, rows in st1.get("per_layer", {}).items():
        for e in rows:
            k8 = e.get("angles_by_k", {}).get("8", {})
            post = e.get("deanisotropized_k8", {}).get("by_k", {}).get("8", {})
            exs.append(_ex(f"Step-1 {combo} layer {e['layer']}: SafeRL-vs-abliteration difference geometry",
                           str(e.get("verdict")),
                           predict_layer_verdict=e.get("verdict"),
                           eval_cos_mean_difference=e.get("cos_mean_difference"),
                           eval_first_principal_angle_k8=k8.get("first_principal_angle_deg"),
                           eval_first_angle_k8_deanisotropized=post.get("first_principal_angle_deg"),
                           metadata_combo=combo, metadata_layer=e["layer"]))
    datasets.append({"dataset": "step1_per_layer", "examples": exs})
    # --- 6. ledger
    exs = []
    for r in led["rows"]:
        exs.append(_ex(f"[{r.get('row_group')}] {r.get('claim_text')} (panel {r.get('panel_tag')}, unit {r.get('unit')})",
                       str(r.get("found_value")),
                       predict_claimed_value=r.get("claimed_value"), predict_status=r.get("status"),
                       eval_reproduced=float(r.get("reproduced") is True),
                       metadata_source=f"{r.get('source_file')}:{r.get('json_key')}",
                       metadata_n=r.get("n"), metadata_ci=r.get("ci")))
    datasets.append({"dataset": "numbers_ledger", "examples": exs})

    out = {"metadata": {"evaluation_name": "Re-scoring old safety reads without new runs (iter-3 eval 1)",
                        "cause_B_answer": orc["cause_B_answer"],
                        "step1_overall_verdict": ov_v,
                        "mde_source": orc["mde_source"],
                        "label": "every target correlation here is n<=15: SCATTER ONLY, no survival verdict",
                        "files": ["oracle_rescore.json", "early_scatter.json", "power.json",
                                  "step1_reconciled.json", "numbers_ledger.json"]},
           "metrics_agg": agg, "datasets": datasets}
    write_json(WS / "full_eval_out.json", out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["oracle", "scatter", "power", "step1", "ledger", "finalize", "all"])
    a = ap.parse_args()
    setup_logging(f"eval_{a.cmd}")
    if a.cmd == "all":
        # power is the longest pure-CPU job: start it first, in the background, PID-tracked
        pw = subprocess.Popen([PY, str(WS / "power.py")], cwd=WS,
                              stdout=open(WS / "logs" / "power_stdout.log", "w"), stderr=subprocess.STDOUT)
        logger.info(f"power started in background, PID {pw.pid}")
        for m in ("oracle", "scatter", "step1", "ledger"):
            _run_module(m)
        rc = pw.wait()
        logger.info(f"power PID {pw.pid} exited {rc}")
        finalize()
    elif a.cmd == "finalize":
        finalize()
    else:
        _run_module(a.cmd)


if __name__ == "__main__":
    main()
