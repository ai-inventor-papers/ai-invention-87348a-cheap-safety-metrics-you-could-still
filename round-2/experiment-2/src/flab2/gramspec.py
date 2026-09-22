#!/usr/bin/env python3
"""Float64 Gram spectra, streamed one tensor at a time, and EXACT Gram updates.

Every weight statistic in this study reads the LEFT singular structure of a
residual-write matrix W (d_out x d_in), i.e. the eigen-structure of G = W W^T.
Three facts make the ladder affordable on a contended 2-CPU container:

  1. G is formed ONCE per layer in float64 with a symmetric rank-k update
     (BLAS dsyrk: half the flops of a general matmul). Float64 is not optional:
     a float32 Gram returned sigma_min = 0 exactly on honest OLMo-2 (true value
     1.7e-5), i.e. a manufactured 'abliterated' signature.
  2. Every weight rung of the ladder is a LOW-RANK LEFT/RIGHT modification of W,
     so the edited Gram is an O(d_out^2) update of G -- no new d_out x d_in
     product is ever formed:
        ROSI       W' = (I + c d 1^T) W          (w_bar^T = 1^T W / d_out)
                   G' = G + c d g1^T + c g1 d^T + c^2 (1^T G 1) d d^T,  g1 = G 1
        carrier    W' = W + u e_j^T
                   G' = G + u w_j^T + w_j u^T + u u^T,                  w_j = W e_j
     These are algebraic identities, checked numerically in `selftest()`.
  3. Matrices are read one at a time from the safetensors byte ranges and
     dropped after their Gram is formed, so resident memory is one layer.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh as _eigh
from scipy.linalg.blas import dsyrk

from . import repo_io as R
from . import wmetrics as W


def gram64(w: np.ndarray) -> np.ndarray:
    """G = W W^T in float64 via dsyrk on the transposed (Fortran-ordered) view."""
    w64 = np.asarray(w, dtype=np.float64)
    c = dsyrk(1.0, w64.T, trans=1, lower=0)          # upper triangle of W W^T
    g = np.triu(c)
    g = g + np.triu(g, 1).T
    return g


def spectrum_from_gram(g: np.ndarray, layer: int, name: str, d_out: int, d_in: int,
                       *, n_keep: int = 64, vectors: bool = True) -> W.LayerSpectrum:
    """The same LayerSpectrum `wmetrics.spectrum_of` returns, from a Gram."""
    if vectors:
        evals, evecs = _eigh(g, driver="evd")
    else:
        evals = _eigh(g, eigvals_only=True, driver="ev")
        evecs = np.zeros((d_out, 0))
    n_struct_zero = max(0, d_out - d_in)          # rank-deficient Gram (gemma o_proj)
    evals = np.asarray(evals)[n_struct_zero:]
    if evecs.shape[1] > 0:
        evecs = evecs[:, n_struct_zero:]
    k = int(min(n_keep, evals.shape[0]))
    s = np.sqrt(np.clip(evals.astype(np.float64), 0.0, None))[::-1]
    if evecs.shape[1] == 0:
        u_top = u_bot = np.zeros((d_out, 0))
    else:
        u_top = np.asarray(evecs[:, -k:], dtype=np.float64)[:, ::-1]
        u_bot = np.asarray(evecs[:, :k], dtype=np.float64)
    diag = np.clip(np.diag(g), 0.0, None)
    return W.LayerSpectrum(
        layer=layer, name=name, s=np.ascontiguousarray(s),
        u_top=np.ascontiguousarray(u_top), u_bot=np.ascontiguousarray(u_bot),
        d_out=int(d_out), d_in=int(d_in), fro=float(np.sqrt(np.trace(g))),
        row_mean_norm=float(np.mean(np.sqrt(diag))))


# ---------------------------------------------------------------------------
# exact Gram updates for the ladder's weight rungs
# ---------------------------------------------------------------------------

def rosi_gram(g: np.ndarray, direction: np.ndarray, mult: float,
              frob_fraction: float = 0.01) -> tuple[np.ndarray, float, float]:
    """Gram of W + alpha d w_bar^T, alpha = mult*frob_fraction*||W||_F/||w_bar||.

    Returns (G', alpha, ||Delta W||_F)."""
    m = g.shape[0]
    d = np.asarray(direction, dtype=np.float64).ravel()
    d = d / max(float(np.linalg.norm(d)), 1e-12)
    g1 = g.sum(axis=1)                               # G 1
    s11 = float(g1.sum())                            # 1^T G 1 = m^2 ||w_bar||^2
    fro = float(np.sqrt(np.trace(g)))
    wbar = np.sqrt(max(s11, 0.0)) / m
    alpha = mult * frob_fraction * fro / max(wbar, 1e-12)
    c = alpha / m
    gp = g + c * (np.outer(d, g1) + np.outer(g1, d)) + (c * c * s11) * np.outer(d, d)
    return gp, alpha, alpha * wbar


def column_gram(g: np.ndarray, w_j: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Gram of W + u e_j^T given column w_j = W e_j."""
    w_j = np.asarray(w_j, dtype=np.float64)
    u = np.asarray(u, dtype=np.float64)
    return g + np.outer(u, w_j) + np.outer(w_j, u) + np.outer(u, u)


# ---------------------------------------------------------------------------
# streaming base pass
# ---------------------------------------------------------------------------

def stream_host(snapshot: Path, *, keep_grams: bool = False,
                keep_columns: dict[int, int] | None = None,
                gram_dir: Path | None = None, log=None) -> dict:
    """Read o_proj / down_proj one tensor at a time -> spectra (+ Grams).

    keep_columns: {layer: j} -> also return down_proj column j of that layer.
    """
    index = R.build_index(snapshot)
    qr = R.quantization_reason(index)
    if qr:
        raise R.QuantizedCheckpoint(f"{snapshot.name}: {qr}")
    o_refs, d_refs = R.residual_write_refs(index)
    if not o_refs or not d_refs:
        raise ValueError(f"{snapshot}: no residual-write matrices")
    o_specs, d_specs, g_o, g_d = [], [], [], []
    cols: dict[int, np.ndarray] = {}
    t0 = time.time()
    mm_o = mm_d = None
    if gram_dir is not None:
        # write each Gram straight into an on-disk array: peak memory is ONE
        # layer, not the whole float64 stack (2.2 GB for gemma-2-2b)
        from numpy.lib.format import open_memmap
        L = len(o_refs)
        mm_o = open_memmap(gram_dir / "g_o.npy.part", mode="w+", dtype=np.float64,
                           shape=(L, o_refs[0].shape[0], o_refs[0].shape[0]))
        mm_d = open_memmap(gram_dir / "g_d.npy.part", mode="w+", dtype=np.float64,
                           shape=(L, d_refs[0].shape[0], d_refs[0].shape[0]))
    for li, (ro, rd) in enumerate(zip(o_refs, d_refs)):
        wo = R.read_tensor(ro)
        go = gram64(wo)
        o_specs.append(spectrum_from_gram(go, li, "o_proj", wo.shape[0], wo.shape[1]))
        if mm_o is not None:
            mm_o[li] = go
        elif keep_grams:
            g_o.append(go)
        del wo, go
        wd = R.read_tensor(rd)
        gd = gram64(wd)
        d_specs.append(spectrum_from_gram(gd, li, "down_proj", wd.shape[0], wd.shape[1],
                                          vectors=False))
        if keep_columns and li in keep_columns:
            cols[li] = np.asarray(wd[:, keep_columns[li]], dtype=np.float64).copy()
        if mm_d is not None:
            mm_d[li] = gd
        elif keep_grams:
            g_d.append(gd)
        del wd, gd
        if log is not None and li % 8 == 7:
            log(f"  streamed {li+1}/{len(o_refs)} layers ({time.time()-t0:.0f}s)")
    if mm_o is not None:
        mm_o.flush()
        mm_d.flush()
        del mm_o, mm_d
        (gram_dir / "g_o.npy.part").replace(gram_dir / "g_o.npy")
        (gram_dir / "g_d.npy.part").replace(gram_dir / "g_d.npy")
    return {"o_specs": o_specs, "d_specs": d_specs, "g_o": g_o, "g_d": g_d,
            "columns": cols, "index": index, "n_layers": len(o_refs),
            "o_shape": list(o_refs[0].shape), "d_shape": list(d_refs[0].shape),
            "total_bytes": int(sum(r.nbytes for r in index.values())),
            "seconds": round(time.time() - t0, 1)}


def selftest(seed: int = 0) -> dict:
    """The two update identities and the dsyrk Gram, against dense recomputation."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((40, 90)).astype(np.float32)
    g = gram64(w)
    dense = w.astype(np.float64) @ w.astype(np.float64).T
    e_gram = float(np.abs(g - dense).max())
    d = rng.standard_normal(40)
    gp, alpha, dn = rosi_gram(g, d, 3.0)
    w64 = w.astype(np.float64)
    wbar = w64.mean(axis=0)
    wp = w64 + alpha * np.outer(d / np.linalg.norm(d), wbar)
    e_rosi = float(np.abs(gp - wp @ wp.T).max() / np.abs(wp @ wp.T).max())
    e_dn = abs(dn - float(np.linalg.norm(wp - w64)))
    u = rng.standard_normal(40)
    j = 7
    gc = column_gram(g, w64[:, j], u)
    wc = w64.copy()
    wc[:, j] += u
    e_col = float(np.abs(gc - wc @ wc.T).max() / np.abs(wc @ wc.T).max())
    ok = e_gram < 1e-9 and e_rosi < 1e-10 and e_col < 1e-10 and e_dn < 1e-8
    return {"gram_max_abs_err": e_gram, "rosi_rel_err": e_rosi,
            "rosi_delta_norm_err": e_dn, "column_rel_err": e_col, "pass": bool(ok)}
