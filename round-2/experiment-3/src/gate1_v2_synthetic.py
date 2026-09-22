#!/usr/bin/env python3
"""GATE 1a (v2 settings): the parent-free strength estimator on SYNTHETIC known truth, INCLUDING kappa > 1.

W is a random rectangular matrix (d_out=1024, d_in=3072) with a heavy-tailed singular spectrum; the edit is
W' = (I - kappa r r^T) W with r a random unit vector, rounded to bf16 and back (the shipped precision). The v2
read (exact float64 eigh of W W^T, tail fit j in [3, 40], index scan j in [0, 15]) must:
  - recover |1 - kappa| where the operating range allows it (|1-kappa| below sigma_min/sigma_rms of the untouched W),
  - find the edited direction at kappa = 1.5 even though it is NOT rank-last (index scan),
  - show BOTGAP collapsing toward 0 as kappa -> 1 and NOT collapsing at kappa = 1.5 (the binary flag's blind spot),
  - align the recovered bottom direction with r (|cos| > 0.95) wherever the edited value is the bottom one.
Writes results/gate1_v2_synthetic.json.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import json
import sys
from pathlib import Path

import numpy as np
import torch

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec.recipe import fit_tail  # noqa: E402


def main() -> None:
    rng = np.random.default_rng(20260921)
    d_out, d_in = 1024, 3072
    U, _ = np.linalg.qr(rng.standard_normal((d_out, d_out)))
    V, _ = np.linalg.qr(rng.standard_normal((d_in, d_out)))
    # heavy-tailed spectrum with a healthy bottom edge bounded away from zero (rectangular, like down_proj)
    s = np.sort(0.35 + 1.0 / (np.arange(1, d_out + 1) ** 0.6) + 0.15 * rng.random(d_out))[::-1]
    W0 = (U * s) @ V.T
    r = rng.standard_normal(d_out)
    r /= np.linalg.norm(r)
    rows = []
    sig_min_over_rms = float(s.min() / np.sqrt(np.mean(s ** 2)))
    for kappa in (0.0, 0.3, 0.5, 0.7, 0.9, 1.0, 1.1, 1.2, 1.5):
        W = W0 - kappa * np.outer(r, r @ W0)
        W = torch.from_numpy(W).to(torch.bfloat16).to(torch.float64).numpy()
        G = W @ W.T
        ev, E = np.linalg.eigh(0.5 * (G + G.T))
        sv = np.sqrt(np.clip(ev, 0, None))
        t = fit_tail(sv, lo=3, hi=40, scan_max=16)
        j = int(t["j_star"])
        rows.append({"kappa": kappa, "abs_dev_true": abs(1 - kappa), "kappa_hat": t["kappa_hat"], "abs_dev_hat": t["abs_dev"],
                     "j_star": j, "botgap": float(sv[0] / sv[1]),
                     "cos_u_bottom_vs_r": float(abs(E[:, 0] @ r)), "cos_u_jstar_vs_r": float(abs(E[:, j] @ r)),
                     "in_operating_range": bool(abs(1 - kappa) < sig_min_over_rms)})
    in_rng = [x for x in rows if x["in_operating_range"] and x["kappa"] > 0]
    checks = {
        "abs_dev_recovered_within_0.10_in_operating_range": all(abs(x["abs_dev_hat"] - x["abs_dev_true"]) < 0.10 for x in in_rng),
        "kappa1.5_index_scan_finds_r": next(x for x in rows if x["kappa"] == 1.5)["cos_u_jstar_vs_r"] > 0.9,
        "botgap_collapses_at_kappa1": next(x for x in rows if x["kappa"] == 1.0)["botgap"] < 0.1,
        "botgap_does_NOT_collapse_at_kappa1.5": next(x for x in rows if x["kappa"] == 1.5)["botgap"] > 0.1,
        "botgap_near_1_at_kappa0": next(x for x in rows if x["kappa"] == 0.0)["botgap"] > 0.5,
        "u_min_aligns_with_r_at_kappa1": next(x for x in rows if x["kappa"] == 1.0)["cos_u_bottom_vs_r"] > 0.95,
    }
    out = {"setting": {"d_out": d_out, "d_in": d_in, "tail_window": [3, 40], "scan": 16, "bf16_roundtrip": True,
                       "sigma_min_over_rms_untouched": sig_min_over_rms,
                       "operating_range_rule": "|1-kappa| < sigma_min/sigma_rms"},
           "rows": rows, "checks": checks, "n_pass": int(sum(checks.values())), "n_checks": len(checks),
           "bf16_floor_botgap_at_kappa1": next(x for x in rows if x["kappa"] == 1.0)["botgap"]}
    (WS / "results" / "gate1_v2_synthetic.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
