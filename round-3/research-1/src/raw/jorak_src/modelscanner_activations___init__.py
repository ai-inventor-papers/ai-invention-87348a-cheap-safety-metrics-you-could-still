"""Activations : forward pass unique -> hidden states au dernier token. [J3]

C'est le "scan-once" : un unique forward pass sur les sondes, dont on extrait
par couche le hidden state au dernier token (position de génération), pour les
classes harmful et harmless.

On lit `output_hidden_states` (residual stream après chaque couche) plutôt que
des hooks : c'est l'espace exact où vit la direction de refus r̂, et ça reprend
le pattern éprouvé de experiments/pipeline.py. On saute `hidden_states[0]`
(sortie d'embedding) pour que `Activations[ℓ]` corresponde à la sortie de la
couche décodeur ℓ — donc aux poids o_proj/down_proj de la couche ℓ (alignement
nécessaire pour la suppression_ℓ en J6).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np


@dataclass
class Activations:
    """Hidden states collectés au dernier token, par couche.

    harmful / harmless : [n_layers, n_prompts, hidden]. On garde les vecteurs
    individuels (pas seulement les moyennes) car Cohen's d a besoin des
    distributions intra-classe.
    """

    harmful: np.ndarray
    harmless: np.ndarray

    @property
    def n_layers(self) -> int:
        return self.harmful.shape[0]

    @property
    def hidden_size(self) -> int:
        return self.harmful.shape[-1]

    def mean_harmful(self) -> np.ndarray:   # [n_layers, hidden]
        return self.harmful.mean(axis=1)

    def mean_harmless(self) -> np.ndarray:  # [n_layers, hidden]
        return self.harmless.mean(axis=1)


def collect_activations(
    handle,
    probes,
    *,
    layers: Optional[List[int]] = None,
    batch_size: int = 8,
    system: Optional[str] = None,
    progress=None,
) -> Activations:
    """Forward pass unique + extraction du dernier token -> Activations.

    Args:
        handle: ModelHandle runnable (plan ACTIVATIONS).
        probes: ProbeSet (harmful/harmless appariés).
        layers: sous-ensemble d'indices de couches décodeur (None = toutes).
        batch_size: taille de lot pour le forward.
        system: prompt système optionnel (défaut: aucun -> refus intrinsèque).
        progress: callback optionnel `progress(n, desc=None)` (barre de progression),
            appelé une fois par prompt traité.
    """
    import torch

    from modelscanner.probes.templates import format_prompt

    model = handle.runnable
    if model is None:
        raise RuntimeError(
            "Plan ACTIVATIONS indisponible : ce ModelHandle n'est pas runnable "
            "(ex. GGUF). Utiliser les plans Jorak + behavioral."
        )
    tok = handle.tokenizer
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    device = next(model.parameters()).device

    @torch.no_grad()
    def _run(prompts: List[str], desc: Optional[str] = None) -> np.ndarray:
        chunks = []
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i : i + batch_size]
            texts = [
                format_prompt(p, handle.model_type, tokenizer=tok, system=system)
                for p in batch
            ]
            # add_special_tokens=False : le template inclut déjà les tokens
            # spéciaux (sinon double BOS sur Gemma).
            enc = tok(
                texts, return_tensors="pt", padding=True, add_special_tokens=False
            ).to(device)
            out = model(**enc, output_hidden_states=True)
            hs = out.hidden_states  # tuple (n_layers+1) de [B, T, H]

            mask = enc["attention_mask"]
            total = mask.sum(dim=1, keepdim=True)
            # index du DERNIER token réel, robuste au padding gauche/droite
            last_idx = (mask.cumsum(dim=1) == total).int().argmax(dim=1)  # [B]
            ar = torch.arange(mask.shape[0], device=device)

            sel = range(1, len(hs)) if layers is None else [l + 1 for l in layers]
            per_layer = [hs[k][ar, last_idx].float().cpu().numpy() for k in sel]
            chunks.append(np.stack(per_layer, axis=0))  # [n_layers, B, H]
            del out
            if progress is not None:
                progress(len(batch), desc=desc)
        return np.concatenate(chunks, axis=1)  # [n_layers, n_prompts, H]

    harmful = _run(list(probes.harmful), desc="activations · harmful")
    harmless = _run(list(probes.harmless), desc="activations · harmless")
    return Activations(harmful=harmful, harmless=harmless)
