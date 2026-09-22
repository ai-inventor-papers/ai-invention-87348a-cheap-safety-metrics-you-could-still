"""Erreurs de chargement PRÉCISES — rendent les échecs actionnables. [J10]

Le détecteur tourne souvent en batch (campagne) : un échec opaque « exit 1 »
n'aide personne. Chaque cause racine non récupérable a ici son exception, avec
un message clair (FR + EN) :

  - ``UnsupportedFormat``  : pas de poids safetensors/bin chargeables (dépôt
    GGUF-only ou vide) -> on ne peut PAS scanner (Jorak a besoin des tenseurs).
  - ``TransformersOutdated`` : le ``model_type`` du dépôt est inconnu de la
    version de ``transformers`` installée (ex. ``mistral3`` sur une box pas à
    jour) -> réparable par un upgrade, pas par notre code.

Le nom de classe se retrouve tel quel dans le traceback du sous-processus de
scan ; ``experiments/run_scan.py::_classify_error`` s'en sert pour étiqueter
l'échec (``gguf_only`` / ``transformers_outdated``).
"""
from __future__ import annotations


class UnsupportedFormat(Exception):
    """Aucun poids chargeable (GGUF-only / dépôt sans safetensors ni .bin)."""


class TransformersOutdated(Exception):
    """``model_type`` du dépôt inconnu de la version de transformers installée."""
