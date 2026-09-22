#!/usr/bin/env python3
"""STEP H (simulation part): lineage-cluster power for Spearman tests, reusing iter-3 power.py.

Imports power.py's simulation core (grow_family_sizes, family_id_array,
build_bootstrap_idx_map, chol_or_none, simulate_TGX, pearson_of_ranks) -- nothing is
re-implemented. Tests (all use the family(lineage)-cluster percentile bootstrap, as power.py):
  single_2s : 95% CI of rho(X,T) excludes 0              (two-sided alpha 0.05)
  single_1s : 90% CI lower bound of rho(X,T) > 0           (one-sided alpha 0.05)
  diff      : power.py's S1 rule: 2.5th pct of |rho_XT|-|rho_GT| > 0 AND point diff >= 0.15
  partial   : NEW S1 = partial Spearman rho(X,T | G) (rank-residualised on G); 95% CI excludes 0
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
from io_utils import EVAL3, dump, get, src  # noqa: E402

sys.path.insert(0, str(WS / "vendor/iter3_power"))  # verbatim copy of iter-3 power.py (sha256 in SHA256)
import power as P3  # noqa: E402  (imported, not rewritten)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs/h_power.log"), rotation="30 MB", level="DEBUG")

CHUNK = 100


def partial_rank(rX, rT, rG):
    """Partial correlation of rank vectors X,T given G (last axis)."""
    rxt = P3.pearson_of_ranks(rX, rT)
    rxg = P3.pearson_of_ranks(rX, rG)
    rtg = P3.pearson_of_ranks(rT, rG)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (rxt - rxg * rtg) / np.sqrt((1 - rxg ** 2) * (1 - rtg ** 2))


def cell(n, fs, rho_X, *, ICC, rho_G, c_XG, n_mc, B, rng, idx_map, fam_id, tests):
    L = P3.chol_or_none(rho_G, rho_X, c_XG)
    if L is None:
        return None
    A = len(fs)
    rej = {t: 0 for t in tests}
    tot = 0
    for s in range(0, n_mc, CHUNK):
        m = min(CHUNK, n_mc - s)
        T, G, X = P3.simulate_TGX(m, n, fam_id, A, L, ICC, rng, need_G=True)
        rT, rX = rankdata(T[:, idx_map], axis=-1), rankdata(X[:, idx_map], axis=-1)
        rxt_b = P3.pearson_of_ranks(rX, rT)
        if "single_2s" in tests:
            lo, hi = np.percentile(rxt_b, [2.5, 97.5], axis=-1)
            rej["single_2s"] += int(np.sum((lo > 0) | (hi < 0)))
        if "single_1s" in tests:
            lo = np.percentile(rxt_b, 5, axis=-1)
            rej["single_1s"] += int(np.sum(lo > 0))
        if "diff" in tests or "partial" in tests:
            rG = rankdata(G[:, idx_map], axis=-1)
            if "diff" in tests:
                pt = (np.abs(P3.pearson_of_ranks(rankdata(X, axis=-1), rankdata(T, axis=-1)))
                      - np.abs(P3.pearson_of_ranks(rankdata(G, axis=-1), rankdata(T, axis=-1))))
                d = np.abs(rxt_b) - np.abs(P3.pearson_of_ranks(rG, rT))
                lo = np.nanpercentile(d, 2.5, axis=-1)
                rej["diff"] += int(np.sum((lo > 0) & (pt >= 0.15)))
            if "partial" in tests:
                pb = partial_rank(rX, rT, rG)
                lo, hi = np.nanpercentile(pb, [2.5, 97.5], axis=-1)
                rej["partial"] += int(np.sum((lo > 0) | (hi < 0)))
        tot += m
    return {t: rej[t] / tot for t in tests}


def mde_from_curve(curve: list[tuple[float, float]], target: float = 0.8):
    for (r0, p0), (r1, p1) in zip(curve, curve[1:]):
        if p0 < target <= p1:
            return r0 + (target - p0) * (r1 - r0) / (p1 - p0)
    return curve[0][0] if curve and curve[0][1] >= target else None


@logger.catch(reraise=True)
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_mc", type=int, default=400)
    ap.add_argument("--B", type=int, default=300)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    pj = EVAL3 / "power.json"
    base = get(pj, "config.family_sizes_by_n.15")
    ICC = get(pj, "observed.ICC_obs")
    rho_G = get(pj, "observed.rho_G_obs")
    seed = get(pj, "config.seed")
    stored = {n: get(pj, f"config.family_sizes_by_n.{n}") for n in ("15", "24", "30", "38")}
    n_list = [15, 21, 24, 30, 38, 50] if not a.quick else [15, 30]
    rho_grid = [round(x, 2) for x in np.arange(0.1, 0.951, 0.05)]
    t0 = time.time()
    res = {"config": {"ICC": ICC, "rho_G": rho_G, "n_mc": a.n_mc, "B": a.B, "seed": seed,
                      "base_family_sizes_n15": base, "rho_grid": rho_grid,
                      "power_py": src(EVAL3 / "power.py", "simulate_TGX/build_bootstrap_idx_map/grow_family_sizes"),
                      "sources": [src(pj, "observed.ICC_obs"), src(pj, "observed.rho_G_obs"),
                                  src(pj, "config.family_sizes_by_n")]},
           "family_sizes": {}, "curves": {}, "MDE": {}}
    for n in n_list:
        fs = stored.get(str(n)) or P3.grow_family_sizes(base, n)
        res["family_sizes"][str(n)] = {"sizes": fs, "from": "power.json stored" if str(n) in stored
                                       else "grow_family_sizes(base n=15, 6 groups) extrapolated"}
        rng = np.random.default_rng(seed + n)
        idx_map = P3.build_bootstrap_idx_map(fs, a.B, rng)
        fam_id = P3.family_id_array(fs)
        curves = {"single_2s": [], "single_1s": [], "diff_c0.3": [], "partial_c0.0": [],
                  "partial_c0.3": [], "partial_c0.6": []}
        for r in rho_grid:
            p = cell(n, fs, r, ICC=ICC, rho_G=0.0, c_XG=0.0, n_mc=a.n_mc, B=a.B, rng=rng,
                     idx_map=idx_map, fam_id=fam_id, tests=("single_2s", "single_1s"))
            curves["single_2s"].append((r, p["single_2s"])); curves["single_1s"].append((r, p["single_1s"]))
            for c in (0.0, 0.3, 0.6):
                tests = ("partial", "diff") if c == 0.3 else ("partial",)
                q = cell(n, fs, r, ICC=ICC, rho_G=rho_G, c_XG=c, n_mc=a.n_mc, B=a.B, rng=rng,
                         idx_map=idx_map, fam_id=fam_id, tests=tests)
                if q is None:
                    continue
                curves[f"partial_c{c}"].append((r, q["partial"]))
                if c == 0.3:
                    curves["diff_c0.3"].append((r, q["diff"]))
        res["curves"][str(n)] = curves
        res["MDE"][str(n)] = {k: mde_from_curve(v) for k, v in curves.items()}
        logger.info(f"n={n} fs={fs} MDE={res['MDE'][str(n)]} t={time.time()-t0:.0f}s")
        dump(res, WS / "results/H_power_sim.json")
    # n needed for rho=0.5 / 0.4 (single two-sided and one-sided): coarse-to-fine search 15..100
    need = {}
    for rho in (0.5, 0.4):
        for test in ("single_2s", "single_1s"):
            found = None
            prev = 15
            for n in list(range(15, 101, 5)):
                fs = P3.grow_family_sizes(base, n)
                rng = np.random.default_rng(seed + 1000 + n)
                idx_map = P3.build_bootstrap_idx_map(fs, a.B, rng)
                p = cell(n, fs, rho, ICC=ICC, rho_G=0.0, c_XG=0.0, n_mc=a.n_mc, B=a.B, rng=rng,
                         idx_map=idx_map, fam_id=P3.family_id_array(fs), tests=(test,))[test]
                logger.info(f"search rho={rho} {test} n={n} power={p:.3f}")
                if p >= 0.8:
                    found = n
                    break
                prev = n
            need[f"rho{rho}_{test}"] = (found if found is not None else "unreachable below 100")
            if found is not None:
                need[f"rho{rho}_{test}_bracket"] = [prev, found]
    res["n_needed"] = need
    res["runtime_s"] = time.time() - t0
    res["note"] = ("family sizes keep 6 lineage clusters at every n (power.py grow_family_sizes); with ICC 0.617 "
                   "the effective n saturates, which is why power grows slowly in n")
    dump(res, WS / "results/H_power_sim.json")
    logger.info(f"n_needed={need}; runtime {res['runtime_s']:.0f}s")


if __name__ == "__main__":
    main()
