"""Probes : datasets harmful/harmless versionnés, appariés en longueur/registre. [J2]

EN = signal de base. Sondes MULTILINGUES (zh, fr, de, es, it) alignées index par
index avec l'EN -> détection d'asymétrie multilingue (ablation EN-only).
Fichiers : ``probes/data/refusal_<lang>_<version>.json`` (l'EN historique reste
``refusal_<version>.json``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

_DATA_DIR = Path(__file__).parent / "data"


@dataclass
class ProbeSet:
    """Jeu de sondes apparié. `harmful[i]` et `harmless[i]` ont la même taille
    et des longueurs/registres comparables (isoler le refus du topic shift)."""

    harmful: List[str] = field(default_factory=list)
    harmless: List[str] = field(default_factory=list)
    lang: str = "en"
    version: str = "v0"

    def __len__(self) -> int:
        return len(self.harmful) + len(self.harmless)

    def __post_init__(self):
        if len(self.harmful) != len(self.harmless):
            raise ValueError(
                f"Sondes non appariées : {len(self.harmful)} harmful vs "
                f"{len(self.harmless)} harmless (l'appariement index-par-index est requis)."
            )

    @property
    def n_pairs(self) -> int:
        return len(self.harmful)


def load_probes(lang: str = "en", version: str = "v1") -> ProbeSet:
    """Charge le jeu de sondes pour une langue depuis probes/data/.

    Cherche ``refusal_<lang>_<version>.json`` ; pour l'EN, retombe sur le fichier
    historique ``refusal_<version>.json``."""
    candidates = [f"refusal_{lang}_{version}.json"]
    if lang == "en":
        candidates.append(f"refusal_{version}.json")  # rétro-compat EN
    path = next((_DATA_DIR / c for c in candidates if (_DATA_DIR / c).exists()), None)
    if path is None:
        available = sorted(p.name for p in _DATA_DIR.glob("refusal_*.json"))
        raise FileNotFoundError(
            f"Sondes introuvables (lang={lang}, version={version}). Disponibles : {available}"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProbeSet(
        harmful=data["harmful"],
        harmless=data["harmless"],
        lang=data.get("lang", lang),
        version=data.get("version", version),
    )


def available_languages(version: str = "v1") -> List[str]:
    """Langues pour lesquelles un jeu de sondes existe (ex. ['de','en','es','fr','it','zh'])."""
    langs = set()
    for p in _DATA_DIR.glob(f"refusal_*_{version}.json"):
        parts = p.stem.split("_")  # refusal_<lang>_<version>
        if len(parts) == 3:
            langs.add(parts[1])
    if (_DATA_DIR / f"refusal_{version}.json").exists():
        langs.add("en")
    return sorted(langs)
