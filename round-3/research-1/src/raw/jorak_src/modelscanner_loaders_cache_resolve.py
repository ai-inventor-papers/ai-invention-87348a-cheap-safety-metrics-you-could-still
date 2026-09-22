"""Résolution d'un id HF -> snapshot LOCAL, sans réseau ni certificat.

Contexte (serveur air-gapped, proxy TLS d'inspection self-signed) : on ne
télécharge rien. Les modèles vivent soit dans le cache HF standard, soit dans le
cache du service vLLM (`/srv/data/vllm-cache/hub`). Les deux ont le MÊME format hub
(`models--org--name/snapshots/<hash>/`) car vLLM passe par `huggingface_hub`.

Stratégie : on ne déplace RIEN. On résout le nom du YAML vers le chemin absolu
du snapshot, en cherchant le cache HF D'ABORD puis le cache vLLM. Passer le
chemin du snapshot (et non `models--org--name`) à `from_pretrained` évite aussi
le rejet repo_id de transformers.
"""
from __future__ import annotations

import os
from typing import List

# Cache vLLM par défaut (chemin type) ; surchargeable par env si le chemin change.
_VLLM_CACHE_DEFAULT = "/srv/data/vllm-cache/hub"


def cache_roots() -> List[str]:
    """Racines de cache hub à fouiller, dans l'ordre : HF standard puis vLLM.

    Respecte HF_HUB_CACHE / HF_HOME s'ils sont posés ; sinon ~/.cache/huggingface/hub.
    Le cache vLLM est surchargeable via MODELSCANNER_VLLM_CACHE.
    """
    roots: List[str] = []

    # 1) cache HF standard
    if os.environ.get("HF_HUB_CACHE"):
        roots.append(os.environ["HF_HUB_CACHE"])
    elif os.environ.get("HF_HOME"):
        roots.append(os.path.join(os.environ["HF_HOME"], "hub"))
    else:
        roots.append(os.path.expanduser("~/.cache/huggingface/hub"))

    # 2) cache vLLM
    roots.append(os.environ.get("MODELSCANNER_VLLM_CACHE", _VLLM_CACHE_DEFAULT))

    # dédup en gardant l'ordre, et seulement les dossiers existants
    seen, out = set(), []
    for r in roots:
        if r and r not in seen and os.path.isdir(r):
            seen.add(r)
            out.append(r)
    return out


def resolve_model_ref(model_id: str) -> str:
    """id HF -> chemin du snapshot local (cache HF puis cache vLLM).

    - Si `model_id` est déjà un dossier local utilisable, le renvoie tel quel.
    - Sinon, cherche un snapshot complet dans chaque racine (offline, sans réseau).
    - Si rien n'est trouvé, renvoie `model_id` inchangé : `from_pretrained`
      gèrera (ou lèvera une erreur explicite) sans qu'on masque le problème ici.
    """
    if os.path.isdir(model_id):
        return model_id

    # Import tardif : pas de dépendance au réseau, juste la résolution de cache.
    from huggingface_hub import snapshot_download
    from huggingface_hub.utils import LocalEntryNotFoundError

    for root in cache_roots():
        try:
            # local_files_only=True => AUCUN appel réseau, donc aucun certificat requis.
            return snapshot_download(model_id, cache_dir=root, local_files_only=True)
        except (LocalEntryNotFoundError, FileNotFoundError, OSError):
            continue
    return model_id
