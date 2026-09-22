"""Barre de progression + ETA pour le scan d'un *seul* modèle (sans dépendance).

Affichée sur **stderr** (stdout reste réservé aux résultats du scan), elle se
branche comme callback `progress(n=1, desc=None)` dans les boucles coûteuses :
`collect_activations` (forward), `refusal_rate` et `multilingual_asymmetry`
(génération). Une « unité » = un prompt traité. L'ETA (estimation de fin du
scan) vient du débit moyen observé depuis le départ — comme tqdm, elle se
recalibre toute seule.

Le total attendu est estimé AVANT le scan par `estimate_scan_units()` (qui
reproduit le découpage interne de `classifier.scan`), pour que la barre atteigne
naturellement 100 %.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Optional, TextIO

from modelscanner import ui


def _fmt_dur(seconds: float) -> str:
    """Durée -> `MM:SS` ou `H:MM:SS`. Renvoie `--:--` si inconnue."""
    if seconds is None or seconds != seconds or seconds < 0 or seconds == float("inf"):
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class ProgressBar:
    """Barre de progression minimaliste (total connu) avec ETA, sur une ligne.

    Contrat de callback : `pb.update` a la signature `(n=1, *, desc=None)`, donc
    on peut passer `pb.update` tel quel partout où une fonction `progress` est
    attendue.

        pb = ProgressBar(total, desc="scan")
        pb.update(1, desc="multilingual · zh")
        pb.freeze()   # fige la ligne courante avant des prints externes
        pb.close()    # ligne 100 % + retour chariot final
    """

    def __init__(self, total: int, *, desc: str = "scan", enabled: bool = True,
                 width: int = 28, stream: Optional[TextIO] = None,
                 min_interval: Optional[float] = None):
        self.total = max(int(total), 1)
        self.desc = desc
        self.enabled = enabled
        self.width = width
        self.stream = stream or sys.stderr
        # tty : rafraîchissement fluide sur place (\r). Hors tty (log/fichier/
        # nohup) : on imprime une LIGNE de heartbeat espacée -> le scan reste
        # visible même redirigé (c'est le cas qui faisait croire à un blocage).
        self.tty = bool(getattr(self.stream, "isatty", lambda: False)())
        if min_interval is None:
            if self.tty:
                min_interval = 0.15
            else:
                try:
                    min_interval = float(
                        os.environ.get("MODELSCANNER_PROGRESS_INTERVAL", "15"))
                except ValueError:
                    min_interval = 15.0
        self.min_interval = min_interval
        self.n = 0
        self.start = time.monotonic()
        self._last_draw = 0.0
        self._closed = False
        if self.enabled:
            self._draw(force=True)

    # -- API publique ------------------------------------------------------- #
    def update(self, n: int = 1, *, desc: Optional[str] = None) -> None:
        """Avance de `n` unités (callback `progress`)."""
        self.n += n
        if desc is not None:
            self.desc = desc
        if not self.enabled or self._closed:
            return
        now = time.monotonic()
        if self.n >= self.total or (now - self._last_draw) >= self.min_interval:
            self._draw()

    def set_total(self, total: int) -> None:
        """Réajuste le total si l'estimation initiale s'avère imprécise."""
        self.total = max(int(total), self.n, 1)

    def freeze(self) -> None:
        """Fige la ligne courante (saut de ligne) avant d'écrire des prints
        externes ; la barre reprendra au prochain `update`. Sans effet hors tty
        (les lignes de heartbeat sont déjà terminées) ni si désactivée/fermée."""
        if not self.enabled or self._closed or not self.tty:
            return
        self.stream.write("\n")
        self.stream.flush()

    def close(self) -> None:
        """Termine : ligne 100 % + saut de ligne. Idempotent."""
        if self._closed:
            return
        self._closed = True
        if not self.enabled:
            return
        self.n = self.total
        on = ui.supports_color(self.stream)
        bar = ui.style("█" * self.width, ui.fg(ui.ORANGE), enabled=on)
        check = ui.style("✓", ui.BOLD, ui.fg(ui.GREEN), enabled=on)
        pct = ui.style("100.0%", ui.BOLD, ui.fg(ui.GREEN), enabled=on)
        elapsed = _fmt_dur(time.monotonic() - self.start)
        line = (f"  {check} [{bar}] {pct}  {self.total}/{self.total}  done in {elapsed}")
        if self.tty:
            self.stream.write("\r" + line + " " * 24 + "\n")
        else:
            self.stream.write(line + "\n")
        self.stream.flush()

    # -- interne ------------------------------------------------------------ #
    def _draw(self, *, force: bool = False) -> None:
        now = time.monotonic()
        self._last_draw = now
        frac = min(self.n / self.total, 1.0)
        filled = int(round(self.width * frac))
        on = ui.supports_color(self.stream)
        bar = (ui.style("█" * filled, ui.fg(ui.ORANGE), enabled=on)
               + ui.style("░" * (self.width - filled), ui.fg(ui.NAVY), enabled=on))
        elapsed = now - self.start
        rate = (self.n / elapsed) if (elapsed > 0 and self.n > 0) else 0.0
        remaining = ((self.total - self.n) / rate) if rate > 0 else float("inf")
        desc = (self.desc or "")[:30]
        pct = ui.style(f"{frac * 100:5.1f}%", ui.BOLD, ui.fg(ui.BLUE), enabled=on)
        eta = ui.style(_fmt_dur(remaining), ui.fg(ui.ORANGE), enabled=on)
        desc_s = ui.style(f"{desc:<30}", ui.fg(ui.GREY), enabled=on)
        line = (f"  [{bar}] {pct}  {self.n}/{self.total}  "
                f"elapsed {_fmt_dur(elapsed)} · ETA {eta}  {desc_s}")
        if self.tty:
            self.stream.write("\r" + line)        # réécrit sur place
        else:
            self.stream.write(line + "\n")        # heartbeat : une ligne par tick
        self.stream.flush()

    def __enter__(self) -> "ProgressBar":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _split_eval_count(n: int, direction_split: float = 0.6) -> int:
    """Nombre de prompts réellement passés au plan behavioral (jeu d'éval).

    Reproduit fidèlement le découpage train/test de `classifier.scan` : la
    direction est apprise sur le TRAIN, la santé d'axe + le comportement
    mesurés sur le TEST."""
    n_train = int(round(direction_split * n))
    split_applied = (0.5 <= direction_split < 1.0) and n_train >= 4 and (n - n_train) >= 4
    return (n - n_train) if split_applied else n


def estimate_scan_units(
    lang: str = "en",
    *,
    probe_subset: Optional[int] = None,
    with_activations: bool = True,
    with_behavioral: bool = True,
    with_multilingual: bool = True,
    multilingual_harmless: bool = True,
    multilingual_n: Optional[int] = None,
    direction_split: float = 0.6,
    jorak_layers: int = 0,
    jorak_targets: int = 1,
) -> int:
    """Estime le nombre d'unités (étapes) d'un scan, pour caler la barre.

    Couvre les sources de coût : signature JORAK des poids (1 SVD/couche × cible),
    forward d'activations, génération comportementale (jeu d'éval harmful +
    harmless), et génération multilingue (toutes langues × harmful [+ harmless]).
    Tolérant : renvoie au moins 1 et ignore les langues dont la sonde est absente.
    `jorak_layers` = nombre de couches (handle.n_layers) ; 0 si inconnu.
    `jorak_targets` = nombre de cibles JORAK (1 = o_proj seul, 2 = +down_proj)."""
    from modelscanner.probes import available_languages, load_probes

    try:
        base = load_probes(lang=lang)
    except FileNotFoundError:
        base = load_probes()
    n_h = len(base.harmful)
    n_hl = len(base.harmless)
    if probe_subset:
        n_h = min(n_h, probe_subset)
        n_hl = min(n_hl, probe_subset)

    total = max(int(jorak_layers), 0) * max(int(jorak_targets), 1)   # JORAK : 1 SVD/couche × cible
    if with_activations:
        total += n_h + n_hl                       # collect_activations (tous les probes)
    if with_behavioral:
        total += _split_eval_count(n_h, direction_split)        # refusal_rate harmful
        if with_activations:                                    # over_refusal harmless
            total += _split_eval_count(n_hl, direction_split)
    if with_multilingual:
        cap = multilingual_n if multilingual_n else 10 ** 6
        for lg in available_languages():
            try:
                ps = load_probes(lang=lg)
            except FileNotFoundError:
                continue
            total += min(len(ps.harmful), cap)
            if multilingual_harmless:
                total += min(len(ps.harmless), cap)
    return max(total, 1)


def progress_enabled() -> bool:
    """Barre active par défaut. Sur un terminal -> barre fluide sur place ; hors
    terminal (log, fichier, nohup) -> lignes de heartbeat espacées (toujours
    visibles : c'est justement le cas où l'on croyait à un blocage). On ne coupe
    QUE si `MODELSCANNER_NO_PROGRESS=1`."""
    return os.environ.get("MODELSCANNER_NO_PROGRESS") != "1"
