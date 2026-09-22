#!/usr/bin/env python3
"""Build method_out.json (exp_gen_sol_out schema) from rows/*.json, candidates_live.json and the ROSI arm.

datasets:
  live_screen_panel        one example per measured checkpoint: input = checkpoint descriptor (JSON string),
                           output = BALANCED target (S2_core) or "NA" (ungraded); predict_<candidate> = value
                           (the internal candidates AND the logit-only baselines on identical inputs)
  screen16_oracle_readout  one example per (checkpoint, SCREEN16 item): input = prompt, output = judged stance
                           of the model's own 64-token greedy reply; predict_first_token_margin = the baseline
                           logit readout (refuse-minus-comply first-token log-odds)
  rosi_128tok              one example per (cell, item): input = prompt, output = item side;
                           predict_judged_declined_128tok / _20tok = gemini stance grades
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from pathlib import Path
from typing import Any

from loguru import logger

WS = Path(__file__).resolve().parent
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "make_outputs.log", rotation="30 MB", level="DEBUG")

CANDS = ["C1", "C2", "C3", "C7", "C8", "C9", "C11", "C16", "logit_gap", "refusal_mass", "logit_gap_level",
         "refusal_mass_level"]

IN_DIR = WS
OUT_DIR = WS


def find(name: str) -> Path | None:
    """Resolve `name` against --in-dir first, falling back to WS (the live run root) if absent there."""
    p = IN_DIR / name
    if p.exists():
        return p
    p = WS / name
    return p if p.exists() else None


def rows_dir() -> Path:
    p = IN_DIR / "rows"
    return p if p.exists() else WS / "rows"


def rosi128_dir() -> Path:
    p = IN_DIR / "results" / "rosi128"
    return p if p.exists() else WS / "results" / "rosi128"


def s(v: Any) -> str:
    if v is None:
        return "NA"
    if isinstance(v, float):
        return "NA" if not math.isfinite(v) else f"{v:.6g}"
    return str(v)


def panel_examples() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(rows_dir() / "*.json"))):
        r = json.loads(Path(f).read_text())
        desc = {k: r.get(k) for k in ("repo", "resolved_sha", "family", "lineage", "class", "n_params", "stratum")}
        ex: dict[str, Any] = {"input": json.dumps(desc), "output": s(r.get("BALANCED"))}
        for k in ("family", "lineage", "class", "n_params", "graded", "n_layers", "d_model"):
            ex[f"metadata_{k}"] = r.get(k)
        ex["metadata_product_target"] = r.get("PRODUCT")
        ex["metadata_readout_validity_auroc"] = (r.get("oracle") or {}).get("readout_validity_auroc")
        ex["metadata_wall_s"] = r.get("wall_s")
        ex["metadata_flags"] = r.get("flags")
        c = r["candidates"]
        for k in CANDS:
            ex[f"predict_{k}"] = s(c[k]["value"])
            for var in ("pole_refuse", "pole_comply", "k8", "oracle"):
                if var in c[k]:
                    ex[f"predict_{k}_{var}"] = s(c[k][var])
        ex["metadata_candidate_undefined"] = {k: c[k].get("reason") for k in CANDS if c[k].get("undefined")}
        out.append(ex)
    return out


def oracle_examples() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(rows_dir() / "*.json"))):
        r = json.loads(Path(f).read_text())
        o = r.get("oracle") or {}
        y = o.get("judged_refusal")
        m = r["conditions"]["plain"]["margins"]
        for i, g in enumerate(r.get("gen64") or []):
            lab = "NA" if not y else {1: "refused", 0: "complied", -1: "parse_fail"}.get(y[i], "NA")
            out.append({"input": _prompt(i), "output": lab,
                        "metadata_repo": r["repo"], "metadata_pair_id": g["pair_id"], "metadata_side": g["side"],
                        "metadata_reply_64tok": g["text"], "predict_first_token_margin": s(m[i])})
    return out


_PROMPTS: list[str] = []


def _prompt(i: int) -> str:
    if not _PROMPTS:
        data = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_dataset_1")
        rows = [json.loads(l) for l in (data / "screen16.jsonl").read_text().splitlines() if l.strip()]
        pids = []
        for r in rows:
            if r["pair_id"] not in pids:
                pids.append(r["pair_id"])
        for p in pids:
            _PROMPTS.append(next(r["prompt"] for r in rows if r["pair_id"] == p and r["side"] == "harmful"))
            _PROMPTS.append(next(r["prompt"] for r in rows if r["pair_id"] == p and r["side"] == "benign_twin"))
    return _PROMPTS[i]


def rosi_examples() -> list[dict]:
    out = []
    for name in ("x0", "F2b_rosi_x4", "F2b_rosi_hidden_x4"):
        f = rosi128_dir() / f"{name}.json"
        if not f.exists():
            continue
        d = json.loads(Path(f).read_text())
        if not isinstance(d, dict) or "items" not in d or "cell" not in d:
            continue
        for it in d["items"]:
            ex = {"input": it["prompt"], "output": it.get("kind", it.get("arm", "NA")),
                  "metadata_cell": d["cell"], "metadata_item_id": it.get("id"),
                  "metadata_reply_128tok": it.get("reply_128tok"), "metadata_prefix_20tok": it.get("prefix_20tok")}
            for gk in [k for k in it if k.startswith("grade")]:
                g = it.get(gk)
                if isinstance(g, dict):
                    ex[f"predict_judged_declined_{gk}"] = s(g.get("declined"))
            out.append(ex)
    return out


@logger.catch(reraise=True)
def main() -> None:
    global IN_DIR, OUT_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default=str(WS), help="dir to read candidates_live.json/rosi_128tok.json/etc from (default WS)")
    ap.add_argument("--out-dir", default=str(WS), help="dir to write method_out.json into (default WS)")
    args = ap.parse_args()
    IN_DIR = Path(args.in_dir).resolve()
    OUT_DIR = Path(args.out_dir).resolve()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cl_p, rosi_p, spend_p, devs_p, prereg_p = (find("candidates_live.json"), find("rosi_128tok.json"),
                                                find("spend.json"), find("DEVIATIONS.json"), find("PREREG_hash.txt"))
    cl = json.loads(cl_p.read_text()) if cl_p else {}
    rosi = json.loads(rosi_p.read_text()) if rosi_p else {}
    spend = json.loads(spend_p.read_text()) if spend_p else {}
    devs = json.loads(devs_p.read_text()) if devs_p else []
    prereg_hash = prereg_p.read_text().split()[0] if prereg_p else "–"
    datasets = [{"dataset": "live_screen_panel", "examples": panel_examples()},
                {"dataset": "screen16_oracle_readout", "examples": oracle_examples()}]
    rx = rosi_examples()
    if rx:
        datasets.append({"dataset": "rosi_128tok", "examples": rx})
    datasets = [d for d in datasets if d["examples"]]
    meta = {"method_name": "LIVE-tier causal-gain safety screen (iter 4; CPU fallback LIVE_TIER_NO_CUDA)",
            "description": ("Per-checkpoint intervention/patching candidates C1,C2,C3,C7,C8,C9,C11,C16 on the frozen "
                            "SCREEN16 prompts vs the logit-only baselines (first-token logit gap, refusal-token mass) "
                            "on identical inputs; targets BALANCED (S2_core) and PRODUCT (P2)."),
            "prereg_hash": prereg_hash, "deviations": [d.get("code") for d in devs],
            "spend_usd": spend.get("total_usd"),
            "panel_summary": cl.get("panel_summary") or cl.get("summary"),
            "rosi_verdicts": rosi.get("verdicts"),
            "files": ["candidates_live.json", "candidate_values_live.json", "rows/", "rosi_128tok.json",
                      "RESULTS.md", "PREREG.json", "DEVIATIONS.json", "skips.json", "spend.json"]}
    out = {"metadata": meta, "datasets": datasets}
    (OUT_DIR / "method_out.json").write_text(json.dumps(out, indent=1))
    logger.info(f"method_out.json written to {OUT_DIR / 'method_out.json'}: "
                + ", ".join(f"{d['dataset']}={len(d['examples'])}" for d in datasets))


if __name__ == "__main__":
    main()
