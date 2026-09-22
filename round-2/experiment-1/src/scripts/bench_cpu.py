#!/usr/bin/env python3
"""Micro-benchmark: can this 2-thread CPU box afford a tier-G (acts + generation) harvest?

Times, for one checkpoint and both dtypes: model load, a batched prefill with
output_hidden_states on real battery prompts, and a short batched greedy decode.
Writes results/bench_cpu.json. Used ONLY to decide the queue; never scored.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import torch
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")


@logger.catch(reraise=True)
def main() -> None:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from screen.harvest import probe_template, render_prompt
    from screen.harvest_cpu import resolve_snapshot

    repo = sys.argv[1] if len(sys.argv) > 1 else "Qwen/Qwen2.5-1.5B-Instruct"
    items = json.loads((ROOT / "inherited" / "items.json").read_text())
    items = items["items"] if isinstance(items, dict) else items
    snap = resolve_snapshot(repo)
    tok = AutoTokenizer.from_pretrained(str(snap))
    tinfo = probe_template(tok, snap)
    prompts = [render_prompt(tok, tinfo, it["prompt"]) for it in items[:16]]
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    res: dict = {"repo": repo, "torch_threads": torch.get_num_threads()}
    for dt_name, dt in (("bfloat16", torch.bfloat16), ("float32", torch.float32)):
        t = time.time()
        model = AutoModelForCausalLM.from_pretrained(str(snap), dtype=dt, low_cpu_mem_usage=True)
        model.eval()
        r = {"load_s": time.time() - t}
        with torch.no_grad():
            enc = tok(prompts[:8], return_tensors="pt", padding=True, add_special_tokens=False)
            r["prefill_tokens"] = int(enc["attention_mask"].sum())
            r["prefill_padded_shape"] = list(enc["input_ids"].shape)
            t = time.time()
            out = model(**enc, output_hidden_states=True, use_cache=True)
            r["prefill_s"] = time.time() - t
            del out
            enc = tok(prompts[:16], return_tensors="pt", padding=True, add_special_tokens=False)
            t = time.time()
            gen = model.generate(**enc, max_new_tokens=16, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
            r["gen16x16_s"] = time.time() - t
            r["sample"] = tok.decode(gen[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        res[dt_name] = r
        logger.info(f"{dt_name}: {r}")
        del model
    (ROOT / "results" / "bench_cpu.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
