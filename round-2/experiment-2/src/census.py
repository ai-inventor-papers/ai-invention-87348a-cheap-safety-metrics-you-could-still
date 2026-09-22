#!/usr/bin/env python3
"""Enumerate the local HuggingFace cache and decide what is auditable.

`usable` means: dense safetensors present on disk, a config with a layer count,
and a residual-write matrix this reader can locate by name.  Quantized,
vision/audio/embedding and adapter-only repositories are excluded WITH A REASON,
because a silent exclusion would change the honest null without saying so.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))
from flab2 import repo_io as R

CACHE = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/.shared_cache/hf/hub")
BAD_NAME = ("gguf", "-mlx", "mlx-", "awq", "gptq", "fp8", "nvfp4", "bnb-4bit",
            "w4a16", "w8a8", "exl3", "exl2", "quantized", "-int4", "-int8",
            "4bit", "8bit", "3bit", "-qat", "bpw", "mxfp4", "optiq", "-ggml")
BAD_ARCH = ("VL", "Vision", "TTS", "ASR", "Embedding", "Reranker", "CLIP",
            "Whisper", "ForSequenceClassification", "Blip", "Llava", "Omni")


def main() -> None:
    t0 = time.time()
    repos, n = [], 0
    for dd in sorted(CACHE.glob("models--*")):
        n += 1
        repo = dd.name[len("models--"):].replace("--", "/")
        rec = {"repo_id": repo, "snapshot_dir": None, "usable": False,
               "files_present": False, "exclude_reason": None}
        low = repo.lower()
        hit = next((b for b in BAD_NAME if b in low), None)
        if hit:
            rec["exclude_reason"] = f"name marks a quantized/converted mirror ('{hit}')"
            repos.append(rec); continue
        snap = R.snapshot_dir(CACHE, repo)
        if snap is None:
            rec["exclude_reason"] = "no snapshot directory"
            repos.append(rec); continue
        rec["snapshot_dir"] = str(snap)
        cfgp = snap / "config.json"
        if not cfgp.exists():
            rec["exclude_reason"] = "no config.json"
            repos.append(rec); continue
        try:
            cfg = json.loads(cfgp.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            rec["exclude_reason"] = f"unreadable config.json: {exc}"
            repos.append(rec); continue
        arch = (cfg.get("architectures") or [None])[0]
        rec.update({"model_type": cfg.get("model_type"), "arch": arch,
                    "n_layers": cfg.get("num_hidden_layers"),
                    "hidden_size": cfg.get("hidden_size"),
                    "tie_word_embeddings": cfg.get("tie_word_embeddings")})
        if arch and any(b.lower() in arch.lower() for b in BAD_ARCH):
            rec["exclude_reason"] = f"architecture {arch} is not a text decoder"
            repos.append(rec); continue
        if not cfg.get("num_hidden_layers"):
            rec["exclude_reason"] = "config has no num_hidden_layers"
            repos.append(rec); continue
        sts = list(snap.glob("*.safetensors"))
        if not sts:
            rec["exclude_reason"] = "no .safetensors on disk"
            repos.append(rec); continue
        try:
            nb = sum(f.resolve().stat().st_size for f in sts)
        except OSError as exc:
            rec["exclude_reason"] = f"broken blob symlink: {exc}"
            repos.append(rec); continue
        rec["safetensors_bytes"] = int(nb)
        rec["files_present"] = True
        try:
            idx = R.build_index(snap)
        except (OSError, ValueError) as exc:
            rec["exclude_reason"] = f"unreadable safetensors header: {exc}"
            repos.append(rec); continue
        qr = R.quantization_reason(idx)
        if qr:
            rec["exclude_reason"] = qr
            repos.append(rec); continue
        o, d = R.residual_write_refs(idx)
        if not o or not d:
            rec["exclude_reason"] = "no residual-write matrices locatable by name"
            repos.append(rec); continue
        tc = snap / "tokenizer_config.json"
        has_ct = False
        if (snap / "chat_template.jinja").exists():
            has_ct = True
        elif tc.exists():
            try:
                has_ct = bool(json.loads(tc.read_text()).get("chat_template"))
            except (OSError, json.JSONDecodeError):
                has_ct = False
        rec.update({"usable": True, "n_o_proj": len(o), "n_down_proj": len(d),
                    "has_chat_template": has_ct, "n_tensors": len(idx)})
        repos.append(rec)
    usable = [r for r in repos if r["usable"]]
    out = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_scanned": n,
           "n_usable": len(usable), "seconds": round(time.time()-t0, 1),
           "repos": repos}
    (WORKSPACE / "out" / "cache_census.json").write_text(json.dumps(out, indent=1))
    print(f"scanned {n}, usable {len(usable)}, {time.time()-t0:.0f}s")
    from collections import Counter
    print(Counter(r.get("model_type") for r in usable))


if __name__ == "__main__":
    main()
