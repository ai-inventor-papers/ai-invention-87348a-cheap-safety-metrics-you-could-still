"""Model Scanner — détection reference-free d'abliteration de LLM.

Point d'entrée haut niveau : ``scan()`` (à brancher en J8). Pour l'instant on
expose les contrats de données stables.
"""
from modelscanner.core.types import (
    ModelHandle,
    Provenance,
    Quantization,
    ScanResult,
    WeightTarget,
)

__version__ = "0.1.0"

__all__ = [
    "ModelHandle",
    "Provenance",
    "Quantization",
    "ScanResult",
    "WeightTarget",
    "__version__",
]
