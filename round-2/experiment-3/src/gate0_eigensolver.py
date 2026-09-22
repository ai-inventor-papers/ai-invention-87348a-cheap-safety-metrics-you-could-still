#!/usr/bin/env python3
"""GATE 0 - the fast eigensolver must agree with an exact eigh before it is trusted at scale.

A dense eigh of the Gram costs 12 s at d=1024 and 52 s at d=2048 on this box, which makes the
panel infeasible. Everything read here needs only the bottom ~48 and top ~4 eigenpairs, so the
statistics are computed by shifted randomized subspace iteration instead. This gate asserts that
substitution is sound - on a matrix with a FLAT bottom (the hard case, an honest layer) and on one
with a rank-one ablation scar (the easy case).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec import recipe as R  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "gate0.log"), rotation="10 MB", level="DEBUG")


def mk(d, din, seed, cond=40.0):
    rs = np.random.default_rng(seed)
    U, _ = np.linalg.qr(rs.standard_normal((d, d)))
    j = np.arange(d)
    s = np.sort((1.0 / cond) + (1.0 - 1.0 / cond) * np.exp(-3.0 * j / d))
    Vt, _ = np.linalg.qr(rs.standard_normal((din, d)))
    return (U * s) @ Vt.T


def main() -> None:
    checks, timings = [], {}
    for tag, kappa in (("honest_flat_bottom", 0.0), ("ablated_kappa1", 1.0)):
        W = mk(512, 1536, seed=4)
        if kappa > 0:
            rs = np.random.default_rng(9)
            r = rs.standard_normal(512); r /= np.linalg.norm(r)
            W = W - kappa * np.outer(r, r @ W)
        t = time.time(); ex = R.spectrum_stats(W, exact=True); t_ex = time.time() - t
        t = time.time(); fa = R.spectrum_stats(W, exact=False); t_fa = time.time() - t
        sb_e = np.array(ex["s_bottom"]); sb_f = np.array(fa["s_bottom"])
        rel = float(np.max(np.abs(sb_f - sb_e) / np.maximum(sb_e, 1e-12)))
        cos_u = float(abs(np.dot(ex["u_bottom"][:, 0].astype(np.float64),
                                 fa["u_bottom"][:, 0].astype(np.float64))))
        logger.info(f"  {tag}: exact {t_ex:.2f}s vs fast {t_fa:.2f}s ({t_ex/max(t_fa,1e-9):.1f}x); "
                    f"max rel err on bottom-8 sigma = {rel:.2e}; |cos(u_min)| = {cos_u:.6f}; "
                    f"botgap exact {ex['botgap']:.5f} fast {fa['botgap']:.5f}; "
                    f"kappa_hat exact {ex['kappa_hat']:.4f} fast {fa['kappa_hat']:.4f}")
        checks += [
            {"name": f"{tag}_bottom_sigma_within_1pct", "pass": bool(rel < 0.01), "detail": rel},
            {"name": f"{tag}_u_min_aligned", "pass": bool(cos_u > 0.99), "detail": cos_u},
            {"name": f"{tag}_botgap_agrees",
             "pass": bool(abs(ex["botgap"] - fa["botgap"]) < 0.02),
             "detail": [ex["botgap"], fa["botgap"]]},
            {"name": f"{tag}_kappa_hat_agrees",
             "pass": bool(abs(ex["kappa_hat"] - fa["kappa_hat"]) < 0.05),
             "detail": [ex["kappa_hat"], fa["kappa_hat"]]},
        ]
        timings[tag] = {"exact_s": round(t_ex, 2), "fast_s": round(t_fa, 2)}

    for d, din in ((1024, 3072),):
        W = mk(d, din, seed=7)
        t = time.time(); R.spectrum_stats(W, exact=False); dt = time.time() - t
        timings[f"fast_d{d}"] = round(dt, 2)
        logger.info(f"  fast spectrum_stats d={d}: {dt:.2f}s")

    n_pass = sum(1 for c in checks if c["pass"])
    res = {"gate": "GATE_0_EIGENSOLVER", "n_pass": n_pass, "n_checks": len(checks),
           "verdict": "FAST_EIGENSOLVER_VALIDATED" if n_pass == len(checks) else "FAST_EIGENSOLVER_SUSPECT",
           "checks": checks, "timings_seconds": timings}
    (WS / "results" / "gate0_eigensolver.json").write_text(json.dumps(res, indent=2, default=float))
    logger.info(f"GATE 0: {n_pass}/{len(checks)} -> {res['verdict']}")
    for c in checks:
        if not c["pass"]:
            logger.error(f"  FAIL {c['name']}: {c['detail']}")


if __name__ == "__main__":
    main()
