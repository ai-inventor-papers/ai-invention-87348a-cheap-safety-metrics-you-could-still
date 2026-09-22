#!/usr/bin/env python3
"""STEP H supplement: n needed when the NUMBER OF LINEAGES grows with n (mean 2.5 checkpoints per lineage).

The primary H_power_sim.json search keeps 6 lineage clusters at every n (the plan's design); with ICC 0.617 its
effective sample size saturates, so rho=0.5/0.4 are unreachable below n=100. This supplement answers the design
question the next iteration actually faces: how many checkpoints, spread over how many lineages.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS)); sys.path.insert(0, str(WS / "sections")); sys.path.insert(0, str(WS / "vendor/iter3_power"))
import power as P3  # noqa: E402
from h_power import cell  # noqa: E402
from io_utils import EVAL3, dump, get  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs/h_power_growing.log"), rotation="30 MB", level="DEBUG")


def sizes(n: int, per: float = 2.5) -> list[int]:
    k = max(6, int(round(n / per)))
    base = [n // k] * k
    for i in range(n - sum(base)):
        base[i] += 1
    return base


@logger.catch(reraise=True)
def main():
    pj = EVAL3 / "power.json"
    ICC = get(pj, "observed.ICC_obs"); seed = get(pj, "config.seed")
    n_mc, B = 400, 300
    out = {"design": "k_lineages = max(6, round(n/2.5)), near-equal sizes; single-Spearman lineage-cluster bootstrap test",
           "ICC": ICC, "n_mc": n_mc, "B": B, "search": {}, "n_needed": {}}
    for rho in (0.5, 0.4):
        for test in ("single_2s", "single_1s"):
            found, trace = None, []
            for n in range(15, 101, 5):
                fs = sizes(n)
                rng = np.random.default_rng(seed + 5000 + n)
                idx = P3.build_bootstrap_idx_map(fs, B, rng)
                p = cell(n, fs, rho, ICC=ICC, rho_G=0.0, c_XG=0.0, n_mc=n_mc, B=B, rng=rng, idx_map=idx,
                         fam_id=P3.family_id_array(fs), tests=(test,))[test]
                trace.append({"n": n, "k_lineages": len(fs), "power": p})
                logger.info(f"growing rho={rho} {test} n={n} k={len(fs)} power={p:.3f}")
                if p >= 0.8:
                    found = {"n": n, "k_lineages": len(fs)}
                    break
            key = f"rho{rho}_{test}"
            out["search"][key] = trace
            out["n_needed"][key] = found if found else "unreachable below 100"
    dump(out, WS / "results/H_power_growing.json")
    logger.info(f"n_needed (growing lineages): {out['n_needed']}")


if __name__ == "__main__":
    main()
