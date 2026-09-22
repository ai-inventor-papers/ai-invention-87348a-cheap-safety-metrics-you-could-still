#!/usr/bin/env python3
"""Structural checks that the race cannot leak, plus the deliberate violation.

The testing plan asks for the fit/apply boundary to be enforced STRUCTURALLY and
for a deliberate violation to FAIL LOUDLY.  These are the four checks:

  1. `FoldView` physically does not expose the test rows.
  2. `fit_1d` returns PARAMS, never anything holding the test rows.
  3. On RANDOM labels the held-out score sits at chance while the TUNED score
     does not -- which is exactly the leak the holdout exists to prevent, and is
     the deliberate violation made visible.
  4. The frozen item folds respect `twin_group`, so no near-duplicate item
     straddles a split.

Run:  OMP_NUM_THREADS=1 venv_exp1/bin/python tests/test_isolation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from screen.analysis2 import FoldView, apply_1d, fit_1d, grouped_holdout_score  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    if not ok:
        FAILURES.append(f"{name}: {detail}")


def test_foldview_hides_test_rows() -> None:
    x = np.arange(10, dtype=float)
    y = np.array(["a"] * 5 + ["b"] * 5)
    v = FoldView(x[:6], y[:6], n_test=4)
    check("FoldView exposes only train rows", len(v) == 6, f"len={len(v)}")
    # __slots__ means there is no attribute that could carry the test rows, and
    # no new one can be attached to smuggle them in.
    leaked = False
    try:
        v.x_test = x[6:]          # type: ignore[attr-defined]
        leaked = True
    except AttributeError:
        leaked = False
    check("FoldView refuses to carry test rows (deliberate violation)", not leaked,
          "assignment raised AttributeError" if not leaked else "SMUGGLING SUCCEEDED")
    has_test_attr = any(a in FoldView.__slots__ for a in ("x_test", "y_test", "test"))
    check("FoldView has no test-bearing slot", not has_test_attr,
          f"slots={FoldView.__slots__}")


def test_fit_returns_params_only() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal(20)
    y = np.array(["instruct"] * 10 + ["abliterated"] * 10)
    p = fit_1d(FoldView(x, y, 0))
    bad = [k for k in p if k in ("x", "y", "view", "data")]
    check("fit_1d returns params, not data", not bad, f"suspicious keys={bad}")
    pred = apply_1d(p, rng.standard_normal(7))
    check("apply_1d predicts from params alone", len(pred) == 7, f"n={len(pred)}")


def test_random_labels_land_at_the_empirical_null() -> None:
    """THE DELIBERATE VIOLATION, and the reason 0.5 is the WRONG null.

    With labels that carry no information the TUNED (fit-on-everything) score
    must climb well above the HELD-OUT one -- that gap IS the leak the holdout
    exists to prevent, shown rather than asserted.

    The held-out score, however, does NOT land on 0.5.  Leave-one-GROUP-out
    balanced accuracy on random labels is biased BELOW chance: whichever class
    is over-represented in the held-out group is by construction
    under-represented in the training remainder, so the fitted classifier leans
    against the test group's majority.  Measured here at ~0.40 with 6 groups of
    4.  This is not a defect in the estimator -- it is why every row of the race
    table carries a LABEL-PERMUTATION null computed on the identical pipeline
    instead of being compared against a nominal 0.5.  A paper that scores
    leave-one-family-out balanced accuracy against 0.5 understates its own
    baseline by roughly a tenth of a point.
    """
    n_fam, per = 6, 4
    y0 = np.array(["instruct", "abliterated"] * (n_fam * per // 2))
    np.random.default_rng(20260920).shuffle(y0)
    fam = np.repeat([f"F{i}" for i in range(n_fam)], per)
    held, tuned = [], []
    for s in range(200):
        r = np.random.default_rng(s)
        sc = grouped_holdout_score(r.standard_normal(len(y0)), y0, fam)
        if np.isfinite(sc["held_out"]):
            held.append(sc["held_out"])
            tuned.append(sc["tuned"])
    mh, mt, sd = float(np.mean(held)), float(np.mean(tuned)), float(np.std(held))
    check("TUNED score is inflated above held-out (the leak, shown)", mt > mh + 0.05,
          f"tuned {mt:.3f} vs held-out {mh:.3f} -- gap {mt - mh:+.3f}")
    check("held-out score is NOT at the nominal 0.5 (LOGO anti-correlation bias)",
          abs(mh - 0.5) > 0.02,
          f"empirical LOGO null = {mh:.3f} (sd {sd:.3f}) over {len(held)} draws, "
          f"not 0.500 -- this is why every race row carries a permutation null")
    check("held-out score is stable and below chance, not wild",
          0.30 < mh < 0.50 and sd < 0.20, f"mean {mh:.3f} sd {sd:.3f}")
    out = ROOT / "results" / "logo_null_calibration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "design": "6 groups x 4 checkpoints, balanced random labels, random features, 200 draws",
        "empirical_logo_null_mean": mh, "empirical_logo_null_sd": sd,
        "tuned_on_random_labels": mt, "nominal_chance": 0.5,
        "finding": "Leave-one-GROUP-out balanced accuracy on uninformative labels sits BELOW "
                   "nominal chance because the held-out group's class balance is negatively "
                   "correlated with the training remainder's. Race rows are therefore compared "
                   "against a label-permutation null computed on the identical pipeline, never "
                   "against 0.5.",
    }, indent=2))


def test_folds_respect_twin_groups() -> None:
    p = ROOT / "inherited" / "items.json"
    if not p.exists():
        check("frozen folds respect twin_group", False, "inherited/items.json missing")
        return
    d = json.loads(p.read_text())
    items = d["items"] if isinstance(d, dict) else d
    fold = np.array([int(i["fold"]) for i in items])
    tg = np.array([str(i["twin_group"]) for i in items])
    straddle = [g for g in np.unique(tg) if len(np.unique(fold[tg == g])) > 1]
    check("frozen folds respect twin_group", not straddle,
          f"{len(straddle)} straddling groups"
          + (f" e.g. {straddle[:3]}" if straddle else "")
          + f"; {len(np.unique(tg))} groups over {len(items)} items")


def main() -> int:
    test_foldview_hides_test_rows()
    test_fit_returns_params_only()
    test_random_labels_land_at_the_empirical_null()
    test_folds_respect_twin_groups()
    print("-" * 60)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("ALL ISOLATION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
