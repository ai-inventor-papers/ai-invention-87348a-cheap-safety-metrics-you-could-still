"""Classifieur de provenance : (qualité × compliance × poids) -> 4 buckets."""
from modelscanner.classifier.scanner import Thresholds, classify, scan

__all__ = ["Thresholds", "classify", "scan"]
