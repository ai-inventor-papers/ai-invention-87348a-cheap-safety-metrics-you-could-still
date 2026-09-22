#!/usr/bin/env python3
"""Exact and Monte-Carlo one-sided permutation p-values for Spearman's rho.

The exact test enumerates the n! permutations of the y-labels relative to the
x-labels implicitly, via a subset dynamic programme over which y-items have
been consumed so far (a bitmask DP). Ties are handled with midranks, so the
underlying statistic ``S = sum_i a_i * b_{pi(i)}`` (with ``a_i = 2 *
midrank(x_i)``, ``b_j = 2 * midrank(y_j)``) is always an integer, which keeps
the DP's sum axis exact (no floating point tolerance needed there).

Since Spearman's rho is an increasing affine function of S for fixed margins
(fixed ``a`` and ``b`` multisets), thresholding on S is equivalent to
thresholding on rho, so the DP never needs to recompute a correlation
coefficient per permutation.
"""

from __future__ import annotations

import math
import sys
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import rankdata

logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")

_TOL = 1e-9
_MAX_EXACT_N = 13


def _validate_sign(sign: float) -> int:
    """Validate and normalise the one-sided direction flag.

    Args:
        sign: +1 for the "greater or equal" alternative, -1 for "less or
            equal".

    Returns:
        The sign as a plain int (+1 or -1).

    Raises:
        ValueError: If ``sign`` is not +1 or -1.
    """
    if sign not in (1, -1, 1.0, -1.0):
        raise ValueError(f"sign must be +1 or -1, got {sign!r}")
    return int(sign)


def _validate_xy(x: np.ndarray, y: np.ndarray) -> int:
    """Validate paired input arrays and return their common length.

    Args:
        x: First sample.
        y: Second sample, paired with ``x`` by index.

    Returns:
        The common length ``n``.

    Raises:
        ValueError: If shapes disagree, arrays are not 1-D, or n < 2.
    """
    if x.ndim != 1 or y.ndim != 1:
        raise ValueError("x and y must be 1-D arrays")
    if x.shape[0] != y.shape[0]:
        raise ValueError(f"x and y must have equal length, got {x.shape[0]} vs {y.shape[0]}")
    n = int(x.shape[0])
    if n < 2:
        raise ValueError(f"n must be >= 2, got {n}")
    return n


def _midrank_int_ranks(v: np.ndarray) -> np.ndarray:
    """Return ``2 * midrank(v)`` as exact int64 values.

    Midranks (average of tied ranks) are half-integers at worst, so doubling
    them always yields an integer; ``np.rint`` removes floating-point noise
    before casting.

    Args:
        v: 1-D array of values.

    Returns:
        int64 array of the same length as ``v``.
    """
    midranks = rankdata(v, method="average")
    doubled = np.rint(midranks * 2.0)
    return doubled.astype(np.int64)


def _spearman_rho_from_ranks(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation of two (mid)rank vectors == Spearman's rho.

    Args:
        a: Rank-like vector (need not be scaled/doubled; any affine scaling
            of a valid rank vector gives the same correlation).
        b: Rank-like vector, same length as ``a``.

    Returns:
        The correlation coefficient as a Python float. Returns 0.0 in the
        degenerate case where either vector is constant (zero variance).
    """
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    n = a.shape[0]
    a_mean = a.mean()
    b_mean = b.mean()
    a_c = a - a_mean
    b_c = b - b_mean
    denom = math.sqrt(float(np.sum(a_c * a_c)) * float(np.sum(b_c * b_c)))
    if denom == 0.0:
        return 0.0
    return float(np.sum(a_c * b_c) / denom)


def exact_perm_p_spearman(x: np.ndarray, y: np.ndarray, sign: float) -> dict[str, Any]:
    """Exact one-sided permutation p-value of Spearman's rho via subset DP.

    Enumerates all ``n!`` permutations of the y-side ranks relative to the
    x-side ranks implicitly, using a bitmask dynamic programme: ``dp[mask]``
    holds the distribution (as counts, indexed by an integer sum offset) of
    the partial statistic ``S = sum_{i<popcount(mask)} a_i * b_{sigma(i)}``
    over all ways of injectively assigning the y-indices in ``mask`` to the
    first ``popcount(mask)`` x-positions, in x-order. Midranks make
    ``a_i = 2*midrank(x_i)`` and ``b_j = 2*midrank(y_j)`` integers, so ``S``
    is an exact integer and no floating tolerance is needed for the count
    comparison.

    Because integer mask values only increase when a bit is added, iterating
    ``mask`` from 0 to ``2**n - 1`` guarantees every predecessor of a mask is
    processed before the mask itself, so a single forward pass suffices. Each
    processed mask's array is freed immediately afterwards to bound peak
    memory (only the "frontier" of not-yet-fully-processed masks stays
    resident).

    Args:
        x: First sample, length n (n <= 13).
        y: Second sample, length n, paired with x by index.
        sign: +1 tests P(rho_perm >= rho_obs); -1 tests P(rho_perm <=
            rho_obs).

    Returns:
        dict with keys: "p" (float), "n" (int), "method"
        ("exact_subset_dp"), "rho_obs" (float), "n_perms" (int, = n!).

    Raises:
        ValueError: If n > 13, n < 2, sign is not +-1, or shapes disagree.
    """
    sign_i = _validate_sign(sign)
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n = _validate_xy(x, y)
    if n > _MAX_EXACT_N:
        raise ValueError(f"exact_perm_p_spearman only supports n <= {_MAX_EXACT_N}, got n={n}")

    a = _midrank_int_ranks(x)
    b = _midrank_int_ranks(y)
    rho_obs = _spearman_rho_from_ranks(a.astype(np.float64), b.astype(np.float64))

    s_obs = int(np.sum(a * b))

    n_perms = math.factorial(n)
    full_mask = (1 << n) - 1

    # dp[mask] = (offset, counts_array) where counts_array[k] is the number
    # of ways (partial-assignment orderings) to reach partial sum
    # (offset + k) having assigned the y-indices set in `mask` to the first
    # popcount(mask) x-positions (in x-order).
    dp: list[tuple[int, np.ndarray] | None] = [None] * (1 << n)
    dp[0] = (0, np.array([1.0], dtype=np.float64))

    b_list = [int(v) for v in b]  # plain ints: faster inner-loop arithmetic than np scalars

    for mask in range(1 << n):
        entry = dp[mask]
        if entry is None:
            continue
        offset, counts = entry
        k = bin(mask).count("1")
        if k == n:
            # Full assignment reached (only true for mask == full_mask):
            # keep it resident, it is the final answer read after the loop.
            continue
        ai = int(a[k])
        for j in range(n):
            bit = 1 << j
            if mask & bit:
                continue
            add = ai * b_list[j]
            new_mask = mask | bit
            new_offset = offset + add
            existing = dp[new_mask]
            if existing is None:
                dp[new_mask] = (new_offset, counts.copy())
            else:
                off2, arr2 = existing
                lo = min(new_offset, off2)
                hi = max(new_offset + counts.shape[0] - 1, off2 + arr2.shape[0] - 1)
                merged = np.zeros(hi - lo + 1, dtype=np.float64)
                merged[new_offset - lo : new_offset - lo + counts.shape[0]] += counts
                merged[off2 - lo : off2 - lo + arr2.shape[0]] += arr2
                dp[new_mask] = (lo, merged)
        dp[mask] = None  # free: fully propagated to children, no longer needed

    final_offset, final_counts = dp[full_mask]
    sums = final_offset + np.arange(final_counts.shape[0])

    if sign_i == 1:
        mask_ge = sums >= (s_obs - _TOL)
        count = float(np.sum(final_counts[mask_ge]))
    else:
        mask_le = sums <= (s_obs + _TOL)
        count = float(np.sum(final_counts[mask_le]))

    total = float(np.sum(final_counts))
    if abs(total - n_perms) > max(1.0, n_perms * 1e-9):
        logger.warning(f"DP total count {total} != n! {n_perms} (n={n})")

    p = count / n_perms

    logger.debug(
        f"exact_perm_p_spearman n={n} sign={sign_i} rho_obs={rho_obs:.6f} "
        f"S_obs={s_obs} p={p:.10g}"
    )

    return {
        "p": p,
        "n": n,
        "method": "exact_subset_dp",
        "rho_obs": rho_obs,
        "n_perms": n_perms,
    }


def mc_perm_p_spearman(
    x: np.ndarray,
    y: np.ndarray,
    sign: float,
    n_mc: int,
    seed: int = 20260921,
    batch: int = 200000,
) -> dict[str, Any]:
    """Monte-Carlo one-sided permutation p-value of Spearman's rho.

    Draws ``n_mc`` random permutations of the y-side (mid)ranks, computes the
    Spearman correlation against the fixed x-side (mid)ranks for each in a
    vectorised, batched fashion, and reports both the raw proportion and the
    standard ``(b+1)/(m+1)`` bias-corrected p-value (Davison & Hinkley 1997),
    which is always strictly positive and is the value that should be used
    for inference.

    Args:
        x: First sample, length n.
        y: Second sample, length n, paired with x by index.
        sign: +1 tests P(rho_perm >= rho_obs); -1 tests P(rho_perm <=
            rho_obs).
        n_mc: Number of Monte-Carlo permutation draws.
        seed: RNG seed for reproducibility.
        batch: Number of permutations generated per vectorised batch.

    Returns:
        dict with keys: "p" (float, corrected), "p_uncorrected" (float),
        "n_mc" (int), "method" ("monte_carlo_(b+1)/(m+1)"), "rho_obs"
        (float), "n" (int).

    Raises:
        ValueError: If n_mc < 1, sign is not +-1, or shapes disagree.
    """
    sign_i = _validate_sign(sign)
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n = _validate_xy(x, y)
    if n_mc < 1:
        raise ValueError(f"n_mc must be >= 1, got {n_mc}")
    if batch < 1:
        raise ValueError(f"batch must be >= 1, got {batch}")

    a = rankdata(x, method="average").astype(np.float64)
    b = rankdata(y, method="average").astype(np.float64)
    rho_obs = _spearman_rho_from_ranks(a, b)

    a_mean = a.mean()
    a_c = a - a_mean
    a_ss = float(np.sum(a_c * a_c))

    rng = np.random.default_rng(seed)

    n_ge_or_le = 0
    remaining = n_mc
    while remaining > 0:
        cur = min(batch, remaining)
        perm_idx = np.argsort(rng.random((cur, n)), axis=1)
        b_perm = b[perm_idx]  # shape (cur, n)

        b_mean = b_perm.mean(axis=1, keepdims=True)
        b_c = b_perm - b_mean
        b_ss = np.sum(b_c * b_c, axis=1)
        cov = np.sum(a_c[None, :] * b_c, axis=1)
        denom = np.sqrt(a_ss * b_ss)

        rho = np.zeros(cur, dtype=np.float64)
        nonzero = denom > 0
        rho[nonzero] = cov[nonzero] / denom[nonzero]

        if sign_i == 1:
            n_ge_or_le += int(np.sum(rho >= rho_obs - _TOL))
        else:
            n_ge_or_le += int(np.sum(rho <= rho_obs + _TOL))

        remaining -= cur

    p_uncorrected = n_ge_or_le / n_mc
    p_corrected = (n_ge_or_le + 1) / (n_mc + 1)

    logger.debug(
        f"mc_perm_p_spearman n={n} sign={sign_i} n_mc={n_mc} rho_obs={rho_obs:.6f} "
        f"p={p_corrected:.10g} p_uncorrected={p_uncorrected:.10g}"
    )

    return {
        "p": p_corrected,
        "p_uncorrected": p_uncorrected,
        "n_mc": n_mc,
        "method": "monte_carlo_(b+1)/(m+1)",
        "rho_obs": rho_obs,
        "n": n,
    }


def perm_p_spearman(x: np.ndarray, y: np.ndarray, sign: float, seed: int = 20260921) -> dict[str, Any]:
    """One-sided permutation p-value for Spearman's rho, exact when feasible.

    For n <= 13, runs the exact subset-DP test and attaches a Monte-Carlo
    cross-check (1,000,000 draws) as ``mc_crosscheck_p`` plus the absolute
    difference between the two p-values as ``abs_diff``, so callers can
    sanity-check the exact result without extra bookkeeping. For n > 13
    (where the exact DP is not supported), falls back to Monte Carlo with
    2,000,000 draws.

    Args:
        x: First sample.
        y: Second sample, paired with x by index.
        sign: +1 tests P(rho_perm >= rho_obs); -1 tests P(rho_perm <=
            rho_obs).
        seed: RNG seed used for the Monte-Carlo component (exact or
            fallback).

    Returns:
        dict. For n <= 13: the exact_perm_p_spearman() dict plus
        "mc_crosscheck_p", "abs_diff", and "method" overridden to
        "exact_subset_dp+mc_crosscheck". For n > 13: the
        mc_perm_p_spearman() dict with "method" set to
        "monte_carlo_(b+1)/(m+1)_n_gt_13".
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n = _validate_xy(x, y)

    if n <= _MAX_EXACT_N:
        exact = exact_perm_p_spearman(x, y, sign)
        mc = mc_perm_p_spearman(x, y, sign, n_mc=1_000_000, seed=seed)
        result = dict(exact)
        result["mc_crosscheck_p"] = mc["p"]
        result["abs_diff"] = abs(result["p"] - mc["p"])
        result["method"] = "exact_subset_dp+mc_crosscheck"
        return result

    mc = mc_perm_p_spearman(x, y, sign, n_mc=2_000_000, seed=seed)
    result = dict(mc)
    result["method"] = "monte_carlo_(b+1)/(m+1)_n_gt_13"
    return result
