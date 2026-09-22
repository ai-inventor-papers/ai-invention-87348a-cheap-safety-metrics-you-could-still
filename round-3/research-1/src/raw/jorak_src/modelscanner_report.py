"""Logger JSON d'un scan.

Structure (dans l'ordre) :
  1. ``scan``    — modèle + flags/config du run + horodatage  (EN HAUT)
  2. ``results`` — verdict + stats + métriques par couche
  3. ``prompts`` — paires question/réponse du plan comportemental  (PLUS BAS)

JSON lisible (indent, ``ensure_ascii=False`` pour le chinois/accents).
"""
from __future__ import annotations

import datetime
import json
import os
from typing import Optional

import numpy as np

from modelscanner.core.types import ScanResult


def _r(x, n: int = 4):
    """Arrondi robuste (None -> None)."""
    if x is None:
        return None
    try:
        return round(float(x), n)
    except (TypeError, ValueError):
        return x


def scan_log_dict(result: ScanResult, flags: Optional[dict] = None) -> dict:
    """Construit le dict de trace à partir d'un ScanResult (+ flags appelant)."""
    meta = result.meta or {}
    run = dict(meta.get("run", {}))
    if flags:
        run.update({k: v for k, v in flags.items() if v is not None})

    d = np.asarray(result.cohens_d) if result.cohens_d is not None else None
    a = np.asarray(result.weight_axis_align) if result.weight_axis_align is not None else None
    supp_med = {k: _r(np.median(v)) for k, v in (result.suppression or {}).items()}
    cdet = meta.get("classify_detail") or {}
    sub = meta.get("subspace") or {}

    return {
        # ---------------- 1. flags / config (en haut) ----------------
        "scan": {
            "model": result.model_id,
            "model_type": result.model_type,
            "quantization": result.quantization.value,
            "n_layers": result.n_layers,
            "hidden_size": result.hidden_size,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "expected_label": meta.get("expected_label"),
            "flags": run,
        },
        # ---------------- 2. résultats / stats ----------------
        "results": {
            "label": result.label.value,
            "expected_label": meta.get("expected_label"),
            "matches_expected": (
                None if not meta.get("expected_label")
                else (result.label.value == meta.get("expected_label"))
            ),
            "confidence": _r(result.confidence),
            "svd_alignment_global": _r(result.svd_alignment),
            "band_alignment": _r(cdet.get("band_alignment")),
            "touched_band": cdet.get("band_span"),
            # cibles de la signature poids + ventilation PAR CIBLE (o_proj vs down_proj) :
            # band_alignment/svd_alignment ci-dessus sont le MAX sur les cibles -> sans ce
            # détail on ne peut pas savoir si une bande haute vient de o_proj ou de down_proj
            # (cf. contamination down_proj des bases, MAINTENANCE.md §4). Rend l'audit possible.
            "svd_targets": meta.get("svd_targets"),
            "svd_winning_target": meta.get("svd_target"),
            "svd_per_target": meta.get("svd_per_target"),
            "subspace_alignment": _r(cdet.get("subspace_alignment")),   # signal MULTI-direction (bottom-k)
            "subspace_band": _r(cdet.get("subspace_band")),
            "subspace_touched_band": cdet.get("subspace_band_span"),
            "svd_pairwise_cos": _r(result.svd_pairwise_cos),
            "max_cohens_d": _r(np.nanmax(d)) if d is not None else None,
            "mean_cohens_d": _r(np.nanmean(d)) if d is not None else None,
            "median_suppression": supp_med,
            "behavioral_refusal_rate": _r(result.behavioral_refusal_rate),
            "behavioral_over_refusal": _r(meta.get("behavioral_over_refusal")),  # sur-refus harmless (dégât furtif)
            "evasive_ablation": bool(cdet.get("evasive_ablation", False)),       # ablation furtive détectée au comportement
            "layers_touched": [int(i) for i in result.layers_touched().tolist()] if a is not None else None,
            "classify_detail": meta.get("classify_detail"),
            "per_layer": {
                "cohens_d": [_r(x, 3) for x in d.tolist()] if d is not None else None,
                "weight_axis_align": [_r(x, 3) for x in a.tolist()] if a is not None else None,
                "subspace_align": sub.get("per_layer_align"),
                # suppression par couche & par projection (o_proj=attention, down_proj=MLP)
                "suppression": {
                    k: [_r(x, 3) for x in np.asarray(v).reshape(-1).tolist()]
                    for k, v in (result.suppression or {}).items()
                },
            },
        },
        # ---------------- 3. profil du modèle (si --profile) ----------------
        "model_profile": meta.get("model_profile"),
        # ---------------- 3bis. asymétrie multilingue (si --multilingual) ----------------
        "multilingual": meta.get("multilingual"),
        # ---------------- 4. question / réponse (plus bas) ----------------
        "prompts": meta.get("behavioral_qa", []),
    }


def write_scan_log(result: ScanResult, path: str, flags: Optional[dict] = None) -> str:
    """Écrit la trace JSON sur disque et renvoie le chemin."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scan_log_dict(result, flags), f, ensure_ascii=False, indent=2)
    return str(path)
