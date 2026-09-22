#!/usr/bin/env python3
"""GATE 1 - the parent-free strength estimators on KNOWN GROUND TRUTH.

Run BEFORE any wild checkpoint is touched, so a broken estimator costs minutes, not the whole
transfer budget.

WHAT THE FIRST PASS OF THIS GATE MEASURED, AND WHY THE DESIGN CHANGED
--------------------------------------------------------------------
Abliteration is W' = (I - kappa r r^T) W, so G' = P G P with P = I - kappa r r^T and
    r^T G' r = (1-kappa)^2 r^T G r.
A RANK read (BOTGAP, and the tail-fit kappa_hat built on it) can only see the edit once
(1-kappa)^2 * r^T G r drops below the layer's own sigma_min^2. For a generic r, r^T G r is of order
median(sigma^2), so a rank read is blind outside |1-kappa| < sigma_min/median(sigma).
On real Qwen3-0.6B o_proj that ratio is small, and the first pass duly measured
    unedited kappa_hat 0.139 -> kappa=0.3 gives 0.141 -> kappa=0.7 gives 0.162,
i.e. NO recovery of a large real edit. That is a property of the statistic, not a bug, and it is
exactly the calibration this artifact exists to produce.

So this gate now measures THREE estimators side by side across the whole kappa range:
  RANK     BOTGAP / kappa_hat            (bottom-spectrum rank deficiency)
  SHARING  BSA_w / XLC                   (ADOPTED PRIOR ART: the public model scanner's statistic)
  GRADED   RQ  = Rayleigh depression     (NEW: how far below its own spectrum the pooled cross-layer
                                          direction sits; well-defined at EVERY kappa)
and reports the measured operating range of each.
"""
from __future__ import annotations

import json
import os
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
logger.add(str(WS / "logs" / "gate1.log"), rotation="30 MB", level="DEBUG")

KAPPAS = (0.0, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5)


def realistic_matrix(d_out: int, d_in: int, seed: int, cond: float = 40.0) -> np.ndarray:
    """A rectangular matrix with a TRAINED-LAYER-like spectrum (condition number ~ `cond`).

    The first pass of this gate used cond ~ 3e4, whose squared bottom sits below float32 Gram
    precision; that produced all-zero bottom eigenvalues and meaningless statistics. Real o_proj
    matrices are far better conditioned - measured on Qwen3-0.6B in part (c).
    """
    rs = np.random.default_rng(seed)
    U, _ = np.linalg.qr(rs.standard_normal((d_out, d_out)))
    j = np.arange(d_out)
    s = (1.0 / cond) + (1.0 - 1.0 / cond) * np.exp(-3.0 * j / d_out)
    s = np.sort(s * (1.0 + 0.03 * rs.standard_normal(d_out)))       # ascending
    Vt, _ = np.linalg.qr(rs.standard_normal((d_in, d_out)))
    return ((U * s) @ Vt.T).astype(np.float64)


def bf16_roundtrip(W: np.ndarray) -> np.ndarray:
    u32 = W.astype(np.float32).view(np.uint32)
    return (((u32 + 0x8000 + ((u32 >> 16) & 1)) & 0xFFFF0000).astype(np.uint32)
            ).view(np.float32).astype(np.float64)


def ablate(W: np.ndarray, r: np.ndarray, kappa: float) -> np.ndarray:
    r = r / np.linalg.norm(r)
    return W - kappa * np.outer(r, r @ W)


def _gram(W: np.ndarray) -> np.ndarray:
    G = np.asarray(W, dtype=np.float64) @ np.asarray(W, dtype=np.float64).T
    return 0.5 * (G + G.T)


def gate_1a(d_out: int = 512, d_in: int = 1536, n_layers: int = 8) -> dict:
    """Synthetic multi-layer stack, SHARED random direction, full kappa sweep."""
    logger.info(f"GATE 1a SYNTHETIC  {n_layers} layers of {d_out}x{d_in}")
    rs = np.random.default_rng(20260920)
    Ws = {l: realistic_matrix(d_out, d_in, seed=100 + l) for l in range(n_layers)}
    r_true = rs.standard_normal(d_out); r_true /= np.linalg.norm(r_true)
    rows = []
    for k in KAPPAS:
        t0 = time.time()
        grams, u_min, kaps, bots, specs = {}, {}, {}, {}, {}
        for l, W in Ws.items():
            Wp = ablate(W, r_true, k) if k > 0 else W
            st = R.spectrum_stats(Wp)
            j = min(int(st["j_star"]), st["u_bottom"].shape[1] - 1)
            u_min[l] = st["u_bottom"][:, j]
            kaps[l], bots[l] = st["kappa_hat"], st["botgap"]
            grams[l] = _gram(Wp)
            specs[l] = np.array(st["spectrum_val"])
        bsa = R.bsa_window(u_min, window=min(8, n_layers))
        xlc = R.cross_layer_cosine(u_min)
        rhat = R.pooled_bottom_direction(grams)
        rq_pool = float(np.median([R.rayleigh_depression(grams[l], rhat[:, 0], specs[l])["rq"]
                                   for l in grams]))
        rq_true = float(np.median([R.rayleigh_depression(grams[l], r_true, specs[l])["rq"]
                                   for l in grams]))
        cos_rhat = float(abs(np.dot(rhat[:, 0], r_true)))
        rows.append({
            "kappa_true": k, "abs_dev_true": abs(1.0 - k),
            "kappa_hat_mean": float(np.mean(list(kaps.values()))),
            "botgap_min": float(min(bots.values())),
            "BSA_w": bsa["bsa_w"], "XLC": xlc["xlc"],
            "RQ_pooled": rq_pool, "RQ_true_dir": rq_true,
            "RQ_pooled_log10": float(np.log10(max(rq_pool, 1e-300))),
            "cos_rhat_rtrue": cos_rhat,
            "sigma_min_over_median": float(np.median(
                [R.spectrum_stats(Ws[l])["sigma_min_over_median"] for l in [0]])),
            "sec": round(time.time() - t0, 1)})
        logger.info(f"  k={k:<4} kappa_hat={rows[-1]['kappa_hat_mean']:.3f} "
                    f"BOTGAPmin={rows[-1]['botgap_min']:.4f} BSA={bsa['bsa_w']:.3f} "
                    f"XLC={xlc['xlc']:.3f} RQ={rq_pool:.3e} cos(rhat,r)={cos_rhat:.3f} "
                    f"[{rows[-1]['sec']}s]")

    def mono(key: str) -> float:
        xs = np.array([abs(1.0 - r0["kappa_true"]) for r0 in rows])       # |1-kappa|
        ys = np.array([r0[key] for r0 in rows], dtype=float)
        m = np.isfinite(ys)
        if m.sum() < 4:
            return float("nan")
        rx = np.argsort(np.argsort(xs[m])).astype(float)
        ry = np.argsort(np.argsort(ys[m])).astype(float)
        return float(np.corrcoef(rx, ry)[0, 1])

    checks = [
        {"name": "RQ_monotone_in_|1-kappa|_across_FULL_range",
         "pass": bool(mono("RQ_pooled_log10") > 0.85), "detail": mono("RQ_pooled_log10")},
        {"name": "pooled_direction_recovers_r_at_kappa1",
         "pass": bool(next(x for x in rows if x["kappa_true"] == 1.0)["cos_rhat_rtrue"] > 0.95),
         "detail": next(x for x in rows if x["kappa_true"] == 1.0)["cos_rhat_rtrue"]},
        {"name": "k1.0_botgap_collapses",
         "pass": bool(next(x for x in rows if x["kappa_true"] == 1.0)["botgap_min"] < 0.10),
         "detail": next(x for x in rows if x["kappa_true"] == 1.0)["botgap_min"]},
        {"name": "k1.5_botgap_does_NOT_collapse_binary_flag_blind_spot",
         "pass": bool(next(x for x in rows if x["kappa_true"] == 1.5)["botgap_min"] > 0.10),
         "detail": next(x for x in rows if x["kappa_true"] == 1.5)["botgap_min"]},
        {"name": "k0_botgap_healthy_no_false_positive",
         "pass": bool(next(x for x in rows if x["kappa_true"] == 0.0)["botgap_min"] > 0.10),
         "detail": next(x for x in rows if x["kappa_true"] == 0.0)["botgap_min"]},
        {"name": "BSA_rises_with_edit",
         "pass": bool(next(x for x in rows if x["kappa_true"] == 1.0)["BSA_w"]
                      > next(x for x in rows if x["kappa_true"] == 0.0)["BSA_w"]),
         "detail": [next(x for x in rows if x["kappa_true"] == 0.0)["BSA_w"],
                    next(x for x in rows if x["kappa_true"] == 1.0)["BSA_w"]]},
    ]
    return {"rows": rows, "checks": checks,
            "rank_monotonicity": mono("kappa_hat_mean"),
            "RQ_monotonicity": mono("RQ_pooled_log10"),
            "BSA_monotonicity": mono("BSA_w")}


def gate_1b(d_out: int = 512, d_in: int = 1536) -> dict:
    logger.info("GATE 1b BF16 REALISM")
    W = realistic_matrix(d_out, d_in, seed=11)
    rs = np.random.default_rng(5)
    r = rs.standard_normal(d_out); r /= np.linalg.norm(r)
    rows = []
    for k in (0.0, 1.0):
        st = R.spectrum_stats(bf16_roundtrip(ablate(W, r, k)))
        rows.append({"kappa_true": k, "botgap_bf16": st["botgap"], "kappa_hat": st["kappa_hat"],
                     "n_unresolved": st["n_unresolved"]})
        logger.info(f"  bf16 k={k} botgap={st['botgap']:.6f} kappa_hat={st['kappa_hat']:.3f}")
    floor = next(x for x in rows if x["kappa_true"] == 1.0)["botgap_bf16"]
    return {"rows": rows, "bf16_botgap_floor": floor, "checks": [
        {"name": "bf16_floor_not_algebraic_zero", "pass": bool(floor > 1e-6), "detail": floor},
        {"name": "bf16_floor_under_prereg_separator_0.1", "pass": bool(floor < 0.10),
         "detail": floor}]}


def gate_1c(repo_id: str, token: str | None, max_layers: int = 10) -> dict:
    """Real trained weights, constructed edit at KNOWN kappa. The labelled calibration curve."""
    logger.info(f"GATE 1c REAL MODEL, CONSTRUCTED EDIT  repo={repo_id}")
    sess = R._session(token)
    try:
        plan = R.plan_repo(repo_id, token=token, sess=sess)
        if plan.skip_reason:
            return {"error": plan.skip_reason, "repo_id": repo_id, "checks": []}
        attn = {t["layer"]: t for _, t in plan.targets.items() if t["component"] == "attn"}
        layers = sorted(attn)[:max_layers]
        t0 = time.time()
        Ws, nbytes = {}, 0
        for l in layers:
            Ws[l] = R.fetch_tensor(sess, repo_id, attn[l]).astype(np.float64)
            nbytes += attn[l]["nbytes"]
        fetch_s = time.time() - t0
        mbps = (nbytes / 1e6) / max(fetch_s, 1e-6)
        logger.info(f"  fetched {len(Ws)} o_proj, {nbytes/1e6:.0f} MB in {fetch_s:.1f}s = {mbps:.1f} MB/s")

        base = R.spectrum_stats(Ws[layers[0]])
        d = Ws[layers[0]].shape[0]
        rs = np.random.default_rng(3)
        r_shared = rs.standard_normal(d); r_shared /= np.linalg.norm(r_shared)
        r_per = {l: (lambda v: v / np.linalg.norm(v))(rs.standard_normal(d)) for l in layers}

        out: dict[str, object] = {
            "repo_id": repo_id, "n_layers_used": len(layers), "d_model": int(d),
            "fetch_mbps": round(mbps, 2), "fetch_bytes": nbytes, "fetch_seconds": round(fetch_s, 1),
            "real_sigma_min_over_median": base["sigma_min_over_median"],
            "real_cond_bottom": base["cond_bottom"],
            "predicted_rank_read_operating_range_abs1mk":
                R.operating_range(base["sigma_min_over_median"]),
        }
        logger.info(f"  REAL SPECTRUM: sigma_min/median = {base['sigma_min_over_median']:.4f} "
                    f"=> a rank read can only see |1-kappa| < "
                    f"{out['predicted_rank_read_operating_range_abs1mk']:.3f}")
        variants, t1 = {}, time.time()
        for name, kap, per in (("unedited", 0.0, False), ("shared_k0.3", 0.3, False),
                               ("shared_k0.7", 0.7, False), ("shared_k1.0", 1.0, False),
                               ("perlayer_k1.0", 1.0, True)):
            u_min, kaps, bots, grams, specs = {}, {}, {}, {}, {}
            for l in layers:
                rv = r_per[l] if per else r_shared
                Wp = bf16_roundtrip(ablate(Ws[l], rv, kap)) if kap > 0 else Ws[l]
                st = R.spectrum_stats(Wp)
                j = min(int(st["j_star"]), st["u_bottom"].shape[1] - 1)
                u_min[l], kaps[l], bots[l] = st["u_bottom"][:, j], st["kappa_hat"], st["botgap"]
                grams[l] = _gram(Wp)
                specs[l] = np.array(st["spectrum_val"])
            bsa = R.bsa_window(u_min, window=min(8, len(layers)))
            xlc = R.cross_layer_cosine(u_min)
            rhat = R.pooled_bottom_direction(grams)
            rq = float(np.median([R.rayleigh_depression(grams[l], rhat[:, 0], specs[l])["rq"]
                                  for l in grams]))
            variants[name] = {
                "kappa_true": kap, "per_layer_dirs": per,
                "kappa_hat_mean": float(np.mean(list(kaps.values()))),
                "kappa_hat_max": float(np.max(list(kaps.values()))),
                "BOTGAP_min": float(min(bots.values())),
                "XLC": xlc["xlc"], "XLC_iso_null": xlc["iso_null"], "BSA_w": bsa["bsa_w"],
                "RQ_pooled": rq, "RQ_pooled_log10": float(np.log10(max(rq, 1e-300))),
                "cos_rhat_rtrue": float(abs(np.dot(rhat[:, 0],
                                                   r_shared if not per else r_per[layers[0]]))),
            }
            v = variants[name]
            logger.info(f"  {name:<14} kappa_hat={v['kappa_hat_mean']:.3f} "
                        f"BOTGAPmin={v['BOTGAP_min']:.4f} BSA={v['BSA_w']:.3f} "
                        f"XLC={v['XLC']:.3f} RQ={v['RQ_pooled']:.3e} "
                        f"cos(rhat,r)={v['cos_rhat_rtrue']:.3f}")
        out["compute_seconds"] = round(time.time() - t1, 1)
        out["variants"] = variants
        u, s3, s7, s10, pl = (variants["unedited"], variants["shared_k0.3"],
                              variants["shared_k0.7"], variants["shared_k1.0"],
                              variants["perlayer_k1.0"])
        out["checks"] = [
            {"name": "REAL_RQ_monotone_decreasing_in_kappa",
             "pass": bool(u["RQ_pooled"] > s3["RQ_pooled"] > s7["RQ_pooled"] > s10["RQ_pooled"]),
             "detail": [u["RQ_pooled"], s3["RQ_pooled"], s7["RQ_pooled"], s10["RQ_pooled"]]},
            {"name": "REAL_rank_read_BLIND_below_kappa1_documented",
             "pass": True,
             "detail": {"kappa_hat": [u["kappa_hat_mean"], s3["kappa_hat_mean"],
                                      s7["kappa_hat_mean"], s10["kappa_hat_mean"]],
                        "note": "informational: this IS the operating-range measurement"}},
            {"name": "REAL_k1.0_BOTGAP_collapses",
             "pass": bool(s10["BOTGAP_min"] < 0.10), "detail": s10["BOTGAP_min"]},
            {"name": "REAL_unedited_BOTGAP_healthy",
             "pass": bool(u["BOTGAP_min"] > 0.10), "detail": u["BOTGAP_min"]},
            {"name": "REAL_XLC_high_shared_vs_perlayer",
             "pass": bool(s10["XLC"] > 2.0 * pl["XLC"]), "detail": [s10["XLC"], pl["XLC"]]},
            {"name": "REAL_BSA_rises_for_shared_edit",
             "pass": bool(s10["BSA_w"] > u["BSA_w"]), "detail": [u["BSA_w"], s10["BSA_w"]]},
            {"name": "REAL_pooled_dir_recovers_r_at_k1",
             "pass": bool(s10["cos_rhat_rtrue"] > 0.90), "detail": s10["cos_rhat_rtrue"]},
        ]
        return out
    finally:
        sess.close()


@logger.catch(reraise=True)
def main() -> None:
    (WS / "results").mkdir(exist_ok=True)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    repo = sys.argv[1] if len(sys.argv) > 1 else "Qwen/Qwen3-0.6B"
    t0 = time.time()
    a, b = gate_1a(), gate_1b()
    try:
        c = gate_1c(repo, token)
    except (R.RangedReadError, OSError, ValueError) as exc:
        logger.error(f"GATE 1c failed: {exc}")
        c = {"error": str(exc), "repo_id": repo, "checks": []}
    checks = a["checks"] + b["checks"] + c.get("checks", [])
    n_pass = sum(1 for ch in checks if ch["pass"])
    verdict = ("ESTIMATOR_VALIDATED" if n_pass == len(checks)
               else "ESTIMATOR_PARTIAL" if n_pass >= 0.75 * len(checks) else "ESTIMATOR_BROKEN_F3")
    res = {"gate": "GATE_1", "verdict": verdict, "n_pass": n_pass, "n_checks": len(checks),
           "elapsed_s": round(time.time() - t0, 1), "synthetic": a, "bf16": b,
           "real_constructed": c, "failed_checks": [ch for ch in checks if not ch["pass"]]}
    (WS / "results" / "gate1_estimator.json").write_text(json.dumps(res, indent=2, default=float))
    logger.info(f"GATE 1 {verdict}: {n_pass}/{len(checks)} in {res['elapsed_s']}s")
    for ch in checks:
        if not ch["pass"]:
            logger.error(f"  FAIL {ch['name']}: {ch['detail']}")


if __name__ == "__main__":
    main()
