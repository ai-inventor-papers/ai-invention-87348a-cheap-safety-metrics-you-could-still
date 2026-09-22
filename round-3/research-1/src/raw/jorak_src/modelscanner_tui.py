"""Assistant interactif plein écran (curses) — surcouche des commandes JORAK.

N'REMPLACE rien : construit et lance les commandes existantes
(`modelscanner scan …` et `experiments/run_scan.py …`) depuis une interface
plein écran, **zéro dépendance** (curses = stdlib), assortie au thème de `ui.py`.

Flux :
  Accueil → [Scan d'un modèle unique | Campagne YAML]
    · Scan   : cocher les plans, choisir/saisir le modèle, sortie local/S3, options.
    · Campagne : cocher les plans (appliqués si le YAML n'en déclare pas), choisir
      le YAML (liste de modèles + expected), sortie local/S3, mode AWS, device.

Choix produit → on QUITTE curses puis on exécute la commande dans le terminal
normal (la sortie colorée de `ui.py` + la barre de progression s'affichent telles
quelles). Lancement direct : le bouton « LANCER » démarre l'exécution.

Lancement :  `modelscanner tui`  (ou `python -m modelscanner.tui`).
"""
from __future__ import annotations

import curses
import locale
import os
import shlex
import subprocess
import sys
import time

# Racine du dépôt (…/Jorak) : ce fichier vit dans …/Jorak/modelscanner/tui.py
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RUN_SCAN = os.path.join(_REPO_ROOT, "experiments", "run_scan.py")
_RUNS_DIR = os.path.join(_REPO_ROOT, "experiments", "runs")

# Logo bloc ombré (identique à ui.JORAK_ART — dupliqué pour éviter d'importer ui
# avant d'être en curses ; le rendu couleur diffère de toute façon).
JORAK_ART = (
    "░▀▀█░█▀█░█▀▄░█▀█░█░█",
    "░░░█░█░█░█▀▄░█▀█░█▀▄",
    "░▀▀░░▀▀▀░▀░▀░▀░▀░▀░▀",
)
# « MODEL SCANNER » dans la même police figlet « pagga » (toilet -f pagga),
# figé en dur comme JORAK_ART ; rendu en orange sur une 2e rangée sous le logo.
MODEL_SCANNER_ART = (
    "░█▄█░█▀█░█▀▄░█▀▀░█░░  ░█▀▀░█▀▀░█▀█░█▀█░█▀█░█▀▀░█▀▄",
    "░█░█░█░█░█░█░█▀▀░█░░  ░▀▀█░█░░░█▀█░█░█░█░█░█▀▀░█▀▄",
    "░▀░▀░▀▀▀░▀▀░░▀▀▀░▀▀▀  ░▀▀▀░▀▀▀░▀░▀░▀░▀░▀░▀░▀▀▀░▀░▀",
)
TAGLINE = "ABLITERATION DETECTOR · REFERENCE-FREE"

# Modèles préréglés pour la démo — (id, provenance attendue, étiquette).
# 3 × 8B qui ont « bien marché » en campagne (box GPU AWS) + 1 × 0.5B qui tourne
# VRAIMENT sur CPU local (rapide, verdict ABLATED démonstratif).
PRESETS = [
    ("Qwen/Qwen3-8B", "censored", "GPU · 8B"),
    ("mlabonne/Qwen3-8B-abliterated", "ablated", "GPU · 8B"),
    ("huihui-ai/Huihui-Qwen3-8B-abliterated-v2", "ablated", "GPU · 8B"),
    ("huihui-ai/Qwen2.5-0.5B-Instruct-abliterated", "ablated", "CPU · 0.5B, fast"),
]
CUSTOM = -1  # valeur de model_choice pour « Autre — saisir un id »

DEVICES = ["auto", "cuda", "cpu"]
# Repli si les sondes ne sont pas importables (env minimal) — surchargé au runtime
# par modelscanner.probes.available_languages() (toutes les langues disponibles).
LANGS_FALLBACK = ["en", "fr", "zh", "de", "es", "it"]
EXPECTED_CHOICES = ["", "censored", "ablated", "finetuned_decensored", "ambiguous"]


def _probe_langs():
    """Toutes les langues pour lesquelles un jeu de sondes existe ('en' en tête)."""
    try:
        from modelscanner.probes import available_languages

        langs = available_languages() or list(LANGS_FALLBACK)
    except Exception:
        langs = list(LANGS_FALLBACK)
    if "en" in langs:  # 'en' d'abord = défaut naturel
        langs = ["en"] + [x for x in langs if x != "en"]
    return langs

# --- Paires de couleurs (approx. 256 couleurs de la palette JORAK) ----------- #
C_BLUE, C_ORANGE, C_NAVY, C_GREY, C_GREEN, C_RED, C_AMBER, C_TEXT = range(1, 9)
_256 = {C_BLUE: 33, C_ORANGE: 208, C_NAVY: 25, C_GREY: 245,
        C_GREEN: 40, C_RED: 196, C_AMBER: 214, C_TEXT: 255}
_8 = {C_BLUE: curses.COLOR_BLUE, C_ORANGE: curses.COLOR_YELLOW,
      C_NAVY: curses.COLOR_BLUE, C_GREY: curses.COLOR_WHITE,
      C_GREEN: curses.COLOR_GREEN, C_RED: curses.COLOR_RED,
      C_AMBER: curses.COLOR_YELLOW, C_TEXT: curses.COLOR_WHITE}


def _setup_colors() -> None:
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK
    palette = _256 if curses.COLORS >= 256 else _8
    for pid, fg in palette.items():
        try:
            curses.init_pair(pid, fg, bg)
        except curses.error:
            curses.init_pair(pid, _8[pid], bg)


def _c(pid: int, *, bold: bool = False, dim: bool = False, rev: bool = False) -> int:
    a = curses.color_pair(pid)
    if bold:
        a |= curses.A_BOLD
    if dim:
        a |= curses.A_DIM
    if rev:
        a |= curses.A_REVERSE
    return a


# --------------------------------------------------------------------------- #
# Primitives d'affichage sûres (aucune exception aux bords de fenêtre)         #
# --------------------------------------------------------------------------- #
def _add(win, y: int, x: int, text: str, attr: int = 0) -> None:
    H, W = win.getmaxyx()
    if y < 0 or y >= H or x >= W:
        return
    if x < 0:
        text = text[-x:]
        x = 0
    avail = W - x
    if avail <= 0:
        return
    # la dernière cellule (coin bas-droit) fait planter addstr : on rogne d'1.
    if y == H - 1:
        avail -= 1
    if avail <= 0:
        return
    try:
        win.addstr(y, x, text[:avail], attr)
    except curses.error:
        pass


def _add_segs(win, y: int, x: int, segs) -> int:
    for text, attr in segs:
        _add(win, y, x, text, attr)
        x += len(text)
    return x


def _draw_banner(win, compact: bool) -> int:
    """Dessine le bandeau JORAK en haut ; renvoie le nombre de lignes utilisées."""
    W = win.getmaxyx()[1]
    rule = "═" * min(W - 4, 58)
    if compact:
        segs = [("  JORAK ", _c(C_BLUE, bold=True)),
                ("· ", _c(C_ORANGE)),
                ("model scanner ", _c(C_ORANGE, bold=True)),
                ("// ", _c(C_ORANGE, bold=True)),
                (TAGLINE, _c(C_GREY))]
        _add_segs(win, 0, 0, segs)
        _add(win, 1, 2, rule, _c(C_ORANGE))
        return 2
    y = 0
    _add(win, y, 2, rule, _c(C_ORANGE)); y += 1
    for line in JORAK_ART:
        _add(win, y, 3, line, _c(C_BLUE, bold=True)); y += 1
    for line in MODEL_SCANNER_ART:
        _add(win, y, 3, line, _c(C_ORANGE)); y += 1
    _add(win, y, 2, rule, _c(C_ORANGE)); y += 1
    _add_segs(win, y, 3, [(TAGLINE, _c(C_BLUE)), ("  ", 0),
                          ("//", _c(C_ORANGE, bold=True))]); y += 1
    _add(win, y, 2, rule, _c(C_ORANGE)); y += 1
    return y


def _draw_footer(win, hint: str) -> None:
    H, W = win.getmaxyx()
    _add(win, H - 2, 2, "─" * min(W - 4, 80), _c(C_NAVY))
    _add(win, H - 1, 2, hint, _c(C_GREY, dim=True))


# --------------------------------------------------------------------------- #
# Écran d'accueil                                                             #
# --------------------------------------------------------------------------- #
_HOME_MENU = [
    ("scan", "Scan a single model",
     "one model · à-la-carte plans · local or S3 output"),
    ("campaign", "Campaign (YAML-driven batch)",
     "model list (path + expected) · injected plans · 4-bucket matrix"),
    ("quit", "Quit", ""),
]

_ABOUT = [
    "Analyzes an open-source LLM WITHOUT a reference model and returns a",
    "provenance verdict:  CENSORED · ABLATED · FINETUNED_DECENSORED · AMBIGUOUS.",
    "",
    "Available plans:  weights (JORAK/SVD signature) · activations (Cohen's d)",
    "· behavioral (refusal rate) · multilingual · model profile.",
]


def _home(stdscr) -> str:
    idx = 0
    while True:
        stdscr.erase()
        H, W = stdscr.getmaxyx()
        compact = H < 24 or W < 62
        y = _draw_banner(stdscr, compact) + 1
        if not compact:
            for line in _ABOUT:
                _add(stdscr, y, 3, line, _c(C_GREY)); y += 1
            y += 1
        _add(stdscr, y, 2, "── WHAT DO YOU WANT TO DO? " + "─" * max(W - 27, 2),
             _c(C_ORANGE, bold=True)); y += 2
        for i, (_, label, note) in enumerate(_HOME_MENU):
            focused = i == idx
            arrow = "▸ " if focused else "  "
            lab_attr = _c(C_TEXT, bold=True) if focused else _c(C_TEXT)
            segs = [(arrow, _c(C_ORANGE, bold=True)), (label, lab_attr)]
            _add_segs(stdscr, y, 3, segs)
            if note and not compact:
                _add(stdscr, y + 1, 7, note, _c(C_GREY, dim=True))
                y += 2
            else:
                y += 1
        _draw_footer(stdscr, "↑↓ navigate · ⏎ select · q quit")
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (curses.KEY_UP, ord("k")):
            idx = (idx - 1) % len(_HOME_MENU)
        elif ch in (curses.KEY_DOWN, ord("j")):
            idx = (idx + 1) % len(_HOME_MENU)
        elif ch in (ord("q"), 27):
            return "quit"
        elif ch in (curses.KEY_ENTER, 10, 13):
            return _HOME_MENU[idx][0]


# --------------------------------------------------------------------------- #
# Moteur de formulaire générique (liste d'items scrollable)                    #
# --------------------------------------------------------------------------- #
# Types d'items :
#   header {text}                     · titre de section (non focusable)
#   help   {text}                     · ligne d'aide grise (non focusable)
#   blank  {}                         · ligne vide (non focusable)
#   check  {id,label,key,note?}       · case [x]/[ ] -> st[key] bool
#   toggle {id,label,keys}            · [x] tout cocher / décocher (groupe)
#   radio  {id,label,group,value,note?}· (o)/( ) -> st[group] = value
#   text   {id,label,key,ph?}         · saisie inline -> st[key] str
#   select {id,label,key,choices}     · ‹ valeur › -> st[key] cyclé
#   button {id,label}                 · action -> submit
_FOCUS = {"check", "toggle", "radio", "text", "select", "button"}


def _visible(it, st) -> bool:
    vif = it.get("visible_if")
    return True if vif is None else bool(vif(st))


def _render_item(it, st, focused: bool):
    t = it["type"]
    arrow = ("▸ ", _c(C_ORANGE, bold=True)) if focused else ("  ", 0)
    lab_attr = _c(C_TEXT, bold=True) if focused else _c(C_TEXT)
    if t == "header":
        return [("── ", _c(C_ORANGE)), (it["text"], _c(C_ORANGE, bold=True)),
                (" ", 0)]
    if t == "help":
        return [("  ", 0), (it["text"], _c(C_GREY, dim=True))]
    if t == "blank":
        return [("", 0)]
    if t == "check":
        on = st.get(it["key"], False)
        box = ("[x] ", _c(C_GREEN, bold=True)) if on else ("[ ] ", _c(C_GREY))
        segs = [arrow, box, (it["label"], lab_attr)]
        if it.get("note"):
            segs.append(("   " + it["note"], _c(C_GREY, dim=True)))
        return segs
    if t == "toggle":
        on = all(st.get(k, False) for k in it["keys"])
        box = ("[x] ", _c(C_AMBER, bold=True)) if on else ("[ ] ", _c(C_GREY))
        return [arrow, box, (it["label"], _c(C_AMBER))]
    if t == "radio":
        on = st.get(it["group"]) == it["value"]
        dot = ("(o) ", _c(C_ORANGE, bold=True)) if on else ("( ) ", _c(C_GREY))
        segs = [arrow, dot, (it["label"], lab_attr)]
        if it.get("note"):
            segs.append(("   " + it["note"], _c(C_GREY, dim=True)))
        return segs
    if t == "text":
        val = st.get(it["key"], "")
        shown = val if val else it.get("ph", "")
        vattr = _c(C_TEXT) if val else _c(C_GREY, dim=True)
        cursor = ("▏", _c(C_ORANGE, bold=True)) if focused else ("", 0)
        return [arrow, (it["label"] + " : ", _c(C_NAVY)),
                (shown, vattr), cursor]
    if t == "select":
        val = str(st.get(it["key"], ""))
        return [arrow, (it["label"] + "  ", _c(C_NAVY)),
                ("‹ ", _c(C_ORANGE)), (val or "—", lab_attr),
                (" ›", _c(C_ORANGE))]
    if t == "button":
        a = _c(C_ORANGE, bold=True, rev=True) if focused else _c(C_ORANGE, bold=True)
        return [arrow, (" " + it["label"] + " ", a)]
    return [("", 0)]


def _activate(it, st) -> str:
    """Espace/Entrée sur un item : mute st. Renvoie 'submit' pour le bouton."""
    t = it["type"]
    if t == "check":
        st[it["key"]] = not st.get(it["key"], False)
    elif t == "toggle":
        target = not all(st.get(k, False) for k in it["keys"])
        for k in it["keys"]:
            st[k] = target
    elif t == "radio":
        st[it["group"]] = it["value"]
        cb = it.get("on_select")
        if cb:
            cb(st)
    elif t == "select":
        _cycle_select(it, st, +1)
    elif t == "button":
        return "submit"
    return ""


def _cycle_select(it, st, step: int) -> None:
    ch = it["choices"]
    cur = st.get(it["key"], ch[0])
    i = ch.index(cur) if cur in ch else 0
    st[it["key"]] = ch[(i + step) % len(ch)]


def _edit_text(it, st, ch: int) -> None:
    key = it["key"]
    val = st.get(key, "")
    if ch in (curses.KEY_BACKSPACE, 127, 8):
        st[key] = val[:-1]
    elif 32 <= ch <= 126:
        st[key] = val + chr(ch)


_FORM_HINT = ("↑↓ field · space/⏎ toggle/choose · ←→ adjust · "
              "type directly in text fields · ⏎ on RUN · Esc back")


def _run_form(stdscr, subtitle: str, items, st):
    """Boucle d'un formulaire. Renvoie st (submit) ou None (Échap)."""
    focus_id = None
    offset = 0
    while True:
        vis = [it for it in items if _visible(it, st)]
        focusables = [it for it in vis if it["type"] in _FOCUS]
        if not focusables:
            return None
        ids = [it["id"] for it in focusables]
        if focus_id not in ids:
            focus_id = ids[0]

        stdscr.erase()
        H, W = stdscr.getmaxyx()
        compact = H < 22 or W < 62
        top = _draw_banner(stdscr, compact) + 1
        _add(stdscr, top - 1, 3, subtitle, _c(C_GREY)) if not compact else None
        region_h = H - top - 2  # 2 lignes de footer
        if region_h < 3:
            region_h = 3

        # Rangées à dessiner + index de la rangée focalisée (pour le scroll).
        rows, focus_row = [], 0
        for it in vis:
            foc = it.get("type") in _FOCUS and it["id"] == focus_id
            if foc:
                focus_row = len(rows)
            rows.append(_render_item(it, st, foc))

        if focus_row < offset:
            offset = focus_row
        elif focus_row >= offset + region_h:
            offset = focus_row - region_h + 1
        offset = max(0, min(offset, max(0, len(rows) - region_h)))

        for i in range(offset, min(len(rows), offset + region_h)):
            _add_segs(stdscr, top + (i - offset), 3, rows[i])
        if offset > 0:
            _add(stdscr, top, W - 4, "▲", _c(C_ORANGE))
        if offset + region_h < len(rows):
            _add(stdscr, top + region_h - 1, W - 4, "▼", _c(C_ORANGE))
        _draw_footer(stdscr, _FORM_HINT if not compact else
                     "↑↓ · space · ⏎ · Esc")
        stdscr.refresh()

        ch = stdscr.getch()
        cur = next(it for it in focusables if it["id"] == focus_id)
        pos = ids.index(focus_id)

        if ch == 27:  # Échap -> retour
            return None
        if ch in (curses.KEY_UP,):
            focus_id = ids[(pos - 1) % len(ids)]
        elif ch in (curses.KEY_DOWN, 9):  # ↓ ou Tab
            focus_id = ids[(pos + 1) % len(ids)]
        elif cur["type"] == "text":
            if ch in (curses.KEY_ENTER, 10, 13):
                focus_id = ids[(pos + 1) % len(ids)]
            else:
                _edit_text(cur, st, ch)
        elif ch == curses.KEY_LEFT and cur["type"] == "select":
            _cycle_select(cur, st, -1)
        elif ch == curses.KEY_RIGHT and cur["type"] == "select":
            _cycle_select(cur, st, +1)
        elif ch in (ord(" "), curses.KEY_ENTER, 10, 13):
            if _activate(cur, st) == "submit":
                return st


# --------------------------------------------------------------------------- #
# Formulaire : scan d'un modèle unique                                        #
# --------------------------------------------------------------------------- #
def _scan_form(stdscr):
    st = {
        "behavioral": True, "activations": True, "multilingual": False,
        "profile": False, "wt_o": True, "wt_down": False,
        "model_choice": 0, "custom_model": "", "expected": PRESETS[0][1],
        "output": "local", "s3_dest": "", "keep_local": False,
        "device": "auto", "lang": "en", "probe_subset": "", "max_new_tokens": "64",
        "subspace_k": "4",
    }

    def _preset(i):
        def cb(s):
            s["expected"] = PRESETS[i][1]
        return cb

    def _custom(s):
        s["expected"] = ""

    items = [
        {"type": "header", "text": "ANALYSIS PLANS (space = toggle)"},
        {"type": "check", "id": "behavioral", "key": "behavioral",
         "label": "Behavioral", "note": "refusal rate (generation)"},
        {"type": "check", "id": "activations", "key": "activations",
         "label": "Activations", "note": "Cohen's d · clean GPU/CPU"},
        {"type": "check", "id": "multilingual", "key": "multilingual",
         "label": "Multilingual", "note": "refusal asymmetry · sweeps ALL languages"},
        {"type": "check", "id": "profile", "key": "profile",
         "label": "Model profile", "note": "quality · hallu · HF tags"},
        {"type": "toggle", "id": "all_plans",
         "keys": ["behavioral", "activations", "multilingual", "profile"],
         "label": "Check all / uncheck all"},
        {"type": "blank"},
        {"type": "header", "text": "JORAK WEIGHT SIGNATURE (always on)"},
        {"type": "check", "id": "wt_o", "key": "wt_o",
         "label": "o_proj target", "note": "attention residual writer (default)"},
        {"type": "check", "id": "wt_down", "key": "wt_down",
         "label": "down_proj target", "note": "+ MLP writer (MLP-carried ablation)"},
        {"type": "text", "id": "subspace_k", "key": "subspace_k",
         "label": "subspace k (multi-direction)", "ph": "4"},
        {"type": "blank"},
        {"type": "header", "text": "MODEL"},
    ]
    for i, (mid, exp, tag) in enumerate(PRESETS):
        items.append({"type": "radio", "id": f"m{i}", "group": "model_choice",
                      "value": i, "label": mid, "note": f"expected: {exp} · {tag}",
                      "on_select": _preset(i)})
    items += [
        {"type": "radio", "id": "mcustom", "group": "model_choice", "value": CUSTOM,
         "label": "Other — enter an HF id / local path", "on_select": _custom},
        {"type": "text", "id": "custom_model", "key": "custom_model",
         "label": "  id/path", "ph": "e.g. Qwen/Qwen2.5-0.5B-Instruct",
         "visible_if": lambda s: s["model_choice"] == CUSTOM},
        {"type": "select", "id": "expected", "key": "expected",
         "label": "Expected provenance (optional)", "choices": EXPECTED_CHOICES},
        {"type": "blank"},
        {"type": "header", "text": "OUTPUT"},
        {"type": "radio", "id": "out_local", "group": "output", "value": "local",
         "label": "Local", "note": "JORAK bundle (HTML+CSV+JSON) on disk"},
        {"type": "radio", "id": "out_s3", "group": "output", "value": "s3",
         "label": "Push S3", "note": "upload then purge the local folder"},
        {"type": "text", "id": "s3_dest", "key": "s3_dest", "label": "  S3 dest",
         "ph": "default s3://your-bucket/results/Jorak",
         "visible_if": lambda s: s["output"] == "s3"},
        {"type": "check", "id": "keep_local", "key": "keep_local",
         "label": "  also keep the bundle locally (--keep-local)",
         "visible_if": lambda s: s["output"] == "s3"},
        {"type": "blank"},
        {"type": "header", "text": "OPTIONS"},
        {"type": "select", "id": "device", "key": "device", "label": "Device",
         "choices": DEVICES},
        {"type": "select", "id": "lang", "key": "lang",
         "label": "Probe language (main plan)", "choices": _probe_langs(),
         "visible_if": lambda s: not s["multilingual"]},
        {"type": "help", "text": "Probe language: all (multilingual plan active)",
         "visible_if": lambda s: s["multilingual"]},
        {"type": "text", "id": "probe_subset", "key": "probe_subset",
         "label": "Probes/class (empty = full)", "ph": "e.g. 32"},
        {"type": "text", "id": "max_new_tokens", "key": "max_new_tokens",
         "label": "Max new tokens", "ph": "64"},
        {"type": "blank"},
        {"type": "button", "id": "submit", "label": "▸ RUN SCAN"},
    ]
    sub = "SCAN · one model → provenance verdict + JORAK bundle"
    res = _run_form(stdscr, sub, items, st)
    return res


# --------------------------------------------------------------------------- #
# Formulaire : campagne                                                       #
# --------------------------------------------------------------------------- #
def _discover_yamls():
    """YAML de campagne proposés : convention `campaign_*.yaml` (les copies de
    l'utilisateur apparaissent donc automatiquement). Modèles turnkey d'abord,
    le gabarit `*_base.yaml` en dernier."""
    try:
        files = [f for f in os.listdir(_RUNS_DIR)
                 if f.startswith("campaign_") and f.endswith(".yaml")]
    except OSError:
        return []
    return sorted(files, key=lambda f: (f.endswith("_base.yaml"), f))


def _yaml_note(f):
    """Étiquette courte dérivée du nom de fichier (affichée dans la TUI)."""
    n = f[:-5]  # sans .yaml
    if n.endswith("_base"):
        return "template — duplicate & edit"
    if "cpu" in n:
        return "CPU · small models (runs locally)"
    if "mistral" in n:
        return "GPU · Mistral / Ministral family"
    if "qwen" in n:
        return "GPU · Qwen3-8B family"
    return "experiments/runs/"


def _campaign_form(stdscr):
    yamls = _discover_yamls()
    st = {
        "behavioral": True, "activations": True, "multilingual": False,
        "profile": False, "wt_o": True, "wt_down": False,
        "yaml_choice": 0, "custom_yaml": "",
        "output": "local", "s3_dest": "", "download": False, "purge": False,
        "device": "auto",
    }
    items = [
        {"type": "header",
         "text": "PLANS (applied if the YAML declares no plans: section)"},
        {"type": "check", "id": "behavioral", "key": "behavioral",
         "label": "Behavioral", "note": "refusal rate"},
        {"type": "check", "id": "activations", "key": "activations",
         "label": "Activations", "note": "Cohen's d"},
        {"type": "check", "id": "multilingual", "key": "multilingual",
         "label": "Multilingual"},
        {"type": "check", "id": "profile", "key": "profile", "label": "Profile"},
        {"type": "toggle", "id": "all_plans",
         "keys": ["behavioral", "activations", "multilingual", "profile"],
         "label": "Check all / uncheck all"},
        {"type": "check", "id": "wt_down", "key": "wt_down",
         "label": "weight target +down_proj", "note": "o_proj always included"},
        {"type": "blank"},
        {"type": "header", "text": "YAML FILE (model list + expected)"},
    ]
    for i, f in enumerate(yamls):
        items.append({"type": "radio", "id": f"y{i}", "group": "yaml_choice",
                      "value": i, "label": f, "note": _yaml_note(f)})
    items += [
        {"type": "radio", "id": "ycustom", "group": "yaml_choice",
         "value": -1, "label": "Other — enter a path"},
        {"type": "text", "id": "custom_yaml", "key": "custom_yaml",
         "label": "  YAML path", "ph": "e.g. ./my_campaign.yaml",
         "visible_if": lambda s: s["yaml_choice"] == -1},
        {"type": "blank"},
        {"type": "header", "text": "OUTPUT"},
        {"type": "radio", "id": "out_local", "group": "output", "value": "local",
         "label": "Local", "note": "1 JSON/model under runs_out/ + report"},
        {"type": "radio", "id": "out_s3", "group": "output", "value": "s3",
         "label": "Push S3", "note": "JSON + report pushed incrementally"},
        {"type": "text", "id": "s3_dest", "key": "s3_dest", "label": "  S3 dest",
         "ph": "default s3://your-bucket/results",
         "visible_if": lambda s: s["output"] == "s3"},
        {"type": "blank"},
        {"type": "header", "text": "AWS MODE (GPU box — download/purge on the fly)"},
        {"type": "check", "id": "download", "key": "download",
         "label": "download", "note": "fetch each model missing from the cache"},
        {"type": "check", "id": "purge", "key": "purge",
         "label": "purge", "note": "evict from cache what THIS run downloaded"},
        {"type": "blank"},
        {"type": "header", "text": "OPTIONS"},
        {"type": "select", "id": "device", "key": "device", "label": "Device",
         "choices": DEVICES},
        {"type": "blank"},
        {"type": "button", "id": "submit", "label": "▸ RUN CAMPAIGN"},
    ]
    st["_yamls"] = yamls
    sub = "CAMPAIGN · model matrix → 4-bucket report"
    res = _run_form(stdscr, sub, items, st)
    return res


# --------------------------------------------------------------------------- #
# Construction des commandes (pur — testable sans curses)                      #
# --------------------------------------------------------------------------- #
def build_scan_command(st) -> list:
    """Construit la commande `modelscanner scan …` depuis l'état du formulaire."""
    if st["model_choice"] == CUSTOM:
        model = st["custom_model"].strip()
    else:
        model = PRESETS[st["model_choice"]][0]
    cmd = [sys.executable, "-m", "modelscanner.cli", "scan", model]
    if st["behavioral"]:
        cmd.append("--behavioral")
    if not st["activations"]:
        cmd.append("--no-activations")
    if st["multilingual"]:
        cmd.append("--multilingual")
    if st["profile"]:
        cmd.append("--profile")
    targets = [t for t, on in (("o_proj", st["wt_o"]), ("down_proj", st["wt_down"]))
               if on]
    if targets and targets != ["o_proj"]:
        cmd += ["--weight-targets", ",".join(targets)]
    # Le plan multilingue balaye TOUTES les langues : le choix mono-langue est alors
    # masqué (cf. TUI) et sans effet -> le plan principal reste en 'en' par défaut.
    if st["lang"] != "en" and not st["multilingual"]:
        cmd += ["--lang", st["lang"]]
    if st["probe_subset"].strip():
        cmd += ["--probe-subset", st["probe_subset"].strip()]
    if st["max_new_tokens"].strip() not in ("", "64"):
        cmd += ["--max-new-tokens", st["max_new_tokens"].strip()]
    if st["subspace_k"].strip() not in ("", "4"):  # 4 = défaut du scanner
        cmd += ["--subspace-k", st["subspace_k"].strip()]
    if st["device"] != "auto":
        cmd += ["--device", st["device"]]
    if st["expected"]:
        cmd += ["--expected-label", st["expected"]]
    if st["output"] == "s3":
        cmd.append("--s3")
        if st["s3_dest"].strip():
            cmd.append(st["s3_dest"].strip())
        if st["keep_local"]:
            cmd.append("--keep-local")
    else:
        cmd += ["--report", "runs_out"]
    return cmd


def _resolve_yaml_path(st) -> str:
    if st["yaml_choice"] == -1:
        return os.path.abspath(st["custom_yaml"].strip())
    return os.path.join(_RUNS_DIR, st["_yamls"][st["yaml_choice"]])


def build_campaign(st):
    """Prépare la campagne. Renvoie (config_path, merged_dict_or_None).

    Auto-détection : si le YAML choisi ne déclare pas `plans:`, on écrit un YAML
    fusionné (plans cochés + device + sortie) et on le lance ; sinon on lance le
    fichier tel quel."""
    import yaml

    src = _resolve_yaml_path(st)
    data = yaml.safe_load(open(src, encoding="utf-8")) or {}
    if "plans" in data:  # YAML complet -> lancé tel quel
        return src, None

    merged = dict(data)
    merged["device"] = st["device"]
    plans = {"behavioral": st["behavioral"], "activations": st["activations"]}
    if st["wt_down"]:
        plans["weight_targets"] = "o_proj,down_proj"
    merged["plans"] = plans
    merged["multilingual"] = st["multilingual"]
    merged["profile"] = st["profile"]
    merged.setdefault("output_dir", "runs_out")
    if st["output"] == "s3":
        merged["output_s3"] = st["s3_dest"].strip() or "s3://your-bucket/results"
    merged["download"] = st["download"]
    merged["purge"] = st["purge"]

    out_dir = os.path.join(_REPO_ROOT, "runs_out")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"_tui_{time.strftime('%Y%m%d_%H%M%S')}.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(merged, fh, sort_keys=False, allow_unicode=True)
    return out, merged


# --------------------------------------------------------------------------- #
# Application curses (collecte des choix) + exécution (hors curses)            #
# --------------------------------------------------------------------------- #
def _app(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    _setup_colors()
    while True:
        choice = _home(stdscr)
        if choice == "quit":
            return None
        if choice == "scan":
            st = _scan_form(stdscr)
            if st is None:
                continue
            if st["model_choice"] == CUSTOM and not st["custom_model"].strip():
                continue  # pas de modèle saisi -> on revient à l'accueil
            return ("scan", st)
        if choice == "campaign":
            st = _campaign_form(stdscr)
            if st is None:
                continue
            if st["yaml_choice"] == -1 and not st["custom_yaml"].strip():
                continue
            return ("campaign", st)


def main(argv=None) -> int:
    locale.setlocale(locale.LC_ALL, "")
    try:
        result = curses.wrapper(_app)
    except KeyboardInterrupt:
        result = None
    if not result:
        print("Cancelled.")
        return 0

    mode, st = result
    from modelscanner import ui  # thème partagé, une fois hors curses

    if mode == "scan":
        cmd = build_scan_command(st)
        ui.banner("TUI", "model scan — direct launch")
        ui.kv("command", "$ " + " ".join(shlex.quote(c) for c in cmd))
        return subprocess.call(cmd, cwd=_REPO_ROOT)

    # campagne
    try:
        config, merged = build_campaign(st)
    except FileNotFoundError:
        ui.banner("TUI", "campaign")
        ui.bullet("fail", "YAML file not found — check the entered path")
        return 1
    cmd = [sys.executable, _RUN_SCAN, config]
    ui.banner("TUI", "campaign — direct launch")
    if merged is None:
        ui.bullet("info", "complete YAML (plans: present) → launched as-is")
    else:
        ui.bullet("info", f"merged YAML written → {config}")
    ui.kv("command", "$ " + " ".join(shlex.quote(c) for c in cmd))
    return subprocess.call(cmd, cwd=_REPO_ROOT)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
