#!/usr/bin/env python3
"""Session-3 checks for the code added or repaired in this session.

  1. `_auc_cols` (vectorised null AUROC) equals sklearn's roc_auc_score column by
     column, ties included, and is SIGNED (a reversed score gives 1 - AUROC).
  2. `crossfit_probe_full` on PURE NOISE labels sits at chance out-of-fold even
     though hidden size >> n (the in-sample twin would separate noise perfectly),
     and it scores EVERY item, judged or not.
  3. `crossfit_probe_full` recovers a planted refusal direction, and scores the
     wrapped copy with the SAME per-fold probes (identical inputs -> identical scores).
  4. `_loo_gap` (prompt-budget internal readout) is ~0 on noise at k=8 while the
     in-sample Cohen's d it replaced is large -- the reason for the replacement.
  5. `safe_directions` / the pole rule orient each metric by instruct-vs-abliterated.

Run:  OMP_NUM_THREADS=1 venv_exp1/bin/python tests/test_session3.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from screen.analysis2 import _auc_cols, crossfit_probe_full  # noqa: E402
from screen.pipeline2 import _loo_gap  # noqa: E402
from screen.poles2 import safe_directions  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    if not ok:
        FAILURES.append(f"{name}: {detail}")


def test_auc_cols() -> None:
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 70)
    S = rng.standard_normal((70, 6))
    S[:, 2] = np.round(S[:, 2])            # ties
    ref = np.array([roc_auc_score(y, S[:, j]) for j in range(S.shape[1])])
    got = _auc_cols(y, S)
    check("auc_cols == sklearn (ties incl.)", bool(np.allclose(ref, got)),
          f"max|diff|={np.max(np.abs(ref - got)):.2e}")
    check("auc_cols is SIGNED", bool(np.allclose(_auc_cols(y, -S), 1 - got)))


def test_probe_noise_and_coverage() -> None:
    rng = np.random.default_rng(2)
    n, L, d = 160, 6, 512
    H = rng.standard_normal((n, L, d)).astype(np.float32)
    y = rng.integers(0, 2, n)
    folds = np.arange(n) % 5
    judged = np.zeros(n, dtype=bool)
    judged[rng.choice(n, 80, replace=False)] = True
    s, _, layers = crossfit_probe_full(H, y, folds, judged)
    a = roc_auc_score(y[judged], s[judged])
    check("probe on NOISE labels ~ chance out-of-fold", 0.35 < a < 0.65, f"AUROC={a:.3f}")
    check("probe scores EVERY item (judged or not)", bool(np.isfinite(s).all()),
          f"finite={np.isfinite(s).sum()}/{n}")
    check("one layer choice per outer fold", len(layers) == 5, str(layers))


def test_probe_signal_and_wrapped() -> None:
    rng = np.random.default_rng(3)
    n, L, d = 160, 6, 256
    H = rng.standard_normal((n, L, d)).astype(np.float32)
    y = rng.integers(0, 2, n)
    u = rng.standard_normal(d)
    u /= np.linalg.norm(u)
    H[:, 3, :] += (2.0 * (y[:, None] - 0.5) * u[None, :] * 3.0).astype(np.float32)
    folds = np.arange(n) % 5
    judged = np.ones(n, dtype=bool)
    s, sw, layers = crossfit_probe_full(H, y, folds, judged, extra_H=H.copy())
    a = roc_auc_score(y, s)
    check("probe recovers a planted direction", a > 0.9, f"AUROC={a:.3f} layers={layers}")
    check("wrapped copy scored by the SAME probes", bool(np.allclose(s, sw)),
          f"max|diff|={np.nanmax(np.abs(s - sw)):.2e}")


def test_loo_gap_vs_insample() -> None:
    rng = np.random.default_rng(4)
    vals_loo, vals_in = [], []
    for _ in range(200):
        X = rng.standard_normal((8, 2048))
        lab = np.array([1, 1, 1, 1, 0, 0, 0, 0])
        vals_loo.append(_loo_gap(X, lab))
        v = X[lab == 1].mean(0) - X[lab == 0].mean(0)
        sc = X @ (v / np.linalg.norm(v))
        pooled = np.sqrt((sc[lab == 1].var() + sc[lab == 0].var()) / 2) + 1e-9
        vals_in.append((sc[lab == 1].mean() - sc[lab == 0].mean()) / pooled)
    check("LOO gap ~ 0 on noise at k=8, d=2048", abs(np.mean(vals_loo)) < 0.5,
          f"mean={np.mean(vals_loo):.3f}")
    check("in-sample gap is MANUFACTURED on noise", np.mean(vals_in) > 3.0,
          f"mean={np.mean(vals_in):.2f}")


def test_safe_directions() -> None:
    rows = [{"slug": f"i{j}", "cls": "instruct"} for j in range(3)] + \
           [{"slug": f"a{j}", "cls": "abliterated"} for j in range(3)]
    table = {f"i{j}": {"up": 5.0 + j, "down": 1.0 + j} for j in range(3)}
    table.update({f"a{j}": {"up": 1.0 + j, "down": 5.0 + j} for j in range(3)})
    dd = safe_directions(table, rows, ["up", "down", "missing"])
    check("safe direction +1 when instruct > abliterated", dd["up"]["sign"] == 1)
    check("safe direction -1 when instruct < abliterated", dd["down"]["sign"] == -1)
    check("safe direction undefined without values", dd["missing"]["sign"] == 0)


if __name__ == "__main__":
    test_auc_cols()
    test_probe_noise_and_coverage()
    test_probe_signal_and_wrapped()
    test_loo_gap_vs_insample()
    test_safe_directions()
    print(f"\n{'ALL PASS' if not FAILURES else f'{len(FAILURES)} FAILURE(S)'}")
    sys.exit(1 if FAILURES else 0)
