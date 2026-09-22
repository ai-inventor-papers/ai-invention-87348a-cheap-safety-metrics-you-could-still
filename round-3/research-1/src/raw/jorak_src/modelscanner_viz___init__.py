"""Viz matplotlib (livrables). [J9]

(1) `layer_heatmap` : couches × métrique {Cohen's d, suppression, alignement
    poids par couche} = le smoking-gun visuel (où le modèle est touché).
(2) `provenance_scatter` : plan 2D (sévérance des poids × compliance), 4 buckets
    colorés = preuve que le classifieur sépare les provenances (depuis ScanResult).
(3) `campaign_matrix` : même plan 4-buckets mais depuis les *dicts* agrégés d'une
    campagne (JSON multi-modèles) — livrable de `experiments/campaign_report.py`.
PaCMAP/t-SNE par couche : différés (§4, cher en CPU).
"""
from __future__ import annotations

from typing import List, Optional, Sequence

import matplotlib
import numpy as np

matplotlib.use("Agg")  # headless (pas d'affichage requis)
import matplotlib.pyplot as plt  # noqa: E402

from modelscanner.core.types import Provenance, ScanResult  # noqa: E402

# couleur par provenance (cohérent entre les deux figures)
_LABEL_COLOR = {
    Provenance.CENSORED: "#2c7fb8",
    Provenance.ABLATED: "#d7301f",
    Provenance.FINETUNED_DECENSORED: "#41ab5d",
    Provenance.AMBIGUOUS: "#969696",
}

# libellés bilingues de la matrice 4-buckets (coins + axes + titre)
_MATRIX_LABELS = {
    "fr": {
        "title": "Matrice de provenance — campagne",
        "censored": "CENSURÉ\n(refuse · poids intacts)",
        "ambiguous": "AMBIGU / ablation partielle\n(refuse · poids sectionnés)",
        "finetuned": "FINE-TUNÉ\n(obéit · poids intacts)",
        "ablated": "ABLITÉRÉ\n(obéit · poids sectionnés)",
        "xlabel": "sévérance des poids  (sectionné →)",
        "ylabel": "taux de refus  (↑ refuse)",
        "legend": "prédit",
        "no_refusal": ("\n(comportemental absent → losanges sur la médiane ; "
                       "CENSURÉ/FINE-TUNÉ non séparables)"),
    },
    "en": {
        "title": "Provenance matrix — campaign",
        "censored": "CENSORED\n(refuses · weights intact)",
        "ambiguous": "AMBIGUOUS / partial ablation\n(refuses · weights severed)",
        "finetuned": "FINE-TUNED\n(complies · weights intact)",
        "ablated": "ABLITERATED\n(complies · weights severed)",
        "xlabel": "weight severance  (severed →)",
        "ylabel": "refusal rate  (↑ refuses)",
        "legend": "predicted",
        "no_refusal": ("\n(behavioral missing → diamonds on the median; "
                       "CENSORED/FINE-TUNED not separable)"),
    },
}


def layer_heatmap(result: ScanResult, *, path: Optional[str] = None, title: Optional[str] = None):
    """Heatmap couches × métriques. Chaque ligne = une métrique, son échelle.

    Lignes : Cohen's d (santé d'axe), suppression o_proj & down_proj, alignement
    poids par couche (u_min vs axe partagé) = la signature d'ablation par couche.
    """
    rows, labels = [], []
    if result.cohens_d is not None:
        rows.append(np.asarray(result.cohens_d)); labels.append("Cohen's d")
    for tgt in ("o_proj", "down_proj"):
        if tgt in result.suppression:
            rows.append(np.asarray(result.suppression[tgt])); labels.append(f"suppr {tgt}")
    if result.weight_axis_align is not None:
        rows.append(np.asarray(result.weight_axis_align)); labels.append("align poids/couche")
    if not rows:
        raise ValueError("ScanResult sans métrique par couche à tracer.")

    # échelle fixe pour les métriques bornées (comparables entre modèles)
    _FIXED = {"align poids/couche": (0.0, 1.0)}

    n_rows = len(rows)
    fig, axes = plt.subplots(n_rows, 1, figsize=(max(6, result.n_layers * 0.35), 1.1 * n_rows + 1),
                             squeeze=False)
    for ax, row, lab in zip(axes[:, 0], rows, labels):
        vmin, vmax = _FIXED.get(lab, (None, None))
        im = ax.imshow(row[None, :], aspect="auto", cmap="magma", vmin=vmin, vmax=vmax)
        ax.set_yticks([0]); ax.set_yticklabels([lab], fontsize=9)
        ax.set_xticks([])
        fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    axes[-1, 0].set_xticks(range(0, result.n_layers, max(1, result.n_layers // 12)))
    axes[-1, 0].set_xlabel("couche")
    ttl = title or f"{result.model_id} — {result.label.value} (conf {result.confidence:.2f})"
    fig.suptitle(ttl, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    if path:
        fig.savefig(path, dpi=130, bbox_inches="tight")
    return fig


def provenance_scatter(results: Sequence[ScanResult], *, path: Optional[str] = None,
                       severed_thr: float = 0.5, obey_thr: float = 0.5):
    """Plan de provenance : x = alignement SVD (poids sectionnés ->),
    y = taux de refus (compliance, ^ = refuse). Les 4 buckets occupent des coins
    distincts. Couleur = label prédit."""
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ax.axvline(severed_thr, color="0.7", ls="--", lw=1)
    ax.axhline(obey_thr, color="0.7", ls="--", lw=1)

    seen = set()
    for r in results:
        x = r.svd_alignment if r.svd_alignment is not None else np.nan
        y = r.behavioral_refusal_rate
        y = 0.5 if y is None else y  # comportemental absent -> ligne médiane
        c = _LABEL_COLOR.get(r.label, "#969696")
        lab = r.label.value if r.label.value not in seen else None
        seen.add(r.label.value)
        ax.scatter(x, y, c=c, s=120, edgecolors="k", linewidths=0.6, label=lab, zorder=3)
        ax.annotate(r.model_id.split("/")[-1], (x, y), fontsize=7,
                    xytext=(4, 4), textcoords="offset points")

    # annotations de coin (où tombe chaque provenance)
    ax.text(0.02, 0.97, "CENSURÉ\n(refuse, poids intacts)", transform=ax.transAxes,
            fontsize=8, va="top", color="#2c7fb8")
    ax.text(0.98, 0.03, "ABLITÉRÉ\n(obéit, poids sectionnés)", transform=ax.transAxes,
            fontsize=8, ha="right", color="#d7301f")
    ax.text(0.02, 0.03, "FINE-TUNÉ\n(obéit, poids intacts)", transform=ax.transAxes,
            fontsize=8, color="#41ab5d")

    ax.set_xlabel("alignement SVD u_min  (poids sectionnés →)")
    ax.set_ylabel("taux de refus  (↑ refuse)")
    ax.set_xlim(0, 1); ax.set_ylim(-0.05, 1.05)
    ax.set_title("Plan de provenance")
    ax.legend(loc="center left", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130, bbox_inches="tight")
    return fig


def campaign_matrix(records, *, path: Optional[str] = None,
                    title: Optional[str] = None, lang: str = "fr",
                    severed_thr: float = 0.5, obey_thr: float = 0.5):
    """Matrice 4-buckets d'une campagne, tracée à partir de *dicts* (pas de
    ScanResult — on lit directement les JSON agrégés du run).

    Chaque `record` attendu : ``{model, predicted (ou label), severance, refusal,
    expected, status}`` (cf. `experiments/campaign_report.py`). Plan 2D identique à
    `provenance_scatter` mais robuste au multi-modèles :
      - x = sévérance des poids (sectionné →) -> place correctement les ablations
        LOCALISÉES (Heretic : SVD bas, bande haute) ;
      - y = taux de refus (comportemental). Absent -> losange sur la médiane ;
      - couleur = label prédit, anneau rouge = prédiction ≠ attendu.

    `lang` ("fr" | "en") choisit la langue des libellés (coins + axes + titre).
    """
    L = _MATRIX_LABELS["en" if lang == "en" else "fr"]
    title = title if title is not None else L["title"]
    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.axvline(severed_thr, color="0.7", ls="--", lw=1)
    ax.axhline(obey_thr, color="0.7", ls="--", lw=1)

    seen: set = set()
    any_refusal = False
    plotted = 0
    for rec in records:
        if rec.get("status") != "OK":
            continue
        x = rec.get("severance")
        if x is None:
            continue
        ref = rec.get("refusal")
        has_ref = ref is not None
        any_refusal = any_refusal or has_ref
        y = 0.5 if ref is None else ref
        pred = rec.get("predicted", rec.get("label"))
        try:
            lab = Provenance(pred)
        except ValueError:
            lab = Provenance.AMBIGUOUS
        c = _LABEL_COLOR.get(lab, "#969696")
        legend_lab = lab.value if lab.value not in seen else None
        seen.add(lab.value)
        ax.scatter(x, y, c=c, s=130, edgecolors="k", linewidths=0.6,
                   marker=("o" if has_ref else "D"), label=legend_lab, zorder=3)
        exp = rec.get("expected")
        if exp and exp != pred:                       # erreur de classification
            ax.scatter(x, y, s=330, facecolors="none", edgecolors="#d7301f",
                       linewidths=1.8, zorder=2)
        ax.annotate(str(rec.get("model", "")).split("/")[-1], (x, y), fontsize=7,
                    xytext=(5, 4), textcoords="offset points")
        plotted += 1

    # libellés de coin = où tombe chaque provenance
    ax.text(0.02, 0.97, L["censored"], transform=ax.transAxes,
            fontsize=8, va="top", color=_LABEL_COLOR[Provenance.CENSORED])
    ax.text(0.98, 0.97, L["ambiguous"],
            transform=ax.transAxes, fontsize=8, va="top", ha="right",
            color=_LABEL_COLOR[Provenance.AMBIGUOUS])
    ax.text(0.02, 0.03, L["finetuned"], transform=ax.transAxes,
            fontsize=8, color=_LABEL_COLOR[Provenance.FINETUNED_DECENSORED])
    ax.text(0.98, 0.03, L["ablated"], transform=ax.transAxes,
            fontsize=8, ha="right", color=_LABEL_COLOR[Provenance.ABLATED])

    ax.set_xlabel(L["xlabel"])
    ax.set_ylabel(L["ylabel"])
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.05, 1.05)
    ttl = title
    if plotted and not any_refusal:
        ttl += L["no_refusal"]
    ax.set_title(ttl, fontsize=10)
    if seen:
        ax.legend(loc="center left", fontsize=8, framealpha=0.9, title=L["legend"])
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130, bbox_inches="tight")
    return fig
