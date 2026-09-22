#!/usr/bin/env python3
"""Zero-prompt weight metrics: the WL / WX half of the frozen 50-row battery.

Every statistic in this module reads ONLY `state_dict` tensors.  No tokenizer,
no forward pass, no parent model, no reference checkpoint.  That is the whole
point: these are the reads a blind auditor can perform on a repository they
just downloaded.

The bottom-subspace sharing statistic (BSA) is ADOPTED, not invented -- it is
the community model-scanner's subspace signature.  What this module adds is the
calibration it has never been given: a null model, an honest-panel false
positive rate on real trained weights, a rank-band sweep, and bf16-as-shipped
behaviour.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Spectral rank bands swept by the TSA variant.  A shared rank-one injection
# never reaches the top of a heavy-tailed spectrum, so the top-1 projector alone
# is the wrong read; the band sweep is what makes TSA sensitive to ROSI.
RANK_BANDS: tuple[int, ...] = (0, 1, 2, 4, 8, 16, 32, 64)

# Pre-registered separators INHERITED FROM ITERATION 1 (flab/config.py).  They
# are carried here so the output can report them, NOT so they can be used as
# operating thresholds: iteration 1 measured BSA_w8 = 0.565 on honest, unedited
# Qwen3-0.6B against this 0.35 separator, i.e. a 100% false-positive rate on
# real transformers.  Every headline number in this study is threshold-free.
BSA_PREREG_THRESHOLD = 0.35
BOTGAP_PREREG_THRESHOLD = 0.10


@dataclass
class LayerSpectrum:
    """Left singular structure of one residual-write matrix.

    `U` holds left singular vectors as COLUMNS, ordered by descending singular
    value, so `U[:, 0]` is the top direction and `U[:, -1]` the bottom one.
    """

    layer: int
    name: str
    s: np.ndarray                      # (k,) singular values, descending
    u_top: np.ndarray                  # (d_out, n_keep) leading left vectors
    u_bot: np.ndarray                  # (d_out, n_keep) trailing left vectors
    d_out: int = 0
    d_in: int = 0
    fro: float = 0.0
    row_mean_norm: float = 0.0
    extras: dict = field(default_factory=dict)


def _as_f32(t) -> np.ndarray:
    """Torch tensor or ndarray -> contiguous float32 numpy, always 2-D."""
    if hasattr(t, "detach"):
        t = t.detach().to("cpu")
        if hasattr(t, "float"):
            t = t.float()
        t = t.numpy()
    a = np.asarray(t, dtype=np.float32)
    if a.ndim != 2:
        raise ValueError(f"expected a 2-D weight matrix, got shape {a.shape}")
    return np.ascontiguousarray(a)


def bf16_round(a: np.ndarray) -> np.ndarray:
    """Round a float32 array to bfloat16 precision and back.

    bfloat16 is float32 with the low 16 mantissa bits cleared.  Round-to-nearest
    -even is implemented on the raw bit pattern so this needs no torch.
    """
    x = np.ascontiguousarray(a, dtype=np.float32).view(np.uint32)
    # round-to-nearest-even on the 16-bit boundary
    rounding = 0x7FFF + ((x >> 16) & 1)
    y = ((x.astype(np.uint64) + rounding) & 0xFFFF0000).astype(np.uint32)
    return y.view(np.float32).reshape(a.shape)


def spectrum_of(mat, layer: int, name: str, n_keep: int = 64,
                *, vectors: bool = True) -> LayerSpectrum:
    """SVD of one matrix, keeping only the leading and trailing subspaces.

    `mat` is an (d_out, d_in) nn.Linear weight.  Its LEFT singular vectors live
    in the residual stream, which is why they are the object a cross-layer
    sharing statistic compares.
    """
    w = _as_f32(mat)
    d_out, d_in = w.shape
    # The LEFT singular structure is all that is needed -- every statistic here
    # lives in the residual stream, which is the OUTPUT space. eigh of the Gram
    # W W^T gives exactly that (eigenvectors = left singular vectors,
    # eigenvalues = squared singular values) and never forms V, which for a
    # down_proj of shape (2560, 9728) is the dominant cost of a full SVD.
    # Iteration 1 measured eigh-vs-SVD agreement at max_abs_err 4.29e-06 and its
    # stored harvests were computed this way, so this also keeps the two panel
    # sources numerically identical.
    #
    # Two further economies, both of which matter on a box giving ~0.25 of a
    # core: the Gram and its decomposition are done in float32 (the statistics
    # are subspace angles and normalised spectra, not ill-conditioned solves),
    # and only the leading `n_keep` and trailing `n_keep` EIGENVECTORS are
    # requested. The full eigenvalue spectrum is still computed, because the
    # WL block needs it.
    # MEASURED on this box (1024x3072 down_proj, contended):
    #   numpy eigh (full)            17.1 s
    #   eigvalsh + 2 evr subsets     23.0 s   <- three tridiagonalisations
    #   scipy eigh driver='evd'      13.9 s   <- one, divide-and-conquer
    # The subset route loses because the tridiagonalisation, not the eigenvector
    # back-transform, dominates. One 'evd' call it is.
    # FLOAT64 GRAM (corrected 2026-09-21). A float32 Gram squares the condition
    # number into single precision: MEASURED on OLMo-2-0425-1B-Instruct o_proj
    # the true sigma_min is 1.7e-5..3e-4 against sigma_max 5-9, and the float32
    # Gram returned EXACTLY 0 for it (and a 2x-wrong second-smallest value), so
    # botgap read 0.000 -- the 'abliterated' signature -- on an honest model.
    # Every bottom-of-spectrum statistic is therefore computed in float64.
    w64 = w.astype(np.float64)
    g = w64 @ w64.T
    del w64
    k_req = int(min(n_keep, d_out))
    try:
        try:
            from scipy.linalg import eigh as _seigh

            if vectors:
                evals, evecs = _seigh(g, driver="evd")
            else:
                # VALUES ONLY. For `down_proj` in the honest panel the only
                # registry row is w_down_botgap_min, which reads the two
                # smallest singular values and no subspace at all -- and values
                # only is 2.2x cheaper than values-plus-vectors (6.2 s vs 13.9 s
                # measured here). The two down_proj SUBSPACE extensions are then
                # reported as NOT COMPUTED rather than silently dropped.
                evals = _seigh(g, eigvals_only=True, driver="ev")
                evecs = np.zeros((d_out, 0), dtype=np.float32)
        except (ImportError, ValueError, np.linalg.LinAlgError):
            if vectors:
                evals, evecs = np.linalg.eigh(g)
            else:
                evals = np.linalg.eigvalsh(g)
                evecs = np.zeros((d_out, 0), dtype=np.float32)
    except np.linalg.LinAlgError:
        u, sv, _ = np.linalg.svd(w.astype(np.float64), full_matrices=False)
        evals = (sv[::-1]) ** 2
        evecs = u[:, ::-1]
    # RANK-DEFICIENT GRAM (found 2026-09-21 on gemma-2-2b-it, whose o_proj is
    # (2304, 2048)): when d_out > d_in the Gram W W^T has d_out - d_in
    # STRUCTURAL zero eigenvalues, so the "bottom" left singular vectors are an
    # arbitrary basis of the null space of W^T and botgap is 0/0 = NaN. Those
    # directions carry no information about the matrix, so they are dropped and
    # every bottom-of-spectrum statistic reads the bottom of the NONZERO
    # spectrum. For d_out <= d_in (every other host here) this is a no-op.
    n_struct_zero = max(0, d_out - d_in) if np.asarray(evals).shape[0] == d_out else 0
    evals = np.asarray(evals)[n_struct_zero:]
    if evecs.shape[1] > 0:
        evecs = evecs[:, n_struct_zero:]
    k_req = int(min(k_req, evals.shape[0]))
    # eigh returns ASCENDING eigenvalues; singular values are the descending sqrt
    s = np.sqrt(np.clip(np.asarray(evals, dtype=np.float64), 0.0, None))[::-1]
    if evecs.shape[1] == 0:
        u_top_arr = u_bot_arr = np.zeros((d_out, 0), dtype=np.float64)
    else:
        u_top_arr = np.asarray(evecs[:, -k_req:], dtype=np.float64)[:, ::-1]
        u_bot_arr = np.asarray(evecs[:, :k_req], dtype=np.float64)
    return LayerSpectrum(
        layer=layer,
        name=name,
        s=np.ascontiguousarray(s, dtype=np.float64),
        u_top=np.ascontiguousarray(u_top_arr, dtype=np.float64),
        u_bot=np.ascontiguousarray(u_bot_arr, dtype=np.float64),
        d_out=int(d_out),
        d_in=int(d_in),
        fro=float(np.linalg.norm(w)),
        row_mean_norm=float(np.mean(np.linalg.norm(w, axis=1))),
    )


# --------------------------------------------------------------------------
# WX: across-layer relational statistics -- the detector class
# --------------------------------------------------------------------------

def _projector_eig(vecs: list[np.ndarray]) -> float:
    """Leading eigenvalue of the MEAN rank-k projector over a set of layers.

    Each element of `vecs` is (d, k) with orthonormal columns.  If every layer
    shares one direction the mean projector has a leading eigenvalue of 1; if
    the layers are independent and d is large it sits near k/d.  This is the
    sharing statistic.

    Computed through the SMALL Gram matrix rather than the d x d projector.
    With M = [V_1 ... V_L] of shape (d, m), m = L*k, the mean projector is
    (1/L) M M^T, whose nonzero eigenvalues are exactly those of the m x m
    matrix (1/L) M^T M.  For the operating point used here (m = 8, d = 1024 to
    2560) that is three orders of magnitude cheaper than eigvalsh on d x d, and
    it is EXACT, not an approximation -- the two matrices share their nonzero
    spectrum identically.
    """
    if not vecs or any(np.asarray(v).shape[1] == 0 for v in vecs):
        return float("nan")
    m = np.concatenate([np.asarray(v, dtype=np.float64) for v in vecs], axis=1)
    g = (m.T @ m) / float(len(vecs))
    ev = np.linalg.eigvalsh(g)
    return float(ev[-1])


def windowed_subspace_alignment(
    specs: list[LayerSpectrum], *, k: int = 1, window: int = 8, bottom: bool = True
) -> tuple[float, int]:
    """Max over contiguous `window`-layer blocks of the mean-projector eigenvalue.

    Returns (value, window_start_layer_index).  Windowing is what lets a
    HALF-STACK edit show up: an edit confined to 14 of 28 layers dilutes the
    full-stack statistic but saturates a window that lands inside the band.
    """
    if not specs:
        return float("nan"), -1
    mats = []
    for sp in specs:
        src = sp.u_bot if bottom else sp.u_top
        kk = min(k, src.shape[1])
        mats.append(np.ascontiguousarray(src[:, :kk]))
    n = len(mats)
    w = min(window, n)
    best, best_i = float("nan"), -1
    for i in range(0, n - w + 1):
        val = _projector_eig(mats[i : i + w])
        if np.isfinite(val) and (not np.isfinite(best) or val > best):
            best, best_i = val, i
    return float(best), int(best_i)


def full_stack_alignment(specs: list[LayerSpectrum], *, k: int = 1, bottom: bool = True) -> float:
    """The UNWINDOWED sharing statistic over the whole stack."""
    if not specs:
        return float("nan")
    mats = []
    for sp in specs:
        src = sp.u_bot if bottom else sp.u_top
        kk = min(k, src.shape[1])
        mats.append(np.ascontiguousarray(src[:, :kk]))
    return _projector_eig(mats)


def rank_band_alignment(
    specs: list[LayerSpectrum], *, window: int = 8, bands: tuple[int, ...] = RANK_BANDS
) -> dict:
    """Sweep the windowed TOP-subspace statistic over spectral rank bands.

    Band `b` means: skip the leading `b` singular directions, then take the next
    `max(1, b)` of them.  Band 0 is the plain top-1 read.  A rank-one injection
    at moderate alpha lands a few directions down a heavy-tailed spectrum, which
    is exactly why the plain top-1 read misses it and the band sweep does not.
    """
    out: dict[str, float] = {}
    best, best_band = -1.0, -1
    for b in bands:
        width = max(1, b)
        mats = []
        ok = True
        for sp in specs:
            if sp.u_top.shape[1] < b + width:
                ok = False
                break
            mats.append(np.ascontiguousarray(sp.u_top[:, b : b + width]))
        if not ok or not mats:
            out[f"band{b}"] = float("nan")
            continue
        n, w = len(mats), min(window, len(mats))
        bv = float("nan")
        for i in range(0, n - w + 1):
            v = _projector_eig(mats[i : i + w])
            if np.isfinite(v) and (not np.isfinite(bv) or v > bv):
                bv = v
        out[f"band{b}"] = float(bv) if np.isfinite(bv) else float("nan")
        if np.isfinite(bv) and bv > best:
            best, best_band = bv, b
    out["band_max"] = float(best) if best >= 0 else float("nan")
    out["band_argmax"] = float(best_band)
    return out


def cross_layer_cosine(specs: list[LayerSpectrum], *, bottom: bool = True) -> float:
    """Mean pairwise |cos| of per-layer bottom-1 (or top-1) left singular vectors.

    This is the axis on which the real abliteration census locates published
    checkpoints, so it is the axis the detector is graded in.
    """
    if len(specs) < 2 or any(
        (sp.u_bot if bottom else sp.u_top).shape[1] == 0 for sp in specs
    ):
        return float("nan")
    v = np.stack([(sp.u_bot if bottom else sp.u_top)[:, 0] for sp in specs])
    v = v / np.clip(np.linalg.norm(v, axis=1, keepdims=True), 1e-12, None)
    g = np.abs(v @ v.T)
    iu = np.triu_indices(len(specs), k=1)
    return float(np.mean(g[iu]))


def botgap(specs: list[LayerSpectrum]) -> dict:
    """sigma_min / sigma_{min-1}, per layer, plus its min and mid-band mean.

    A full-strength projection sends sigma_min algebraically to 0, so the ratio
    collapses.  It is NOT spectrum-invariant and it does NOT survive bf16 as
    shipped, both of which are reported rather than papered over.
    """
    vals, vals_bf16 = [], []
    for sp in specs:
        s = sp.s
        if s.shape[0] < 2:
            vals.append(float("nan"))
            vals_bf16.append(float("nan"))
            continue
        denom = float(s[-2])
        vals.append(float(s[-1] / denom) if denom > 0 else float("nan"))
        sb = np.sort(bf16_round(s.astype(np.float32)).astype(np.float64))[::-1]
        db = float(sb[-2])
        vals_bf16.append(float(sb[-1] / db) if db > 0 else float("nan"))
    arr = np.asarray(vals, dtype=np.float64)
    arrb = np.asarray(vals_bf16, dtype=np.float64)
    fin, finb = arr[np.isfinite(arr)], arrb[np.isfinite(arrb)]
    lo, hi = int(0.25 * len(arr)), int(0.75 * len(arr))
    mid = arr[lo:hi][np.isfinite(arr[lo:hi])]
    return {
        "per_layer": [None if not np.isfinite(x) else float(x) for x in arr],
        "min": float(np.min(fin)) if fin.size else float("nan"),
        "mid_mean": float(np.mean(mid)) if mid.size else float("nan"),
        "bf16_min": float(np.min(finb)) if finb.size else float("nan"),
        "frac_below": (
            float(np.mean(fin < BOTGAP_PREREG_THRESHOLD)) if fin.size else float("nan")
        ),
    }


# --------------------------------------------------------------------------
# WL: per-layer level statistics, zero-prompt
# --------------------------------------------------------------------------

def spectral_entropy(sp: LayerSpectrum) -> float:
    """Normalised Shannon entropy of the squared singular spectrum (in [0, 1])."""
    p = sp.s.astype(np.float64) ** 2
    tot = float(p.sum())
    if tot <= 0:
        return float("nan")
    p = p / tot
    p = p[p > 0]
    return float(-(p * np.log(p)).sum() / math.log(len(sp.s)))


def effective_rank(sp: LayerSpectrum) -> float:
    """exp(entropy of the normalised singular value distribution)."""
    p = sp.s.astype(np.float64)
    tot = float(p.sum())
    if tot <= 0:
        return float("nan")
    p = p / tot
    p = p[p > 0]
    return float(np.exp(-(p * np.log(p)).sum()))


def stable_rank(sp: LayerSpectrum) -> float:
    """||W||_F^2 / sigma_max^2."""
    s = sp.s.astype(np.float64)
    if s.size == 0 or s[0] <= 0:
        return float("nan")
    return float((s**2).sum() / s[0] ** 2)


def level_block(specs: list[LayerSpectrum]) -> dict:
    """Depth-pooled WL statistics plus their depth slope.

    The mid-band mean is used wherever a single number is wanted, because the
    first and last layers of a transformer are atypical in every spectrum
    statistic and pooling them in is what makes naive weight reads noisy.
    """
    if not specs:
        return {}
    n = len(specs)
    lo, hi = int(0.25 * n), max(int(0.75 * n), int(0.25 * n) + 1)
    depth = np.linspace(0.0, 1.0, n)

    def _pool(fn) -> dict:
        v = np.asarray([fn(sp) for sp in specs], dtype=np.float64)
        f = v[np.isfinite(v)]
        m = v[lo:hi][np.isfinite(v[lo:hi])]
        if f.size >= 2 and np.isfinite(v).all():
            slope = float(np.polyfit(depth, v, 1)[0])
        else:
            slope = float("nan")
        return {
            "mean": float(np.mean(f)) if f.size else float("nan"),
            "mid_mean": float(np.mean(m)) if m.size else float("nan"),
            "slope": slope,
        }

    top1_share = lambda sp: float(sp.s[0] ** 2 / max((sp.s**2).sum(), 1e-30))
    lowrank_k = lambda k: (
        lambda sp: float((sp.s[:k] ** 2).sum() / max((sp.s**2).sum(), 1e-30))
    )
    kurt = lambda sp: float(
        ((sp.s - sp.s.mean()) ** 4).mean() / max(sp.s.var() ** 2, 1e-30)
    )
    return {
        "top1_energy": _pool(top1_share),
        "eff_rank": _pool(effective_rank),
        "stable_rank": _pool(stable_rank),
        "spectral_entropy": _pool(spectral_entropy),
        "log_smax": _pool(lambda sp: float(np.log(max(sp.s[0], 1e-30)))),
        "smin_over_smax": _pool(
            lambda sp: float(sp.s[-1] / max(sp.s[0], 1e-30))
        ),
        "spectrum_kurtosis": _pool(kurt),
        "lowrank_k1": _pool(lowrank_k(1)),
        "lowrank_k4": _pool(lowrank_k(4)),
        "lowrank_k16": _pool(lowrank_k(16)),
        "row_mean_norm": _pool(lambda sp: sp.row_mean_norm),
        "fro": _pool(lambda sp: sp.fro),
    }


# --------------------------------------------------------------------------
# Nulls
# --------------------------------------------------------------------------

def haar_matched_null(
    d: int, n_layers: int, *, k: int = 1, window: int = 8, n_draw: int = 200, seed: int = 0
) -> dict:
    """Independent-random-direction null for the sharing statistic.

    Draws `n_layers` independent Haar-random orthonormal k-frames in R^d and
    reports the resulting windowed statistic.  This is the number an honest
    checkpoint would produce if its per-layer bottom subspaces were unrelated;
    the measured gap between it and a REAL honest transformer is the whole
    reason the published 0.35 separator false-positives.
    """
    rng = np.random.default_rng(seed)
    vals_w, vals_f = [], []
    for _ in range(n_draw):
        mats = []
        for _ in range(n_layers):
            a = rng.standard_normal((d, k))
            q, _ = np.linalg.qr(a)
            mats.append(q[:, :k])
        n, w = len(mats), min(window, len(mats))
        best = max(_projector_eig(mats[i : i + w]) for i in range(0, n - w + 1))
        vals_w.append(best)
        vals_f.append(_projector_eig(mats))
    aw, af = np.asarray(vals_w), np.asarray(vals_f)
    return {
        "windowed_mean": float(aw.mean()),
        "windowed_sd": float(aw.std(ddof=1)),
        "windowed_q95": float(np.quantile(aw, 0.95)),
        "windowed_q99": float(np.quantile(aw, 0.99)),
        "fullstack_mean": float(af.mean()),
        "fullstack_sd": float(af.std(ddof=1)),
        "n_draw": int(n_draw),
        "d": int(d),
        "n_layers": int(n_layers),
        "k": int(k),
        "window": int(window),
    }


def anisotropy_matched_z(
    specs: list[LayerSpectrum], *, k: int = 1, window: int = 8, n_draw: int = 200, seed: int = 0
) -> dict:
    """Within-checkpoint anisotropy-matched z for the windowed BSA statistic.

    The null direction for each layer is drawn from THAT LAYER'S OWN bottom-16
    subspace rather than from the isotropic sphere, so the null inherits the
    checkpoint's anisotropy.  200 draws, never best-of-20: a max over draws
    estimates a maximum, not a null mean, and iteration 1's best-of-20 null tied
    the fitted probe for exactly that reason.

    ITERATION 1 MEASURED THIS z FIRING HARDER ON HONEST WEIGHTS (25.4) THAN ON A
    REAL ABLITERATION (21.7), i.e. with the sign backwards, at n=2 honest and
    n=1 abliterated.  It is recomputed here on a real panel; the verdict is
    whatever the panel says.
    """
    if not specs:
        return {"z": float("nan"), "n_draw": 0}
    rng = np.random.default_rng(seed)
    pool = [np.ascontiguousarray(sp.u_bot[:, : min(16, sp.u_bot.shape[1])]) for sp in specs]
    obs, _ = windowed_subspace_alignment(specs, k=k, window=window, bottom=True)
    draws = []
    for _ in range(n_draw):
        mats = []
        for basis in pool:
            c = rng.standard_normal((basis.shape[1], k))
            v = basis @ c
            q, _ = np.linalg.qr(v)
            mats.append(q[:, :k])
        n, w = len(mats), min(window, len(mats))
        draws.append(max(_projector_eig(mats[i : i + w]) for i in range(0, n - w + 1)))
    a = np.asarray(draws, dtype=np.float64)
    sd = float(a.std(ddof=1))
    return {
        "observed": float(obs),
        "null_mean": float(a.mean()),
        "null_sd": sd,
        "null_q95": float(np.quantile(a, 0.95)),
        "null_q99": float(np.quantile(a, 0.99)),
        "z": float((obs - a.mean()) / sd) if sd > 1e-12 else float("nan"),
        "n_draw": int(n_draw),
    }


# --------------------------------------------------------------------------
# The public entry point
# --------------------------------------------------------------------------

def battery_from_specs(
    o_specs: list[LayerSpectrum], d_specs: list[LayerSpectrum], *,
    with_z: bool = True, seed: int = 0
) -> dict:
    """The whole zero-prompt weight block from already-computed spectra.

    Split out from `weight_battery` so the ladder can recompute the SVD of only
    the layers a rung actually edited and splice them into the base stack.  A
    rung confined to a 35% mid-stack band leaves 65% of the spectra untouched,
    and on a box whose load average is in the hundreds that saving is the
    difference between a complete ladder and a truncated one.
    """

    bsa_w8_k1, w8_at = windowed_subspace_alignment(o_specs, k=1, window=8)
    bsa_w8_k4, _ = windowed_subspace_alignment(o_specs, k=4, window=8)
    bsa_w4_k1, _ = windowed_subspace_alignment(o_specs, k=1, window=4)
    bsa_full = full_stack_alignment(o_specs, k=1)
    tsa_top1_w8, _ = windowed_subspace_alignment(o_specs, k=1, window=8, bottom=False)
    bands = rank_band_alignment(o_specs, window=8)
    bg_o = botgap(o_specs)
    bg_d = botgap(d_specs)

    out: dict = {
        # --- registry rows (weights, n_prompts = 0) -------------------------
        "w_bsa_w8_k1": bsa_w8_k1,
        "w_bsa_w8_k4": bsa_w8_k4,
        "w_crosslayer_cos": cross_layer_cosine(o_specs),
        "w_tsa_top1_w8": tsa_top1_w8,
        "w_tsa_band_max": bands["band_max"],
        "w_botgap_min": bg_o["min"],
        "w_botgap_frac_below": bg_o["frac_below"],
        "w_botgap_bf16_min": bg_o["bf16_min"],
        "w_down_botgap_min": bg_d["min"],
        "w_spectral_entropy": float(
            np.nanmean([spectral_entropy(sp) for sp in o_specs])
        ),
        # --- extensions, all derived from the SAME two SVD passes -----------
        "w_bsa_w4_k1": bsa_w4_k1,
        "w_bsa_fullstack_k1": bsa_full,
        "w_bsa_window_start": float(w8_at),
        "w_tsa_band_argmax": bands["band_argmax"],
        "w_crosslayer_cos_top": cross_layer_cosine(o_specs, bottom=False),
        "w_down_bsa_w8_k1": windowed_subspace_alignment(d_specs, k=1, window=8)[0],
        "w_down_crosslayer_cos": cross_layer_cosine(d_specs),
        "w_botgap_mid_mean": bg_o["mid_mean"],
        "w_windowing_gain": (
            bsa_w8_k1 - bsa_full if np.isfinite(bsa_w8_k1) and np.isfinite(bsa_full)
            else float("nan")
        ),
        "n_layers": float(len(o_specs)),
        "d_model": float(o_specs[0].d_out) if o_specs else float("nan"),
        "_bands": {k: v for k, v in bands.items() if k.startswith("band")},
        "_botgap_o": {k: v for k, v in bg_o.items() if k != "per_layer"},
        "_botgap_d": {k: v for k, v in bg_d.items() if k != "per_layer"},
    }

    for prefix, specs in (("wl_o", o_specs), ("wl_d", d_specs)):
        for stat, block in level_block(specs).items():
            for agg, val in block.items():
                out[f"{prefix}_{stat}_{agg}"] = val

    if with_z and o_specs and o_specs[0].u_bot.shape[1] > 0:
        z = anisotropy_matched_z(o_specs, k=1, window=8, n_draw=200, seed=seed)
        out["w_bsa_z"] = z["z"]
        out["_bsa_z_detail"] = z

    return out


def spectra_of(mats: list, name: str, n_keep: int = 64, *,
               vectors: bool = True) -> list[LayerSpectrum]:
    """Decompose every layer of one module stack."""
    return [spectrum_of(m, i, name, n_keep=n_keep, vectors=vectors)
            for i, m in enumerate(mats)]


def weight_battery(
    o_proj: list, down_proj: list, *, n_keep: int = 64, with_z: bool = True, seed: int = 0
) -> dict:
    """Compute the whole zero-prompt weight block from two lists of matrices.

    `o_proj[i]` / `down_proj[i]` are the attention-output and MLP-output
    projections of layer i -- the two residual-WRITE matrices, which is why
    they and not q/k/v are the ones a residual-stream edit shows up in.
    """
    return battery_from_specs(
        spectra_of(o_proj, "o_proj", n_keep),
        spectra_of(down_proj, "down_proj", n_keep),
        with_z=with_z, seed=seed,
    )


# --------------------------------------------------------------------------
# Spectra cache -- a restart must not pay for the base decomposition twice
# --------------------------------------------------------------------------

def save_specs(path, o_specs: list[LayerSpectrum], d_specs: list[LayerSpectrum]) -> None:
    """Persist both spectrum stacks to one compressed .npz.

    The base decomposition is the single most expensive thing in the ladder --
    on a contended core it is minutes per checkpoint -- and every restart was
    paying for it again. Caching it makes a restart free, which matters when the
    run is being steered around a clock.
    """
    import numpy as _np

    arrs: dict[str, _np.ndarray] = {}
    for tag, specs in (("o", o_specs), ("d", d_specs)):
        arrs[f"{tag}_n"] = _np.asarray([len(specs)])
        for i, sp in enumerate(specs):
            arrs[f"{tag}{i}_s"] = sp.s.astype(_np.float32)
            arrs[f"{tag}{i}_ut"] = sp.u_top.astype(_np.float32)
            arrs[f"{tag}{i}_ub"] = sp.u_bot.astype(_np.float32)
            arrs[f"{tag}{i}_m"] = _np.asarray(
                [sp.d_out, sp.d_in, sp.fro, sp.row_mean_norm], dtype=_np.float64)
    _np.savez_compressed(path, **arrs)


def load_specs(path) -> tuple[list[LayerSpectrum], list[LayerSpectrum]] | None:
    """Reload cached spectra, or None if the file is absent or unreadable."""
    import numpy as _np

    try:
        z = _np.load(path)
    except (OSError, ValueError, EOFError):
        return None
    out = []
    try:
        for tag, name in (("o", "o_proj"), ("d", "down_proj")):
            n = int(z[f"{tag}_n"][0])
            specs = []
            for i in range(n):
                m = z[f"{tag}{i}_m"]
                specs.append(LayerSpectrum(
                    layer=i, name=name,
                    s=z[f"{tag}{i}_s"].astype(_np.float64),
                    u_top=z[f"{tag}{i}_ut"].astype(_np.float64),
                    u_bot=z[f"{tag}{i}_ub"].astype(_np.float64),
                    d_out=int(m[0]), d_in=int(m[1]),
                    fro=float(m[2]), row_mean_norm=float(m[3])))
            out.append(specs)
    except KeyError:
        return None
    return out[0], out[1]
