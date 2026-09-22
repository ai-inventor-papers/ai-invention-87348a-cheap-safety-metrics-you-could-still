#!/usr/bin/env python3
"""Orchestrator's independent sanity check on a measured row (usage: check_invariants.py rows/<slug>.json ...).

It does not recompute the candidates (that is method.py's job); it asserts the invariants each definition implies,
so an implementation slip shows up before the panel runs. Every violation is printed as FAIL with the numbers.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def fnum(x):  # noqa: ANN001, ANN201
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def check(row: dict) -> list[str]:
    out: list[str] = []
    c = row.get("candidates") or {}
    L = row.get("n_layers") or 0
    bands = row.get("bands") or {}

    def val(name, key="value"):  # noqa: ANN001, ANN202
        d = c.get(name)
        return fnum(d.get(key)) if isinstance(d, dict) else None

    def ok(cond: bool, msg: str) -> None:
        out.append(("PASS " if cond else "FAIL ") + msg)

    # presence
    for name in ("C1", "C2", "C1n_cd", "C1n_os", "C6", "C10", "C12", "C13", "C15_erank", "C15_disp",
                 "logit_gap", "refusal_mass"):
        ok(isinstance(c.get(name), dict), f"{name} present")
    # C15_erank of 16 centred rows lives in [1, 15]
    e = val("C15_erank")
    if e is not None:
        ok(1.0 <= e <= 15.5, f"C15_erank={e:.3f} in [1,15.5]")
    d = val("C15_disp")
    if d is not None:
        ok(0.0 <= d <= 2.0, f"C15_disp={d:.3f} in [0,2]")
    # C6 share of the top-5 layers of L
    s6 = val("C6")
    if s6 is not None and L:
        ok(0.0 <= s6 <= 1.0 + 1e-9, f"C6 share={s6:.3f} in [0,1]")
        ok(s6 >= min(5.0 / L, 1.0) - 0.15, f"C6 share={s6:.3f} >= ~5/L={5 / L:.3f} (top-5 of L layers)")
    # C13 invariance in (-inf, 1]
    v13 = val("C13")
    if v13 is not None:
        ok(v13 <= 1.0 + 1e-9, f"C13={v13:.3f} <= 1")
    r13 = val("C13_rank")
    if r13 is not None:
        ok(-1.0 - 1e-9 <= r13 <= 1.0 + 1e-9, f"C13_rank={r13:.3f} in [-1,1]")
    l13 = val("C13_logit")
    if l13 is not None:
        ok(l13 <= 1.0 + 1e-9, f"C13_logit={l13:.3f} <= 1")
    # C10 curves
    c10 = c.get("C10") or {}
    a_curve, d_curve = c10.get("a_curve"), c10.get("d_curve")
    if isinstance(a_curve, list) and isinstance(d_curve, list):
        ok(len(a_curve) == L and len(d_curve) == L, f"C10 curves have L={L} points ({len(a_curve)},{len(d_curve)})")
        fin = [x for x in a_curve if fnum(x) is not None]
        ok(all(0.0 <= x <= 1.0 for x in fin), "C10 a_l are AUROCs in [0,1]")
        v10 = val("C10")
        if v10 is not None:
            ok(abs(v10) <= 1.0, f"C10={v10:.3f} is an area of AUROC differences over depth in [-1,1]")
    # C12 sign agrees with the cross-fitted AUROC at L_h
    v12 = val("C12")
    auc = fnum((row.get("directions") or {}).get("h_auroc_crossfit_Lh"))
    if v12 is not None and auc is not None:
        ok((v12 > 0) == (auc > 0.5) or abs(auc - 0.5) < 0.05, f"C12={v12:.3f} sign agrees with cross-fit AUROC {auc:.3f}")
    # C1n = C1 - median(null); 20 distinct random-steer values
    c1 = val("C1")
    nv = (c.get("C1n_cd") or {}).get("null_values")
    if isinstance(nv, list):
        ok(len(nv) == 20, f"C1n has 20 random-steer values (got {len(nv)})")
        ok(len(set(round(float(x), 9) for x in nv if fnum(x) is not None)) > 15, "C1n random-steer values are distinct")
        med = sorted(float(x) for x in nv if fnum(x) is not None)
        if c1 is not None and med:
            m = med[len(med) // 2] if len(med) % 2 else 0.5 * (med[len(med) // 2 - 1] + med[len(med) // 2])
            v = val("C1n_cd")
            if v is not None:
                ok(abs((c1 - m) - v) < 1e-6 * max(1.0, abs(v)), f"C1n_cd == C1 - median(null) ({c1:.4f}-{m:.4f} vs {v:.4f})")
    # every candidate is either finite or undefined WITH a reason
    for name, dd in c.items():
        if isinstance(dd, dict) and fnum(dd.get("value")) is None:
            ok(bool(dd.get("reason")), f"{name} undefined carries a reason ({dd.get('reason')!r})")
    # bands
    ok(bool(bands.get("B_mid")) and bool(bands.get("B_late")), "bands recorded")
    # timing / VRAM
    peak = fnum((row.get("compute") or {}).get("vram_peak_gb"))
    if peak is not None:
        ok(peak < 10.0, f"VRAM peak {peak:.2f} GB < 10.0 GB cap")
    return out


def main() -> None:
    fails = 0
    for p in sys.argv[1:]:
        row = json.loads(Path(p).read_text())
        print(f"=== {row.get('repo')} ({p})")
        for line in check(row):
            print("  " + line)
            fails += line.startswith("FAIL")
    print(f"\n{fails} FAIL(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
