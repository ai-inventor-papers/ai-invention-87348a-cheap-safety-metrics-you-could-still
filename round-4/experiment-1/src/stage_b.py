#!/usr/bin/env python3
"""Stage-B/D smoke checks on one model (default Qwen2.5-0.5B-Instruct), written to scratch/stage_b_<slug>.json.

B1 batched left-padded last-token margins == unbatched margins (|diff| < 1e-2 in bf16)
B2 r^(b) steering: +alpha*r^(b) at B_mid raises the margin on twins (read from the smoke row: C16 twin slope > 0)
B3 C1 finite differences at eps 0.02 / 0.05 agree within 20% (smoke row: C1 gain_by_eps)
B4 C2 vs its random-direction p95 (smoke row), recorded honestly
B5 harmful-minus-twin logit gap > 0 (smoke row)
D  pole sanity: mean margin pole_refuse > plain > pole_comply (smoke row)
"""
from __future__ import annotations

import json
import sys

import numpy as np

sys.argv = [sys.argv[0]] + sys.argv[1:]
import method as M  # noqa: E402  (sets threads, PREREG gate, logger)
from live_lib import build_batch  # noqa: E402

REPO = sys.argv[1] if len(sys.argv) > 1 else "Qwen/Qwen2.5-0.5B-Instruct"
# optional 2nd argument: the measured row to read B2-B5/D from (default: the smoke row). Session 4 passes the
# production GPU row rows/<slug>.json, and the output file name carries the device so the CPU result is kept.
ROW_PATH = sys.argv[2] if len(sys.argv) > 2 else None


def main() -> None:
    out: dict = {"repo": REPO}
    mr = M.ModelRun(REPO)
    mr.load()
    b = mr.batch("plain")
    b.item_idx = list(range(16))
    base = mr.base_pass(b, [], want_attn=False)
    single = []
    for i, p in enumerate(M.PROMPTS):
        bi = build_batch(mr.tok, REPO, [p], None, mr.meta["template_mode_panel"])
        bi.item_idx = [i]
        single.append(float(mr.base_pass(bi, [], want_attn=False)["m"][0]))
    d = np.abs(np.array(single) - base["m"])
    out["B1_batched_vs_unbatched"] = {"max_abs_diff": float(d.max()), "mean_abs_diff": float(d.mean()),
                                      "pass": bool(d.max() < 1e-2), "batched": base["m"].tolist(),
                                      "unbatched": single}
    sp = M.Path(ROW_PATH) if ROW_PATH else M.WS / "scratch" / f"smoke_{M.slug(REPO)}.json"
    out["row_source"] = str(sp)
    out["device"] = M.DEVICE.type
    if sp.exists():
        r = json.loads(sp.read_text())
        c = r["candidates"]
        g = c["C1"].get("gain_by_eps", {})
        g2, g5 = g.get("0.02"), g.get("0.05")
        out["B2_rb_steer_twin_slope"] = {"twin_slope": c["C16"]["twin_slope"], "harm_slope": c["C16"]["harm_slope"],
                                         "pass": bool(c["C16"]["twin_slope"] is not None and c["C16"]["twin_slope"] > 0)}
        out["B3_c1_eps_agreement"] = {"gain_0.02": g2, "gain_0.05": g5,
                                      "rel_diff": (abs(g2 - g5) / max(abs(g5), 1e-9)) if (g2 is not None and g5 is not None) else None,
                                      "pass": bool(g2 is not None and g5 is not None and abs(g2 - g5) <= 0.2 * max(abs(g5), 1e-9))}
        out["B4_c2_vs_null"] = {"C2": c["C2"]["value"], "null_p95": c["C2"]["null_p95"],
                                "exceeds": (c["C2"]["value"] is not None and c["C2"]["null_p95"] is not None
                                            and c["C2"]["value"] > c["C2"]["null_p95"])}
        out["B5_logit_gap_positive"] = {"logit_gap": c["logit_gap"]["value"], "pass": bool(c["logit_gap"]["value"] > 0)}
        mm = {k: float(np.mean(v["margins"])) for k, v in r["conditions"].items()}
        out["D_pole_order"] = {"mean_margin": mm,
                               "pass": bool(mm.get("pole_refuse", -1e9) > mm["plain"] > mm.get("pole_comply", 1e9))}
    tag = "" if M.DEVICE.type == "cpu" else f"{M.DEVICE.type}_"
    M.atomic_write(M.WS / "scratch" / f"stage_b_{tag}{M.slug(REPO)}.json", out)
    print(json.dumps({k: (v.get("pass", v) if isinstance(v, dict) else v) for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    main()
