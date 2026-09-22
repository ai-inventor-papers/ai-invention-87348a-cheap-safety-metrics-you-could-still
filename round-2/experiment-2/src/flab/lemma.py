"""S5 THE LEMMA -- a constant residual offset is RANK-ZERO for a linear read at its layer.

STATED AS A LEMMA, NOT A FINDING. The general black-box form is already proved in
arXiv 2605.06324 Prop 4.1 and is cited as such. Adding an item-independent offset
``b`` to the residual stream at layer L is a rank-zero change to that layer's affine
map, so it cancels EXACTLY from any across-item statistic computed as a linear read
AT layer L, and only APPROXIMATELY from a read downstream of an RMSNorm.

This module verifies the exact arm in fp32, measures the downstream drift curve,
and -- critically -- fixes a PER-METRIC split-half tolerance ``tau_m`` that replaces
the single global 0.05 constant the hypothesis stage had been using.
"""

from __future__ import annotations

import time
from typing import Callable

import numpy as np
import torch
from loguru import logger

from flab.config import (
    EXACT_ARM_TOL,
    LINEAR_READ_TOL,
    OFFSET_MULTIPLES,
    SEED,
    SPLIT_HALF_REPS,
)
from flab.harvest import _get_layers, activation_pass, refusal_drive
from flab.metrics import harm_estimate, probe_layer


class ResidualOffset:
    """Context manager adding a constant ``b`` to the residual stream at hidden index L.

    ``hidden_states[k]`` is the output of decoder layer ``k-1``, so shifting
    ``hidden_states[L]`` means hooking decoder layer ``L-1``.
    """

    def __init__(self, model, hidden_idx: int, b: torch.Tensor):
        self.model = model
        self.layer = _get_layers(model)[hidden_idx - 1]
        self.b = b
        self.h = None

    def __enter__(self):
        bb = self.b

        def hook(_m, _inp, out):
            if isinstance(out, tuple):
                return (out[0] + bb.to(out[0].dtype).to(out[0].device),) + out[1:]
            return out + bb.to(out.dtype).to(out.device)

        self.h = self.layer.register_forward_hook(hook)
        return self

    def __exit__(self, *exc):
        if self.h is not None:
            self.h.remove()
        return False


def residual_scale(act: dict, layer: int) -> float:
    """Typical per-dimension residual magnitude at ``layer`` -- the unit for ||b||."""
    return float(np.median(np.abs(act["hs_last_prompt"][:, layer, :].astype(np.float64))))


def split_half_tolerance(
    metric_fn: Callable[[np.ndarray], float], n_items: int,
    reps: int = SPLIT_HALF_REPS, seed: int = SEED,
) -> float:
    """tau_m = 2 * sd(metric(half1) - metric(half2)) -- PER METRIC, not one global constant."""
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(reps):
        perm = rng.permutation(n_items)
        a, b = perm[: n_items // 2], perm[n_items // 2 :]
        va, vb = metric_fn(a), metric_fn(b)
        if np.isfinite(va) and np.isfinite(vb):
            diffs.append(va - vb)
    return float(2.0 * np.std(diffs)) if len(diffs) > 2 else float("nan")


def run_lemma(model, tok, items, *, device: str = "cuda", dtype_label: str = "fp32",
              batch_size: int = 8) -> dict:
    """GATE 4 + S5: exact arm, drift arm, and the per-metric tolerances."""
    t0 = time.time()
    base = activation_pass(model, tok, items, device=device, batch_size=batch_size)
    hs = base["hs_last_prompt"]
    pools = np.array(base["pools"])
    folds = np.array(base["folds"])
    L = probe_layer(hs.shape[1])
    d_model = hs.shape[2]
    scale = residual_scale(base, L)
    r_base = refusal_drive(base)
    h_base, _ = harm_estimate(hs, pools, folds, L)

    rng = np.random.default_rng(SEED)
    u = rng.standard_normal(d_model)
    u = u / np.linalg.norm(u)

    # ---- (iii) PER-METRIC split-half tolerances, measured on the UNEDITED host ----
    def _mk(fn):
        return lambda idx: fn(idx)

    taus = {
        "mean_r": split_half_tolerance(_mk(lambda i: float(np.nanmean(r_base[i]))), len(items)),
        "B1_logit_gap": split_half_tolerance(
            _mk(lambda i: float(np.nanmean(r_base[i][pools[i] == "H"]))), len(items)),
        "mean_h": split_half_tolerance(_mk(lambda i: float(np.nanmean(h_base[i]))), len(items)),
        "decision_spread": split_half_tolerance(
            _mk(lambda i: float(np.nanstd(r_base[i]))), len(items)),
    }

    # ---- (i) EXACT ARM -------------------------------------------------------
    b = torch.from_numpy((u * scale).astype(np.float32)).to(device)
    with ResidualOffset(model, L, b):
        off = activation_pass(model, tok, items, device=device, batch_size=batch_size)
    delta = off["hs_last_prompt"][:, L, :].astype(np.float64) - hs[:, L, :].astype(np.float64)
    resid = np.abs(delta - (u * scale)[None, :])
    exact_err = float(resid.max())
    h_off, _ = harm_estimate(off["hs_last_prompt"], pools, folds, L)
    ok = np.isfinite(h_base) & np.isfinite(h_off)
    linear_read_err = float(np.max(np.abs(h_off[ok] - h_base[ok]))) if ok.any() else float("nan")

    exact_pass = exact_err < EXACT_ARM_TOL
    linear_pass = linear_read_err < LINEAR_READ_TOL
    logger.info(
        f"[{dtype_label}] LEMMA exact arm max|dh-b|={exact_err:.3e} (tol {EXACT_ARM_TOL}), "
        f"linear read max|dh_i|={linear_read_err:.3e} (tol {LINEAR_READ_TOL})"
    )

    # ---- (ii) DRIFT ARM ------------------------------------------------------
    drift = []
    for mult in OFFSET_MULTIPLES:
        bb = torch.from_numpy((u * scale * mult).astype(np.float32)).to(device)
        with ResidualOffset(model, L, bb):
            o = activation_pass(model, tok, items, device=device, batch_size=batch_size)
        r_o = refusal_drive(o)
        h_o, _ = harm_estimate(o["hs_last_prompt"], pools, folds, L)
        row = {
            "multiple": mult,
            "norm_b": float(np.linalg.norm(u * scale * mult)),
            "d_mean_r": float(np.nanmean(r_o) - np.nanmean(r_base)),
            "d_B1_logit_gap": float(
                np.nanmean(r_o[pools == "H"]) - np.nanmean(r_base[pools == "H"])),
            "d_mean_h": float(np.nanmean(h_o) - np.nanmean(h_base)),
            "d_decision_spread": float(np.nanstd(r_o) - np.nanstd(r_base)),
        }
        row["invariant_B1"] = bool(abs(row["d_B1_logit_gap"]) < taus["B1_logit_gap"])
        drift.append(row)

    # CONFIRMATION SIGNAL: drift should SATURATE as ||b|| grows rather than diverge.
    mags = [abs(d["d_B1_logit_gap"]) for d in drift]
    saturates = bool(len(mags) >= 3 and (mags[-1] - mags[-2]) <= (mags[1] - mags[0]) + 1e-9)

    return {
        "dtype": dtype_label,
        "layer": L,
        "residual_scale": scale,
        "exact_arm_max_abs_error": exact_err,
        "exact_arm_tol": EXACT_ARM_TOL,
        "exact_arm_pass": exact_pass,
        "linear_read_max_abs_change": linear_read_err,
        "linear_read_tol": LINEAR_READ_TOL,
        "linear_read_pass": linear_pass,
        "tau_m": taus,
        "drift": drift,
        "drift_saturates": saturates,
        "seconds": round(time.time() - t0, 1),
        "citation": "general black-box form: arXiv 2605.06324 Prop 4.1",
    }
