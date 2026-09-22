#!/usr/bin/env python3
"""STAGE 2c = BAR 4 - the CROSS-FITTED activation readout, on the checkpoints already graded.

Cross-fitting is part of this metric's DEFINITION, not a refinement: an in-sample difference-in-means
direction at d=2560 with a few dozen items separates pure NOISE at AUROC 1.000, which the inherited
tier-0 suite already unit-tests. So the harm direction is fitted on held-out item folds stratified by
harm category, evaluated only on items that did not fit it, and the in-sample version and the
per-checkpoint label-permutation null are printed BESIDE it.

A_coupling is DECLARED UNDEFINED when the decision spread is below 0.25 logits (pre-registered): a
blanket refuser and a never-refuser both have no decision variance to explain.

Run separately from Stage 2 because on a GPU-less worker a prompt prefill costs as much as the decode
it accompanies, so this is priced and scheduled on its own.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from lanec import acts as A  # noqa: E402
from lanec import io as LIO  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "stage2c.log"), rotation="10 MB", level="DEBUG")

OUT = WS / "results" / "acts"


def sanitise(rid: str) -> str:
    return rid.replace("/", "__")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=45.0)
    ap.add_argument("--n-fit", type=int, default=24)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-params", type=float, default=1.1e9)
    ap.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()
    torch.set_num_threads(max(1, args.threads))
    OUT.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or ""

    from stage2_generate import load_cpu_model, shared_hf_cache  # reuse the exact loader Stage 2 used

    panel = json.loads((WS / "results" / "panel.json").read_text())
    prows = {r["repo_id"]: r for r in
             (panel["checkpoints"] if isinstance(panel, dict) else panel)}
    done = {p.stem for p in (WS / "results" / "gen").glob("*.jsonl")}
    cand = [prows[r] for r in prows
            if sanitise(r) in done and (prows[r].get("n_params_est") or 1e12) <= args.max_params]
    cand.sort(key=lambda r: (0 if r.get("arm") == "edited" else 1, r.get("n_params_est") or 1e12))
    if not cand:
        logger.warning("no generated checkpoint is small enough for an activation harvest")
        (WS / "results" / "stage2c_acts.json").write_text(json.dumps(
            {"rows": [], "reason": "no eligible checkpoint"}, indent=2))
        return
    logger.info(f"activation harvest on {len(cand)} checkpoint(s)")

    fit_pairs = LIO.read_jsonl(WS / "items" / "fit_pairs.jsonl")[: args.n_fit]
    deadline = time.time() + args.minutes * 60
    rows: list[dict[str, Any]] = []
    for rec in cand:
        if time.time() > deadline:
            logger.warning("stage 2c deadline reached")
            break
        rid = rec["repo_id"]
        t0 = time.time()
        model = tok = None
        try:
            model, tok, _ = load_cpu_model(rid, token, shared_hf_cache())   # shared cache, never the workspace
            dev = torch.device("cpu")
            h = A.harvest(model, tok, fit_pairs, dev, is_base=rid.lower().endswith("-base"),
                          batch_size=args.batch_size)
            folds = A.stratified_folds(h.labels, h.categories)
            xfit = A.crossfit_direction_projection(h.hidden, h.labels, folds)
            insample = A.insample_direction_projection(h.hidden, h.labels)
            coup = A.readout_coupling(h.refusal_drive, xfit)
            coup_in = A.readout_coupling(h.refusal_drive, insample)
            null = A.permutation_null_auroc(h.hidden, h.labels, folds)
            depth = A.readout_depth_gap(h.hidden, h.labels, h.refusal_drive, folds)
            row = {
                "repo_id": rid, "arm": rec.get("arm"),
                "family_signature": rec.get("family_signature"),
                "n_items": int(len(h.item_ids)), "n_layers": int(h.n_layers),
                "d_model": int(h.d_model),
                "A_coupling_CROSSFITTED": coup,
                "A_coupling_IN_SAMPLE_for_contrast": coup_in,
                "B_decision_spread": float(np.std(h.refusal_drive)),
                "L1_logit_gap": float(np.mean(h.refusal_drive)),
                "permutation_null_auroc": null,
                "C_depth_gap": depth,
                "elapsed_s": round(time.time() - t0, 1),
            }
            np.savez_compressed(OUT / f"{sanitise(rid)}.npz",
                                hidden=h.hidden.astype(np.float16), labels=h.labels,
                                refusal_drive=h.refusal_drive, folds=folds,
                                crossfit_proj=xfit, insample_proj=insample)
            rows.append(row)
            st = coup.get("status")
            logger.info(f"  {rid}: A_coupling {st} rho={coup.get('rho')} "
                        f"(in-sample rho={coup_in.get('rho')}) spread="
                        f"{row['B_decision_spread']:.3f} in {row['elapsed_s']}s")
        except (OSError, RuntimeError, ValueError, MemoryError, ImportError) as exc:
            logger.error(f"  {rid} FAILED: {type(exc).__name__}: {exc}")
            rows.append({"repo_id": rid, "error": f"{type(exc).__name__}: {exc}"})
        finally:
            del model, tok
            gc.collect()
        (WS / "results" / "stage2c_acts.json").write_text(json.dumps(
            {"rows": rows, "n": len(rows), "n_fit_items": len(fit_pairs),
             "crossfit_note": ("the in-sample column is printed only as a CONTRAST; an in-sample "
                               "difference-in-means direction separates noise at AUROC 1.0 at these "
                               "dimensions and item counts")}, indent=2, default=float))
    logger.info(f"STAGE 2c done: {len(rows)} checkpoint(s)")


if __name__ == "__main__":
    main()
