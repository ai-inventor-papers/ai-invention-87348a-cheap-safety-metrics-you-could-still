#!/usr/bin/env python3
"""ONE forward pass, purely to locate the F2a carrier coordinate.

F2a is the rung that matters most to the undetectable-cost column: it delivers a
constant residual offset WITHOUT adding a parameter, so the key/shape screen is
structurally blind to it.  Building it needs the per-coordinate mean and sd of
`down_proj`'s INPUT over the item set, which is the one thing no stored harvest
contains -- iteration 1 saved residual-stream states, not MLP intermediates.

So this script does the minimum that unlocks the rung: load the smallest host,
push a handful of prompts through with forward hooks on every `down_proj`, and
write `out/carrier.json`.  No generation, no metrics, no judge.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
os.environ.setdefault("TORCHINDUCTOR_DISABLE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import torch
from loguru import logger

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WORKSPACE / "logs" / "carrier.log", rotation="10 MB", level="DEBUG")

import behaviour as B  # noqa: E402


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="Qwen/Qwen3-0.6B")
    ap.add_argument("--n-items", type=int, default=6)
    ap.add_argument("--batch", type=int, default=3)
    args = ap.parse_args()
    torch.set_num_threads(2)

    out = WORKSPACE / "out" / "carrier.json"
    allc = json.loads(out.read_text()) if out.exists() else {}
    if args.host in allc:
        logger.info(f"{args.host} already probed")
        return

    items = json.loads((WORKSPACE / "items_160.json").read_text())["items"]
    prompts = [it["prompt"] for it in items
               if it["kind"] in ("harmful", "benign_alarming")][: args.n_items]
    t = time.time()
    model, tok = B.load_model(args.host)
    logger.info(f"loaded {args.host} in {time.time()-t:.0f}s")
    rend = B.render(tok, prompts)
    t = time.time()
    info = B.carrier_probe(model, tok, rend, batch_size=args.batch)
    info["seconds"] = round(time.time() - t, 1)
    info["n_prompts"] = len(prompts)
    allc[args.host] = info
    out.write_text(json.dumps(allc, indent=1, default=float))
    logger.info(
        f"carrier: layer {info.get('layer')} coord {info.get('carrier_index')} "
        f"CV={info.get('carrier_cv'):.5g} mean={info.get('carrier_mean'):.4g} "
        f"peak/median={info.get('peak_over_median_ratio'):.1f} "
        f"1000x_met={info.get('literature_1000x_criterion_met')} "
        f"mag100_met={info.get('literature_magnitude_100_met')} "
        f"({info['seconds']}s)")


if __name__ == "__main__":
    main()
