"""Metrics — les trois plans de détection.

Frontière étanche : ces fonctions ne consomment QUE des `ModelHandle`,
`Activations` et directions ; elles ignorent totalement le format/quantif source.
"""
from modelscanner.metrics.axis_health import cohens_d, silhouette_scores
from modelscanner.metrics.behavioral import refusal_rate
from modelscanner.metrics.jorak import suppression, umin_signature, weight_signatures

__all__ = [
    "cohens_d",
    "silhouette_scores",
    "suppression",
    "umin_signature",
    "weight_signatures",
    "refusal_rate",
]
