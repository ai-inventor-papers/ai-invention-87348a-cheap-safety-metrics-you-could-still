"""STAGE 5.3 - the cheapest forgery against the weight detectors: a parent-free RANK-ONE SPECTRAL REPAIR.

Threat model: the forger holds ONLY the edited checkpoint (no parent, no prompts, no labels). For every
residual-write matrix whose bottom gap has collapsed (s0/s1 < `botgap_thresh`) they re-inflate the bottom
singular value:
        W' = W + (s_target - s0) * u0 v0^T
where (u0, s0, v0) is W's own bottom singular triple. This changes exactly ONE singular value and leaves every
singular vector untouched, so the repair is exact and its cost is one small-side eigendecomposition plus one
rank-one update per matrix. `target` controls s_target:
    "gap"   s_target = s1 * 1.0        (heals BOTGAP; the bottom DIRECTION stays u0 -> sharing stats unchanged)
    "swap"  s_target = (s1 + s2) / 2   (u0 leaves the bottom; the new bottom direction is u1 -> sharing stats heal)
    "bulk"  s_target = median singular value (u0 moves into the bulk -> also heals edge-keyed readouts such as RQ)
Pre-registered prediction (plan 5.3): the detector is healed and the behaviour is NOT, because the forger
never learns r^T W_parent - the component the abliteration actually removed - and so cannot put it back.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def bottom_triples(W: np.ndarray, k: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bottom-k singular triples of W (d_out x d_in) via eigh of the SMALL-side Gram, float64."""
    d_out, d_in = W.shape
    if d_in >= d_out:
        G = W @ W.T
        ev, U = np.linalg.eigh(0.5 * (G + G.T))
        s = np.sqrt(np.clip(ev[:k], 0.0, None))
        Uk = U[:, :k]
        Vk = W.T @ Uk
        n = np.linalg.norm(Vk, axis=0, keepdims=True)
        n[n == 0] = 1.0
        return s, Uk, Vk / n
    G = W.T @ W
    ev, V = np.linalg.eigh(0.5 * (G + G.T))
    s = np.sqrt(np.clip(ev[:k], 0.0, None))
    Vk = V[:, :k]
    Uk = W @ Vk
    n = np.linalg.norm(Uk, axis=0, keepdims=True)
    n[n == 0] = 1.0
    return s, Uk / n, Vk


def spectral_repair(W: np.ndarray, *, botgap_thresh: float = 0.1, target: str = "swap",
                    seed: int = 0) -> tuple[np.ndarray, dict[str, Any]]:
    """Return (W_repaired, info). No-op when the bottom gap has not collapsed."""
    s, U, V = bottom_triples(W, k=3)
    bg = float(s[0] / s[1]) if s[1] > 0 else float("nan")
    info: dict[str, Any] = {"botgap_before": bg, "s0": float(s[0]), "s1": float(s[1]), "s2": float(s[2]),
                            "repaired": False}
    if not np.isfinite(bg) or bg >= botgap_thresh:
        return W, info
    u0, v0 = U[:, 0], V[:, 0]
    if not np.all(np.isfinite(v0)) or np.linalg.norm(v0) < 0.5:
        rs = np.random.default_rng(seed)
        v0 = rs.standard_normal(W.shape[1])
        v0 /= np.linalg.norm(v0)
    if target == "gap":
        s_t = float(s[1])
    elif target == "swap":
        s_t = float(0.5 * (s[1] + s[2]))
    elif target == "bulk":
        # median singular value of W (defeats readouts that key on a direction sitting at the spectrum's
        # bottom EDGE in every layer, e.g. the pooled Rayleigh depression RQ)
        sv = np.linalg.svd(W, compute_uv=False)
        s_t = float(np.median(sv))
    else:
        raise ValueError(target)
    W2 = W + (s_t - float(s[0])) * np.outer(u0, v0)
    info.update({"repaired": True, "s_target": s_t, "eps": s_t - float(s[0]), "target": target,
                 "flops_rank_one_update": int(2 * W.shape[0] * W.shape[1])})
    return W2, info
