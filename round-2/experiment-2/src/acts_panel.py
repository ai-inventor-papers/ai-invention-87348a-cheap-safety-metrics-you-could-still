#!/usr/bin/env python3
"""STAGE 1b -- the ACTIVATION half of the honest panel, at zero forward-pass cost.

Iteration 1 left 17 finished harvests on disk: hidden states at every layer for
160 pre-registered items at the last prompt token AND the first generated
position, first-token logit features, presentation-shifted repeats, the
always-refuse / never-refuse poles, and 80 greedy generations per checkpoint.
Every activation-side row of the frozen 50-metric registry is a pure numpy read
of those arrays.

THE ASYMMETRY IS STATED ON EVERY ROW AND IT IS NOT A DETAIL.  All 17 harvests
are Qwen3, Qwen2.5 or TinyLlama, so the activation-side honest-panel accuracies
are WITHIN-FAMILY NUMBERS ONLY.  The weight-side accuracies, computed over the
streamed cache panel, span seven architecture families.  Comparing the two
columns without saying this would be the central error available in this study.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))

import screen.common as SC  # noqa: E402

HARVEST_ROOT = Path(
    "/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_1/gen_art"
    "/gen_art_experiment_1/harvest"
)
# The inherited reads module resolves the harvest directory from its own package
# root.  Repoint it at iteration 1's tree rather than copying 1.5 GB of arrays
# into this workspace; nothing is written there.
SC.HARVEST = HARVEST_ROOT

import screen.reads as RD  # noqa: E402

RD.HARVEST = HARVEST_ROOT

from flab2 import panel as P  # noqa: E402

OUT = WORKSPACE / "out"
ACTS_DIR = OUT / "acts_panel"
LOGS = WORKSPACE / "logs"
for d in (OUT, ACTS_DIR, LOGS):
    d.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(LOGS / "acts_panel.log", rotation="30 MB", level="DEBUG")


def card_text_for(repo: str, snapshot: Path | None) -> str:
    """The model card as a blind auditor would receive it (may be empty)."""
    if snapshot is None:
        return ""
    p = snapshot / "README.md"
    try:
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
    except OSError:
        return ""


@logger.catch(reraise=True)
def main() -> None:
    t0 = time.time()
    items = json.loads((WORKSPACE / "items_160.json").read_text())["items"]
    logger.info(f"item registry: {len(items)} pre-registered items")

    census = {}
    cpath = OUT / "cache_census.json"
    if cpath.exists():
        census = {
            r["repo_id"]: r for r in json.loads(cpath.read_text())["repos"]
        }

    dirs = [
        d
        for d in sorted(HARVEST_ROOT.iterdir())
        if d.is_dir() and (d / "DONE").exists() and (d / "acts.npz").exists()
    ]
    logger.info(f"{len(dirs)} finished harvests with activations")

    rng = np.random.default_rng(SC.SEED)
    done, failed = 0, 0
    for d in dirs:
        slug = d.name
        outp = ACTS_DIR / f"{slug}.json"
        if outp.exists():
            done += 1
            continue
        try:
            t = time.time()
            hv = RD.load_harvest(slug)
            repo = hv["meta"]["repo_id"]
            rec = census.get(repo)
            snap = Path(rec["snapshot_dir"]) if rec and rec.get("snapshot_dir") else None
            card = card_text_for(repo, snap)
            res = RD.compute_metrics(
                hv, items, card_text=card, judge=None, rng=rng
            )
            metrics = {
                k: (float(v) if np.isfinite(v) else None)
                for k, v in res["metrics"].items()
                if isinstance(v, (int, float, np.floating, np.integer))
            }
            diag = res.get("diagnostics", {})
            fam = P.family_of(repo, hv["meta"].get("architecture"))
            tmpl = hv["meta"].get("template", {}) or {}
            has_ct = bool(
                tmpl.get("has_tokenizer_config_template")
                or tmpl.get("has_standalone_jinja")
            )
            row = {
                "repo": repo,
                "slug": slug,
                "source": "harvest_activations",
                "family": fam,
                "lineage": P.lineage_of(repo, fam, hv["meta"].get("n_layers", 0)),
                "declared_label": P.card_label(repo, card, has_chat_template=has_ct),
                "n_layers": hv["meta"].get("n_layers"),
                "d_model": hv["meta"].get("hidden_size"),
                "n_items": int(hv["a"]["hs_last"].shape[0]),
                "metrics": metrics,
                "n_metrics": len(metrics),
                "within_family_only": True,
                "scope_note": (
                    "ACTIVATION-SIDE ONLY. All finished harvests are Qwen3, "
                    "Qwen2.5 or TinyLlama, so any honest-panel accuracy derived "
                    "from this row is a WITHIN-FAMILY number, not a "
                    "cross-family one."
                ),
                "seconds": round(time.time() - t, 2),
            }
            outp.write_text(json.dumps(row, indent=1, default=float))
            # the architecture-free descriptor, the per-item refusal drive and
            # the per-item harm posterior are what the C5 metamodel rows read,
            # so they are persisted beside the scalars rather than recomputed.
            (ACTS_DIR / f"{slug}__diag.json").write_text(
                json.dumps(
                    {
                        "diagnostics": diag,
                        "features": res.get("features"),
                        "g": res.get("g"),
                        "p_all": res.get("p_all"),
                    },
                    indent=1,
                    default=float,
                )
            )
            done += 1
            logger.info(
                f"[{done}/{len(dirs)}] {repo:<50} {row['declared_label']:<12} "
                f"n_metrics={len(metrics)} "
                f"gap={metrics.get('b_logit_gap_mean', float('nan')):.3f} "
                f"spread={metrics.get('x_decision_spread', float('nan')):.3f} "
                f"c1r2={metrics.get('x_c1_r2', float('nan')):.3f} "
                f"({row['seconds']}s)"
            )
            del hv, res
        except (OSError, ValueError, KeyError, IndexError) as exc:
            failed += 1
            logger.error(f"{slug}: {type(exc).__name__}: {exc}")
        gc.collect()

    (OUT / "acts_panel_status.json").write_text(
        json.dumps(
            {"n_rows": done, "n_failed": failed,
             "minutes": round((time.time() - t0) / 60, 2)},
            indent=1,
        )
    )
    logger.info(f"ACTS PANEL DONE n={done} failed={failed} "
                f"in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
