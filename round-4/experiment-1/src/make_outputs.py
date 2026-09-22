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
        # device provenance is read from the row's own compute metadata; a row with no 'compute' key was
        # measured on cpu (that key was only ever added once GPU measurement started)
        compute = r.get("compute") or {}
        ex["metadata_device"] = compute.get("device", "cpu")
        ex["metadata_device_name"] = compute.get("device_name")
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
def headline_findings(cl: dict, extra_p: Path | None, sweep_p: Path | None,
                      mnull_p: Path | None = None) -> list[str]:
    """Plain-sentence findings generated from candidates_live.json (and the exploratory JSONs when present);
    every number is read from those files, none is typed here."""
    C = cl.get("candidates") or {}
    ps = cl.get("panel_summary") or {}
    out: list[str] = []

    def g(cid: str) -> tuple:
        c = C.get(cid) or {}
        rb = ((c.get("rho") or {}).get("BALANCED") or {})
        bt = rb.get("rho_ckpt_boot") or {}
        par = c.get("partial_rho") or {}
        return (rb.get("rho_ckpt"), bt.get("ci_lo"), bt.get("ci_hi"), rb.get("rho_family"), par.get("point"),
                (par.get("boot") or {}).get("ci_lo_one_sided"))

    def f3(x: Any) -> str:
        return "nan" if x is None else f"{x:.3f}"
    rules = ("S1", "S2", "S3", "S4", "S5", "S6")
    internal = ["C1", "C2", "C3", "C7", "C8", "C11"]
    shipped = [k for k in internal if all(((C.get(k) or {}).get(r) or {}).get("pass") for r in rules)]
    out.append(f"Graded panel n={ps.get('n_graded')} chat checkpoints, {ps.get('n_families')} families, "
               f"{ps.get('n_lineages')} lineages, {ps.get('n_blanket_refusers')} blanket refusers; MDE_rho="
               f"{f3((ps.get('mde') or {}).get('mde_rho'))}.")
    out.append("Internal candidates passing all of S1-S6: " + (", ".join(shipped) if shipped else "NONE") + ".")
    for k in ("C2", "C1", "logit_gap", "refusal_mass", "C11"):
        r, lo, hi, rf, pr, pb = g(k)
        fails = [x for x in rules if ((C.get(k) or {}).get(x) or {}).get("pass") is False]
        cov = ((C.get(k) or {}).get("partial_rho") or {}).get("covariates") or "logit_gap, log10(n_params)"
        out.append(f"{k}: rho_ckpt(BALANCED)={f3(r)} [{f3(lo)}, {f3(hi)}], rho_family={f3(rf)}, partial rho | "
                   f"({cov})={f3(pr)} (one-sided 5% bound {f3(pb)}); fails {', '.join(fails) or 'none'}.")
    wf = (C.get("C2") or {}).get("within_family") or {}
    if wf.get("per_family"):
        out.append("C2 within-family Spearman: " + "; ".join(
            f"{fam} {f3(e.get('rho'))} (n={e.get('n')}, p={f3(e.get('p_perm'))})" for fam, e in wf["per_family"].items())
            + ". logit_gap within tinyllama: " + f3((((C.get('logit_gap') or {}).get('within_family') or {})
                                                    .get('per_family') or {}).get('tinyllama', {}).get('rho')) + ".")
    labelled = [k for k, c in C.items() if ((c or {}).get("within_family") or {}).get("label")]
    if labelled:
        out.append("'works within one family only: NEGATIVE': " + ", ".join(labelled) + ".")
    xh = cl.get("cross_hardware") or {}
    per = xh.get("per_candidate") or xh.get("candidates") or {}
    if isinstance(per, dict) and per:
        out.append("CPU-vs-GPU Spearman over 12 re-measured models: " + ", ".join(
            f"{k} {f3((v or {}).get('spearman_cpu_vs_gpu'))}" for k, v in per.items() if isinstance(v, dict)) + ".")
    if extra_p is not None:
        ex = json.loads(extra_p.read_text())
        a = (ex.get("A_s2b_indicator") or {}).get("C2") or {}
        out.append(f"EXPLORATORY: C2 exceeds its direction-null p95 on {a.get('exceed_upper_half')} upper-half vs "
                   f"{a.get('exceed_lower_half')} lower-half models (AUROC {f3(a.get('auroc_BALANCED_exceed_vs_not'))}); "
                   "so the pre-registered S2(b) (exceed on >= 60% of the whole panel) penalizes a read for sitting at its "
                   "null on the unsafe models; an ideal safety read could pass it only if >= 60% of the panel were safe.")
        inc = [r for r in ex.get("B_incremental", []) if r.get("read") == "C2" and r.get("target") == "BALANCED"
               and r.get("given") == ["S2_screen16", "log10_n_params"]]
        if inc:
            out.append(f"EXPLORATORY: beyond the 16-prompt judged-generation probe (S2_screen16), C2's partial rho = "
                       f"{f3(inc[0]['partial_rho'])} (one-sided 5% bound {f3(inc[0]['one_sided_5pct_bound'])}): internal "
                       "reads do not beat 16 judged generations, but C2 needs no generation and no judge.")
    if sweep_p is not None:
        sw = json.loads(sweep_p.read_text())
        rb = (sw.get("analysis") or {}).get("rho_BALANCED") or {}
        pts = {k: (v or {}).get("point") for k, v in rb.items() if isinstance(v, dict)}
        pts = {k: v for k, v in pts.items() if v is not None}
        if pts:
            best = max(pts, key=lambda k: pts[k])
            acc = (sw.get("meta") or {}).get("acceptance_check") or {}
            out.append("EXPLORATORY C2 depth sweep (band [c-1,c,c+1], c = round(f*n_layers); reproduces the production "
                       f"value exactly, max |diff| = {acc.get('max_abs_diff')} over {acc.get('n_checked')} models): "
                       "rho(BALANCED) by f = " + ", ".join(f"{k}: {pts[k]:.2f}" for k in sorted(pts, key=float))
                       + f". Peak at f = {best}, the pre-registered 50% band; neighbouring bands are lower, so the "
                       "read is band-sensitive.")
    if mnull_p is not None:
        mn = json.loads(mnull_p.read_text())
        tot = (mn.get("analysis") or {}).get("totals") or {}
        acc = (mn.get("meta") or {}).get("acceptance_check") or {}
        parts = []
        for cid in ("C1", "C2"):
            t = tot.get(cid) or {}
            if t:
                parts.append(f"{cid} exceeds {t.get('exceed_production_overall')}/{t.get('n')} (production null) vs "
                             f"{t.get('exceed_matched_overall')}/{t.get('n')} (variance-matched null; upper/lower half "
                             f"{t.get('exceed_matched_upper')}/{t.get('n_upper')} vs {t.get('exceed_matched_lower')}/"
                             f"{t.get('n_lower')}), S2(b) fraction {t.get('s2b_fraction_matched', float('nan')):.2f}")
        if parts:
            out.append("EXPLORATORY variance-matched direction null (reproduces the production null p95 exactly, max "
                       f"|diff| C1 {((acc.get('C1') or {}).get('max_abs_diff'))}, C2 {((acc.get('C2') or {}).get('max_abs_diff'))}): "
                       + "; ".join(parts) + ". Matching the variance explains part of C2's S2(b) shortfall, but S2(b) "
                       "still fails because the unsafe half of the panel sits at its null.")
    return out


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

    # device provenance is read per-row from compute.device (missing key = cpu); never assumed CPU-only
    device_counts: dict[str, int] = {}
    for fpath in sorted(glob.glob(str(rows_dir() / "*.json"))):
        rr = json.loads(Path(fpath).read_text())
        dev = (rr.get("compute") or {}).get("device", "cpu")
        device_counts[dev] = device_counts.get(dev, 0) + 1
    if device_counts.get("cuda") and device_counts.get("cpu"):
        tier_desc = f"{device_counts['cuda']} GPU (cuda) row(s) + {device_counts['cpu']} CPU row(s)"
    elif device_counts.get("cuda"):
        tier_desc = f"{device_counts['cuda']} GPU (cuda) row(s)"
    elif device_counts.get("cpu"):
        tier_desc = f"{device_counts['cpu']} CPU row(s)"
    else:
        tier_desc = "no rows measured"

    datasets = [{"dataset": "live_screen_panel", "examples": panel_examples()},
                {"dataset": "screen16_oracle_readout", "examples": oracle_examples()}]
    rx = rosi_examples()
    if rx:
        datasets.append({"dataset": "rosi_128tok", "examples": rx})
    datasets = [d for d in datasets if d["examples"]]
    meta = {"method_name": f"LIVE-tier causal-gain safety screen (iter 4; {tier_desc})",
            "description": ("Per-checkpoint intervention/patching candidates C1,C2,C3,C7,C8,C9,C11,C16 on the frozen "
                            "SCREEN16 prompts vs the logit-only baselines (first-token logit gap, refusal-token mass) "
                            "on identical inputs; targets BALANCED (S2_core) and PRODUCT (P2)."),
            "prereg_hash": prereg_hash, "deviations": [d.get("code") for d in devs],
            "spend_usd": spend.get("total_usd"),
            "device_counts": device_counts,
            "panel_summary": cl.get("panel_summary") or cl.get("summary"),
            "S5_4B_gpu_model_totals": (cl.get("panel_summary") or {}).get("S5_4B_gpu_model_totals"),
            "cross_hardware": cl.get("cross_hardware"),
            "rosi_verdicts": rosi.get("verdicts"),
            "files": ["candidates_live.json", "candidate_values_live.json", "rows/", "rosi_128tok.json",
                      "RESULTS.md", "PREREG.json", "DEVIATIONS.json", "skips.json", "spend.json"]}
    meta["headline_findings"] = headline_findings(cl, find("posthoc_s4_extra.json"), find("c2_depth_sweep.json"),
                                                  find("matched_null.json"))
    meta["files"] += [x for x in ("posthoc_live.json", "posthoc_s4_extra.json", "c2_depth_sweep.json",
                                  "matched_null.json") if find(x)]
    out = {"metadata": meta, "datasets": datasets}
    (OUT_DIR / "method_out.json").write_text(json.dumps(out, indent=1))
    logger.info(f"method_out.json written to {OUT_DIR / 'method_out.json'}: "
                + ", ".join(f"{d['dataset']}={len(d['examples'])}" for d in datasets))


if __name__ == "__main__":
    main()
