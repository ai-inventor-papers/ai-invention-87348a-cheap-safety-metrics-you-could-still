"""Contrats de données partagés — la *frontière étanche* loaders <-> metrics.

Principe architectural NON négociable (cf. brief §3.6) : `metrics/` ne sait
JAMAIS d'où vient un modèle. Il consomme un `ModelHandle` (API tenseurs +
inférence unifiée) et produit des morceaux de `ScanResult`. Les loaders
(safetensors, gguf, ...) produisent un `ModelHandle`.

Ce module reste *neutre et léger* : il n'importe ni torch ni transformers à
l'exécution (seulement sous TYPE_CHECKING), pour pouvoir être importé partout
sans tirer la stack ML.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional

import numpy as np

if TYPE_CHECKING:  # imports lourds : annotations uniquement
    import torch
    from transformers import PreTrainedModel


# ---------------------------------------------------------------------------
# Énumérations
# ---------------------------------------------------------------------------
class Provenance(str, Enum):
    """Label de provenance multi-classe — la sortie du classifieur (§3.4)."""

    CENSORED = "censored"                       # négatif / base
    ABLATED = "ablated"                         # abliteré (la cible)
    FINETUNED_DECENSORED = "finetuned_decensored"  # ex. Dolphin — faux positif à éviter
    AMBIGUOUS = "ambiguous"


class Quantization(str, Enum):
    """Niveau de quantif détecté — pilote les seuils quant-aware (§3.2)."""

    FP32 = "fp32"
    FP16 = "fp16"
    BF16 = "bf16"
    BNB_4BIT = "bnb-4bit"
    BNB_8BIT = "bnb-8bit"
    GGUF = "gguf"  # variante précise (Q4_K_M, ...) dans ScanResult.meta["gguf_quant"]


class WeightTarget(str, Enum):
    """Poids qui écrivent dans le residual stream — cibles de l'ablation."""

    O_PROJ = "o_proj"        # self_attn.o_proj
    DOWN_PROJ = "down_proj"  # mlp.down_proj


# ---------------------------------------------------------------------------
# Frontière : l'API unifiée que tout le pipeline consomme
# ---------------------------------------------------------------------------
class ModelHandle(ABC):
    """API tenseurs + inférence unifiée produite par les loaders.

    Les implémentations concrètes (``SafetensorsHandle``, ``GgufHandle``, ...)
    masquent totalement le format/quantif de provenance. Toutes les méthodes
    d'accès aux poids renvoient des tenseurs **fp32** (déquantifiés).

    Attributs attendus (posés par le `__init__` concret) :
        model_id, model_type, quantization, n_layers, hidden_size
    """

    model_id: str
    model_type: str
    quantization: Quantization
    n_layers: int
    hidden_size: int

    # --- accès poids (déquantifiés fp32), chargés à la demande ---
    @abstractmethod
    def o_proj(self, layer: int) -> "torch.Tensor":
        """self_attn.o_proj de la couche `layer`, shape [d_model, d_attn]."""

    @abstractmethod
    def down_proj(self, layer: int) -> "torch.Tensor":
        """mlp.down_proj de la couche `layer`, shape [d_model, d_ff]."""

    @abstractmethod
    def embed_tokens(self) -> "torch.Tensor":
        """Matrice d'embedding, shape [vocab, d_model]."""

    def weight(self, target: WeightTarget, layer: int) -> "torch.Tensor":
        """Dispatch générique vers le poids cible (utilisé par metrics/)."""
        if target == WeightTarget.O_PROJ:
            return self.o_proj(layer)
        if target == WeightTarget.DOWN_PROJ:
            return self.down_proj(layer)
        raise ValueError(f"WeightTarget inconnu : {target!r}")

    # --- inférence (plan ACTIVATIONS) ---
    @property
    def runnable(self) -> Optional["PreTrainedModel"]:
        """Modèle torch exécutable pour le plan ACTIVATIONS.

        Vaut ``None`` quand l'inférence par couche n'est pas disponible
        (ex. GGUF via llama.cpp) -> le scanner retombe sur les plans Jorak +
        behavioral. Mode d'échec assumé, encodé dans le type.
        """
        return None

    @property
    def supports_activations(self) -> bool:
        return self.runnable is not None


# ---------------------------------------------------------------------------
# L'objet riche produit par un unique scan (scan-once -> vues)
# ---------------------------------------------------------------------------
@dataclass
class ScanResult:
    """Résultat d'un scan unique. Toutes les "vues" (`is_ablated`,
    `layers_touched`, `axis_quality`) sont des *projections* de cet objet,
    jamais des recalculs (cf. brief §3.6, principe scan-once)."""

    # --- identité / contexte ---
    model_id: str
    model_type: str
    quantization: Quantization
    n_layers: int
    hidden_size: int

    # --- mesures par couche (remplies au fil des jalons) ---
    directions: Optional[np.ndarray] = None    # r̂_ℓ        [n_layers, hidden]
    cohens_d: Optional[np.ndarray] = None       # d_ℓ         [n_layers]
    silhouette: Optional[np.ndarray] = None     # silhouette  [n_layers]
    # suppression_ℓ par cible : {"o_proj": [n_layers], "down_proj": [n_layers]}
    suppression: Dict[str, np.ndarray] = field(default_factory=dict)
    # alignement par couche du u_min à l'axe partagé (signal poids par couche) [n_layers]
    weight_axis_align: Optional[np.ndarray] = None

    # --- signature de poids globale (plan 1, sans sonde) ---
    svd_alignment: Optional[float] = None       # σ₁(U)/‖U‖_F sur les u_min empilés
    svd_pairwise_cos: Optional[float] = None     # cosinus moyen par paires

    # --- comportemental (plan 3) ---
    behavioral_refusal_rate: Optional[float] = None

    # --- verdict ---
    label: Provenance = Provenance.AMBIGUOUS
    confidence: float = 0.0

    # seuils utilisés, niveau quant détaillé, params de scan, etc.
    meta: dict = field(default_factory=dict)

    # ---------------- vues (projections, pas de recalcul) ----------------
    @property
    def is_ablated(self) -> bool:
        return self.label == Provenance.ABLATED

    def _min_suppression_per_layer(self) -> np.ndarray:
        """min de suppression sur les cibles (o_proj/down_proj) -> [n_layers]."""
        mats = [np.asarray(v) for v in self.suppression.values()]
        return np.min(np.stack(mats, axis=0), axis=0)

    def layers_touched(self, threshold: Optional[float] = None) -> np.ndarray:
        """Indices des couches touchées par l'ablation.

        Signal PRIMAIRE = `weight_axis_align` (alignement du u_min à l'axe partagé
        par couche) : une couche est « touchée » si son u_min ≥ seuil. C'est le
        signal qui marche sur les vraies ablations (la `suppression(mean-diff)`
        reste au plancher ~0.038 — voir le finding du rapport). Repli sur
        suppression seulement si `weight_axis_align` est absent."""
        if self.weight_axis_align is not None:
            thr = threshold if threshold is not None else self.meta.get("weight_align_threshold", 0.5)
            return np.flatnonzero(np.asarray(self.weight_axis_align) >= thr)
        if self.suppression:
            thr = threshold if threshold is not None else self.meta.get("suppression_threshold")
            if thr is None:
                raise ValueError("Seuil non fourni et absent de meta.")
            return np.flatnonzero(self._min_suppression_per_layer() < thr)
        return np.array([], dtype=int)

    @property
    def axis_quality(self) -> dict:
        """Résumé "santé d'axe" : d moyen, suppression min, alignement SVD,
        liveness comportementale (cf. mapping livrables §3.5)."""
        return {
            "mean_cohens_d": (
                float(np.nanmean(self.cohens_d)) if self.cohens_d is not None else None
            ),
            "min_suppression": (
                float(self._min_suppression_per_layer().min()) if self.suppression else None
            ),
            "svd_alignment": self.svd_alignment,
            "behavioral_refusal_rate": self.behavioral_refusal_rate,
        }

    # ---------------- (dé)sérialisation ----------------
    def save(self, path) -> str:
        """Sauve en .npz (arrays) + un blob JSON pour les scalaires/meta.
        Pas de pickle (allow_pickle=False à la relecture)."""
        arrays: Dict[str, np.ndarray] = {}
        for name in ("directions", "cohens_d", "silhouette", "weight_axis_align"):
            v = getattr(self, name)
            if v is not None:
                arrays[name] = np.asarray(v)
        for k, v in self.suppression.items():
            arrays[f"sup__{k}"] = np.asarray(v)

        meta = {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "quantization": self.quantization.value,
            "n_layers": self.n_layers,
            "hidden_size": self.hidden_size,
            "svd_alignment": self.svd_alignment,
            "svd_pairwise_cos": self.svd_pairwise_cos,
            "behavioral_refusal_rate": self.behavioral_refusal_rate,
            "label": self.label.value,
            "confidence": self.confidence,
            "meta": self.meta,
        }
        meta_bytes = np.frombuffer(json.dumps(meta).encode("utf-8"), dtype=np.uint8)
        with open(path, "wb") as f:  # file handle => np.savez n'ajoute pas ".npz"
            np.savez(f, _meta=meta_bytes, **arrays)
        return str(path)

    @classmethod
    def load(cls, path) -> "ScanResult":
        data = np.load(path, allow_pickle=False)
        meta = json.loads(bytes(data["_meta"]).decode("utf-8"))
        suppression = {k[len("sup__"):]: data[k] for k in data.files if k.startswith("sup__")}
        return cls(
            model_id=meta["model_id"],
            model_type=meta["model_type"],
            quantization=Quantization(meta["quantization"]),
            n_layers=meta["n_layers"],
            hidden_size=meta["hidden_size"],
            directions=data["directions"] if "directions" in data.files else None,
            cohens_d=data["cohens_d"] if "cohens_d" in data.files else None,
            silhouette=data["silhouette"] if "silhouette" in data.files else None,
            weight_axis_align=(
                data["weight_axis_align"] if "weight_axis_align" in data.files else None
            ),
            suppression=suppression,
            svd_alignment=meta["svd_alignment"],
            svd_pairwise_cos=meta["svd_pairwise_cos"],
            behavioral_refusal_rate=meta["behavioral_refusal_rate"],
            label=Provenance(meta["label"]),
            confidence=meta["confidence"],
            meta=meta["meta"],
        )
