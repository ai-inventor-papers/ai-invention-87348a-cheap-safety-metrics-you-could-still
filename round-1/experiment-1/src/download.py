#!/usr/bin/env python3
"""Streamed panel downloader: safetensors + configs only, 3 workers, resumable."""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from huggingface_hub import snapshot_download

ALLOW = ["*.safetensors", "*.safetensors.index.json", "config.json", "generation_config.json",
         "tokenizer*.json", "tokenizer.model", "vocab.json", "merges.txt",
         "special_tokens_map.json", "*.jinja", "README.md"]
IGNORE = ["*.gguf", "*.bin", "*.pth", "*.onnx", "consolidated*", "*.msgpack", "*.h5"]

def fetch(repo: str) -> dict:
    t0 = time.time()
    for attempt in range(3):
        try:
            p = snapshot_download(repo, allow_patterns=ALLOW, ignore_patterns=IGNORE,
                                  max_workers=4)
            gb = sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file()) / 1e9
            return {"repo": repo, "ok": True, "path": p, "gb": round(gb, 2),
                    "secs": round(time.time() - t0, 1)}
        except Exception as e:
            if attempt == 2:
                return {"repo": repo, "ok": False, "error": f"{type(e).__name__}: {e}"[:300],
                        "secs": round(time.time() - t0, 1)}
            time.sleep(5 * (attempt + 1))
    return {"repo": repo, "ok": False, "error": "unreachable"}

def main() -> None:
    repos = json.loads(Path(sys.argv[1]).read_text())
    out_path = Path(sys.argv[2])
    done = json.loads(out_path.read_text()) if out_path.exists() else {}
    todo = [r for r in repos if r not in done or not done[r].get("ok")]
    print(f"downloading {len(todo)} of {len(repos)} repos", flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(fetch, r): r for r in todo}
        for f in as_completed(futs):
            res = f.result()
            done[res["repo"]] = res
            out_path.write_text(json.dumps(done, indent=2))
            print(("OK  " if res["ok"] else "FAIL") + f" {res['repo']} "
                  + (f"{res.get('gb')}GB in {res['secs']}s" if res["ok"] else res.get("error", "")),
                  flush=True)

if __name__ == "__main__":
    main()
