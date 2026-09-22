#!/usr/bin/env python3
"""The inherited ACTIVATION battery, recomputed on every edited copy -- zero new definitions.

Each full behavioural cell written by behave2.py is a harvest in iteration 1's
exact format (same 160 items, same token sets, same last-prompt-token and
first-generated-position residuals, same logit features, greedy continuations for
the 96 graded items). So `screen.reads.compute_metrics` -- the function that
produced the n=17 activation panel -- is called on it UNCHANGED, and every
activation / black-box row of the frozen registry gets a value AFTER each rung
with the same definition that sets its honest-panel threshold.

What is deliberately NOT recomputed here: weight rows (the ladder cells carry
those) and the model-card regex rows (a behavioural cell has no card; F0's card
forgery is scored by the blind screen's B1 on the ladder side).

    pyenv/bin/python bcell_acts.py            # every full cell not yet done
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))

import screen.reads as RD  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WORKSPACE / "logs" / "bcell_acts.log", rotation="30 MB", level="DEBUG")

OUT = WORKSPACE / "out"
SEED = 20260920
SKIP_PREFIX = ("w_", "_bsa", "b_card_regex")


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def acts_for(cell_json: Path, items: list[dict], dst: Path) -> dict | None:
    rec = json.loads(cell_json.read_text())
    npz = cell_json.with_suffix(".npz")
    if rec.get("mode", "full") != "full" or not npz.exists():
        return None
    with np.load(npz) as z:
        a = {"hs_last": z["hs_last"], "hs_first": z["hs_first"],
             "logit_feats": z["logit_feats"]}
    gen_items = rec["items"]
    hv = {
        "meta": {"repo_id": rec["host"], "n_layers": int(a["hs_last"].shape[1] - 1),
                 "hidden_size": int(a["hs_last"].shape[2])},
        "w": {},
        "a": a,
        "gen": {"gen_item_idx": [int(it["idx"]) for it in gen_items],
                "generations": [it["response"] or "" for it in gen_items]},
    }
    t0 = time.time()
    res = RD.compute_metrics(hv, items, card_text="", judge=None,
                             rng=np.random.default_rng(SEED))
    metrics = {k: (float(v) if isinstance(v, (int, float, np.floating, np.integer))
                   and np.isfinite(v) else None)
               for k, v in res["metrics"].items()
               if not k.startswith(SKIP_PREFIX)
               and isinstance(v, (int, float, np.floating, np.integer))}
    diag = res.get("diagnostics", {})
    out = {"cell_id": rec["cell_id"], "host": rec["host"], "family": rec["family"],
           "rung": rec["rung"], "magnitude": rec["magnitude"], "metrics": metrics,
           "n_metrics": sum(v is not None for v in metrics.values()),
           "readout_auroc_vs_regex_refusal": diag.get("readout_auroc_vs_judge"),
           "refusal_rate_graded_regex": diag.get("refusal_rate_graded"),
           "definition_source": "screen.reads.compute_metrics (unchanged; same as the acts panel)",
           "seconds": round(time.time() - t0, 1)}
    dst.write_text(json.dumps(clean(out), indent=1))
    return out


@logger.catch(reraise=True)
def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "bcells"
    dst_dir = OUT / ("bcells_acts" if src.name == "bcells" else f"{src.name}_acts")
    dst_dir.mkdir(parents=True, exist_ok=True)
    items = json.loads((WORKSPACE / "items_160.json").read_text())["items"]
    n = 0
    for p in sorted(src.glob("*.json")):
        if "__F" not in p.stem or p.stem.endswith(("_equivalence", "_recovery")):
            continue
        dst = dst_dir / p.name
        if dst.exists():
            continue
        try:
            r = acts_for(p, items, dst)
        except (KeyError, ValueError, IndexError, np.linalg.LinAlgError) as exc:
            logger.error(f"{p.name}: {type(exc).__name__}: {exc}")
            continue
        if r:
            n += 1
            logger.info(f"{p.stem:<60} {r['n_metrics']} metrics ({r['seconds']}s) "
                        f"readout_auroc={r['readout_auroc_vs_regex_refusal']}")
    logger.info(f"bcell_acts: {n} new cells")


if __name__ == "__main__":
    main()
