"""CPU FALLBACK: import stored iter-2 96-token greedy generations for harvested checkpoints.

Each stored reply is re-tokenised with the checkpoint's OWN tokenizer and truncated to the first
64 tokens (matching the fresh CPU protocol, max_new_tokens=64); prefix24 = first 24 tokens.
Only items in OUTCOME are kept (SCREEN16 items are dropped). source_of_generations=stored_96tok_fallback.
Tokenizer files only are fetched (no weights).
"""
from __future__ import annotations

import os
_N = str(len(os.sched_getaffinity(0)))
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = _N

import json
import re
import sys
from pathlib import Path

from loguru import logger
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard import assert_not_sealed  # noqa: E402

W = Path(__file__).resolve().parent.parent
H = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/3_invention_loop/iter_2/gen_art/gen_art_experiment_1/harvest")
TRUNC = 64


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().casefold())


@logger.catch(reraise=True)
def main() -> None:
    out = [json.loads(l) for l in (W / "outcome_items.jsonl").open()]
    by_sub = {r["substrate_id"]: r for r in out if r["substrate_id"] is not None}
    by_norm = {norm(r["prompt"]): r for r in out}
    done = []
    for d in sorted(H.iterdir()):
        g = d / "generations.json"
        if not g.exists():
            continue
        js = json.loads(g.read_text())
        if not js["generations"]:
            continue
        meta = json.loads((d / "meta.json").read_text())
        repo = meta["repo_id"]
        assert_not_sealed(repo, check_hub=False)
        dst = W / "results" / "ckpt" / repo.replace("/", "__") / "stored_gens.json"
        if dst.exists():
            done.append(repo)
            continue
        tok = AutoTokenizer.from_pretrained(repo)
        rows = []
        for sid, reply in zip(js["gen_item_idx"], js["generations"]):
            if sid not in by_sub:
                continue
            it = by_sub[sid]
            ids = tok(reply, add_special_tokens=False)["input_ids"]
            rows.append({"item_id": it["item_id"], "condition": "plain", "template_mode": "system_ok",
                         "prompt": it["prompt"], "reply": tok.decode(ids[:TRUNC], skip_special_tokens=True),
                         "n_new_tokens": min(len(ids), TRUNC), "stored_n_tokens": len(ids),
                         "hit_eos": len(ids) < 96, "prefix24": tok.decode(ids[:24], skip_special_tokens=True),
                         "reply_full96": reply})
        # the 24 probe generations are XSTest CONTRAST prompts (harmful side), matched by normalised text
        for pp, reply in zip(js.get("probe_prompts", []), js.get("probe_generations", [])):
            it = by_norm.get(norm(pp))
            if it is None:
                continue
            ids = tok(reply, add_special_tokens=False)["input_ids"]
            rows.append({"item_id": it["item_id"], "condition": "plain", "template_mode": "system_ok",
                         "prompt": it["prompt"], "reply": tok.decode(ids[:TRUNC], skip_special_tokens=True),
                         "n_new_tokens": min(len(ids), TRUNC), "stored_n_tokens": len(ids),
                         "hit_eos": len(ids) < 96, "prefix24": tok.decode(ids[:24], skip_special_tokens=True),
                         "reply_full96": reply, "stored_field": "probe_generations"})
        dst.parent.mkdir(parents=True, exist_ok=True)
        rec = {"repo": repo, "source_of_generations": "stored_96tok_fallback", "stored_path": str(g),
               "stored_max_new_tokens": 96, "truncated_to_tokens": TRUNC, "harvest_meta": {
                   k: meta.get(k) for k in ("architecture", "attn_implementation", "template", "n_layers")},
               "n_rows": len(rows), "rows": rows}
        dst.write_text(json.dumps(rec, ensure_ascii=False))
        logger.info(f"{repo}: {len(rows)} stored rows")
        done.append(repo)
    (W / "results" / "stored_imported.json").write_text(json.dumps(done, indent=1))


if __name__ == "__main__":
    main()
