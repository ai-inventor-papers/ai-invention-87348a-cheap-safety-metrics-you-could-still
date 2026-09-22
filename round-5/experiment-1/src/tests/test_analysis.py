"""Unit tests for analyze_gpu.py's numeric core: venv_gpu/bin/python -m pytest -q tests/test_analysis.py

(i)   partial Spearman against a hand-computed synthetic case (independent closed-form formula, not a
      re-implementation of ols_resid_rank).
(ii)  the lineage bootstrap resamples LINEAGES, not checkpoints (a synthetic case where the two differ:
      one singleton lineage vs. one 9-member lineage -- only lineage-level resampling can ever produce a
      resample of length 1 made of the singleton alone).
(iii) the label-permutation p-value on a known-null (pure-noise) synthetic dataset is uniform-ish
      (p_one_sided > 0.2 at a fixed seed).
(iv)  the S3 orientation flip is actually applied: a candidate with declared orientation -1 is compared
      AFTER sign flip, not on the raw values (a bug that forgot the flip would get part (i) backwards).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))

import analyze_gpu as ag  # noqa: E402


# =====================================================================================================
# (i) partial Spearman vs. a hand-computed closed-form partial correlation
# =====================================================================================================
def test_partial_spearman_matches_closed_form_single_covariate():
    rng = np.random.default_rng(12345)
    n = 30
    z = rng.normal(size=n)                       # covariate
    x = 0.6 * z + rng.normal(size=n) * 0.8        # value
    y = 0.5 * z + 0.3 * x + rng.normal(size=n) * 0.7  # target (depends on both z and x)

    got = ag.partial_spearman(x, y, [z])

    # independent closed-form check: classic partial-correlation formula applied to the RANK-transformed
    # variables (ols_resid_rank + pearson-of-residuals is mathematically equivalent to this for one
    # covariate: both project out the linear effect of rank(z) from rank(x) and rank(y)).
    rx, ry, rz = ag._safe_rank(x), ag._safe_rank(y), ag._safe_rank(z)
    r_xy = ag.pearson(rx, ry)
    r_xz = ag.pearson(rx, rz)
    r_yz = ag.pearson(ry, rz)
    expected = (r_xy - r_xz * r_yz) / np.sqrt((1 - r_xz ** 2) * (1 - r_yz ** 2))

    assert got == pytest.approx(expected, abs=1e-9)
    # sanity: controlling for z should pull the raw x-y correlation down noticeably (y was built to
    # depend on z too), so the partial should differ from the plain Spearman rho.
    plain = ag.spearman(x, y)
    assert abs(got - plain) > 0.01


def test_partial_spearman_near_zero_when_covariate_fully_explains():
    """x and y are correlated ONLY THROUGH z (independent noise on top): raw rho(x,y) is large and
    positive, but once z is controlled for, the partial should collapse towards 0."""
    rng = np.random.default_rng(99)
    n = 300
    z = rng.normal(size=n)
    x = z + rng.normal(size=n) * 0.05   # x almost equals z
    y = z + rng.normal(size=n) * 0.05   # y almost equals z (independent noise from x's)
    raw = ag.spearman(x, y)
    got = ag.partial_spearman(x, y, [z])
    assert raw > 0.9  # x, y look strongly correlated before controlling for z
    assert abs(got) < 0.25  # controlling for the shared driver collapses the partial towards 0


# =====================================================================================================
# (ii) lineage bootstrap resamples LINEAGES, not checkpoints
# =====================================================================================================
def test_lineage_bootstrap_resamples_lineages_not_checkpoints():
    # one singleton lineage "A" (n=1) and one large lineage "B" (n=9): a CHECKPOINT-level i.i.d. bootstrap
    # of the N=10 rows would always return exactly 10 indices, every time. A LINEAGE-level bootstrap draws
    # len(groups)=2 lineage KEYS with replacement and concatenates their members, so the resample length is
    # random: AA -> 1+1=2, AB/BA -> 1+9=10, BB -> 9+9=18. Seeing lengths other than {10}, and in particular
    # seeing the "both draws are the singleton lineage A" case (length 2, both indices point at A's one
    # row), is only possible if the resampling unit is the LINEAGE, not the checkpoint.
    lineages = np.array(["A"] + ["B"] * 9)
    values = np.array([100.0] + [0.0] * 9)
    groups = ag.lineage_groups(lineages)
    assert set(groups.keys()) == {"A", "B"}

    rng = np.random.default_rng(0)
    lengths_seen = set()
    saw_pure_singleton_A = False
    saw_pure_B = False
    for _ in range(500):
        idx = ag.lineage_bootstrap_resample_idx(groups, rng)
        lengths_seen.add(len(idx))
        if np.all(values[idx] == 100.0):
            saw_pure_singleton_A = True
        if len(idx) == 18:
            saw_pure_B = True

    # a checkpoint-level (non-lineage) bootstrap of 10 i.i.d. draws is ALWAYS exactly length 10
    assert lengths_seen != {10}, "resample lengths never varied -- looks like checkpoint-level, not lineage-level"
    assert saw_pure_singleton_A, "never saw a resample made purely of the singleton lineage A: not resampling by lineage"
    assert saw_pure_B, "never saw a resample made purely of the 9-member lineage B (length 18): not resampling by lineage"


def test_bootstrap_rho_ci_uses_lineage_groups_of_unequal_size():
    """End-to-end: bootstrap_rho_ci must be able to draw a resample dominated by the tiny lineage, which
    should widen the CI far beyond what a checkpoint-level bootstrap of the same data would give."""
    lineages = np.array(["A"] + ["B"] * 9)
    value = np.array([1.0] + list(np.linspace(0, 1, 9)))
    target = np.array([0.0] + list(np.linspace(0, 1, 9)))
    ci = ag.bootstrap_rho_ci(value, target, lineages, n_boot=500, seed=1)
    assert ci["n_boot"] > 0
    # the CI must be wide (lineage A's single extreme point can dominate or vanish a resample)
    assert (ci["ci_hi"] - ci["ci_lo"]) > 0.3


# =====================================================================================================
# (iii) permutation p-value is uniform-ish on a known-null (pure noise) dataset
# =====================================================================================================
def test_permutation_p_value_uniform_ish_on_null_data():
    rng = np.random.default_rng(7)
    n = 23
    value = rng.normal(size=n)
    target = rng.normal(size=n)  # independent of value: the null is TRUE here
    res = ag.checkpoint_perm_null(value, target, sign=1.0, n_perm=2000, seed=42)
    assert res["n_perm"] == 2000
    assert res["p_one_sided"] > 0.2


def test_permutation_p_value_small_for_planted_signal():
    """Sanity counterpart: a strong planted monotone signal should give a tiny p, so the test above is
    not just "the permutation test always returns a big p"."""
    rng = np.random.default_rng(3)
    n = 23
    value = np.arange(n, dtype=float) + rng.normal(scale=0.01, size=n)
    target = np.arange(n, dtype=float) + rng.normal(scale=0.01, size=n)
    res = ag.checkpoint_perm_null(value, target, sign=1.0, n_perm=2000, seed=42)
    assert res["p_one_sided"] < 0.01


# =====================================================================================================
# (iv) S3 orientation flip is applied before the blanket-refuser-vs-parent comparison
# =====================================================================================================
def _toy_wide_and_labels(child_raw: float, parent_raw: float) -> tuple["ag.WideTable", pd.DataFrame]:
    records = [
        {"repo": "parent", "candidate_id": "C10", "variant": "primary", "value": parent_raw,
         "undefined": False, "undefined_reason": None, "n_params": 1e9, "family": "fam",
         "lineage": "lin1", "class": "instruct", "stratum": "chat"},
        {"repo": "child", "candidate_id": "C10", "variant": "primary", "value": child_raw,
         "undefined": False, "undefined_reason": None, "n_params": 1e9, "family": "fam",
         "lineage": "lin1", "class": "blanket_refuser", "stratum": "chat"},
    ]
    wide = ag.WideTable(records)
    labels_df = pd.DataFrame([
        {"repo": "parent", "BALANCED": 0.5, "PRODUCT": 0.5, "family": "fam", "lineage": "lin1", "class": "instruct"},
        {"repo": "child", "BALANCED": 0.1, "PRODUCT": 0.1, "family": "fam", "lineage": "lin1", "class": "blanket_refuser"},
    ])
    return wide, labels_df


def test_s3_orientation_flip_applied_negative_sign():
    # C10 is declared orientation -1 in PREREG.json (higher raw = LESS safe). child's raw value (10) is
    # numerically ABOVE parent's (5): a naive (un-flipped) comparison "child_raw < parent_raw" would say
    # the blanket-refuser check FAILS (10 is not < 5). Once oriented by sign=-1, child_oriented=-10 <
    # parent_oriented=-5, so the check correctly HOLDS -- proving the flip is applied before compare.
    wide, labels_df = _toy_wide_and_labels(child_raw=10.0, parent_raw=5.0)
    res = ag.s3_repaired("C10", -1.0, wide, labels_df, {"child": "parent"})
    check = res["part_i_checks"][0]
    assert check["parent_oriented"] == pytest.approx(-5.0)
    assert check["child_oriented"] == pytest.approx(-10.0)
    assert check["holds"] is True
    assert res["part_i_pass"] is True
    # raw (un-oriented) comparison would have given the OPPOSITE answer (10.0 is not < 5.0) -- pinning that
    # down here documents exactly what the sign multiplication in s3_repaired is required to flip.
    assert not (10.0 < 5.0)


def test_s3_orientation_flip_applied_positive_sign():
    """Same raw values, orientation +1 (e.g. C1/C2): now the RAW comparison is already the right one, and
    it should FAIL this time (child's raw value is above parent's, and positive orientation keeps it that
    way), showing the flip is genuinely sign-dependent, not a hard-coded direction."""
    wide, labels_df = _toy_wide_and_labels(child_raw=10.0, parent_raw=5.0)
    res = ag.s3_repaired("C10", 1.0, wide, labels_df, {"child": "parent"})
    check = res["part_i_checks"][0]
    assert check["parent_oriented"] == pytest.approx(5.0)
    assert check["child_oriented"] == pytest.approx(10.0)
    assert check["holds"] is False
    assert res["part_i_pass"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
