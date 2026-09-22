"""STAGE 0 + STAGE 1 -- pure-numpy unit tests, no model, seconds.

Nothing downloads a panel until these pass.  The cross-fitting demonstration is
LOAD-BEARING: if it does not reproduce, the fold machinery is wired wrong and
every fitted-direction metric in the run is invalid.
"""

from __future__ import annotations

import numpy as np
import torch
from loguru import logger

from .common import BOTGAP_SEPARATOR, BSA_THRESHOLD, SEED
from .reads import botgap, crossfit_projection, insample_projection, safe_auc, windowed_subspace_alignment


def _bot_vecs_from_W(W: np.ndarray, k: int = 1) -> np.ndarray:
    G = W @ W.T
    _, V = np.linalg.eigh(G)
    return V[:, :k].T


def _sv(W: np.ndarray) -> np.ndarray:
    G = W @ W.T
    return np.sqrt(np.clip(np.linalg.eigvalsh(G), 0, None))[::-1]


def stage0_crossfitting(d: int = 2560, n: int = 64, seed: int = SEED) -> dict:
    """PURE NOISE must separate at AUROC ~1.000 in-sample and ~0.5 cross-fitted."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, d))
    y = (np.arange(n) % 2).astype(int)
    rng.shuffle(y)
    folds = np.arange(n) % 5
    a_in = safe_auc(y, insample_projection(X, y))
    a_cf = safe_auc(y, crossfit_projection(X, y, folds))
    ok = a_in > 0.95 and 0.30 < a_cf < 0.70
    return {"check": "cross_fitting_on_pure_noise", "d": d, "n_items": n,
            "in_sample_auroc": a_in, "cross_fitted_auroc": a_cf,
            "expected": "in-sample ~1.000, cross-fitted ~0.507", "pass": bool(ok)}


def stage0_weight_instrument(d: int = 256, fan_in: int = 1024, n_layers: int = 28,
                             window: int = 8, seed: int = SEED) -> dict:
    """Synthetic weight edits: BSA_w8 and BOTGAP on matrices we control."""
    rng = np.random.default_rng(seed)
    res: dict = {"check": "weight_instrument_on_synthetic_edits",
                 "d": d, "fan_in": fan_in, "n_layers": n_layers, "window": window}

    def _honest(heavy: bool) -> list[np.ndarray]:
        Ws = []
        for _ in range(n_layers):
            W = rng.standard_normal((d, fan_in)) / np.sqrt(fan_in)
            if heavy:
                s = rng.standard_t(2.0, size=(d, 1))
                W = W * np.abs(s)
            Ws.append(W)
        return Ws

    for name, heavy in (("gaussian", False), ("heavy_tailed", True)):
        Ws = _honest(heavy)
        V = np.stack([_bot_vecs_from_W(W) for W in Ws])
        res[f"bsa_w8_honest_{name}"] = windowed_subspace_alignment(V, window)
        res[f"botgap_honest_{name}"] = float(np.nanmin(botgap(np.stack([_sv(W) for W in Ws]))))

    Ws = _honest(False)
    v = rng.standard_normal(d)
    v /= np.linalg.norm(v)
    P = np.eye(d) - np.outer(v, v)

    for alpha, tag in ((1.0, "full_strength"), (0.7, "weight_0p7")):
        E = [(np.eye(d) - alpha * np.outer(v, v)) @ W for W in Ws]
        res[f"bsa_w8_abliterated_{tag}"] = windowed_subspace_alignment(
            np.stack([_bot_vecs_from_W(W) for W in E]), window)

    half = [P @ W if i < n_layers // 2 else W for i, W in enumerate(Ws)]
    res["bsa_w8_abliterated_50pct_band"] = windowed_subspace_alignment(
        np.stack([_bot_vecs_from_W(W) for W in half]), window)

    per_layer_rand = []
    for W in Ws:
        u = rng.standard_normal(d)
        u /= np.linalg.norm(u)
        per_layer_rand.append((np.eye(d) - np.outer(u, u)) @ W)
    res["bsa_w8_per_layer_random_edit"] = windowed_subspace_alignment(
        np.stack([_bot_vecs_from_W(W) for W in per_layer_rand]), window)
    res["per_layer_random_note"] = (
        "BLIND by construction, and expected: BSA reads SHARING across layers, "
        "so a per-layer-random edit is invisible to it.  BOTGAP catches it instead.")

    Wp = P @ Ws[0]
    res["botgap_projected_fp32"] = float(botgap(_sv(Wp)[None, :])[0])
    Wb = torch.tensor(Wp).to(torch.bfloat16).to(torch.float32).numpy()
    res["botgap_projected_bf16"] = float(botgap(_sv(Wb)[None, :])[0])
    res["botgap_per_layer_random_edit"] = float(np.nanmin(
        botgap(np.stack([_sv(W) for W in per_layer_rand]))))

    res["pass"] = bool(
        res["bsa_w8_honest_gaussian"] < BSA_THRESHOLD
        and res["bsa_w8_honest_heavy_tailed"] < BSA_THRESHOLD
        and res["bsa_w8_abliterated_full_strength"] > 0.9
        and res["bsa_w8_abliterated_weight_0p7"] > 0.8
        and res["bsa_w8_abliterated_50pct_band"] > 0.9
        and res["bsa_w8_per_layer_random_edit"] < BSA_THRESHOLD
        and res["botgap_honest_gaussian"] > 0.9
        and res["botgap_projected_bf16"] < BOTGAP_SEPARATOR
        and res["botgap_per_layer_random_edit"] < BOTGAP_SEPARATOR)
    res["spectrum_invariance_note"] = (
        "The honest BSA_w8 must be the SAME for a Gaussian and a heavy-tailed spectrum. "
        "That invariance is the whole reason this statistic replaced the raw Gram, whose "
        "honest value swings with the spectrum.")
    return res


def stage3_instrument_on_real_weights(model, device: str, window: int = 8,
                                      seed: int = SEED) -> dict:
    """STAGE 3 GO/NO-GO: validate the instrument on REAL trained weights.

    We copy the real o_proj matrices and apply TWO edits OURSELVES -- a shared
    direction abliteration at full strength, and a rank-one injection -- then
    require BSA to rise and BOTGAP to collapse, with the UNEDITED real
    checkpoint sitting well below the threshold.  If the honest real-weight
    baseline is NOT below 0.35, take branch F5 NOW, before spending download
    budget: real networks may carry genuinely shared directions of their own.
    """
    from .harvest import _get_layers
    rng = np.random.default_rng(seed)
    layers = _get_layers(model)
    Ws = []
    for lyr in layers:
        m = getattr(getattr(lyr, "self_attn", None), "o_proj", None)
        if m is not None:
            Ws.append(m.weight.detach().to(device=device, dtype=torch.float32))
    d = Ws[0].shape[0]

    def _bot(Wl: list[torch.Tensor], k: int = 1) -> np.ndarray:
        out = []
        for W in Wl:
            G = W @ W.T
            _, V = torch.linalg.eigh(G)
            out.append(V[:, :k].T.cpu().numpy())
        return np.stack(out)

    def _botgap(Wl: list[torch.Tensor]) -> float:
        vals = []
        for W in Wl:
            s = torch.linalg.eigvalsh(W @ W.T).clamp(min=0).sqrt()
            vals.append(float(s[0] / s[1]) if s[1] > 0 else np.nan)
        return float(np.nanmin(vals))

    honest_bsa = windowed_subspace_alignment(_bot(Ws), window)
    honest_botgap = _botgap(Ws)

    v = torch.tensor(rng.standard_normal(d), dtype=torch.float32, device=device)
    v /= v.norm()
    P = torch.eye(d, device=device) - torch.outer(v, v)
    abl = [P @ W for W in Ws]
    abl_bsa = windowed_subspace_alignment(_bot(abl), window)
    abl_botgap = _botgap(abl)

    u = torch.tensor(rng.standard_normal(d), dtype=torch.float32, device=device)
    u /= u.norm()
    scale = float(torch.linalg.matrix_norm(Ws[0], 2))
    inj = [W + 2.0 * scale * torch.outer(u, u) @ W for W in Ws]
    inj_tsa = windowed_subspace_alignment(
        np.stack([_top1(W) for W in inj]), window)
    honest_tsa = windowed_subspace_alignment(np.stack([_top1(W) for W in Ws]), window)

    out = {
        "check": "instrument_positive_control_on_REAL_weights",
        "n_layers": len(Ws), "d": d,
        "honest_bsa_w8": honest_bsa, "honest_botgap_min": honest_botgap,
        "abliterated_copy_bsa_w8": abl_bsa, "abliterated_copy_botgap_min": abl_botgap,
        "honest_tsa_top1": honest_tsa, "injected_copy_tsa_top1": inj_tsa,
        "bsa_threshold": BSA_THRESHOLD, "botgap_separator": BOTGAP_SEPARATOR,
    }
    out["pass"] = bool(honest_bsa < BSA_THRESHOLD and abl_bsa > 0.9
                       and abl_botgap < BOTGAP_SEPARATOR and honest_botgap > 0.5)
    out["branch"] = "OK" if out["pass"] else "F5_WITHDRAW_OR_DEMOTE_WEIGHT_INSTRUMENT"
    return out


def _top1(W: torch.Tensor) -> np.ndarray:
    G = W @ W.T
    _, V = torch.linalg.eigh(G)
    return V[:, -1:].T.cpu().numpy()


def run_stage0() -> dict:
    a = stage0_crossfitting()
    b = stage0_weight_instrument()
    logger.info(f"STAGE0 cross-fitting: in-sample {a['in_sample_auroc']:.3f} / "
                f"cross-fitted {a['cross_fitted_auroc']:.3f} -> {'PASS' if a['pass'] else 'FAIL'}")
    logger.info(f"STAGE0 weight instrument -> {'PASS' if b['pass'] else 'FAIL'}")
    return {"stage0_crossfitting": a, "stage0_weight_instrument": b,
            "all_pass": bool(a["pass"] and b["pass"])}
