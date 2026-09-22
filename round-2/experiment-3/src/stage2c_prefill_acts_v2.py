#!/usr/bin/env python3
"""Prefill-only activation pass for a checkpoint generated BEFORE hidden-state capture was added: the same 88
rendered prompts, the same last-prompt-token layers and the same first-token logit gap as stage2_generate_v2.py,
without decoding. Writes results/acts_v2/<id>.npz (identical format)."""
import os
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import sys
from pathlib import Path
import numpy as np
import torch
WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from stage2_generate_v2 import HS_FRACS, COMPLIANCE_STR, REFUSAL_STR, load_items, load_real, render, token_set  # noqa: E402


@torch.no_grad()
def main() -> None:
    torch.set_num_threads(2)
    repo = sys.argv[1]
    cid = repo.replace("/", "__")
    rows, _ = load_items()
    model, tok, _ = load_real(repo)
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    ref_ids = token_set(tok, REFUSAL_STR)
    com_ids = [i for i in token_set(tok, COMPLIANCE_STR) if i not in set(ref_ids)]
    texts = [render(tok, r["prompt"])[0] for r in rows]
    hs_all, gaps = [None] * len(rows), [None] * len(rows)
    keep = None
    for b0 in range(0, len(rows), 22):
        idx = list(range(b0, min(b0 + 22, len(rows))))
        enc = tok([texts[i] for i in idx], return_tensors="pt", padding=True, add_special_tokens=False)
        out = model(**enc, output_hidden_states=True)
        hs = out.hidden_states
        n_hs = len(hs)
        keep = sorted({min(n_hs - 1, max(1, int(round(f * (n_hs - 1))))) for f in HS_FRACS})
        lp = torch.log_softmax(out.logits[:, -1, :].float(), dim=-1)
        g = torch.logsumexp(lp[:, ref_ids], -1) - torch.logsumexp(lp[:, com_ids], -1)
        for k, i in enumerate(idx):
            hs_all[i] = torch.stack([hs[L][k, -1, :].float() for L in keep]).to(torch.float16).numpy()
            gaps[i] = float(g[k])
    (WS / "results" / "acts_v2").mkdir(exist_ok=True)
    np.savez_compressed(WS / "results" / "acts_v2" / f"{cid}.npz", hs_last=np.stack(hs_all), layers=np.array(keep),
                        item_id=np.array([str(r["item_id"]) for r in rows]), l1_gap=np.array(gaps, dtype=np.float32),
                        note=np.array("prefill-only pass (no decoding); same prompts/layers as the generation pass"))
    print("wrote", cid, np.stack(hs_all).shape)


if __name__ == "__main__":
    main()
