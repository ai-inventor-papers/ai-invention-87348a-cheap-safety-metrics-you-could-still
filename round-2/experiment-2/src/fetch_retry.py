#!/usr/bin/env python3
"""Per-file retry for repositories whose snapshot_download returned no weights.

`snapshot_download(allow_patterns=...)` returned instantly with only the small
text files for most targets, leaving the safetensors absent.  Resolving each
weight file by name with `hf_hub_download` is slower but deterministic, and the
files it writes land in the same cache layout the rest of the run reads.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"
from loguru import logger

WORKSPACE = Path(__file__).resolve().parent
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WORKSPACE / "logs" / "fetch_retry.log", rotation="10 MB", level="DEBUG")

TARGETS = [
    "huihui-ai/Llama-3.2-3B-Instruct-abliterated",
    "mylesgoose/Llama-3.2-1B-Instruct-abliterated",
    "Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct-abliterated",
    "microsoft/Phi-3.5-mini-instruct",
    "tiiuae/Falcon3-1B-Instruct",
    "h2oai/h2o-danube3-500m-chat",
    "stabilityai/stablelm-2-1_6b-chat",
    "unsloth/gemma-2b-it",
    "huihui-ai/Qwen2.5-1.5B-Instruct-CensorTune",
    "UnfilteredAI/DAN-Qwen3-1.7B",
    "unsloth/Llama-3.2-3B-Instruct",
    "banghua/Qwen3-0.6B-SFT",
    "allenai/OLMo-2-0425-1B-RLVR1",
    "tiiuae/Falcon3-3B-Instruct",
]
SMALL = ("config.json", "tokenizer_config.json", "generation_config.json",
         "chat_template.jinja", "README.md")
MAX_BYTES = 9.0e9


def main() -> None:
    from huggingface_hub import HfApi, hf_hub_download
    from huggingface_hub.utils import HfHubHTTPError
    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token)
    res = []
    t0 = time.time()
    for repo in TARGETS:
        rec = {"repo": repo, "ok": False, "files": 0, "bytes": 0}
        try:
            info = api.model_info(repo, files_metadata=True)
            sib = {s.rfilename: (s.size or 0) for s in info.siblings}
            want = [f for f in sib if f.endswith(".safetensors")
                    or f.endswith(".safetensors.index.json")]
            total = sum(sib[f] for f in want)
            if total > MAX_BYTES:
                rec["skip"] = f"{total/1e9:.1f} GB exceeds the {MAX_BYTES/1e9:.0f} GB cap"
                res.append(rec); logger.warning(f"SKIP {repo}: {rec['skip']}"); continue
            for f in want + [s for s in SMALL if s in sib]:
                try:
                    p = hf_hub_download(repo, f, token=token)
                    rec["files"] += 1
                    rec["bytes"] += Path(p).stat().st_size
                except (HfHubHTTPError, OSError) as exc:
                    logger.debug(f"{repo}:{f} {type(exc).__name__}")
            rec["ok"] = rec["files"] > 0 and rec["bytes"] > 1e6
            logger.info(f"{'OK  ' if rec['ok'] else 'PART'} {repo:<50} "
                        f"{rec['files']} files {rec['bytes']/1e9:5.2f} GB")
        except (HfHubHTTPError, OSError, ValueError) as exc:
            rec["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
            logger.warning(f"FAIL {repo}: {rec['error']}")
        res.append(rec)
        (WORKSPACE / "out" / "fetch_retry.json").write_text(
            json.dumps({"results": res,
                        "minutes": round((time.time()-t0)/60, 2)}, indent=1))
    logger.info(f"RETRY DONE {sum(1 for r in res if r['ok'])}/{len(TARGETS)} "
                f"in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
