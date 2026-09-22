"""Thème terminal JORAK — bleu nuit + orange Ubuntu, **zéro dépendance**.

ANSI 24-bit (truecolor) avec repli automatique : les couleurs sont coupées hors
TTY (sortie redirigée vers un fichier / nohup / pipe), si ``NO_COLOR`` ou
``MODELSCANNER_NO_COLOR=1`` sont définis, ou sur un ``TERM=dumb``. Quand la
couleur est coupée, on imprime exactement le même texte, juste sans séquences
d'échappement — donc un log reste lisible.

Sert les 3 surfaces du scanner partagées :
  - le **rapport** d'un modèle (`scan --report`, sans push S3) ;
  - la **campagne** par lot (`experiments/run_scan.py`) ;
  - l'**upload S3** (`scan --s3` [`--keep-local`], et campagne `output_s3`).

S'inspire du style de présentation d'OBLITERATUS (bandeau lettré, règles de
section, puces d'état) sans en reprendre le code.
"""
from __future__ import annotations

import os
import sys
from typing import Optional, TextIO, Tuple

RGB = Tuple[int, int, int]

# --- Palette de marque ------------------------------------------------------ #
BLUE = (38, 109, 224)      # bleu nuit (nom JORAK)
NAVY = (26, 64, 130)       # bleu nuit (règles, bordures, accents discrets)
ORANGE = (233, 84, 32)     # orange Ubuntu #E95420 (nom JORAK + accents)
GREY = (146, 154, 168)     # texte secondaire
GREEN = (54, 168, 84)      # état OK / sain
RED = (221, 76, 70)        # échec / ablation
AMBER = (224, 162, 38)     # alerte / ambigu

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"

# --- Logo « JORAK » en bloc ombré (police figlet « pagga », 3 lignes) -------- #
# Figé en dur (généré une fois via `toilet -f pagga JORAK`) pour ne dépendre
# d'aucun binaire figlet à l'exécution — même esprit « bloc ombré ░▀▄█ » que le
# bandeau OBLITERATUS dont s'inspire le rendu.
JORAK_ART = (
    "░▀▀█░█▀█░█▀▄░█▀█░█░█",
    "░░░█░█░█░█▀▄░█▀█░█▀▄",
    "░▀▀░░▀▀▀░▀░▀░▀░▀░▀░▀",
)
_TAGLINE = "ABLITERATION DETECTOR · REFERENCE-FREE"
BANNER_WIDTH = 58


def fg(rgb: RGB) -> str:
    """Séquence de couleur d'avant-plan (truecolor)."""
    r, g, b = rgb
    return f"\033[38;2;{r};{g};{b}m"


def supports_color(stream: Optional[TextIO] = None) -> bool:
    """Couleurs actives ? TTY requis, sauf ``FORCE_COLOR``. Coupées par
    ``NO_COLOR`` / ``MODELSCANNER_NO_COLOR=1`` / ``TERM=dumb``."""
    stream = stream or sys.stdout
    if os.environ.get("MODELSCANNER_NO_COLOR") == "1":
        return False
    if "NO_COLOR" in os.environ:
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("TERM") == "dumb":
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def style(text: str, *codes: str, stream: Optional[TextIO] = None,
          enabled: Optional[bool] = None) -> str:
    """Enrobe `text` des `codes` ANSI donnés (no-op si couleur coupée).

    `codes` = séquences déjà formées : `fg(BLUE)`, `BOLD`, `DIM`… On peut passer
    `enabled` pour forcer l'état (sinon déduit du `stream`)."""
    if enabled is None:
        enabled = supports_color(stream)
    if not enabled or not codes or not text:
        return text
    return "".join(codes) + text + RESET


# --------------------------------------------------------------------------- #
# Bandeau                                                                      #
# --------------------------------------------------------------------------- #
def banner(mode: str, subtitle: str, *, stream: Optional[TextIO] = None) -> None:
    """Imprime le bandeau JORAK : wordmark ASCII bleu encadré d'orange Ubuntu.

    `mode` = pastille de surface (« RAPPORT », « CAMPAGNE », « S3 »), `subtitle`
    = ligne d'explication. Le logo (3 lignes, bloc ombré) reste affiché même hors
    couleur (lisible dans un log), seules les couleurs sont coupées. Imprimé
    UNE seule fois — pas de redraw (contrairement à un Live qui empile les boîtes)."""
    stream = stream or sys.stdout
    on = supports_color(stream)
    rule_s = style("═" * BANNER_WIDTH, fg(ORANGE), enabled=on)
    out = ["\n", "  " + rule_s + "\n"]
    for line in JORAK_ART:
        out.append("   " + style(line, BOLD, fg(BLUE), enabled=on) + "\n")
    out.append("  " + rule_s + "\n")
    tag = style(_TAGLINE, fg(BLUE), enabled=on)
    sep = style("//", BOLD, fg(ORANGE), enabled=on)
    chip = style(f" {mode} ", BOLD, fg(ORANGE), enabled=on)
    out.append("   " + tag + "  " + sep + "  " + chip + "\n")
    out.append("  " + rule_s + "\n")
    out.append("   " + style(subtitle, fg(GREY), enabled=on) + "\n\n")
    stream.write("".join(out))
    stream.flush()


# --------------------------------------------------------------------------- #
# Règles, titres, paires clé/valeur, puces                                     #
# --------------------------------------------------------------------------- #
def rule(label: Optional[str] = None, *, width: int = 52,
         color: RGB = ORANGE, stream: Optional[TextIO] = None) -> None:
    """Règle de section, avec libellé optionnel encadré du trait."""
    stream = stream or sys.stdout
    on = supports_color(stream)
    line = "─" * width
    if label:
        head = style("──", fg(color), enabled=on)
        lab = style(f" {label} ", BOLD, fg(color), enabled=on)
        tail = style("─" * max(width - len(label) - 4, 2), fg(color), enabled=on)
        stream.write("\n" + head + lab + tail + "\n")
    else:
        stream.write(style(line, fg(color), enabled=on) + "\n")
    stream.flush()


def kv(key: str, value: str, *, key_w: int = 10, value_codes: Tuple[str, ...] = (),
       stream: Optional[TextIO] = None) -> None:
    """Ligne « clé : valeur » alignée (clé en bleu nuit, valeur stylée option.)."""
    stream = stream or sys.stdout
    on = supports_color(stream)
    k = style(f"{key:<{key_w}}", fg(NAVY), enabled=on)
    sep = style("│", fg(NAVY), enabled=on)
    v = style(value, *value_codes, enabled=on) if value_codes else value
    stream.write(f"  {k} {sep} {v}\n")
    stream.flush()


# Puces d'état partagées (campagne + rapport + S3).
_BULLETS = {
    "ok":   ("✓", GREEN),
    "fail": ("✗", RED),
    "skip": ("•", GREY),
    "warn": ("!", AMBER),
    "info": ("›", BLUE),
    "s3":   ("⇪", ORANGE),
    "run":  ("▸", ORANGE),
}


def bullet(kind: str, text: str, *, stream: Optional[TextIO] = None) -> None:
    """Puce d'état : ``ok|fail|skip|warn|info|s3|run`` + texte."""
    stream = stream or sys.stdout
    on = supports_color(stream)
    glyph, color = _BULLETS.get(kind, _BULLETS["info"])
    stream.write("  " + style(glyph, BOLD, fg(color), enabled=on) + " " + text + "\n")
    stream.flush()


def s3_uri(uri: str, *, stream: Optional[TextIO] = None) -> str:
    """URI S3 mise en valeur en orange (à insérer dans une ligne)."""
    return style(uri, BOLD, fg(ORANGE), enabled=supports_color(stream))


# Couleur du verdict de provenance (cf. enum Provenance). Le label imprimé est
# `result.label.value` : censored/ablated/finetuned_decensored/ambiguous.
_LABEL_COLORS = {
    "censored": GREEN,                 # garde-fous intacts -> sain
    "finetuned_decensored": BLUE,      # décensuré par fine-tuning (légitime)
    "ablated": RED,                    # abliteration directionnelle -> alerte
    "ambiguous": AMBER,
}


def label_badge(label_value: str, *, stream: Optional[TextIO] = None) -> str:
    """Verdict de provenance en pastille colorée (MAJUSCULES)."""
    color = _LABEL_COLORS.get(label_value, GREY)
    return style(f" {label_value.upper()} ", BOLD, fg(color),
                 enabled=supports_color(stream))
