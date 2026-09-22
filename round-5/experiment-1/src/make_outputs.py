#!/usr/bin/env python3
"""STEP 9 -- method_out.json (exp_gen_sol_out) + full_/mini_/preview_ variants.

Two datasets:
  checkpoint_candidate_values   one example per measured checkpoint. input = the HuggingFace repo id,
                                output = a JSON string of that checkpoint's candidate values, predict_<cand> =
                                each candidate's plain (primary) value as a string, metadata_* = family, lineage,
                                class, n_params, setA flag, AMS verdict, timings, and the label ONLY for the
                                23 graded checkpoints (Set A is measured blind: no label exists at write time).
  screen16_readout              one example per (checkpoint, SCREEN16 item): input = the prompt, output = the
                                judged stance of the model's own 64-token reply ("refused"/"complied"/"unparsed"),
                                metadata = the first-token refuse-minus-comply margin, refusal mass and the reply.

Run AFTER the panel and the analysis. Never reads a Set A label (none exists in this workspace).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import blind_guard

blind_guard.install()

from loguru import logger  # noqa: E402

WS = Path(__file__).resolve().parent
ROWS = WS / "rows"
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "make_outputs.log", rotation="10 MB", level="DEBUG")

CANDS = ["C1", "C2", "C1n_cd", "C1n_os", "C6", "C6_insample", "C6_lens", "C10", "C12", "C12r", "C13", "C13_rank",
         "C13_logit", "C15_erank", "C15_disp", "C11", "AMS_published", "AMS_mean3", "AMS_cf_layer", "AMS_cf_sweep",
         "AMS_screen16", "logit_gap", "refusal_mass", "logit_gap_level", "refusal_mass_level"]
VARIANTS = ["value", "pole_refuse", "pole_comply", "k8", "offset_late", "offset_mid",
            "null_mean", "null_median", "null_p95", "eps_0.02", "eps_0.05", "eps_0.1"]


def fnum(x: object) -> float | None:
    try:
        v = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def s(x: object) -> str:
    v = fnum(x)
    return "" if v is None else repr(v)


def rows() -> list[dict]:
    out = []
    for p in sorted(ROWS.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            logger.error(f"unreadable row {p}")
    return out


def status_of(r: dict, setA: list[str]) -> str:
    if r.get("stratum") == "base":
        return "base"
    return "setA" if r["repo"] in setA else ("graded" if r.get("graded") else "ungraded_other")


def main() -> None:
    prereg = json.loads((WS / "PREREG.json").read_text())
    setA = list(prereg["panel"]["setA"])
    rr = rows()
    logger.info(f"{len(rr)} rows")
    ex_ckpt, ex_item = [], []
    for r in rr:
        cands = r.get("candidates") or {}
        st = status_of(r, setA)
        vals = {}
        for c in CANDS:
            d = cands.get(c)
            if not isinstance(d, dict):
                continue
            vals[c] = {k: fnum(d.get(k)) for k in VARIANTS if k in d}
            vals[c]["undefined_reason"] = d.get("reason")
        ex = {
            "input": r["repo"],
            "output": json.dumps(vals, sort_keys=True),
            "metadata_repo": r["repo"], "metadata_resolved_sha": r.get("resolved_sha"),
            "metadata_family": r.get("family"), "metadata_lineage": r.get("lineage"), "metadata_class": r.get("class"),
            "metadata_n_params": r.get("n_params"), "metadata_stratum": r.get("stratum"),
            "metadata_status": st, "metadata_setA": st == "setA",
            "metadata_n_layers": r.get("n_layers"), "metadata_d_model": r.get("d_model"),
            "metadata_bands": r.get("bands"), "metadata_tier": r.get("tier"),
            "metadata_prereg_hash": r.get("prereg_hash"), "metadata_code_hash": r.get("code_hash"),
            "metadata_seconds_shared": fnum(r.get("seconds_shared")),
            "metadata_seconds_total_after_load": fnum((r.get("timing") or {}).get("total_after_load_s")),
            "metadata_candidate_seconds": r.get("candidate_seconds"),
            "metadata_vram_peak_gb": fnum((r.get("compute") or {}).get("vram_peak_gb")),
            "metadata_ams_verdict": ((r.get("ams") or {}).get("summary") or {}).get("verdict"),
            "metadata_ams_path_used": (r.get("ams") or {}).get("path_used"),
            "metadata_ams_package": (r.get("ams") or {}).get("package"),
            "metadata_flags": r.get("flags"),
            "metadata_screen16_judged_harm_refusal": fnum((r.get("oracle") or {}).get("judged_harm_refusal")),
            "metadata_screen16_judged_twin_refusal": fnum((r.get("oracle") or {}).get("judged_twin_refusal")),
        }
        if st == "graded":  # the label exists ONLY for the 23 graded checkpoints
            ex["metadata_BALANCED"] = fnum(r.get("BALANCED"))
            ex["metadata_PRODUCT"] = fnum(r.get("PRODUCT"))
        for c in CANDS:
            d = cands.get(c)
            if isinstance(d, dict):
                ex[f"predict_{c.replace('.', '_')}"] = s(d.get("value"))
        ex_ckpt.append(ex)
        # per-item readout
        y = (r.get("oracle") or {}).get("judged_refusal") or []
        margins = ((r.get("conditions") or {}).get("plain") or {}).get("margins") or []
        mass = ((r.get("conditions") or {}).get("plain") or {}).get("mass") or []
        for i, g in enumerate(r.get("gen64") or []):
            lab = ("refused" if (i < len(y) and y[i] == 1) else "complied" if (i < len(y) and y[i] == 0) else "unparsed")
            ex_item.append({
                "input": g.get("prompt") or g.get("pair_id", "") + ":" + g.get("side", ""),
                "output": lab,
                "metadata_repo": r["repo"], "metadata_pair_id": g.get("pair_id"), "metadata_side": g.get("side"),
                "metadata_status": st, "metadata_setA": st == "setA",
                "metadata_reply": (g.get("text") or "")[:1200], "metadata_n_tokens": g.get("n_tokens"),
                "metadata_margin_refuse_minus_comply": fnum(margins[i]) if i < len(margins) else None,
                "metadata_refusal_mass": fnum(mass[i]) if i < len(mass) else None,
                # logit-only per-item baseline: does the first-token refuse-minus-comply margin predict the
                # judged stance of the model's own reply? (this is the readout-validity check, per item)
                "predict_logit_margin_stance": ("refused" if (i < len(margins) and fnum(margins[i]) is not None
                                                              and float(margins[i]) > 0) else "complied"),
            })
    # the SCREEN16 prompts are not stored per row; fill them from the frozen substrate
    d3 = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_3/gen_art/gen_art_dataset_1")
    s16 = [json.loads(l) for l in (d3 / "screen16.jsonl").read_text().splitlines() if l.strip()]
    by_key = {(x["pair_id"], x["side"]): x["prompt"] for x in s16}
    for e in ex_item:
        p = by_key.get((e["metadata_pair_id"], e["metadata_side"]))
        if p:
            e["input"] = p
    out = {"metadata": {"method_name": "iter5 GPU tier: C1n random-steer control + C6/C10/C12/C13/C15-act + AMS Tier-1",
                        "run": "run_fcYd_7ruOwtm", "iteration": 5, "tier": "gpu5",
                        "prereg_sha256": (WS / "PREREG_hash.txt").read_text().split()[0],
                        "n_checkpoints": len(ex_ckpt), "n_graded": sum(1 for e in ex_ckpt if e["metadata_status"] == "graded"),
                        "n_setA_blind": sum(1 for e in ex_ckpt if e["metadata_setA"]),
                        "candidates": CANDS, "variants": VARIANTS,
                        "note": ("Set A checkpoints are measured and hashed BEFORE any Set A label exists, so their "
                                 "examples carry no label by construction; the base stratum is excluded from every "
                                 "correlation.")},
            "datasets": [{"dataset": "checkpoint_candidate_values", "examples": ex_ckpt},
                         {"dataset": "screen16_readout", "examples": ex_item}]}
    (WS / "method_out.json").write_text(json.dumps(out, indent=1))
    logger.info(f"method_out.json: {len(ex_ckpt)} checkpoints, {len(ex_item)} item rows")


if __name__ == "__main__":
    main()
