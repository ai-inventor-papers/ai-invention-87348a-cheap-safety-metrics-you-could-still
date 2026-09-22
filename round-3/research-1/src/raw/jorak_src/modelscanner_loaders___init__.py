"""Loaders : safetensors + GGUF -> ModelHandle (API tenseurs unifiée).

Frontière étanche : tout ce qui sort d'ici est un `ModelHandle` ; rien en aval
ne sait d'où vient le modèle ni comment il était quantifié.
"""
from modelscanner.loaders.arch_adapter import (
    ArchSpec,
    UnsupportedArchitecture,
    autodetect_arch,
    get_hidden_size,
    get_num_layers,
    resolve,
    resolve_against_model,
    supported_model_types,
)
from modelscanner.loaders.errors import TransformersOutdated, UnsupportedFormat

__all__ = [
    "ArchSpec",
    "UnsupportedArchitecture",
    "UnsupportedFormat",
    "TransformersOutdated",
    "autodetect_arch",
    "get_hidden_size",
    "get_num_layers",
    "resolve",
    "resolve_against_model",
    "supported_model_types",
    "load_model",
]


def load_model(*args, **kwargs):  # pragma: no cover - défini en J1
    """Charge un modèle (safetensors/gguf) -> ModelHandle. Implémenté en J1."""
    from modelscanner.loaders.safetensors_loader import load_model as _load

    return _load(*args, **kwargs)
