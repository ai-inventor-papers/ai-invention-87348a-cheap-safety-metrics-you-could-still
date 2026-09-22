#!/usr/bin/env python3
"""Prefetch the smallest UNCACHED EDITED checkpoints into the run-shared HF cache.

The graded panel is limited by how many EDITED checkpoints can be generated from, and only four of
them were already cached. Downloading is network-bound and barely competes with the two CPU-bound
stages, so it runs alongside them and simply widens the pool Stage 2 can reach.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
from loguru import logger
from huggingface_hub import snapshot_download

WS = Path(__file__).resolve().parent
logger.remove(); logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "prefetch.log"), rotation="10 MB", level="DEBUG")

def main() -> None:
    max_params = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0e9
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    panel = json.loads((WS / "results" / "panel.json").read_text())
    rows = panel["checkpoints"] if isinstance(panel, dict) else panel
    cstat = {c["repo_id"]: c["fully_cached"]
             for c in json.loads((WS / "results" / "cache_status.json").read_text())}
    arm = sys.argv[3] if len(sys.argv) > 3 else "edited"
    want = [r for r in rows
            if (arm == "all" or r.get("arm") == arm)
            and not cstat.get(r["repo_id"])
            and (r.get("n_params_est") or 1e12) <= max_params]
    # mirror STAGE 1's own order (edited first, then size) so the next checkpoint it reaches is
    # already local: a snapshot download runs at 56-76 MB/s here against ~3 MB/s for HTTP Range
    # reads of individual tensor spans, so caching first and reading locally is strictly faster.
    want.sort(key=lambda r: (0 if r.get("arm") == "edited" else 1, r.get("n_params_est") or 1e12))
    logger.info(f"prefetching up to {len(want)} edited checkpoints <= {max_params/1e9:.1f}B")
    deadline = time.time() + minutes * 60
    done = []
    for r in want:
        if time.time() > deadline:
            logger.warning("prefetch deadline reached"); break
        rid = r["repo_id"]
        t0 = time.time()
        try:
            snapshot_download(rid, token=token, max_workers=4,
                              allow_patterns=["*.safetensors", "*.json", "*.txt", "*.model",
                                              "tokenizer*"])
            dt = time.time() - t0
            mb = (r.get("total_safetensors_bytes") or 0) / 1e6
            logger.info(f"  OK {rid} {mb:.0f} MB in {dt:.0f}s = {mb/max(dt,1e-9):.1f} MB/s")
            done.append({"repo_id": rid, "seconds": round(dt, 1), "mb": round(mb, 1)})
        except (OSError, ValueError, RuntimeError) as exc:
            logger.warning(f"  FAIL {rid}: {type(exc).__name__}: {exc}")
        (WS / "results" / "prefetch.json").write_text(json.dumps(done, indent=2))
    logger.info(f"prefetch done: {len(done)} checkpoints")

if __name__ == "__main__":
    main()
