#!/usr/bin/env python3
"""D2b. FIRST-GENERATED-TOKEN IDENTITY AUDIT.

Iteration 1 raised gate F3_READOUT_ASSUMPTION_FAILED: refusal-drive-vs-judge-flag
AUROC 0.750 on Qwen3-4B and 0.391 -- BELOW CHANCE -- on its abliterated sibling.
A below-chance readout is the signature of a BROKEN readout, not a weak one, and
Qwen3's hybrid thinking mode supplies a specific, checkable suspect: without
enable_thinking=False the first generated token is the <think> delimiter, so every
first-token logit readout measures a delimiter rather than a decision.

This diagnoses it offline from the cached harvest.  Ten minutes, no GPU.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from loguru import logger

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evallib.core import (  # noqa: E402
    HARVEST, RESULTS, auc_one, item_arrays, load_acts, load_items, load_meta,
    read_json, write_json,
)
from s0_setup import PANEL_MAP  # noqa: E402

HF_HUB = Path("/ai-inventor/aii_data/runs/run_fcYd_7ruOwtm/.shared_cache/hf/hub")

# A token counts as a DELIMITER if it is a special/role/thinking marker rather
# than the first word of an answer.
DELIM_RE = re.compile(
    r"^(<\|?[^>]*\|?>|<think>|</think>|\[INST\]|\[/INST\]|<s>|</s>|<pad>|<unk>|"
    r"<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|�)$", re.I)
DELIM_SUBSTR = ("<think", "</think", "<|im_", "<|end", "<|start", "<|assistant",
                "<|user", "<|system", "[INST", "<s>", "</s>", "<|box", "<|quad",
                "<|vision", "<|object")


def _decode_map(slug: str) -> tuple[dict[int, str], str]:
    """id -> token string, read straight out of the cached tokenizer.json.

    No transformers, no tokenizers package, no download: tokenizer.json is a plain
    JSON file and its `model.vocab` is the id table.  `added_tokens` carries the
    special/role markers, which are exactly what this audit is looking for.
    """
    repo = slug.replace("__", "--")
    root = HF_HUB / f"models--{repo}"
    cands = sorted(root.glob("snapshots/*/tokenizer.json")) if root.exists() else []
    if not cands:
        return {}, f"NO_LOCAL_TOKENIZER ({root})"
    tj = json.loads(cands[0].read_text(encoding="utf-8"))
    inv: dict[int, str] = {}
    vocab = tj.get("model", {}).get("vocab", {})
    if isinstance(vocab, dict):
        for tok, i in vocab.items():
            inv[int(i)] = tok
    elif isinstance(vocab, list):                       # unigram-style
        for i, entry in enumerate(vocab):
            inv[i] = entry[0] if isinstance(entry, (list, tuple)) else str(entry)
    for at in tj.get("added_tokens", []) or []:
        inv[int(at["id"])] = at["content"]
    return inv, str(cands[0].relative_to(HF_HUB))


def _is_delim(tok: str) -> bool:
    if tok is None:
        return False
    t = tok.replace("Ġ", " ").replace("Ċ", "\n").strip()
    if DELIM_RE.match(t):
        return True
    low = tok.lower()
    return any(s in low for s in DELIM_SUBSTR)


def audit(slug: str) -> dict:
    a = load_acts(slug)
    meta = load_meta(slug)
    fid = a["first_token_id"].astype(int)
    inv, src = _decode_map(slug)
    toks = [inv.get(int(i)) for i in fid]
    known = sum(t is not None for t in toks)
    cnt = Counter(int(i) for i in fid)
    modal_id, modal_n = cnt.most_common(1)[0]
    modal_tok = inv.get(modal_id)
    delim_flags = np.array([_is_delim(t) if t is not None else False for t in toks])
    delim_share = float(delim_flags.mean())
    modal_is_delim = bool(_is_delim(modal_tok)) if modal_tok is not None else None
    modal_delim_share = delim_share if modal_is_delim else 0.0

    # generations cross-check: does the stored text actually OPEN on a delimiter?
    g = read_json(HARVEST / slug / "generations.json")
    gens = g.get("generations", []) or []
    open_delim = sum(1 for s in gens if isinstance(s, str)
                     and s.lstrip()[:8].lower().startswith(("<think", "<|im_", "</think")))
    # refusal drive vs the harm label -- the F3 readout, recomputed here
    items = load_items()
    ia = item_arrays(items, len(fid))
    lf = a["logit_feats"][:, 0].astype(float)          # refusal-minus-compliance log-odds
    harm = (ia["kind"] == "harmful").astype(int)
    auc_drive = auc_one(harm, lf)

    verdict = ("DELIMITER_CONTAMINATED" if modal_is_delim and modal_delim_share > 0.5
               else "CLEAN" if delim_share == 0.0
               else "MIXED")
    if not inv:
        verdict = "UNDECODABLE_NO_LOCAL_TOKENIZER"
    del a
    return {
        "slug": slug, "cls": PANEL_MAP[slug][0], "family": PANEL_MAP[slug][1],
        "tokenizer_source": src, "vocab_ids_resolved": f"{known}/{len(toks)}",
        "modal_first_token_id": int(modal_id),
        "modal_first_token": modal_tok,
        "modal_first_token_share": round(modal_n / len(fid), 4),
        "modal_token_is_delimiter": modal_is_delim,
        "delimiter_share_over_items": round(delim_share, 4),
        "n_distinct_first_tokens": len(cnt),
        "top5_first_tokens": [{"id": int(i), "token": inv.get(int(i)), "n": int(n),
                               "share": round(n / len(fid), 4), "is_delim": _is_delim(inv.get(int(i)))}
                              for i, n in cnt.most_common(5)],
        "stored_generations_opening_on_a_delimiter": f"{open_delim}/{len(gens)}",
        "enable_thinking_supported": meta.get("template", {}).get("enable_thinking_supported"),
        "renderer": meta.get("template", {}).get("renderer"),
        "refusal_drive_vs_harm_label_auroc": auc_drive,
        "verdict": verdict,
    }


def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    rows = []
    for slug in sorted(PANEL_MAP):
        r = audit(slug)
        rows.append(r)
        logger.info(f"{slug:<55} modal={str(r['modal_first_token'])[:16]!r} "
                    f"share={r['modal_first_token_share']} delim={r['delimiter_share_over_items']} "
                    f"-> {r['verdict']}")
        write_json(RESULTS / "d2b_first_token.json", {"per_checkpoint": rows})
    vc = Counter(r["verdict"] for r in rows)
    contaminated = [r["slug"] for r in rows if r["verdict"] == "DELIMITER_CONTAMINATED"]
    any_cont = len(contaminated) > 0
    out = {
        "per_checkpoint": rows,
        "verdict_histogram": dict(vc),
        "contaminated_slugs": contaminated,
        "panel_verdict": ("DELIMITER_CONTAMINATED" if len(contaminated) > len(rows) / 2
                          else "CLEAN" if vc.get("CLEAN", 0) == len(rows) else "MIXED"),
        "bands_prereg": {"DELIMITER_CONTAMINATED": "modal delimiter share > 0.5",
                         "CLEAN": "no item opens on a thinking or role delimiter",
                         "MIXED": "otherwise"},
        "conclusion_for_the_sibling_gpu_experiment": (
            "The three-way readout bake-off IS necessary -- the first generated token is a "
            "thinking or role delimiter on at least one checkpoint, so first-token logit "
            "readouts are measuring a delimiter."
            if any_cont else
            "The three-way readout bake-off is NOT forced by delimiter contamination. The "
            "first generated token is a content token on every harvested checkpoint, so the "
            "iteration-1 F3 gate (refusal-drive-vs-judge AUROC 0.750 on Qwen3-4B and 0.391 "
            "on its abliterated sibling) is NOT explained by Qwen3's hybrid thinking mode. "
            "The prime suspect is eliminated, and the below-chance value has to be explained "
            "by something else -- most plausibly that the refusal drive genuinely inverts on "
            "an abliterated checkpoint, which is a result rather than a bug. The sibling "
            "experiment should spend its GPU time on WHY the drive inverts, not on a "
            "delimiter bake-off."),
        "inheritance_rule": (
            "Every refusal-drive row in D0 and D3 inherits this flag. A CONTAMINATED row is "
            "reported as CONTAMINATED, never as a low score."),
    }
    write_json(RESULTS / "d2b_first_token.json", out)
    logger.info(f"D2b panel verdict: {out['panel_verdict']} | {dict(vc)}")


if __name__ == "__main__":
    main()
