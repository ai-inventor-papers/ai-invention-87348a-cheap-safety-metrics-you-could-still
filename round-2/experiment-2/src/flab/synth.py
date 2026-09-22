"""GATE 1 + GATE 2: synthetic reproduction of the weight statistic, and its null.

No model is loaded here. A synthetic stack with a known spectrum is edited in
known ways and the statistics of :mod:`flab.wstats` must reproduce the table the
hypothesis stage simulated. If they do not, the implementation is wrong -- this
gate exists so that a later negative result cannot be blamed on the theory.

GATE 2 rebuilds every synthetic layer as ``U diag(s) V^T`` with Haar-random U, V
and the SAME singular values. If BSA is high on that null, the statistic is
reading the spectrum rather than the sharing, and the whole detection axis is
suspect before a single byte is downloaded.
"""

from __future__ import annotations

import numpy as np
import torch
from loguru import logger

from flab.config import BSA_WINDOW, SEED
from flab.wstats import (
    LayerSpectrum,
    cross_layer_cosine,
    jorak_score,
    layer_spectrum,
    windowed_subspace_alignment,
)

D_MODEL = 256
D_IN = 1024
N_LAYERS = 28


def _spectrum(kind: str, k: int, rng: np.random.Generator) -> np.ndarray:
    """Singular-value profile. 'gaussian' = Marchenko-Pastur-ish, 'heavy' = power law."""
    if kind == "gaussian":
        A = rng.standard_normal((D_MODEL, D_IN)) / np.sqrt(D_IN)
        return np.linalg.svd(A, compute_uv=False)
    idx = np.arange(1, k + 1, dtype=np.float64)
    s = idx ** (-0.7)
    return s / s[0]


def _build_layer(svals: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    k = min(D_MODEL, D_IN)
    U = np.linalg.qr(rng.standard_normal((D_MODEL, k)))[0]
    V = np.linalg.qr(rng.standard_normal((D_IN, k)))[0]
    return (U * svals[:k][None, :]) @ V.T


def _stack(kind: str, rng: np.random.Generator) -> list[np.ndarray]:
    sv = _spectrum(kind, min(D_MODEL, D_IN), rng)
    return [_build_layer(sv, rng) for _ in range(N_LAYERS)]


def _correlated_dirs(n: int, target_cos: float, rng: np.random.Generator) -> list[np.ndarray]:
    """n unit vectors in R^D_MODEL with mean pairwise |cos| ~ target_cos.

    Built as ``normalize(a*shared + sqrt(1-a^2)*indep)``; for near-orthogonal
    independent parts the pairwise cosine concentrates at a^2, so a = sqrt(c).
    """
    a = float(np.sqrt(np.clip(target_cos, 0.0, 1.0)))
    shared = rng.standard_normal(D_MODEL)
    shared /= np.linalg.norm(shared)
    out = []
    for _ in range(n):
        e = rng.standard_normal(D_MODEL)
        e -= (e @ shared) * shared
        e /= np.linalg.norm(e)
        v = a * shared + np.sqrt(max(0.0, 1.0 - a * a)) * e
        out.append(v / np.linalg.norm(v))
    return out


def _ablate(W: np.ndarray, r: np.ndarray, kappa: float) -> np.ndarray:
    """Partial directional ablation W' = (I - kappa r r^T) W. kappa=1 is a true projection."""
    return W - kappa * np.outer(r, r @ W)


def _specs(mats: list[np.ndarray], device: str) -> list[LayerSpectrum]:
    return [
        layer_spectrum(torch.from_numpy(W.astype(np.float32)), i, "synthetic", device=device)
        for i, W in enumerate(mats)
    ]


def _bsa(mats: list[np.ndarray], device: str, window: int = BSA_WINDOW) -> tuple[float, float, float, float]:
    sp = _specs(mats, device)
    bots = [s.bottom_k1 for s in sp]
    return (
        windowed_subspace_alignment(bots, window),
        jorak_score(bots),
        float(np.median([s.botgap for s in sp])),
        cross_layer_cosine(bots),
    )


def run_gate1(device: str = "cuda") -> dict:
    """Reproduce the simulated table. Returns every measured number."""
    rng = np.random.default_rng(SEED)
    res: dict[str, object] = {"n_layers": N_LAYERS, "d_model": D_MODEL, "d_in": D_IN,
                              "window": BSA_WINDOW}
    rows: list[dict] = []

    for kind in ("gaussian", "heavy"):
        mats = _stack(kind, rng)
        bsa, jor, bot, xcos = _bsa(mats, device)
        rows.append({"arm": f"honest_{kind}", "bsa_w8": bsa, "jorak": jor,
                     "botgap": bot, "xlayer_cos": xcos,
                     "expected_bsa": 0.168 if kind == "gaussian" else 0.177})

        # shared-direction abliteration, all layers, at three strengths
        r = rng.standard_normal(D_MODEL)
        r /= np.linalg.norm(r)
        for kappa, exp in ((1.0, 1.000), (0.7, 0.95), (0.3, 0.62)):
            ed = [_ablate(W, r, kappa) for W in mats]
            bsa, jor, bot, xcos = _bsa(ed, device)
            rows.append({"arm": f"shared_kappa{kappa}_{kind}", "bsa_w8": bsa, "jorak": jor,
                         "botgap": bot, "xlayer_cos": xcos,
                         "expected_bsa": exp if kind == "heavy" or kappa != 0.3 else exp})

        if kind != "heavy":
            continue

        # 50% layer band at full strength: windowing is the whole point
        half = N_LAYERS // 2
        ed = [_ablate(W, r, 1.0) if i < half else W for i, W in enumerate(mats)]
        bsa, jor, bot, xcos = _bsa(ed, device)
        rows.append({"arm": "band50_heavy", "bsa_w8": bsa, "jorak": jor, "botgap": bot,
                     "xlayer_cos": xcos, "expected_bsa": 1.000, "expected_jorak": 0.105})

        # INDEPENDENT per-layer directions -- the negative control, expected BLIND
        dirs = [rng.standard_normal(D_MODEL) for _ in range(N_LAYERS)]
        dirs = [d / np.linalg.norm(d) for d in dirs]
        ed = [_ablate(W, d, 1.0) for W, d in zip(mats, dirs)]
        bsa, jor, bot, xcos = _bsa(ed, device)
        rows.append({"arm": "independent_heavy", "bsa_w8": bsa, "jorak": jor, "botgap": bot,
                     "xlayer_cos": xcos, "expected_bsa": 0.17})

        # correlated per-layer directions: monotone in the cross-layer cosine
        for c, exp in ((0.81, 0.81), (0.65, 0.67), (0.48, 0.53), (0.25, 0.36)):
            dirs = _correlated_dirs(N_LAYERS, c, rng)
            ed = [_ablate(W, d, 1.0) for W, d in zip(mats, dirs)]
            bsa, jor, bot, xcos = _bsa(ed, device)
            rows.append({"arm": f"corr_cos{c}_heavy", "bsa_w8": bsa, "jorak": jor,
                         "botgap": bot, "xlayer_cos": xcos, "expected_bsa": exp})

        # BOTGAP in fp32 vs bf16: a projected matrix is algebraically singular in
        # fp32 but bf16 rounding lifts it off zero. This fixes the bf16 separator.
        ed = [_ablate(W, r, 1.0) for W in mats]
        sp32 = _specs(ed, device)
        bot32 = float(np.median([s.botgap for s in sp32]))
        sp16 = [
            layer_spectrum(
                torch.from_numpy(W.astype(np.float32)).to(torch.bfloat16).to(torch.float32),
                i, "synthetic", device=device,
            )
            for i, W in enumerate(ed)
        ]
        bot16 = float(np.median([s.botgap for s in sp16]))
        res["botgap_projected_fp32"] = bot32
        res["botgap_projected_bf16"] = bot16
        res["botgap_expected_fp32"] = 0.000
        res["botgap_expected_bf16"] = 0.010

    res["rows"] = rows

    # Verdicts: qualitative reproduction criteria, stated in advance.
    by = {r["arm"]: r for r in rows}
    checks = {
        "honest_gaussian_in_range": 0.10 <= by["honest_gaussian"]["bsa_w8"] <= 0.30,
        "honest_heavy_in_range": 0.10 <= by["honest_heavy"]["bsa_w8"] <= 0.30,
        "full_share_saturates": by["shared_kappa1.0_heavy"]["bsa_w8"] >= 0.98,
        "independent_is_blind": by["independent_heavy"]["bsa_w8"] <= 0.30,
        "band50_windowing_gain": (
            by["band50_heavy"]["bsa_w8"] >= 0.95
            and by["band50_heavy"]["jorak"] <= 0.30
        ),
        "correlated_monotone": (
            by["corr_cos0.81_heavy"]["bsa_w8"]
            > by["corr_cos0.65_heavy"]["bsa_w8"]
            > by["corr_cos0.48_heavy"]["bsa_w8"]
            > by["corr_cos0.25_heavy"]["bsa_w8"]
        ),
        "botgap_projection_collapses": res["botgap_projected_fp32"] < 0.05,
        "botgap_bf16_not_algebraic_zero": res["botgap_projected_bf16"] > 0.0,
        "botgap_honest_high": by["honest_heavy"]["botgap"] >= 0.90,
    }
    res["checks"] = checks
    res["passed"] = bool(all(checks.values()))
    for k, v in checks.items():
        logger.info(f"GATE1 {k}: {v}")
    return res


def run_gate2(device: str = "cuda") -> dict:
    """Anisotropy-matched null: same singular values, Haar-random subspaces."""
    rng = np.random.default_rng(SEED + 1)
    out: dict[str, object] = {}
    for kind in ("gaussian", "heavy"):
        sv = _spectrum(kind, min(D_MODEL, D_IN), rng)
        mats = [_build_layer(sv, rng) for _ in range(N_LAYERS)]
        bsa, jor, bot, xcos = _bsa(mats, device)
        out[f"null_{kind}"] = {"bsa_w8": bsa, "jorak": jor, "botgap": bot, "xlayer_cos": xcos}
    out["checks"] = {
        "null_gaussian_in_honest_range": out["null_gaussian"]["bsa_w8"] <= 0.30,
        "null_heavy_in_honest_range": out["null_heavy"]["bsa_w8"] <= 0.30,
    }
    out["passed"] = bool(all(out["checks"].values()))
    logger.info(f"GATE2 null BSA gaussian={out['null_gaussian']['bsa_w8']:.4f} "
                f"heavy={out['null_heavy']['bsa_w8']:.4f} passed={out['passed']}")
    return out
