#!/usr/bin/env python3
"""Tests for perm_exact.py.

Validates the exact subset-DP permutation test against brute-force
itertools.permutations enumeration (n=5..8, with and without ties, both
signs), cross-checks the DP against Monte Carlo at n=12, and measures the
n=13 DP's runtime and peak memory.
"""

from __future__ import annotations

import itertools
import math
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perm_exact import exact_perm_p_spearman, mc_perm_p_spearman, perm_p_spearman


def _brute_force_p(x: np.ndarray, y: np.ndarray, sign: int) -> float:
    """Reference one-sided exact permutation p-value via full enumeration.

    Enumerates every permutation of the y-side midranks relative to the
    x-side midranks with itertools.permutations and counts how many give a
    statistic at least (sign=+1) or at most (sign=-1) as extreme as observed.

    Args:
        x: First sample.
        y: Second sample.
        sign: +1 or -1.

    Returns:
        The brute-force p-value.
    """
    n = len(x)
    a = np.rint(rankdata(x, method="average") * 2.0).astype(np.int64)
    b = np.rint(rankdata(y, method="average") * 2.0).astype(np.int64)
    s_obs = int(np.sum(a * b))

    count = 0
    total = 0
    for perm in itertools.permutations(range(n)):
        b_perm = b[list(perm)]
        s = int(np.sum(a * b_perm))
        if sign == 1:
            if s >= s_obs:
                count += 1
        else:
            if s <= s_obs:
                count += 1
        total += 1
    assert total == math.factorial(n)
    return count / total


def _make_data(n: int, seed: int, with_ties: bool) -> tuple[np.ndarray, np.ndarray]:
    """Build a random (x, y) pair of length n, optionally with tied values.

    Args:
        n: Sample size.
        seed: RNG seed.
        with_ties: If True, draw from a small integer alphabet that forces
            repeated values (ties) in both x and y.

    Returns:
        Tuple (x, y) of float64 arrays of length n.
    """
    rng = np.random.default_rng(seed)
    if with_ties:
        # Small alphabet relative to n guarantees ties in both arrays.
        alphabet = max(2, n // 2)
        x = rng.integers(0, alphabet, size=n).astype(np.float64)
        y = rng.integers(0, alphabet, size=n).astype(np.float64)
    else:
        x = rng.permutation(n).astype(np.float64) + rng.normal(0, 1e-6, size=n)
        y = rng.permutation(n).astype(np.float64) + rng.normal(0, 1e-6, size=n)
    return x, y


@pytest.mark.parametrize("n", [5, 6, 7, 8])
@pytest.mark.parametrize("with_ties", [False, True])
@pytest.mark.parametrize("sign", [1, -1])
def test_dp_matches_brute_force(n: int, with_ties: bool, sign: int) -> None:
    """DP exact p-value must match full-enumeration brute force to 1e-12."""
    x, y = _make_data(n=n, seed=1000 * n + (1 if with_ties else 0) + sign, with_ties=with_ties)

    dp_result = exact_perm_p_spearman(x, y, sign)
    brute_p = _brute_force_p(x, y, sign)

    assert dp_result["n"] == n
    assert dp_result["n_perms"] == math.factorial(n)
    assert dp_result["p"] == pytest.approx(brute_p, abs=1e-12), (
        f"n={n} with_ties={with_ties} sign={sign}: dp_p={dp_result['p']!r} "
        f"brute_p={brute_p!r}"
    )


@pytest.mark.parametrize("with_ties", [False, True])
def test_dp_matches_brute_force_multiple_seeds(with_ties: bool) -> None:
    """Extra seeds at a fixed small n to broaden coverage cheaply."""
    n = 6
    for seed in range(5):
        x, y = _make_data(n=n, seed=seed + (100 if with_ties else 0), with_ties=with_ties)
        for sign in (1, -1):
            dp_p = exact_perm_p_spearman(x, y, sign)["p"]
            brute_p = _brute_force_p(x, y, sign)
            assert dp_p == pytest.approx(brute_p, abs=1e-12)


def test_dp_probabilities_sum_consistently() -> None:
    """p(sign=+1) + p(sign=-1) = 1 + P(S == S_obs) >= 1, since both tails include S_obs."""
    x, y = _make_data(n=7, seed=42, with_ties=False)
    p_ge = exact_perm_p_spearman(x, y, 1)["p"]
    p_le = exact_perm_p_spearman(x, y, -1)["p"]
    # The identity permutation's own sum S_obs is <= itself and >= itself, so it
    # is counted in both tails: the two p-values must sum to at least 1.
    assert p_ge + p_le >= 1.0 - 1e-9


def test_invalid_sign_raises() -> None:
    x, y = _make_data(n=5, seed=1, with_ties=False)
    with pytest.raises(ValueError):
        exact_perm_p_spearman(x, y, 0)


def test_n_too_large_raises() -> None:
    x, y = _make_data(n=14, seed=1, with_ties=False)
    with pytest.raises(ValueError):
        exact_perm_p_spearman(x, y, 1)


def test_n12_dp_vs_monte_carlo() -> None:
    """n=12 DP result must agree with a 1e6-draw Monte Carlo within 0.003."""
    n = 12
    x, y = _make_data(n=n, seed=777, with_ties=True)
    sign = 1

    dp_result = exact_perm_p_spearman(x, y, sign)
    mc_result = mc_perm_p_spearman(x, y, sign, n_mc=1_000_000, seed=20260921)

    diff = abs(dp_result["p"] - mc_result["p"])
    print(f"\nn=12 DP p={dp_result['p']:.6f} MC p={mc_result['p']:.6f} diff={diff:.6f}")
    assert diff < 0.003, f"n=12 DP vs MC diff too large: {diff}"


def test_n13_dp_timing_and_memory() -> None:
    """n=13 DP must finish in < 120s; report peak memory via tracemalloc."""
    n = 13
    x, y = _make_data(n=n, seed=13131313, with_ties=False)
    sign = 1

    tracemalloc.start()
    t0 = time.perf_counter()
    result = exact_perm_p_spearman(x, y, sign)
    elapsed = time.perf_counter() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    print(
        f"\nn=13 DP: elapsed={elapsed:.3f}s peak_memory={peak_mb:.2f}MB "
        f"p={result['p']!r} n_perms={result['n_perms']}"
    )

    assert elapsed < 120.0, f"n=13 DP took {elapsed:.2f}s, exceeds 120s budget"
    assert result["n_perms"] == 6227020800
    # Soft ceiling generously above the ~300MB target to avoid flakiness
    # across environments while still catching a real memory blow-up.
    assert peak_mb < 500.0, f"n=13 DP peak memory {peak_mb:.2f}MB exceeds 500MB ceiling"


def test_perm_p_spearman_small_n_has_crosscheck() -> None:
    """perm_p_spearman for n<=13 attaches an MC cross-check close to exact p."""
    x, y = _make_data(n=8, seed=5, with_ties=False)
    result = perm_p_spearman(x, y, sign=1, seed=20260921)
    assert result["method"] == "exact_subset_dp+mc_crosscheck"
    assert "mc_crosscheck_p" in result
    assert "abs_diff" in result
    assert result["abs_diff"] < 0.01


def test_perm_p_spearman_large_n_uses_mc() -> None:
    """perm_p_spearman for n>13 falls back to Monte Carlo."""
    x, y = _make_data(n=16, seed=6, with_ties=True)
    result = perm_p_spearman(x, y, sign=-1, seed=20260921)
    assert result["method"] == "monte_carlo_(b+1)/(m+1)_n_gt_13"
    assert result["n_mc"] == 2_000_000
    assert 0.0 < result["p"] <= 1.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
