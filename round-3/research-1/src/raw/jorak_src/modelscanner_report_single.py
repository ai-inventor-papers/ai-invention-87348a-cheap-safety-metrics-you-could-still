"""Rapport JORAK — bundle autonome d'un *scan unique* (terminal, hors campagne).

`modelscanner scan <model> --report` produit un dossier local daté :

    <model>_jorak_<YYYYMMDD>/
      jorak_report_en.html  — rapport autonome, explications EN, onglets de langue, tooltips
      jorak_report_fr.html  — idem en français
      prompts.csv           — toutes les paires question/réponse (comportemental + multilingue + profil)
      summary.csv           — une ligne de métriques (verdict + signaux poids/activations/refus)
      scan_log.json         — la trace JSON complète (réutilise modelscanner.report)
      layers_heatmap.png    — heatmap couches × métriques (si plan activations dispo)
      bucket_position.png   — plan 4-buckets, 1 point = ce modèle (réutilisable par `compare`)

Chaque HTML est autonome (CSS/JS inline, aucun asset externe) : un fichier par langue,
avec bascule thème clair/sombre, onglets cliquables par langue pour les Q/R, infobulles
d'interprétation sur chaque indicateur, et surtout deux schématiques **interactives**
dessinées en HTML/SVG depuis la trace JSON — la heatmap par couche (survol = lecture des
métriques de la couche) et le plan 4-buckets du modèle (pas de PNG embarqué).
`compare_bundles()` superpose plusieurs bundles sur un même plan (CLI : `modelscanner
compare`). La campagne multi-modèles reste dans experiments/campaign_report.py.
"""
from __future__ import annotations

import csv
import datetime
import glob
import html
import io
import json
import os
import re
import shutil
import subprocess
from typing import Optional

from modelscanner import ui
from modelscanner.core.types import ScanResult
from modelscanner.report import scan_log_dict, write_scan_log

# palette partagée avec modelscanner.viz / campaign_report (cohérence des labels)
_LABEL_COLOR = {
    "censored": "#2c7fb8",
    "ablated": "#d7301f",
    "finetuned_decensored": "#41ab5d",
    "ambiguous": "#969696",
}

# ----------------------------------------------------------------------------- #
# i18n — tout le texte d'interface, par langue ("en" / "fr")                     #
# ----------------------------------------------------------------------------- #
_LABEL = {
    "en": {"censored": "Censored / base", "ablated": "Abliterated (directional ablation)",
           "finetuned_decensored": "Fine-tuned decensored", "ambiguous": "Ambiguous"},
    "fr": {"censored": "Censuré / base", "ablated": "Abliteré (ablation directionnelle)",
           "finetuned_decensored": "Fine-tuné décensuré", "ambiguous": "Ambigu"},
}
_LABEL_DESC = {
    "en": {
        "censored": "The model refuses harmful requests; the refusal axis is intact in the weights.",
        "ablated": "The refusal axis has been severed in the weights (directional ablation / abliteration).",
        "finetuned_decensored": "Decensored through fine-tuning (Dolphin-style), not directional ablation.",
        "ambiguous": "Contradictory or insufficient signals to decide.",
    },
    "fr": {
        "censored": "Le modèle refuse les requêtes nuisibles ; l'axe de refus est intact dans les poids.",
        "ablated": "L'axe de refus a été sectionné dans les poids (ablation directionnelle / abliteration).",
        "finetuned_decensored": "Décensuré par fine-tuning (type Dolphin), pas par ablation directionnelle.",
        "ambiguous": "Signaux contradictoires ou insuffisants pour trancher.",
    },
}
_LANG_NAMES = {
    "en": {"en": "English", "zh": "Chinese", "fr": "French", "de": "German",
           "es": "Spanish", "it": "Italian"},
    "fr": {"en": "Anglais", "zh": "Chinois", "fr": "Français", "de": "Allemand",
           "es": "Espagnol", "it": "Italien"},
}
_SRC = {
    "en": {"behavioral": "behavioral", "multilingual": "multilingual", "profile": "profile"},
    "fr": {"behavioral": "comportemental", "multilingual": "multilingue", "profile": "profil"},
}
_CAT = {
    "en": {"harmful": "harmful", "harmless": "harmless", "fact": "fact"},
    "fr": {"harmful": "nuisible", "harmless": "inoffensif", "fact": "fait"},
}
_TAG = {
    "en": {"refusal": "refusal", "answers": "answers", "correct": "correct", "wrong": "wrong"},
    "fr": {"refusal": "refus", "answers": "répond", "correct": "correct", "wrong": "faux"},
}
_STR = {
    "en": {
        "tagline": "Reference-free directional-ablation detection · Model Scanner",
        "layers": "layers", "confidence": "confidence",
        "expected": "expected", "conform": "✓ conform", "divergent": "✗ divergent",
        "h2_signals": "Key signals", "h2_heatmap": "Per-layer signature",
        "h2_bucket": "4-bucket position", "sub_bucket": "weight severance × refusal",
        "sub_heatmap": "severance & axis health · per layer · hover for detail",
        "h2_multilingual": "Multilingual asymmetry", "sub_multilingual": "refusal & over-refusal per language",
        "mra_lab": "MRA (max asymmetry)", "over_max_lab": "max over-refusal",
        "ml_language": "language", "ml_refusal": "refusal (harmful)", "ml_over": "over-refusal (harmless)",
        "h2_profile": "Model profile", "sub_profile": "behavior · quality · hallucination",
        "h2_prompts": "Prompt responses", "n_generations": "generations",
        "prompts_empty": "No generation captured (model not runnable, or behavioral/profile plans disabled).",
        "col_source": "source", "col_lang": "language", "col_category": "category",
        "col_question": "question", "col_response": "response", "col_verdict": "verdict",
        "meaning": "Meaning", "reading": "Reading",
        "evasive": "⚠ Stealthy ablation suspected — weights look intact to JORAK, but the axis is "
                   "strongly live, the model complies on harmful, and behavior is damaged "
                   "(norm-preserving multi-direction).",
        "footer": "Report generated by JORAK (Model Scanner) on {now}. Reference-free verdict: "
                  "no original model required. Weight severance = max(global SVD, band, subspace).",
        "tabs_hint": "Click a language tab to see its prompts and responses.",
    },
    "fr": {
        "tagline": "Détection reference-free d'ablation directionnelle · Model Scanner",
        "layers": "couches", "confidence": "confiance",
        "expected": "attendu", "conform": "✓ conforme", "divergent": "✗ divergent",
        "h2_signals": "Signaux clés", "h2_heatmap": "Signature par couche",
        "h2_bucket": "Position 4-buckets", "sub_bucket": "sévérance des poids × refus",
        "sub_heatmap": "sévérance & santé d'axe · par couche · survol pour le détail",
        "h2_multilingual": "Asymétrie multilingue", "sub_multilingual": "refus & sur-refus par langue",
        "mra_lab": "MRA (asymétrie max)", "over_max_lab": "sur-refus max",
        "ml_language": "langue", "ml_refusal": "refus (harmful)", "ml_over": "sur-refus (harmless)",
        "h2_profile": "Profil du modèle", "sub_profile": "comportement · qualité · hallucination",
        "h2_prompts": "Réponses aux prompts", "n_generations": "générations",
        "prompts_empty": "Aucune génération capturée (modèle non exécutable, ou plans "
                         "comportemental/profil désactivés).",
        "col_source": "source", "col_lang": "langue", "col_category": "catégorie",
        "col_question": "question", "col_response": "réponse", "col_verdict": "verdict",
        "meaning": "Signification", "reading": "Interprétation",
        "evasive": "⚠ Ablation furtive suspectée — les poids paraissent intacts pour JORAK, mais "
                   "l'axe est fortement vivant, le modèle obéit au harmful et le comportement est "
                   "abîmé (norm-preserving multi-direction).",
        "footer": "Rapport généré par JORAK (Model Scanner) le {now}. Verdict reference-free : "
                  "aucun modèle de référence requis. Sévérance des poids = max(SVD global, bande, sous-espace).",
        "tabs_hint": "Clique un onglet de langue pour voir ses prompts et réponses.",
    },
}
# infobulles par indicateur : (signification, interprétation), par langue
_TIP = {
    "en": {
        "svd_global": ("Global SVD alignment A = σ₁(U)/‖U‖_F over the per-layer u_min vectors stacked.",
                       "High (>~0.5) → the refusal direction is severed from the weights across the whole model: full-ablation signature."),
        "band": ("Band alignment B = the same measure restricted to the most-aligned contiguous band of layers.",
                 "High while A is low → localized / stealthy ablation (Heretic-style) confined to a few layers."),
        "subspace": ("Subspace alignment S = alignment of the shared bottom-k weight subspace (k ≈ number of ablated directions).",
                     "Catches multi-direction ablation (n_directions>1, e.g. OBLITERATUS) that a single u_min dilutes."),
        "cohens_mean": ("Mean Cohen's d between harmful and harmless activations across layers (axis health).",
                        "High → the refusal axis is still alive in the activations even if the weights were severed."),
        "cohens_max": ("Maximum per-layer Cohen's d (peak separability of the refusal axis).",
                       "A live axis (high d) combined with severed weights is the abliteration smoking-gun."),
        "refusal": ("Behavioral refusal rate: fraction of harmful prompts the model declines.",
                    "Low → the model complies (decensored); high → it still refuses (censored)."),
        "over_refusal": ("Harmless over-refusal: fraction of harmless prompts wrongly refused.",
                         "High & incoherent → behavioral damage typical of stealthy ablation, not a clean fine-tune."),
        "confidence": ("Classifier confidence in the predicted provenance label.",
                       "Margin of the winning bucket over the others; reference-free, no original model needed."),
        "mra": ("MRA = max(other-language refusal) − base-language refusal.",
                ">~0.3 → EN-only / partial ablation: obeys in English but still refuses in other languages."),
        "prof_refusal_harmful": ("Profile refusal rate on harmful prompts (independent generation pass).",
                                 "Cross-check of the behavioral refusal signal."),
        "prof_compliance_harmless": ("Compliance on harmless prompts (1 − over-refusal).",
                                     "Low → the model over-refuses benign requests (usability / damage signal)."),
        "prof_factual": ("Factual accuracy on a mini fact-QA set (lightweight hallucination proxy).",
                         "Drops can signal capability damage from aggressive ablation."),
        "prof_perplexity": ("Perplexity on neutral text (fluency proxy, reference-free KL stand-in).",
                            "Higher → more degraded language modeling."),
        "prof_repetition": ("Repetition rate of generations.",
                            "High → looping / degraded output, a side effect of heavy weight editing."),
    },
    "fr": {
        "svd_global": ("Alignement SVD global A = σ₁(U)/‖U‖_F sur les vecteurs u_min empilés par couche.",
                       "Élevé (>~0,5) → la direction de refus est sectionnée des poids sur tout le modèle : signature d'ablation totale."),
        "band": ("Alignement de bande B = même mesure restreinte à la bande de couches contiguës la plus alignée.",
                 "Élevé alors que A est bas → ablation localisée / furtive (type Heretic) confinée à quelques couches."),
        "subspace": ("Alignement de sous-espace S = alignement du sous-espace bottom-k partagé des poids (k ≈ nb de directions ablatées).",
                     "Capte l'ablation multi-direction (n_directions>1, ex. OBLITERATUS) qu'un seul u_min dilue."),
        "cohens_mean": ("Cohen's d moyen entre activations harmful et harmless sur les couches (santé d'axe).",
                        "Élevé → l'axe de refus est encore vivant dans les activations même si les poids ont été sectionnés."),
        "cohens_max": ("Cohen's d maximal par couche (séparabilité de pointe de l'axe de refus).",
                       "Un axe vivant (d élevé) combiné à des poids sectionnés = le smoking-gun de l'abliteration."),
        "refusal": ("Taux de refus comportemental : fraction des prompts nuisibles que le modèle décline.",
                    "Bas → le modèle obéit (décensuré) ; haut → il refuse encore (censuré)."),
        "over_refusal": ("Sur-refus du harmless : fraction des prompts inoffensifs refusés à tort.",
                         "Élevé et incohérent → dégât comportemental typique d'une ablation furtive, pas d'un fine-tune propre."),
        "confidence": ("Confiance du classifieur dans le label de provenance prédit.",
                       "Marge du bucket gagnant sur les autres ; reference-free, sans modèle d'origine."),
        "mra": ("MRA = max(refus autres langues) − refus langue de base.",
                ">~0,3 → ablation EN-only / partielle : obéit en anglais mais refuse encore ailleurs."),
        "prof_refusal_harmful": ("Taux de refus du profil sur prompts nuisibles (passe de génération indépendante).",
                                 "Contre-vérification du signal de refus comportemental."),
        "prof_compliance_harmless": ("Compliance sur prompts inoffensifs (1 − sur-refus).",
                                     "Bas → le modèle sur-refuse des requêtes bénignes (signal d'utilisabilité / dégât)."),
        "prof_factual": ("Exactitude factuelle sur un mini-QA de faits (proxy léger d'hallucination).",
                         "Une baisse peut signaler un dégât de capacité dû à une ablation agressive."),
        "prof_perplexity": ("Perplexité sur texte neutre (proxy de fluidité, substitut reference-free de la KL).",
                            "Plus élevé → modélisation du langage plus dégradée."),
        "prof_repetition": ("Taux de répétition des générations.",
                            "Élevé → sortie en boucle / dégradée, effet de bord d'une édition lourde des poids."),
    },
}

# ordre de préférence des onglets de langue (anglais en premier)
_LANG_ORDER = ["en", "zh", "fr", "de", "es", "it"]

# ----------------------------------------------------------------------------- #
# i18n des schématiques interactives (heatmap par couche + plan 4-buckets)       #
# Tout ce texte est injecté tel quel dans `window.JORAK_SCHEM` (rendu par _JS).  #
# `rows` : (libellé, domaine) par métrique. `interp` : barème décroissant        #
# [seuil, texte] — le JS prend le 1er dont la valeur ≥ seuil.                     #
# ----------------------------------------------------------------------------- #
_SCHEM_I18N = {
    "en": {
        "rows": {
            "cd": ("Cohen's d", "axis health · activations"),
            "op": ("o_proj suppr.", "attention output"),
            "dp": ("down_proj suppr.", "MLP output"),
            "wa": ("weight–axis align", "weights · u_min"),
        },
        "interp": {
            "cd": [[0.6, "axis strongly separable — alive"], [0.3, "axis present"], [0.0, "axis weak here"]],
            "op": [[0.3, "refusal direction strongly removed (attention)"], [0.1, "partially removed"], [0.0, "attention untouched"]],
            "dp": [[0.3, "refusal direction strongly removed (MLP)"], [0.1, "partially removed"], [0.0, "MLP untouched"]],
            "wa": [[0.5, "weights severed — aligned w/ removed direction"], [0.25, "partial alignment"], [0.0, "direction retained"]],
        },
        "hover": "Hover a layer to read its metrics &amp; interpretation.",
        "layer": "Layer",
        "in_band": "· severed band {a}–{b}",
        "intact": "· intact",
        "band_label": "severed band {a}–{b}",
        "weak": "weak", "strong": "strong",
        "note": "o_proj = attention output · down_proj = MLP output · per-layer suppression",
        "bucket": {
            "ablated": "ABLITERATED", "evasive": "EVASIVE",
            "clean": "CLEAN / DECENSORED", "censored": "CENSORED · INTACT",
            "x": "behavioral refusal rate →", "y": "weight severance →",
            "this": "this model", "sevref": "sev {sev} · ref {ref}",
        },
    },
    "fr": {
        "rows": {
            "cd": ("Cohen's d", "santé d'axe · activations"),
            "op": ("suppr. o_proj", "sortie attention"),
            "dp": ("suppr. down_proj", "sortie MLP"),
            "wa": ("align. poids–axe", "poids · u_min"),
        },
        "interp": {
            "cd": [[0.6, "axe fortement séparable — vivant"], [0.3, "axe présent"], [0.0, "axe faible ici"]],
            "op": [[0.3, "direction de refus fortement retirée (attention)"], [0.1, "partiellement retirée"], [0.0, "attention intacte"]],
            "dp": [[0.3, "direction de refus fortement retirée (MLP)"], [0.1, "partiellement retirée"], [0.0, "MLP intact"]],
            "wa": [[0.5, "poids sectionnés — alignés sur la direction retirée"], [0.25, "alignement partiel"], [0.0, "direction conservée"]],
        },
        "hover": "Survole une couche pour lire ses métriques et leur interprétation.",
        "layer": "Couche",
        "in_band": "· bande sectionnée {a}–{b}",
        "intact": "· intact",
        "band_label": "bande sectionnée {a}–{b}",
        "weak": "faible", "strong": "fort",
        "note": "o_proj = sortie attention · down_proj = sortie MLP · suppression par couche",
        "bucket": {
            "ablated": "ABLITÉRÉ", "evasive": "ÉVASIF",
            "clean": "PROPRE / DÉCENSURÉ", "censored": "CENSURÉ · INTACT",
            "x": "taux de refus comportemental →", "y": "sévérance des poids →",
            "this": "ce modèle", "sevref": "sév {sev} · ref {ref}",
        },
    },
}


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _slug(model_id: str) -> str:
    """`org/Name-v1` | `/chemin/local/Model` -> slug fichier sûr et lisible."""
    base = os.path.basename(model_id.rstrip("/")) or model_id
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_.")
    return base or "model"


def _fmt(v, n: int = 3) -> str:
    """Scalaire -> texte court ('—' si None)."""
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{n}f}"
    return str(v)


def _cell(v) -> str:
    return "" if v in (None, "") else html.escape(str(v))


def _badge(label: Optional[str], lang: str) -> str:
    if not label:
        return ""
    color = _LABEL_COLOR.get(label, "#969696")
    name = _LABEL.get(lang, _LABEL["en"]).get(label, label)
    return (f'<span class="badge" style="background:{color}">'
            f'{html.escape(name)}</span>')


def _lang_name(code: str, lang: str) -> str:
    return _LANG_NAMES.get(lang, _LANG_NAMES["en"]).get(code, code.upper() if code else "—")


# --------------------------------------------------------------------------- #
# Collecte des prompts (Q/R) toutes sources confondues                         #
# --------------------------------------------------------------------------- #
def collect_prompts(result: ScanResult) -> list[dict]:
    """Aplatit toutes les paires Q/R disponibles en lignes normalisées.

    Sources :
      - meta['behavioral_qa']      (plan comportemental --behavioral)
      - meta['multilingual_qa']    (asymétrie multilingue --multilingual)
      - meta['model_profile']['samples']  (profil --profile)

    Colonnes : source, lang, category, prompt, response, refusal, correct.
    """
    meta = result.meta or {}
    run_lang = (meta.get("run") or {}).get("lang", "")
    rows: list[dict] = []

    for r in meta.get("behavioral_qa") or []:
        rows.append({
            "source": "behavioral", "lang": r.get("lang", run_lang),
            "category": "harmful", "prompt": r.get("prompt", ""),
            "response": r.get("response", ""),
            "refusal": r.get("refusal"), "correct": "",
        })
    for r in meta.get("multilingual_qa") or []:
        rows.append({
            "source": "multilingual", "lang": r.get("lang", ""),
            "category": r.get("category", "harmful"), "prompt": r.get("prompt", ""),
            "response": r.get("response", ""),
            "refusal": r.get("refusal"), "correct": "",
        })
    prof = meta.get("model_profile") or {}
    for r in prof.get("samples") or []:
        rows.append({
            "source": "profile", "lang": run_lang,
            "category": r.get("category", ""), "prompt": r.get("prompt", ""),
            "response": r.get("response", ""),
            "refusal": r.get("refusal", ""), "correct": r.get("correct", ""),
        })
    return rows


_PROMPT_COLUMNS = ["source", "lang", "category", "prompt", "response", "refusal", "correct"]


def write_prompts_csv(rows: list[dict], path: str) -> str:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_PROMPT_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in _PROMPT_COLUMNS})
    return path


def _summary_row(result: ScanResult) -> dict:
    """Aplatit la section `results` de la trace en une ligne de métriques."""
    log = scan_log_dict(result)
    scan, res = log["scan"], log["results"]
    detail = res.get("classify_detail") or {}
    mlt = (result.meta or {}).get("multilingual") or {}
    return {
        "model": scan.get("model"),
        "model_type": scan.get("model_type"),
        "quantization": scan.get("quantization"),
        "n_layers": scan.get("n_layers"),
        "hidden_size": scan.get("hidden_size"),
        "timestamp": scan.get("timestamp"),
        "expected_label": res.get("expected_label"),
        "predicted_label": res.get("label"),
        "matches_expected": res.get("matches_expected"),
        "confidence": res.get("confidence"),
        "svd_alignment_global": res.get("svd_alignment_global"),
        "band_alignment": res.get("band_alignment"),
        "subspace_alignment": detail.get("subspace_alignment"),
        "subspace_band": detail.get("subspace_band"),
        "svd_pairwise_cos": res.get("svd_pairwise_cos"),
        "max_cohens_d": res.get("max_cohens_d"),
        "mean_cohens_d": res.get("mean_cohens_d"),
        "behavioral_refusal_rate": res.get("behavioral_refusal_rate"),
        "over_refusal": detail.get("over_refusal"),
        "refusal_spread": detail.get("refusal_spread"),
        "mra": mlt.get("mra"),
        "ml_max_over_refusal": mlt.get("max_over_refusal"),
        "ml_over_refusal_spread": mlt.get("over_refusal_spread"),
        "axis_alive": detail.get("axis_alive"),
        "write_severed": detail.get("write_severed"),
        "evasive_ablation": detail.get("evasive_ablation"),
        "touched_band": res.get("touched_band"),
    }


def write_summary_csv(result: ScanResult, path: str) -> str:
    row = _summary_row(result)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return path


# --------------------------------------------------------------------------- #
# Plan 4-buckets — un point par modèle (réutilise viz.campaign_matrix)         #
# --------------------------------------------------------------------------- #
_BUCKET_COLUMNS = ["model", "status", "predicted", "severance", "refusal", "expected"]


def _bucket_record_from_log(d: dict) -> dict:
    """Trace JSON (`scan_log.json`) -> record pour la matrice 4-buckets.

    severance (x) = max des signaux de poids dispo (SVD global, bande, sous-espace) ;
    refusal (y) = taux de refus comportemental ; couleur = label prédit.
    """
    scan = d.get("scan") or {}
    res = d.get("results") or {}
    detail = res.get("classify_detail") or {}
    is_err = bool(d.get("error")) or not d.get("results")
    sev_vals = [res.get("svd_alignment_global"), res.get("band_alignment"),
                detail.get("subspace_alignment"), detail.get("subspace_band")]
    sev = max([v for v in sev_vals if v is not None], default=None)
    return {
        "model": scan.get("model") or "?",
        "status": "ERROR" if is_err else "OK",
        "predicted": "ERROR" if is_err else res.get("label"),
        "severance": sev,
        "refusal": res.get("behavioral_refusal_rate"),
        "expected": res.get("expected_label") or scan.get("expected_label"),
    }


def bucket_record(result: ScanResult) -> dict:
    """Record 4-buckets directement depuis un ScanResult vivant."""
    return _bucket_record_from_log(scan_log_dict(result))


def render_bucket_png(records: list[dict], path: Optional[str] = None, *,
                      lang: str = "fr", title: Optional[str] = None) -> Optional[bytes]:
    """Trace le plan 4-buckets (1 point/record) -> octets PNG (et fichier si `path`).

    Renvoie ``None`` si matplotlib indisponible (best-effort, comme la heatmap)."""
    try:
        import matplotlib.pyplot as plt

        from modelscanner.viz import campaign_matrix
    except Exception as e:
        print(f"  [warn] plan 4-buckets ignoré (matplotlib KO) : {e}")
        return None
    fig = campaign_matrix(records, lang=lang, title=title)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    data = buf.getvalue()
    if path:
        with open(path, "wb") as f:
            f.write(data)
    return data


# --------------------------------------------------------------------------- #
# HTML — branding JORAK (CSS/JS statiques, contenu i18n)                       #
# --------------------------------------------------------------------------- #
# Marque JORAK : le « J » est dessiné en grille géométrique (le mot rend « JORAK »
# = ce glyphe + le span "ORAK"). Inline, dégradé bleu, HTML autonome (pas d'asset).
_JORAK_MARK = """\
<svg class="mark" viewBox="40 0 70 100" width="58" height="82" role="img" aria-label="J">\
<rect x="84" y="4" width="22" height="15.5" fill="#7cc2ff"/>\
<rect x="84" y="19.5" width="22" height="15.5" fill="#5fb2ff"/>\
<rect x="84" y="35" width="22" height="15.5" fill="#41a0ff"/>\
<rect x="84" y="50.5" width="22" height="15.5" fill="#2f90f6"/>\
<rect x="84" y="66" width="22" height="15.5" fill="#2f80ee"/>\
<rect x="84" y="81.5" width="22" height="14.5" fill="#2f6fe0"/>\
<rect x="50" y="68" width="18" height="18" fill="#2f80ee"/>\
<rect x="50" y="86" width="56" height="10" fill="#2f6fe0"/>\
<rect x="76" y="4" width="8" height="82" fill="#0b0b0c"/>\
<rect x="42" y="68" width="8" height="28" fill="#0b0b0c"/></svg>"""

# bouton bascule thème (clair/sombre), inline dans le header
_THEME_TOGGLE = """\
<button id="themeToggle" class="theme-toggle" type="button" aria-label="Toggle dark mode" title="Dark / light">
      <svg class="ic-moon" viewBox="0 0 24 24" width="19" height="19" aria-hidden="true"><path fill="currentColor" d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>
      <svg class="ic-sun" viewBox="0 0 24 24" width="19" height="19" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19"/></g></svg>
    </button>"""

# script (dans <head>) : applique le thème mémorisé AVANT le rendu (anti-flash)
_THEME_INIT = (
    "<script>(function(){try{var t=localStorage.getItem('jorak-theme')||"
    "((window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light');"
    "document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>"
)

_CSS = """\
  :root { --accent:#2563eb; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0;
          --bg:#f8fafc; --card:#ffffff; --verdict:#969696;
          --orange:#f97316; }
  * { box-sizing:border-box; }
  body { font:14px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,sans-serif;
         margin:0; color:var(--ink); background:var(--bg); }
  .wrap { max-width:1080px; margin:0 auto; padding:0 24px 56px; }
  header.brand { background:linear-gradient(120deg,#1e3a8a 0%,#16233f 45%,#0b1220 100%);
         color:#e9eef7; padding:22px 0; margin-bottom:26px;
         border-bottom:3px solid var(--accent); }
  .brand .wrap { display:flex; align-items:center; gap:16px; padding-bottom:0; }
  .mark { flex:none; display:block; }
  .brandgroup { display:flex; align-items:flex-start; gap:1px; }
  .namewrap { display:flex; flex-direction:column; }
  .word { line-height:1; }
  .word .wf { font-size:48px; font-weight:700; letter-spacing:4px;
          font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
          background:linear-gradient(180deg,#7fb6ff 0%,#2f6fe0 100%);
          -webkit-background-clip:text; background-clip:text; color:transparent; }
  .tagline { color:#9fb3d1; font-size:12px; letter-spacing:1px; margin-top:8px;
          text-transform:uppercase;
          font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace; }
  .tagline .sep { color:var(--orange); font-weight:800; margin:0 7px; letter-spacing:1px; }
  .brand .meta { margin-left:auto; text-align:right; color:#9fb3d1; font-size:12.5px;
          font-family:ui-monospace,monospace; }
  h1.model { font-size:20px; margin:0 0 2px; font-family:ui-monospace,monospace;
          word-break:break-all; }
  h2 { font-size:16px; margin:34px 0 12px; border-left:3px solid var(--accent);
       padding-left:10px; }
  h2 small { color:var(--muted); font-weight:400; font-size:12.5px; margin-left:6px; }
  .verdict { display:flex; align-items:center; gap:22px; flex-wrap:wrap;
          background:var(--card); border:1px solid var(--line);
          border-left:6px solid var(--verdict); border-radius:14px;
          padding:20px 24px; box-shadow:0 1px 3px rgba(15,23,42,.05); }
  .v-label { font-size:24px; font-weight:800; color:var(--verdict); }
  .v-desc { color:var(--muted); max-width:560px; }
  .gauge { margin-left:auto; text-align:center; flex:none; }
  .gauge .ring { width:96px; height:96px; border-radius:50%;
          background:conic-gradient(var(--verdict) calc(var(--p)*1%), var(--line) 0);
          display:flex; align-items:center; justify-content:center; }
  .gauge .ring i { width:74px; height:74px; border-radius:50%; background:var(--card);
          display:flex; align-items:center; justify-content:center;
          font-size:20px; font-weight:800; font-style:normal; }
  .gauge .cap { color:var(--muted); font-size:11.5px; margin-top:6px; }
  .expected { margin-top:14px; }
  .alert { margin-top:16px; padding:12px 16px; border-radius:10px; font-size:13px;
          background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; }
  .metrics { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
          gap:14px; margin-top:6px; }
  .metric { position:relative; background:var(--card); border:1px solid var(--line);
          border-radius:12px; padding:14px 16px; cursor:help; outline:none; }
  .metric:hover, .metric:focus { border-color:var(--accent); }
  .m-val { font-size:24px; font-weight:800; }
  .m-lab { color:var(--muted); font-size:12.5px; margin-top:2px; }
  .m-sub { color:#94a3b8; font-size:11px; margin-top:4px; }
  .info { position:absolute; top:9px; right:11px; width:16px; height:16px; border-radius:50%;
          background:#eef2f7; color:#64748b; font-size:11px; font-weight:700; line-height:16px;
          text-align:center; }
  .tip { position:absolute; left:0; top:calc(100% + 8px); z-index:20; width:280px;
          background:#0f172a; color:#e9eef7; border-radius:10px; padding:11px 13px;
          font-size:12px; line-height:1.5; box-shadow:0 8px 24px rgba(15,23,42,.25);
          display:none; }
  .tip b { color:#93c5fd; }
  .tip .rd { color:#5eead4; }
  .metric:hover .tip, .metric:focus .tip { display:block; }
  .grid2 { display:grid; grid-template-columns:1.4fr 1fr; gap:20px; align-items:start; }
  table { border-collapse:collapse; width:100%; background:var(--card);
          border:1px solid var(--line); border-radius:12px; overflow:hidden; }
  th,td { padding:8px 11px; text-align:left; border-bottom:1px solid var(--line);
          vertical-align:top; }
  thead th { background:#eef2f7; font-size:12px; text-transform:uppercase;
          letter-spacing:.4px; color:#475569; }
  table.lang th { width:64px; }
  .bar { display:inline-block; width:120px; height:8px; border-radius:5px;
          background:var(--line); margin-right:8px; vertical-align:middle; overflow:hidden; }
  .bar span { display:block; height:100%; background:var(--accent); }
  .bar span.warn { background:#ea580c; }
  .aside .metric { margin-bottom:10px; cursor:default; }
  .hint { color:var(--muted); font-size:12px; }
  .tabwrap { margin-top:6px; }
  .tabbar { display:flex; gap:2px; flex-wrap:wrap; border-bottom:2px solid var(--line); }
  .tabbar button { border:none; background:transparent; font:inherit; font-weight:600;
          color:var(--muted); cursor:pointer; padding:9px 15px; border-bottom:2px solid transparent;
          margin-bottom:-2px; border-radius:8px 8px 0 0; }
  .tabbar button:hover { color:var(--ink); background:#eef2f7; }
  .tabbar button.active { color:var(--accent); border-bottom-color:var(--accent); }
  .tabbar .cnt { color:#94a3b8; font-weight:600; }
  .tabpane { display:none; margin-top:12px; }
  .tabpane.active { display:block; }
  table.qa td.q { width:30%; color:#334155; }
  table.qa td.a { width:42%; font-family:ui-monospace,monospace; font-size:12.5px;
          color:#0f172a; white-space:pre-wrap; }
  td.src { font-family:ui-monospace,monospace; font-size:12px; color:var(--muted); }
  .tag { display:inline-block; padding:1px 8px; border-radius:10px; font-size:11px;
          font-weight:700; }
  .tag.ok { background:#dcfce7; color:#15803d; }
  .tag.bad { background:#fee2e2; color:#b91c1c; }
  .badge { display:inline-block; padding:2px 10px; border-radius:11px; color:#fff;
          font-size:12px; font-weight:700; }
  img { max-width:100%; border:1px solid var(--line); border-radius:12px; background:#fff;
       margin-top:6px; }
  footer { color:var(--muted); font-size:12px; margin-top:40px; padding-top:16px;
          border-top:2px solid var(--orange); }
  @media (max-width:720px) { .grid2 { grid-template-columns:1fr; } .tip { width:220px; } }
  /* ---- theme toggle button ---- */
  .theme-toggle { flex:none; display:inline-flex; align-items:center; justify-content:center;
          width:40px; height:40px; border-radius:10px; cursor:pointer; margin-left:6px;
          border:1px solid rgba(255,255,255,.28); background:rgba(255,255,255,.08); color:#e9eef7;
          transition:background .15s, border-color .15s; }
  .theme-toggle:hover { background:rgba(255,255,255,.18); border-color:var(--orange); }
  .theme-toggle .ic-sun { display:none; }
  :root[data-theme="dark"] .theme-toggle .ic-sun { display:block; }
  :root[data-theme="dark"] .theme-toggle .ic-moon { display:none; }

  /* ---- dark mode ---- */
  :root[data-theme="dark"] { --ink:#e7eef9; --muted:#9fb1c7; --line:#26344b;
          --bg:#0b1220; --card:#141d30; }
  :root[data-theme="dark"] thead th { background:#1a2540; color:#9fb1c7; }
  :root[data-theme="dark"] .info { background:#1a2540; color:#9fb1c7; }
  :root[data-theme="dark"] .tabbar button:hover { background:#1a2540; }
  :root[data-theme="dark"] .alert { background:#2a1d10; border-color:#6e4423; color:#f6c08a; }
  :root[data-theme="dark"] .bar { background:#26344b; }
  :root[data-theme="dark"] table.qa td.q { color:#b8c4d6; }
  :root[data-theme="dark"] table.qa td.a { color:#e7eef9; }
  /* ---- HTML schematics (heatmap + bucket) ---- */
  .schem { background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px 16px 10px; margin-top:6px; }
  .schem svg { display:block; width:100%; height:auto; }
  /* interactive heatmap */
  .hm { font-size:11px; }
  .hm-grid { display:grid; grid-template-columns:128px 1fr; row-gap:5px; align-items:center; }
  .hm-rl { text-align:right; padding-right:10px; color:#3a4a5e; font-weight:600; line-height:1.12; }
  .hm-rl small { display:block; color:#94a3b8; font-weight:400; font-size:9px; }
  .hm-strip { display:flex; gap:3px; }
  .hm-strip .cell { flex:1; height:24px; border-radius:2px; cursor:pointer; box-shadow:inset 0 0 0 1px rgba(20,50,100,.06); }
  .hm-strip .cell.hot { outline:2px solid var(--orange); outline-offset:-1px; }
  .hm-bandrow { position:relative; height:14px; }
  .hm-band { position:absolute; bottom:0; height:8px; border:2px solid var(--orange); border-bottom:none; border-radius:4px 4px 0 0; }
  .hm-band b { position:absolute; left:50%; top:-12px; transform:translateX(-50%); font-size:9.5px; color:var(--orange); font-weight:700; white-space:nowrap; }
  .hm-x { position:relative; height:13px; }
  .hm-x span { position:absolute; transform:translateX(-50%); font-size:9.5px; color:#94a3b8; }
  .hm-readout { margin-top:12px; border:1px solid #e4e8ee; border-radius:8px; background:#f7faff; padding:10px 14px; font-size:12.5px; color:#1f2937; min-height:138px; }
  .hm-readout .hint { color:#94a3b8; }
  .ro-h { font-weight:700; color:#1e3a8a; margin-bottom:7px; }
  .ro-h .sev { color:var(--orange); } .ro-h .int { color:#2f6b3d; }
  .ro-r { display:grid; grid-template-columns:148px 56px 1fr; gap:4px 12px; align-items:baseline; padding:2.5px 0; border-top:1px solid #eef2f7; }
  .ro-m { color:#5b6b7f; } .ro-v { font-variant-numeric:tabular-nums; font-weight:700; text-align:right; color:#1f2937; }
  .ro-i { color:#475569; }
  .hm-foot { display:flex; justify-content:space-between; align-items:center; margin-top:8px; flex-wrap:wrap; gap:8px; }
  .hm-scale { display:flex; align-items:center; gap:7px; font-size:10px; color:#94a3b8; }
  .hm-scale i { width:120px; height:8px; border-radius:4px; background:linear-gradient(90deg,#e9f1fd,#0a39d6); }
  .hm-note { font-size:10.5px; color:#94a3b8; }
  /* dark mode — schematics */
  :root[data-theme="dark"] .schem { background:#0f1830; border-color:#26344b; }
  :root[data-theme="dark"] .hm-rl { color:#aebfd6; }
  :root[data-theme="dark"] .hm-rl small { color:#7e8ea8; }
  :root[data-theme="dark"] .hm-x span { color:#8295b0; }
  :root[data-theme="dark"] .hm-strip .cell { box-shadow:inset 0 0 0 1px rgba(255,255,255,.07); }
  :root[data-theme="dark"] .hm-readout { background:#0d1730; border-color:#26344b; color:#e7eef9; }
  :root[data-theme="dark"] .hm-readout .hint { color:#8295b0; }
  :root[data-theme="dark"] .ro-h { color:#7fb6ff; }
  :root[data-theme="dark"] .ro-r { border-top-color:#22304a; }
  :root[data-theme="dark"] .ro-m { color:#9fb1c7; }
  :root[data-theme="dark"] .ro-v { color:#e7eef9; }
  :root[data-theme="dark"] .ro-i { color:#bcc8da; }
  :root[data-theme="dark"] .hm-scale { color:#8295b0; }
  :root[data-theme="dark"] .hm-note { color:#8295b0; }"""

# JS d'interface : bascule thème clair/sombre + onglets de langue + rendu des deux
# schématiques (heatmap par couche & plan 4-buckets) pilotées par `window.JORAK_SCHEM`
# (objet injecté par render_html — c'est le « pont » données JSON → HTML). Aucune
# dépendance externe ; chaque schématique se dessine seulement si ses données existent.
_JS = """\
/* dark / light toggle */
(function(){
  var btn=document.getElementById('themeToggle');
  if(!btn) return;
  btn.addEventListener('click', function(){
    var next = document.documentElement.getAttribute('data-theme')==='dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try{ localStorage.setItem('jorak-theme', next); }catch(e){}
  });
})();

/* language tabs (scoped to the parent .tabwrap) */
document.querySelectorAll('.tabbar button').forEach(function(btn){
  btn.addEventListener('click', function(){
    var wrap = btn.closest('.tabwrap');
    wrap.querySelectorAll('.tabbar button').forEach(function(b){ b.classList.remove('active'); });
    wrap.querySelectorAll('.tabpane').forEach(function(p){ p.classList.remove('active'); });
    btn.classList.add('active');
    var pane = wrap.querySelector('#' + btn.getAttribute('data-tab'));
    if (pane) pane.classList.add('active');
  });
});

/* interactive schematics — data comes from window.JORAK_SCHEM (injected) */
(function(){
  var D = window.JORAK_SCHEM || {};
  var FONT='-apple-system,Segoe UI,Arial', OR='#f97316';

  /* ---- per-layer heatmap (Cohen's d · o_proj · down_proj · weight–axis) ---- */
  var hm=document.getElementById('heatmapSchem');
  if(hm && D.rows && D.rows.length){
    var rows=D.rows, n=D.n, band=D.band, T=D.hm||{};
    var b0=band?band[0]:-1, b1=band?band[1]:-1;
    rows.forEach(function(r){ r.max=Math.max.apply(null,r.arr)||1; });
    var blue=function(t){t=Math.max(0,Math.min(1,t));var a=[206,224,247],z=[10,57,214];
      return 'rgb('+Math.round(a[0]+(z[0]-a[0])*t)+','+Math.round(a[1]+(z[1]-a[1])*t)+','+Math.round(a[2]+(z[2]-a[2])*t)+')';};
    var interp=function(tbl,v){ for(var j=0;j<tbl.length;j++){ if(v>=tbl[j][0]) return tbl[j][1]; } return tbl[tbl.length-1][1]; };
    var bandHtml=band?'<div class="hm-band" style="left:'+(b0/n*100).toFixed(2)+'%;width:'+((b1-b0+1)/n*100).toFixed(2)+'%"><b>'+T.band_label+'</b></div>':'';
    var g='<div></div><div class="hm-bandrow">'+bandHtml+'</div>';
    rows.forEach(function(r){var cells='';for(var i=0;i<n;i++){cells+='<i class="cell" data-l="'+i+'" style="background:'+blue(r.arr[i]/r.max)+'"></i>';}
      g+='<div class="hm-rl">'+r.lab+'<small>'+r.dom+'</small></div><div class="hm-strip">'+cells+'</div>';});
    var ticks=[]; [0,0.25,0.5,0.75,1].forEach(function(f){var i=Math.min(n-1,Math.round(f*(n-1))); if(ticks.indexOf(i)<0)ticks.push(i);});
    var xl=''; ticks.forEach(function(i){xl+='<span style="left:'+(((i+0.5)/n)*100).toFixed(2)+'%">L'+i+'</span>';});
    g+='<div></div><div class="hm-x">'+xl+'</div>';
    hm.innerHTML='<div class="hm-grid">'+g+'</div>'+
      '<div class="hm-readout" id="hmReadout"><span class="hint">'+T.hover+'</span></div>'+
      '<div class="hm-foot"><span class="hm-scale"><span>'+T.weak+'</span><i></i><span>'+T.strong+'</span></span>'+
      '<span class="hm-note">'+T.note+'</span></div>';
    var ro=document.getElementById('hmReadout');
    var clearHot=function(){ hm.querySelectorAll('.cell.hot').forEach(function(k){k.classList.remove('hot');}); };
    hm.querySelectorAll('.hm-strip .cell').forEach(function(c){
      c.addEventListener('mouseenter',function(){
        var i=+c.getAttribute('data-l'), inb=band&&i>=b0&&i<=b1;
        clearHot();
        hm.querySelectorAll('.cell[data-l="'+i+'"]').forEach(function(k){k.classList.add('hot');});
        var tag=inb?'<span class="sev">'+T.in_band+'</span>':'<span class="int">'+T.intact+'</span>';
        var h='<div class="ro-h">'+T.layer+' '+i+' '+tag+'</div>';
        rows.forEach(function(r){h+='<div class="ro-r"><span class="ro-m">'+r.lab+'</span><b class="ro-v">'+r.arr[i].toFixed(3)+'</b><span class="ro-i">'+interp(r.interp,r.arr[i])+'</span></div>';});
        ro.innerHTML=h;
      });
    });
  }

  /* ---- 4-bucket position (SVG, re-rendered on theme change) ---- */
  function renderBucket(){
    var bk=document.getElementById('bucketSchem'); if(!bk) return;
    var B=D.bucket; if(!B) return;
    var dark=document.documentElement.getAttribute('data-theme')==='dark';
    var FAINT=dark?'#8295b0':'#9aa0b3', LINE=dark?'#2a3a57':'#d8dfe8', MU2=dark?'#9fb1c7':'#64748b',
        AX=dark?'#34465f':'#c2cad6', TINT=dark?'rgba(249,115,22,.13)':'#fff3ea';
    var W2=760,H2=320, x0=62,x1=720,y0=300,y1=30, s2='';
    var X=function(r){return x0+r*(x1-x0);}, Y=function(v){return y0-v*(y0-y1);};
    var sev=B.sev, ref=(B.ref==null?0.5:B.ref), hiSev=sev>=0.5, hiRef=ref>=0.5;
    /* tint the quadrant the model actually falls in */
    var rx=hiRef?X(0.5):x0, ry=hiSev?y1:Y(0.5);
    s2+='<rect x="'+rx+'" y="'+ry+'" width="'+(X(0.5)-x0)+'" height="'+(Y(0.5)-y1)+'" fill="'+TINT+'"/>';
    s2+='<line x1="'+X(0.5)+'" y1="'+y1+'" x2="'+X(0.5)+'" y2="'+y0+'" stroke="'+LINE+'" stroke-dasharray="3 5"/>';
    s2+='<line x1="'+x0+'" y1="'+Y(0.5)+'" x2="'+x1+'" y2="'+Y(0.5)+'" stroke="'+LINE+'" stroke-dasharray="3 5"/>';
    s2+='<line x1="'+x0+'" y1="'+y0+'" x2="'+x1+'" y2="'+y0+'" stroke="'+AX+'"/>';
    s2+='<line x1="'+x0+'" y1="'+y0+'" x2="'+x0+'" y2="'+y1+'" stroke="'+AX+'"/>';
    /* quadrant labels — active one (model's quadrant) in orange/bold, others faint */
    var lab=function(txt,qx,qy,on){return '<text x="'+qx+'" y="'+qy+'" fill="'+(on?OR:FAINT)+'" font-family="'+FONT+'" font-size="12"'+(on?' font-weight="700"':'')+'>'+txt+'</text>';};
    s2+=lab(B.ablated, x0+14, y1+22, hiSev&&!hiRef);
    s2+=lab(B.evasive, X(0.5)+14, y1+22, hiSev&&hiRef);
    s2+=lab(B.clean, x0+14, y0-12, !hiSev&&!hiRef);
    s2+=lab(B.censored, X(0.5)+14, y0-12, !hiSev&&hiRef);
    s2+='<text x="'+((x0+x1)/2)+'" y="'+(H2-6)+'" text-anchor="middle" fill="'+MU2+'" font-family="'+FONT+'" font-size="12">'+B.x+'</text>';
    s2+='<text x="18" y="'+((y0+y1)/2)+'" text-anchor="middle" fill="'+MU2+'" font-family="'+FONT+'" font-size="12" transform="rotate(-90 18 '+((y0+y1)/2)+')">'+B.y+'</text>';
    var px=X(ref), py=Y(sev);
    s2+='<circle cx="'+px+'" cy="'+py+'" r="22" fill="rgba(249,115,22,.12)" stroke="'+OR+'"/>';
    s2+='<circle cx="'+px+'" cy="'+py+'" r="6" fill="'+OR+'"/>';
    s2+='<text x="'+(px+30)+'" y="'+(py-5)+'" fill="'+OR+'" font-family="'+FONT+'" font-size="12.5" font-weight="700">'+B.this+'</text>';
    s2+='<text x="'+(px+30)+'" y="'+(py+12)+'" fill="'+MU2+'" font-family="'+FONT+'" font-size="11">'+B.sevref+'</text>';
    bk.innerHTML=s2;
  }
  renderBucket();
  if(document.getElementById('bucketSchem'))
    new MutationObserver(renderBucket).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
})();"""


def _metric_card(mid: str, label: str, value: str, sub: str, tips: dict) -> str:
    """Carte métrique + infobulle (signification / interprétation) au survol."""
    sub_html = f'<div class="m-sub">{html.escape(sub)}</div>' if sub else ""
    tip_html = ""
    if mid in tips:
        meaning, reading = tips[mid]
        ml = _STR_CUR["meaning"]; rl = _STR_CUR["reading"]
        tip_html = (f'<span class="info">i</span>'
                    f'<div class="tip"><b>{html.escape(ml)}:</b> {html.escape(meaning)}<br>'
                    f'<b class="rd">{html.escape(rl)}:</b> {html.escape(reading)}</div>')
    return (f'<div class="metric" tabindex="0">{tip_html}'
            f'<div class="m-val">{html.escape(value)}</div>'
            f'<div class="m-lab">{html.escape(label)}</div>{sub_html}</div>')


# _STR_CUR : langue courante du rendu (évite de threader partout dans _metric_card)
_STR_CUR: dict = _STR["en"]


def _bar(v, cls: str = "") -> str:
    """Barre de proportion 0..1 -> HTML ('—' si None)."""
    if v is None:
        return "—"
    w = min(100, max(0, float(v) * 100))
    return (f'<div class="bar"><span class="{cls}" style="width:{w:.0f}%"></span></div>'
            f'{float(v):.0%}')


def _section_multilingual(meta: dict, lang: str, tips: dict) -> str:
    mlt = meta.get("multilingual")
    if not mlt:
        return ""
    s = _STR[lang]
    per = mlt.get("per_lang_refusal") or {}
    over = mlt.get("per_lang_over_refusal") or {}
    has_over = bool(over)

    if has_over:
        head = (f'<thead><tr><th>{html.escape(s["ml_language"])}</th>'
                f'<th>{html.escape(s["ml_refusal"])}</th>'
                f'<th>{html.escape(s["ml_over"])}</th></tr></thead>')
        rows = "".join(
            f'<tr><th>{html.escape(_lang_name(k, lang))}</th>'
            f'<td>{_bar(per.get(k))}</td>'
            f'<td>{_bar(over.get(k), "warn")}</td></tr>'
            for k in per
        )
        table = f'<table class="lang">{head}<tbody>{rows}</tbody></table>'
    else:
        rows = "".join(
            f'<tr><th>{html.escape(_lang_name(k, lang))}</th><td>{_bar(v)}</td></tr>'
            for k, v in per.items()
        )
        table = f'<table class="lang"><tbody>{rows}</tbody></table>'

    note = html.escape(mlt.get("note", ""))
    aside = _metric_card("mra", s["mra_lab"], _fmt(mlt.get("mra")), "", tips)
    if has_over:
        aside += _metric_card("over_refusal", s["over_max_lab"],
                              _fmt(mlt.get("max_over_refusal"), 2), "", tips)
    return f"""
  <section>
    <h2>{html.escape(s['h2_multilingual'])} <small>{html.escape(s['sub_multilingual'])}</small></h2>
    <div class="grid2">
      {table}
      <div class="aside">{aside}<p class="hint">{note}</p></div>
    </div>
  </section>"""


def _section_profile(meta: dict, lang: str, tips: dict) -> str:
    prof = meta.get("model_profile")
    if not prof:
        return ""
    s = _STR[lang]
    b, q, h = prof.get("behavior", {}), prof.get("quality", {}), prof.get("hallucination", {})
    lab = {
        "en": ("harmful refusal", "harmless compliance", "factual accuracy",
               "hallucination proxy", "neutral perplexity", "repetition"),
        "fr": ("refus harmful", "compliance harmless", "exactitude factuelle",
               "proxy hallucination", "perplexité neutre", "répétition"),
    }[lang]
    cards = "".join([
        _metric_card("prof_refusal_harmful", lab[0], _fmt(b.get("refusal_rate_harmful"), 2), "", tips),
        _metric_card("prof_compliance_harmless", lab[1], _fmt(b.get("compliance_rate_harmless"), 2), "", tips),
        _metric_card("prof_factual", lab[2], _fmt(h.get("factual_accuracy"), 2), lab[3], tips),
        _metric_card("prof_perplexity", lab[4], _fmt(q.get("neutral_perplexity"), 1), "", tips),
        _metric_card("prof_repetition", lab[5], _fmt(q.get("repetition_rate"), 3), "", tips),
    ])
    return f"""
  <section>
    <h2>{html.escape(s['h2_profile'])} <small>{html.escape(s['sub_profile'])}</small></h2>
    <div class="metrics">{cards}</div>
  </section>"""


def _qa_table(rows: list[dict], lang: str) -> str:
    s = _STR[lang]
    src_map, cat_map, tag_map = _SRC[lang], _CAT[lang], _TAG[lang]
    trs = ""
    for r in rows:
        flag = ""
        if r.get("refusal") in (True, "True", "true"):
            flag = f'<span class="tag bad">{html.escape(tag_map["refusal"])}</span>'
        elif r.get("refusal") in (False, "False", "false"):
            flag = f'<span class="tag ok">{html.escape(tag_map["answers"])}</span>'
        if r.get("correct") in (True, "True", "true"):
            flag = f'<span class="tag ok">{html.escape(tag_map["correct"])}</span>'
        elif r.get("correct") in (False, "False", "false"):
            flag = f'<span class="tag bad">{html.escape(tag_map["wrong"])}</span>'
        src = src_map.get(r.get("source"), r.get("source"))
        cat = cat_map.get(r.get("category"), r.get("category"))
        trs += (
            f'<tr><td class="src">{_cell(src)}</td>'
            f'<td>{_cell(cat)}</td>'
            f'<td class="q">{_cell(r.get("prompt"))}</td>'
            f'<td class="a">{_cell(r.get("response"))}</td>'
            f'<td class="flag">{flag}</td></tr>'
        )
    return (f'<table class="qa"><thead><tr>'
            f'<th>{html.escape(s["col_source"])}</th>'
            f'<th>{html.escape(s["col_category"])}</th>'
            f'<th>{html.escape(s["col_question"])}</th>'
            f'<th>{html.escape(s["col_response"])}</th>'
            f'<th>{html.escape(s["col_verdict"])}</th></tr></thead>'
            f'<tbody>{trs}</tbody></table>')


def _section_prompts(rows: list[dict], lang: str) -> str:
    s = _STR[lang]
    if not rows:
        return (f'\n  <section><h2>{html.escape(s["h2_prompts"])}</h2>'
                f'<p class="hint">{html.escape(s["prompts_empty"])}</p></section>')

    # groupe par langue, anglais d'abord (puis ordre de préférence, puis le reste)
    by_lang: dict[str, list] = {}
    for r in rows:
        by_lang.setdefault(r.get("lang") or "?", []).append(r)
    present = list(by_lang)
    ordered = [c for c in _LANG_ORDER if c in by_lang] + sorted(c for c in present if c not in _LANG_ORDER)

    tabs, panes = "", ""
    for i, code in enumerate(ordered):
        active = " active" if i == 0 else ""
        name = html.escape(_lang_name(code, lang))
        tabs += (f'<button data-tab="pane-{html.escape(code)}" class="{active.strip()}">'
                 f'{name} <span class="cnt">{len(by_lang[code])}</span></button>')
        panes += (f'<div id="pane-{html.escape(code)}" class="tabpane{active}">'
                  f'{_qa_table(by_lang[code], lang)}</div>')

    return f"""
  <section>
    <h2>{html.escape(s['h2_prompts'])} <small>{len(rows)} {html.escape(s['n_generations'])}</small></h2>
    <p class="hint">{html.escape(s['tabs_hint'])}</p>
    <div class="tabwrap"><div class="tabbar">{tabs}</div>{panes}</div>
  </section>"""


def render_html(result: ScanResult, prompts: list[dict], lang: str = "en", *,
                heatmap_path: Optional[str] = None) -> str:
    """Rend le rapport HTML autonome dans la langue `lang` ('en' | 'fr')."""
    global _STR_CUR
    lang = lang if lang in _STR else "en"
    _STR_CUR = _STR[lang]
    s = _STR[lang]
    tips = _TIP[lang]

    meta = result.meta or {}
    log = scan_log_dict(result)
    res = log["results"]
    detail = res.get("classify_detail") or {}
    sub = meta.get("subspace") or {}
    label = result.label.value
    color = _LABEL_COLOR.get(label, "#969696")
    conf = result.confidence or 0.0

    expected = res.get("expected_label")
    match = res.get("matches_expected")
    exp_html = ""
    if expected:
        mk = s["conform"] if match else s["divergent"]
        cls = "ok" if match else "bad"
        exp_html = (f'<div class="expected">{html.escape(s["expected"])} {_badge(expected, lang)} '
                    f'<span class="tag {cls}">{html.escape(mk)}</span></div>')

    alert_html = (f'<div class="alert">{html.escape(s["evasive"])}</div>'
                  if detail.get("evasive_ablation") else "")

    # --- cartes de signaux clés (avec tooltips) ---
    cards_list = [
        _metric_card("svd_global",
                     {"en": "global SVD alignment", "fr": "alignement SVD global"}[lang],
                     _fmt(result.svd_alignment),
                     {"en": "stacked u_min (weight signature)",
                      "fr": "u_min empilés (signature poids)"}[lang], tips),
        _metric_card("band",
                     {"en": "band alignment", "fr": "alignement de bande"}[lang],
                     _fmt(res.get("band_alignment")),
                     f"{s['layers']} {res.get('touched_band') or '—'}", tips),
    ]
    if sub:
        cards_list.append(_metric_card(
            "subspace", {"en": "subspace alignment", "fr": "alignement de sous-espace"}[lang],
            _fmt(sub.get("alignment")), f"bottom-k · k={sub.get('k')}", tips))
    cards_list += [
        _metric_card("cohens_mean",
                     {"en": "mean Cohen's d", "fr": "Cohen's d moyen"}[lang],
                     _fmt(res.get("mean_cohens_d")),
                     {"en": "axis health (activations)", "fr": "santé d'axe (activations)"}[lang], tips),
        _metric_card("cohens_max",
                     {"en": "max Cohen's d", "fr": "Cohen's d max"}[lang],
                     _fmt(res.get("max_cohens_d")), "", tips),
        _metric_card("refusal",
                     {"en": "refusal rate", "fr": "taux de refus"}[lang],
                     _fmt(result.behavioral_refusal_rate, 2),
                     {"en": "behavioral", "fr": "comportemental"}[lang], tips),
    ]
    if detail.get("over_refusal") is not None:
        cards_list.append(_metric_card(
            "over_refusal", {"en": "harmless over-refusal", "fr": "sur-refus harmless"}[lang],
            _fmt(detail.get("over_refusal"), 2), "", tips))
    cards = "".join(cards_list)

    # --- calque interactif : pont données JSON → HTML --------------------------
    # La heatmap par couche et le plan 4-buckets ne sont plus des PNG embarqués :
    # ils sont dessinés en HTML/SVG par _JS à partir de `window.JORAK_SCHEM`, que
    # l'on construit ici directement depuis la trace (res["per_layer"], bandes,
    # sévérance, refus). Chaque schématique ne s'affiche que si ses données existent.
    schem = _SCHEM_I18N[lang]
    pl = res.get("per_layer") or {}
    supp = pl.get("suppression") or {}
    n_layers = result.n_layers or 0
    band = res.get("touched_band")
    if isinstance(band, (list, tuple)) and len(band) == 2:
        band = [int(band[0]), int(band[1])]
    else:
        band = None

    # lignes de la heatmap, dans l'ordre du design : Cohen's d, o_proj, down_proj, poids
    rows_payload = []
    for key, arr in (("cd", pl.get("cohens_d")), ("op", supp.get("o_proj")),
                     ("dp", supp.get("down_proj")), ("wa", pl.get("weight_axis_align"))):
        if arr:
            lab, dom = schem["rows"][key]
            if not n_layers:
                n_layers = len(arr)
            rows_payload.append({"k": key, "lab": lab, "dom": dom,
                                 "arr": arr, "interp": schem["interp"][key]})

    hm_i18n = {k: schem[k] for k in ("hover", "layer", "intact", "weak", "strong", "note")}
    hm_i18n["band_label"] = schem["band_label"].format(a=band[0], b=band[1]) if band else ""
    hm_i18n["in_band"] = schem["in_band"].format(a=band[0], b=band[1]) if band else ""

    # plan 4-buckets : 1 point = ce modèle. sévérance = max(SVD, bande, sous-espace) ;
    # refus = taux comportemental (réutilise exactement le record de la matrice PNG).
    brec = bucket_record(result)
    sev, ref = brec.get("severance"), brec.get("refusal")
    bucket_payload = None
    if sev is not None:
        bk = schem["bucket"]
        bucket_payload = {
            "sev": sev, "ref": ref,
            "ablated": bk["ablated"], "evasive": bk["evasive"],
            "clean": bk["clean"], "censored": bk["censored"],
            "x": bk["x"], "y": bk["y"], "this": bk["this"],
            "sevref": bk["sevref"].format(
                sev=f"{sev:.2f}", ref=("—" if ref is None else f"{ref:.2f}")),
        }

    schem_json = json.dumps(
        {"n": n_layers or 1, "band": band, "rows": rows_payload,
         "hm": hm_i18n, "bucket": bucket_payload},
        ensure_ascii=False)

    heatmap_section = ""
    if rows_payload:
        heatmap_section = (f'\n  <section><h2>{html.escape(s["h2_heatmap"])} '
                           f'<small>{html.escape(s["sub_heatmap"])}</small></h2>'
                           f'<div class="schem"><div id="heatmapSchem" class="hm"></div>'
                           f'</div></section>')

    bucket_section = ""
    if bucket_payload:
        bucket_section = (f'\n  <section><h2>{html.escape(s["h2_bucket"])} '
                          f'<small>{html.escape(s["sub_bucket"])}</small></h2>'
                          f'<div class="schem"><svg id="bucketSchem" viewBox="0 0 760 320" '
                          f'role="img" aria-label="4-bucket position"></svg></div></section>')

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    desc = _LABEL_DESC[lang].get(label, "")
    footer = s["footer"].format(now=now)
    conf_pct = f"{conf * 100:.0f}"

    # tagline : « … · Model Scanner » → séparateur orange « // » (style proposal-9)
    tparts = s["tagline"].split(" · ")
    if len(tparts) == 2:
        tagline_html = (f'{html.escape(tparts[0])} <span class="sep">//</span> '
                        f'{html.escape(tparts[1])}')
    else:
        tagline_html = html.escape(s["tagline"])

    head = (
        '<!doctype html>\n<html lang="' + lang + '"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>JORAK — ' + html.escape(result.model_id) + '</title>\n<style>\n'
        + _CSS + '\n</style>\n' + _THEME_INIT + '\n</head>\n'
    )
    body = f"""<body style="--verdict:{color}">
  <header class="brand"><div class="wrap">
    <div class="brandgroup">
      {_JORAK_MARK}
      <div class="namewrap">
        <div class="word"><span class="wf">ORAK</span></div>
        <div class="tagline">{tagline_html}</div>
      </div>
    </div>
    <div class="meta">{html.escape(result.model_type)} · {html.escape(result.quantization.value)}<br>
      {result.n_layers} {html.escape(s['layers'])} · d={result.hidden_size}<br>{now}</div>
    {_THEME_TOGGLE}
  </div></header>

  <div class="wrap">
    <h1 class="model">{html.escape(result.model_id)}</h1>

    <div class="verdict">
      <div>
        <div class="v-label">{html.escape(_LABEL[lang].get(label, label).upper())}</div>
        <div class="v-desc">{html.escape(desc)}</div>
        {exp_html}
        {alert_html}
      </div>
      <div class="gauge"><div class="ring" style="--p:{conf_pct}"><i>{conf:.0%}</i></div>
        <div class="cap">{html.escape(s['confidence'])}</div></div>
    </div>

    <h2>{html.escape(s['h2_signals'])}</h2>
    <div class="metrics">{cards}</div>
{heatmap_section}
{bucket_section}
{_section_multilingual(meta, lang, tips)}
{_section_profile(meta, lang, tips)}
{_section_prompts(prompts, lang)}

    <footer>{html.escape(footer)}</footer>
  </div>
  <script>window.JORAK_SCHEM = {schem_json};</script>
  <script>
{_JS}
  </script>
</body></html>"""
    return head + body


# --------------------------------------------------------------------------- #
# Upload S3 (même mécanique aws CLI que le runner / campaign_report)           #
# --------------------------------------------------------------------------- #
# Destination par défaut des bundles `--s3` (push + purge locale) : bucket your-bucket,
# sous-chemin fixe `results/Jorak`. Rien à préciser au terminal.
S3_DEFAULT_BUCKET = "your-bucket"
S3_RESULT_PREFIX = "results/Jorak"


def resolve_s3_dest(bucket_or_uri: Optional[str] = None) -> str:
    """Destination S3 d'un bundle, à partir d'un `DEST` optionnel.

    - vide -> `s3://<S3_DEFAULT_BUCKET>/results/Jorak` (défaut `your-bucket`) ;
    - un BUCKET seul (`mon-bucket`) -> `s3://mon-bucket/results/Jorak` ;
    - un PRÉFIXE EXACT (`s3://mon-bucket/x/y`, avec un chemin après le bucket) ->
      utilisé TEL QUEL (remplace l'ancien `--report-s3`).

    Le bundle daté sera ensuite poussé sous ce préfixe par `_s3_sync_dir`."""
    root = (bucket_or_uri or "").strip() or S3_DEFAULT_BUCKET
    if not root.startswith("s3://"):
        root = "s3://" + root
    root = root.rstrip("/")
    # préfixe exact si un chemin est fourni après le bucket (ex-`--report-s3`).
    if "/" in root[len("s3://"):]:
        return root
    return root + "/" + S3_RESULT_PREFIX


def _s3_sync_dir(local_dir: str, prefix: str) -> Optional[str]:
    """Pousse `local_dir/` sous `prefix/<nom_dossier>/` via `aws s3 sync`.

    Renvoie l'URI S3 du dossier, ou ``None`` si aws CLI absent / échec (les
    fichiers restent de toute façon en local)."""
    if not shutil.which("aws"):
        ui.bullet("warn", "aws CLI absent → pas d'upload S3 (bundle gardé en local).")
        return None
    dst = prefix.rstrip("/") + "/" + os.path.basename(local_dir.rstrip("/"))
    ui.bullet("s3", "upload S3 → " + ui.s3_uri(dst) + " …")
    r = subprocess.run(["aws", "s3", "sync", local_dir, dst],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return dst
    ui.bullet("warn", f"upload S3 KO : {(r.stderr or '').strip()[:200]}")
    return None


# --------------------------------------------------------------------------- #
# Orchestration                                                               #
# --------------------------------------------------------------------------- #
def write_scan_report(result: ScanResult, *, base_dir: str = ".",
                      out_dir: Optional[str] = None, flags: Optional[dict] = None,
                      with_heatmap: bool = True, date: Optional[str] = None,
                      s3_prefix: Optional[str] = None,
                      delete_local: bool = False) -> dict:
    """Construit le dossier daté `<model>_jorak_<YYYYMMDD>/` et tous les livrables.

    Deux rapports HTML autonomes sont produits : ``jorak_report_en.html`` (explications
    en anglais) et ``jorak_report_fr.html`` (en français). Si `s3_prefix` (s3://…) est
    fourni, le dossier complet est aussi synchronisé sur S3.

    `delete_local` (option `--s3`) : après un upload S3 RÉUSSI, le dossier local est
    supprimé (rien ne reste en local). En cas d'échec/absence d'upload, le local est
    conservé pour ne rien perdre.

    Renvoie un dict de chemins :
    {dir, html_en, html_fr, prompts_csv, summary_csv, json, heatmap, bucket, s3,
     deleted_local}.
    """
    day = date or datetime.datetime.now().strftime("%Y%m%d")
    out_dir = out_dir or os.path.join(base_dir, f"{_slug(result.model_id)}_jorak_{day}")
    os.makedirs(out_dir, exist_ok=True)

    # 1. trace JSON complète (réutilise le logger existant)
    json_path = write_scan_log(result, os.path.join(out_dir, "scan_log.json"), flags=flags)

    # 2. CSV des réponses aux prompts + CSV de synthèse
    prompts = collect_prompts(result)
    prompts_path = write_prompts_csv(prompts, os.path.join(out_dir, "prompts.csv"))
    summary_path = write_summary_csv(result, os.path.join(out_dir, "summary.csv"))

    # 3. heatmap couches (best-effort : absente si plan activations coupé)
    heatmap_path = None
    if with_heatmap:
        try:
            from modelscanner.viz import layer_heatmap

            heatmap_path = os.path.join(out_dir, "layers_heatmap.png")
            layer_heatmap(result, path=heatmap_path)
        except Exception as e:  # pas d'activations / matplotlib KO -> on continue sans
            print(f"  [warn] heatmap ignorée : {e}")
            heatmap_path = None

    # 3bis. plan 4-buckets — PNG autonome (1 point = ce modèle), réutilisable pour
    # `modelscanner compare` (superposition de plusieurs modèles sur un même plan).
    short = result.model_id.split("/")[-1]
    bucket_path = os.path.join(out_dir, "bucket_position.png")
    if render_bucket_png([bucket_record(result)], bucket_path,
                         lang="fr", title=f"Position 4-buckets — {short}") is None:
        bucket_path = None

    # 4. deux HTML autonomes (un par langue), schématiques HTML/SVG interactives inline
    html_paths = {}
    for lg in ("en", "fr"):
        p = os.path.join(out_dir, f"jorak_report_{lg}.html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(render_html(result, prompts, lg, heatmap_path=heatmap_path))
        html_paths[lg] = p

    # 5. upload S3 optionnel (sync du dossier complet)
    s3_uri = _s3_sync_dir(out_dir, s3_prefix) if s3_prefix else None

    # 6. purge locale optionnelle (--s3) : SEULEMENT si l'upload a réussi.
    deleted_local = False
    if delete_local:
        if s3_uri:
            shutil.rmtree(out_dir, ignore_errors=True)
            deleted_local = True
        else:
            ui.bullet("warn", "purge locale annulée : upload S3 absent/KO "
                      "→ on garde le bundle en local pour ne rien perdre.")

    return {
        "dir": out_dir, "html_en": html_paths["en"], "html_fr": html_paths["fr"],
        "prompts_csv": prompts_path, "summary_csv": summary_path,
        "json": json_path, "heatmap": heatmap_path, "bucket": bucket_path, "s3": s3_uri,
        "deleted_local": deleted_local,
    }


# --------------------------------------------------------------------------- #
# Comparaison multi-modèles : superposer plusieurs bundles sur un même plan    #
# --------------------------------------------------------------------------- #
def _find_logs(paths) -> list[str]:
    """Résout des chemins (scan_log.json | bundle dir | dossier parent) -> liste
    de scan_log.json triée et dédupliquée."""
    logs: list[str] = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".json"):
            logs.append(p)
        elif os.path.isdir(p):
            direct = os.path.join(p, "scan_log.json")
            if os.path.isfile(direct):
                logs.append(direct)
            else:                                  # dossier parent de plusieurs bundles
                logs += glob.glob(os.path.join(p, "**", "scan_log.json"), recursive=True)
        else:                                      # glob explicite
            logs += glob.glob(p, recursive=True)
    return sorted({p for p in logs if p.endswith(".json") and os.path.isfile(p)})


def compare_bundles(paths, *, out_png: Optional[str] = None, out_csv: Optional[str] = None,
                    title: Optional[str] = None, lang: str = "fr",
                    date: Optional[str] = None) -> Optional[dict]:
    """Superpose les modèles de plusieurs bundles `--report` sur un même plan
    4-buckets. `paths` = bundles `<model>_jorak_<date>/`, des `scan_log.json`, ou un
    dossier parent. Produit un PNG (+ un CSV récapitulatif). Renvoie un dict, ou
    ``None`` si aucun `scan_log.json` trouvé."""
    logs = _find_logs(paths)
    records = []
    for lp in logs:
        try:
            records.append(_bucket_record_from_log(json.load(open(lp, encoding="utf-8"))))
        except Exception as e:
            print(f"  [warn] {lp} illisible : {e}")
    if not records:
        return None
    records.sort(key=lambda r: (r["status"] != "OK", str(r["model"])))

    day = date or datetime.datetime.now().strftime("%Y%m%d")
    out_png = out_png or f"jorak_compare_{day}.png"
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    ttl = title or ("Comparaison 4-buckets" if lang != "en" else "4-bucket comparison")
    render_bucket_png(records, out_png, lang=lang, title=f"{ttl} — {len(records)} modèles")

    out_csv = out_csv or (out_png.rsplit(".", 1)[0] + ".csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_BUCKET_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in _BUCKET_COLUMNS})
    return {"n": len(records), "png": out_png, "csv": out_csv, "records": records}
