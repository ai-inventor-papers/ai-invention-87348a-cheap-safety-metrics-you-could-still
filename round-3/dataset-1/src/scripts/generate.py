"""STEP 5 (CPU FALLBACK) - greedy generation per checkpoint, resumable.

Usage: generate.py --repos A,B,... [--max-new 64] [--items all|core] [--poles 1] [--batch 16]
Writes results/ckpt/<repo__id>/gens.json the moment a checkpoint finishes.
"""
from __future__ import annotations

import os
_N = str(len(os.sched_getaffinity(0)))
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = _N
os.environ.setdefault("MALLOC_MMAP_THRESHOLD_", "1048576")

import argparse
import ctypes
import gc
import json
import sys
import time
from pathlib import Path

import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard import load_model  # noqa: E402

torch.set_num_threads(int(_N))
W = Path(__file__).resolve().parent.parent
OUT = W / "results" / "ckpt"
POLES = json.loads((W / "poles.json").read_text())

logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add(W / "logs" / "generate.log", rotation="20 MB", level="DEBUG")


def rid(repo: str) -> str:
    return repo.replace("/", "__")


def items_for(mode: str) -> list[dict]:
    out = [json.loads(l) for l in (W / "outcome_items.jsonl").open()]
    if mode == "core":
        core = set(json.loads((W / "results" / "core_items.json").read_text())["item_ids"])
        out = [r for r in out if r["item_id"] in core]
    return out


def pole_items() -> list[dict]:
    return json.loads((W / "results" / "pole_items.json").read_text())["items"]


def render(tok, repo: str, prompt: str, system: str | None, base: bool) -> tuple[str, str]:
    if base:
        s = (system + "\n\n" if system else "") + f"User: {prompt}\nAssistant:"
        return s, "plain_base_renderer"
    kw = {}
    low = repo.lower()
    if "qwen3" in low or "smollm3" in low:
        kw["enable_thinking"] = False
    mode = "system_ok"
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    try:
        if system and "gemma" in low:
            raise ValueError("gemma2 has no system role")
        s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, **kw)
        if system and system[:40] not in s:
            raise ValueError("system dropped by template")
    except Exception:  # noqa: BLE001 - any template failure -> merged mode
        if not system:
            raise
        mode = "system_merged_into_user"
        msgs = [{"role": "user", "content": system + "\n\n" + prompt}]
        s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, **kw)
    if "qwen3" in low or "smollm3" in low:
        assert s.count("<think>") == s.count("</think>"), "open <think> block in rendered prompt"
    return s, mode


@torch.inference_mode()
def gen_batch(model, tok, texts: list[str], max_new: int, bs: int) -> list[dict]:
    res: list[dict | None] = [None] * len(texts)
    order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    i = 0
    eos_ids = set([tok.eos_token_id] if isinstance(tok.eos_token_id, int) else (tok.eos_token_id or []))
    gc_eos = getattr(model.generation_config, "eos_token_id", None)
    eos_ids |= set([gc_eos] if isinstance(gc_eos, int) else (gc_eos or []))
    while i < len(order):
        idx = order[i:i + bs]
        try:
            enc = tok([texts[j] for j in idx], return_tensors="pt", padding=True, add_special_tokens=False,
                      truncation=True, max_length=256)
            out = model.generate(**enc, max_new_tokens=max_new, do_sample=False, temperature=None, top_p=None,
                                 top_k=None, pad_token_id=tok.pad_token_id)
        except (torch.OutOfMemoryError, RuntimeError) as e:
            if "out of memory" in str(e).lower() and bs > 1:
                bs //= 2
                logger.warning(f"OOM -> batch {bs}")
                continue
            raise
        new = out[:, enc["input_ids"].shape[1]:]
        for r, j in enumerate(idx):
            ids = new[r].tolist()
            cut = len(ids)
            hit = False
            for k, t in enumerate(ids):
                if t in eos_ids:
                    cut, hit = k, True
                    break
            ids = ids[:cut]
            res[j] = {"reply": tok.decode(ids, skip_special_tokens=True), "n_new_tokens": len(ids), "hit_eos": hit,
                      "prefix24": tok.decode(ids[:24], skip_special_tokens=True)}
        i += len(idx)
    return res  # type: ignore[return-value]


def run_one(repo: str, args) -> None:
    d = OUT / rid(repo)
    if (d / "gens.json").exists():
        logger.info(f"skip {repo} (done)")
        return
    d.mkdir(parents=True, exist_ok=True)
    base = repo.endswith("-Base")
    t0 = time.time()
    kw = {"attn_implementation": "eager"} if "gemma" in repo.lower() else {}
    model, tok = load_model(repo, **kw)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    t_load = time.time() - t0
    items = items_for(args.items)
    rows = []
    texts, meta = [], []
    for it in items:
        s, m = render(tok, repo, it["prompt"], None, base)
        texts.append(s)
        meta.append((it["item_id"], "plain", m, it["prompt"]))
    if args.poles:
        for it in pole_items():
            for cond in ("always_refuse", "never_refuse"):
                s, m = render(tok, repo, it["prompt"], POLES[cond], base)
                texts.append(s)
                meta.append((it["item_id"], cond, m, it["prompt"]))
    t1 = time.time()
    outs = gen_batch(model, tok, texts, args.max_new, args.batch)
    t_gen = time.time() - t1
    for (iid, cond, m, p), o in zip(meta, outs):
        rows.append({"item_id": iid, "condition": cond, "template_mode": m, "prompt": p, **o})
    rec = {"repo": repo, "max_new_tokens": args.max_new, "item_mode": args.items, "n_rows": len(rows),
           "source_of_generations": "fresh_cpu", "dtype": "bfloat16", "device": "cpu", "decoding": "greedy",
           "timing_s": {"load": round(t_load, 1), "generate": round(t_gen, 1)},
           "template_modes": sorted({r["template_mode"] for r in rows}), "rows": rows}
    tmp = d / "gens.json.tmp"
    tmp.write_text(json.dumps(rec, ensure_ascii=False))
    tmp.rename(d / "gens.json")
    logger.info(f"DONE {repo}: {len(rows)} gens, load {t_load:.0f}s gen {t_gen:.0f}s")
    del model
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except OSError:
        pass


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", required=True)
    ap.add_argument("--max-new", type=int, default=64)
    ap.add_argument("--items", default="all")
    ap.add_argument("--poles", type=int, default=1)
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()
    for repo in [r for r in args.repos.split(",") if r]:
        try:
            run_one(repo, args)
        except Exception as e:  # noqa: BLE001 - mark failed, continue panel
            logger.exception(f"FAILED {repo}")
            d = OUT / rid(repo)
            d.mkdir(parents=True, exist_ok=True)
            (d / "FAILED.txt").write_text(f"{type(e).__name__}: {e}"[:2000])
            gc.collect()


if __name__ == "__main__":
    main()
