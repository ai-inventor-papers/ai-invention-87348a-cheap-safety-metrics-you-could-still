#!/usr/bin/env python3
"""The request's step-1 lineage, read parent-free: Qwen3-4B Base / Instruct / SafeRL / abliterated.

These four share an architecture exactly, so every between-model difference in a weight statistic is
attributable to what was done to the weights rather than to width, depth or family. That makes this
the cleanest contrast in the whole panel, and it is the lineage the original request named.
"""
from __future__ import annotations
import json
from pathlib import Path

WS = Path(__file__).resolve().parent
LINEAGE = [("Qwen/Qwen3-4B-Base", "base"), ("Qwen/Qwen3-4B", "instruct"),
           ("Qwen/Qwen3-4B-SafeRL", "safety-RL"), ("mlabonne/Qwen3-4B-abliterated", "abliterated")]
KEYS = ("kappa_hat", "BOTGAP_min", "BSA_w8", "BSA_all", "TSA_w8", "XLC", "RQ_pooled")


def main() -> None:
    rows, missing = [], []
    for rid, role in LINEAGE:
        fp = WS / "results" / "ckpt" / f"{rid.replace('/', '__')}.json"
        if not fp.exists():
            missing.append(rid)
            continue
        c = json.loads(fp.read_text())
        if c.get("status") != "OK":
            missing.append(rid)
            continue
        mlp = (c.get("by_component") or {}).get("mlp") or {}
        attn = (c.get("by_component") or {}).get("attn") or {}
        rows.append({
            "repo_id": rid, "role": role, "arm": c.get("arm"),
            "layer_stride": c.get("layer_stride"), "n_matrices_read": c.get("n_matrices_read"),
            "down_proj": {k: mlp.get({"kappa_hat": "kappa_hat_max",
                                      "BOTGAP_min": "botgap_min"}.get(k, k)) for k in KEYS},
            "o_proj": {k: attn.get({"kappa_hat": "kappa_hat_max",
                                    "BOTGAP_min": "botgap_min"}.get(k, k)) for k in KEYS},
            "cross_family_cosine": (c.get("cross_family_cosine") or {}).get("xfc"),
            "card_scope": (c.get("card") or {}).get("scope_class"),
        })
    out = {
        "lineage": "Qwen3-4B (identical architecture: Qwen3ForCausalLM, hidden 2560, 36 layers)",
        "why_this_lineage": ("all four share an architecture exactly, so any difference in a weight "
                             "statistic is attributable to what was done to the weights, not to "
                             "width, depth or family"),
        "site_note": ("down_proj is the interpretable site: Qwen3-4B's o_proj is rectangular here, "
                      "but down_proj is the only residual-write site with d_in > d_out on EVERY "
                      "family in the panel, so it is used for the headline row"),
        "n_read": len(rows), "missing": missing, "rows": rows,
    }
    if len(rows) >= 2:
        abl = next((r for r in rows if r["role"] == "abliterated"), None)
        others = [r for r in rows if r["role"] != "abliterated"]
        if abl and others:
            out["abliterated_vs_unedited_siblings"] = {
                k: {"abliterated": abl["down_proj"].get(k),
                    "siblings": {r["role"]: r["down_proj"].get(k) for r in others},
                    "separates": None if abl["down_proj"].get(k) is None else bool(
                        all(v is not None and abl["down_proj"][k] != v
                            for v in [r["down_proj"].get(k) for r in others]))}
                for k in KEYS}
    (WS / "results" / "lineage_qwen3_4b.json").write_text(json.dumps(out, indent=2, default=float))
    print(f"lineage rows read: {len(rows)}/4; missing: {missing}")
    for r in rows:
        d = r["down_proj"]
        print(f"  {r['role']:<12} kappa={d.get('kappa_hat')} BOTGAP={d.get('BOTGAP_min')} "
              f"BSA={d.get('BSA_w8')} XLC={d.get('XLC')} XFC={r['cross_family_cosine']}")


if __name__ == "__main__":
    main()
