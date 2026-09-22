"""Pre-fetch weights for stage 3/5 repos not yet in the shared HF cache (network-bound; run with nice).
Same allow-patterns as live_lib.ensure_local; the seal guard in live_lib.load_model still runs before any load."""
import sys, time
from huggingface_hub import snapshot_download
SEALED = ("ibm-granite/", "stabilityai/stablelm")
pats = ["*.json", "*.safetensors", "tokenizer*", "*.model", "*.txt", "README.md"]
for repo in sys.argv[1:]:
    assert not any(repo.lower().startswith(s) for s in SEALED), repo
    t0 = time.time()
    for a in range(3):
        try:
            d = snapshot_download(repo, allow_patterns=pats)
            print(f"OK {repo} {time.time()-t0:.0f}s {d}", flush=True)
            break
        except Exception as e:
            print(f"FAIL attempt {a+1} {repo}: {type(e).__name__}: {e}", flush=True)
            time.sleep(10 * (a + 1))
