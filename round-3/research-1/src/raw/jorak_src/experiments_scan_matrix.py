#!/usr/bin/env python3
"""Scanne UN modèle (un process = mémoire libérée à la sortie) et imprime les
signaux de calibration. Usage: python experiments/scan_matrix.py <hf-id> [n_probes]"""
import os
import sys

import numpy as np
import torch

from modelscanner.classifier import scan
from modelscanner.loaders import load_model

mid = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
beh = "beh" in sys.argv[3:]
lang = next((a for a in sys.argv[3:] if a in ("en", "zh", "fr", "de", "es", "it")), "en")

h = load_model(mid, device="cpu", dtype=torch.float32)
r = scan(h, probe_subset=n, batch_size=4, with_behavioral=beh, lang=lang)

d = np.asarray(r.cohens_d)
supp_o = np.asarray(r.suppression["o_proj"])
supp_d = np.asarray(r.suppression["down_proj"])

print("\n================  %s  ================" % mid)
print("  LABEL      : %s   (confiance %.2f)" % (r.label.value.upper(), r.confidence))
print("  refusal    : %s                  (obéit si <0.5)" % (
    "None" if r.behavioral_refusal_rate is None else "%.2f" % r.behavioral_refusal_rate))
print("  cohens_d   : max %.2f  mean %.2f  (axe vivant si max>=1.0)" % (np.nanmax(d), np.nanmean(d)))
print("  svd_align  : %.3f                 (sectionné si >=0.5)" % r.svd_alignment)
print("  suppr o_proj median   %.4f        (sectionné si <=1e-2)" % float(np.median(supp_o)))
print("  suppr down_proj median %.4f" % float(np.median(supp_d)))
print("  detail     :", r.meta["classify_detail"])

os.makedirs("scans", exist_ok=True)
tag = mid.replace("/", "__")
out = "scans/%s.npz" % tag
r.save(out)
print("  saved      :", out)

from modelscanner.report import write_scan_log

logp = write_scan_log(r, "logs/%s.json" % tag, flags={"device": "cpu", "dtype": "float32"})
print("  log        :", logp)
