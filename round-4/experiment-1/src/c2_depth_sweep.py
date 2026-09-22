#!/usr/bin/env python3
"""c2_depth_sweep.py -- EXPLORATORY, POST HOC depth sweep of candidate C2 (two-sided self-ablation
sensitivity), reusing method.py's own measurement code path exactly (same base pass, same
cross-fitted direction fitting, same skip-call / c2_block).  NOT pre-registered.  It never enters
PREREG's S1-S6 selection rule; the only pre-registered C2 value is the one written by method.py to
rows/<slug>.json (band = B_mid = [L_h-1, L_h, L_h+1] at 50% depth).  See c2_depth_sweep.md.

For each repo, and for depth fractions f in FRACTIONS (plus an explicit "production" entry at the
model's own B_mid), it:
  - loads the model exactly as measure() does (M.ModelRun(repo); .load());
  - builds the plain batch exactly as measure() does;
  - runs ONE base pass capturing R (per-layer last-token residuals, all layers -- direction fitting
    needs this once, depth-independent) and the full-sequence hidden states at every skip-input layer
    the sweep needs (c-2 for each depth's band [c-1, c, c+1]);
  - fits the per-item cross-fitted harm directions once with method.cf_harm_dirs (same folds);
  - for each depth, temporarily overrides ModelRun.B_mid to that depth's band and calls the SAME
    ModelRun.skip_call (for the reference margins) and ModelRun.c2_block (for the ablated margins and
    the C2 value) that method.py's run_condition() calls for the production band;
  - skips random-direction nulls (out of scope for this sweep);
  - unloads the model before the next one.

Usage:
    venv_gpu/bin/python c2_depth_sweep.py [--repos a,b,...] [--force] [--limit N]

Run with env TORCH_DISABLE_NATIVE_JIT=1 (see method.py's own note: torch 2.14's native Triton DSL
ops need a C toolchain this pod lacks).
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import os

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

import method as M  # noqa: E402 -- PREREG gate, prompts, FOLDS, ModelRun, cf_harm_dirs, atomic_write, ...
from live_lib import DEVICE  # noqa: E402

WS = M.WS
LOGS = WS / "logs"
LOGS.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(LOGS / "c2_depth_sweep.log", rotation="30 MB", level="DEBUG")

OUT_JSON = WS / "c2_depth_sweep.json"
OUT_MD = WS / "c2_depth_sweep.md"

FRACTIONS = [0.15, 0.25, 0.35, 0.45, 0.5, 0.55, 0.65, 0.75, 0.85]
ACCEPTANCE_TOL = 1e-3
BOOT_SEED = 20260921
N_BOOT = 2000

TEST_MODELS = ["Qwen/Qwen2.5-0.5B-Instruct", "HuggingFaceTB/SmolLM2-360M-Instruct"]
BASE_REPO = "Qwen/Qwen3-4B-Base"


# ----------------------------------------------------------------------------- repo list / ordering
def graded_repos() -> list[str]:
    return [r for r, v in M.LABELS.items() if v.get("BALANCED") is not None]


def default_repo_order() -> list[str]:
    repos = graded_repos()
    repos = sorted(repos, key=lambda r: (M.PANEL.get(r, {}).get("n_params") or 9e9))
    return repos + [BASE_REPO]


# ----------------------------------------------------------------------------- depth-band geometry
def centre_from_fraction(f: float, L: int) -> int:
    c = int(round(f * L))
    return min(max(c, 1), L - 2)


def band_for_centre(c: int) -> list[int]:
    return [c - 1, c, c + 1]


def build_entries(L: int, L_h_production: int, B_mid_production: list[int]) -> list[dict]:
    entries = []
    for f in FRACTIONS:
        c = centre_from_fraction(f, L)
        band = band_for_centre(c)
        entries.append({"label": f"{f:g}", "f": f, "c": c, "band": band, "j": band[0]})
    entries.append({"label": "production", "f": None, "c": L_h_production, "band": list(B_mid_production),
                    "j": B_mid_production[0]})
    return entries


# ----------------------------------------------------------------------------- one model's sweep
def run_one_repo(repo: str) -> dict:
    t0 = time.time()
    mr = M.ModelRun(repo)
    out: dict[str, Any] = {"repo": repo}
    try:
        mr.load()
        L = mr.L
        L_h_production, B_mid_production = mr.L_h, list(mr.B_mid)
        out["n_layers"] = L
        out["L_h_production"] = L_h_production
        out["B_mid_production"] = B_mid_production

        b = mr.batch("plain")
        b.item_idx = list(range(2 * M.NP))  # exactly what measure() does for B["plain"] before use

        entries = build_entries(L, L_h_production, B_mid_production)
        needed_layers = sorted({e["j"] - 1 for e in entries if e["j"] > 0})

        # ---- ONE base pass: R (all layers, last-token; depth-independent direction fitting) plus the
        # full-sequence hidden states at every layer the sweep needs as a skip-call input (h_in = the
        # captured output of layer j-1, exactly as run_condition() uses base["full"][j - 1]).
        base = mr.base_pass(b, needed_layers, want_attn=False)
        del base["cache"]  # skip_call() never touches the KV cache; free VRAM before the sweep loop

        # ---- cross-fitted harm directions, same function + folds as measure()/run_condition(), fit ONCE
        allp = list(range(M.NP))
        D = M.cf_harm_dirs(base["R"], allp, M.FOLDS)

        sweep: dict[str, Any] = {}
        for e in entries:
            j = e["j"]
            h_in = base["full"][j - 1] if j > 0 else None
            mr.B_mid = e["band"]  # the only ModelRun state c2_block() reads for the ablation layers
            te = time.perf_counter()
            m_ref, _ = mr.skip_call(b, j, h_in, [], capture_late=False)
            c2 = mr.c2_block(b, j, h_in, D, m_ref, None)  # null_dirs=None: no random-direction nulls
            dt = time.perf_counter() - te
            sweep[e["label"]] = {
                "f": e["f"], "c": e["c"], "band": e["band"], "j": j,
                "value": M.fnum(c2["value"]), "raw": M.fnum(c2["raw"]), "sd_margin": M.fnum(c2["sd_margin"]),
                "drop_harm_mean": M.fnum(c2["drop_harm_mean"]), "drop_twin_mean": M.fnum(c2["drop_twin_mean"]),
                "undefined_reason": c2["undefined_reason"], "elapsed_s": round(dt, 2),
            }
        mr.B_mid = B_mid_production  # restore (tidiness only; mr is discarded right after)

        # ---- acceptance check against the production row
        row_path = M.ROWS / f"{M.slug(repo)}.json"
        prod_row_value = None
        abs_diff = None
        if row_path.exists():
            row = json.loads(row_path.read_text())
            prod_row_value = row.get("candidates", {}).get("C2", {}).get("value")
            sweep_prod_value = sweep["production"]["value"]
            if prod_row_value is not None and sweep_prod_value is not None:
                abs_diff = abs(float(prod_row_value) - float(sweep_prod_value))

        out["sweep"] = sweep
        out["production_row_C2_value"] = prod_row_value
        out["acceptance_abs_diff"] = abs_diff
        out["acceptance_pass"] = (abs_diff is not None) and (abs_diff <= ACCEPTANCE_TOL)
        out["status"] = "ok"
        del base, D, b
    except Exception as e:  # noqa: BLE001 -- never drop a repo silently; record and move on
        logger.exception(f"{repo}: sweep failed")
        out["status"] = "error"
        out["error"] = f"{type(e).__name__}: {e}"
        out["traceback"] = traceback.format_exc()[-4000:]
    finally:
        try:
            mr.unload()
        except Exception:  # noqa: BLE001
            pass
        del mr
        gc.collect()
        if DEVICE.type == "cuda":
            torch.cuda.empty_cache()
    out["wall_s"] = round(time.time() - t0, 1)
    return out


# ----------------------------------------------------------------------------- analysis (pure numpy/scipy)
def spearman(a: np.ndarray, b: np.ndarray) -> float | None:
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size < 2 or np.std(a) == 0 or np.std(b) == 0:
        return None
    r, _ = spearmanr(a, b)
    return float(r) if math.isfinite(r) else None


def lineage_groups(lineages: list[str]) -> dict[str, np.ndarray]:
    g: dict[str, list[int]] = {}
    for i, lin in enumerate(lineages):
        g.setdefault(lin, []).append(i)
    return {k: np.array(v) for k, v in g.items()}


def bootstrap_rho_ci(value: np.ndarray, target: np.ndarray, lineages: list[str],
                     n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    """Lineage-cluster bootstrap 95% CI for Spearman(value, target). Mirrors analyze_live.py's
    bootstrap_rho_ci (same seed, same n_boot, same lineage-resample scheme), reimplemented locally
    so this exploratory script has no runtime dependency on the production analysis module."""
    groups = lineage_groups(lineages)
    point = spearman(value, target)
    if len(groups) < 2:
        return {"point": point, "ci_lo": None, "ci_hi": None, "n_boot": 0,
                "note": "fewer than 2 lineages: bootstrap undefined"}
    rng = np.random.default_rng(seed)
    keys = list(groups.keys())
    boots = []
    for _ in range(n_boot):
        draw = rng.integers(0, len(keys), size=len(keys))
        idx = np.concatenate([groups[keys[i]] for i in draw])
        v, t = value[idx], target[idx]
        if len(v) < 3 or np.std(v) == 0 or np.std(t) == 0:
            continue
        r, _ = spearmanr(v, t)
        if math.isfinite(r):
            boots.append(float(r))
    if not boots:
        return {"point": point, "ci_lo": None, "ci_hi": None, "n_boot": 0, "note": "all resamples degenerate"}
    boots = np.array(boots)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"point": point, "ci_lo": float(lo), "ci_hi": float(hi), "n_boot": int(boots.size), "note": None}


def analyze(results: dict[str, dict]) -> dict:
    graded = [r for r in graded_repos() if results.get(r, {}).get("status") == "ok"]
    fam = {r: M.LABELS[r]["family"] for r in graded}
    lin = {r: M.LABELS[r]["lineage"] for r in graded}
    bal = {r: float(M.LABELS[r]["BALANCED"]) for r in graded}
    prod = {r: float(M.LABELS[r]["PRODUCT"]) for r in graded}
    f_labels = [f"{f:g}" for f in FRACTIONS]

    rho_balanced: dict[str, Any] = {}
    rho_product: dict[str, Any] = {}
    n_gt_01: dict[str, int] = {}
    within_family: dict[str, dict[str, float | None]] = {"qwen3": {}, "qwen2.5": {}, "tinyllama": {}}
    production_match: dict[str, str | None] = {}

    for lbl in f_labels + ["production"]:
        vals = []
        ok_repos = []
        for r in graded:
            sw = results[r]["sweep"].get(lbl)
            if sw is None or sw["value"] is None:
                continue
            vals.append(sw["value"])
            ok_repos.append(r)
        v = np.array(vals)
        b_ = np.array([bal[r] for r in ok_repos])
        p_ = np.array([prod[r] for r in ok_repos])
        lins_ok = [lin[r] for r in ok_repos]
        if lbl != "production":
            rho_balanced[lbl] = {**bootstrap_rho_ci(v, b_, lins_ok), "n": len(ok_repos)}
            rho_product[lbl] = {**bootstrap_rho_ci(v, p_, lins_ok), "n": len(ok_repos)}
            n_gt_01[lbl] = int(np.sum(v > 0.1))
            for family_name in within_family:
                fr = [r for r in ok_repos if fam[r] == family_name]
                if len(fr) >= 3:
                    within_family[family_name][lbl] = spearman(
                        np.array([results[r]["sweep"][lbl]["value"] for r in fr]),
                        np.array([bal[r] for r in fr]))
                else:
                    within_family[family_name][lbl] = None

    # which fraction's band matches each model's own production band (c equal)
    for r in graded:
        prod_c = results[r]["sweep"]["production"]["c"]
        match = None
        for f_lbl in f_labels:
            if results[r]["sweep"][f_lbl]["c"] == prod_c:
                match = f_lbl
                break
        production_match[r] = match
    all_match_same = len(set(v for v in production_match.values() if v is not None)) <= 1
    common_match = next((v for v in production_match.values() if v is not None), None) if all_match_same else None

    return {
        "n_graded_models_used": len(graded),
        "rho_BALANCED": rho_balanced,
        "rho_PRODUCT": rho_product,
        "n_models_C2f_gt_0.1": n_gt_01,
        "within_family_spearman_vs_BALANCED": {
            **within_family,
            "_n": {"qwen3": sum(1 for r in graded if fam[r] == "qwen3"),
                  "qwen2.5": sum(1 for r in graded if fam[r] == "qwen2.5"),
                  "tinyllama": sum(1 for r in graded if fam[r] == "tinyllama")},
        },
        "production_band_match_per_model": production_match,
        "production_band_matches_single_fraction": common_match,
    }


# ----------------------------------------------------------------------------- md report
def write_md(payload: dict) -> None:
    a = payload["analysis"]
    lines = []
    lines.append("# C2 depth sweep (EXPLORATORY, post hoc)\n")
    lines.append("**This sweep is exploratory and post hoc. It was never pre-registered and it never "
                 "enters the S1-S6 selection rule. The only pre-registered C2 value -- the one used "
                 "anywhere in S1-S6 -- is method.py's production value at B_mid = [L_h-1, L_h, L_h+1], "
                 "the band at 50% depth (L_h = round(0.5 * n_layers)). Every other point below exists "
                 "purely to describe how sensitive C2's correlation with BALANCED/PRODUCT is to the "
                 "choice of depth, for interpretation only.**\n")

    acc = payload["meta"]["acceptance_check"]
    lines.append("## Acceptance check\n")
    lines.append(f"Max |sweep production value - rows/<slug>.json candidates.C2.value| over "
                f"{acc['n_checked']} models: **{acc['max_abs_diff']}** (tolerance {ACCEPTANCE_TOL}).\n")
    if acc["failures"]:
        lines.append(f"FAILED on {len(acc['failures'])} model(s): {acc['failures']}\n")
    else:
        lines.append("All checked models passed.\n")

    lines.append("\n## Spearman(C2_f, BALANCED) over the 23 graded models, lineage-cluster bootstrap 95% CI\n")
    lines.append(f"n = {a['n_graded_models_used']} graded models with a valid sweep in every row shown.\n")
    lines.append("| f | centre depth note | rho | 95% CI | n | # models C2_f>0.1 |")
    lines.append("|---|---|---|---|---|---|")
    for f in FRACTIONS:
        lbl = f"{f:g}"
        r = a["rho_BALANCED"][lbl]
        note = " (= production band for every model)" if lbl == "0.5" else ""
        ci = f"[{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]" if r["ci_lo"] is not None else "n/a"
        lines.append(f"| {f} | {note} | {r['point']:.3f} | {ci} | {r['n']} | "
                     f"{a['n_models_C2f_gt_0.1'][lbl]} |")

    lines.append("\n## Spearman(C2_f, PRODUCT), same bootstrap\n")
    lines.append("| f | rho | 95% CI | n |")
    lines.append("|---|---|---|---|")
    for f in FRACTIONS:
        lbl = f"{f:g}"
        r = a["rho_PRODUCT"][lbl]
        ci = f"[{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]" if r["ci_lo"] is not None else "n/a"
        lines.append(f"| {f} | {r['point']:.3f} | {ci} | {r['n']} |")

    lines.append("\n## Within-family Spearman(C2_f, BALANCED)\n")
    wf = a["within_family_spearman_vs_BALANCED"]
    lines.append(f"n: qwen3={wf['_n']['qwen3']}, qwen2.5={wf['_n']['qwen2.5']}, tinyllama={wf['_n']['tinyllama']}\n")
    lines.append("| f | qwen3 | qwen2.5 | tinyllama |")
    lines.append("|---|---|---|---|")
    for f in FRACTIONS:
        lbl = f"{f:g}"
        row = [wf[fam].get(lbl) for fam in ("qwen3", "qwen2.5", "tinyllama")]
        fmt = lambda x: f"{x:.3f}" if x is not None else "n/a"  # noqa: E731
        lines.append(f"| {f} | {fmt(row[0])} | {fmt(row[1])} | {fmt(row[2])} |")

    lines.append(f"\nProduction band match: {a['production_band_matches_single_fraction']!r} "
                 f"(the fraction whose centre layer c equals L_h for every model, or None if it varies "
                 f"by model -- see `production_band_match_per_model` in the JSON).\n")

    lines.append("\n## Runtime\n")
    lines.append(f"Total wall time: {payload['meta']['total_wall_s']:.0f}s over "
                f"{payload['meta']['n_repos_attempted']} repos.\n")

    failed = [r for r, v in payload["repos"].items() if v.get("status") != "ok"]
    lines.append("\n## Failures\n")
    lines.append(f"{len(failed)} repo(s) failed: {failed}\n" if failed else "None.\n")

    OUT_MD.write_text("\n".join(lines) + "\n")


# ----------------------------------------------------------------------------- driver
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default="", help="comma-separated repo list; default = all 23 graded + base")
    ap.add_argument("--force", action="store_true", help="re-run repos that already have a status=ok entry")
    ap.add_argument("--limit", type=int, default=999, help="stop after this many NEW repos")
    a = ap.parse_args()

    if DEVICE.type == "cuda":
        total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        torch.cuda.set_per_process_memory_fraction(M.VRAM_CAP_GB / total_vram_gb)
        logger.info(f"CUDA device {torch.cuda.get_device_name(0)}: {total_vram_gb:.1f} GB total, "
                    f"capped at {M.VRAM_CAP_GB} GB ({M.VRAM_CAP_GB / total_vram_gb:.3f} fraction)")

    repos = [r for r in a.repos.split(",") if r] if a.repos else default_repo_order()
    logger.info(f"repos ({len(repos)}): {repos}")

    payload: dict[str, Any] = {"meta": {}, "repos": {}}
    if OUT_JSON.exists():
        try:
            payload = json.loads(OUT_JSON.read_text())
            payload.setdefault("repos", {})
        except (json.JSONDecodeError, OSError):
            payload = {"meta": {}, "repos": {}}

    t0 = time.time()
    done_new = 0
    for repo in repos:
        if done_new >= a.limit:
            break
        if (not a.force) and payload["repos"].get(repo, {}).get("status") == "ok":
            logger.info(f"skip (already done): {repo}")
            continue
        logger.info(f"=== {repo} ===")
        res = run_one_repo(repo)
        payload["repos"][repo] = res
        done_new += 1
        status_msg = (f"acceptance_abs_diff={res.get('acceptance_abs_diff')} "
                      f"pass={res.get('acceptance_pass')}" if res["status"] == "ok" else res.get("error"))
        logger.info(f"{repo}: status={res['status']} wall_s={res['wall_s']} {status_msg}")
        M.atomic_write(OUT_JSON, {**payload, "meta": {**payload.get("meta", {}), "partial": True}})

    ok_results = {r: v for r, v in payload["repos"].items() if v.get("status") == "ok"}
    diffs = {r: v["acceptance_abs_diff"] for r, v in ok_results.items() if v.get("acceptance_abs_diff") is not None}
    failures = [r for r, d in diffs.items() if d > ACCEPTANCE_TOL]
    acceptance = {"n_checked": len(diffs), "max_abs_diff": (max(diffs.values()) if diffs else None),
                 "per_repo_abs_diff": diffs, "failures": failures, "tolerance": ACCEPTANCE_TOL}

    analysis = analyze(ok_results) if any(r in ok_results for r in graded_repos()) else {}

    payload["meta"] = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                       "fractions": FRACTIONS, "acceptance_check": acceptance,
                       "total_wall_s": time.time() - t0, "n_repos_attempted": len(repos),
                       "boot_seed": BOOT_SEED, "n_boot": N_BOOT,
                       "note": "EXPLORATORY / post hoc. Never enters S1-S6. See c2_depth_sweep.md."}
    payload["analysis"] = analysis
    M.atomic_write(OUT_JSON, payload)
    write_md(payload)
    logger.info(f"acceptance: {acceptance}")
    logger.info(f"wrote {OUT_JSON} and {OUT_MD}")


if __name__ == "__main__":
    main()
