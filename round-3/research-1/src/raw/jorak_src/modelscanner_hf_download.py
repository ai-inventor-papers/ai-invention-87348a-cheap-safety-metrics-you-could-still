"""Téléchargement d'un modèle absent du cache HF — environnement cloisonné.

Sur un serveur cloisonné (sans accès direct au Hub : proxy de paquets privé +
certificats internes), `--s3` doit pouvoir récupérer un modèle non encore présent
dans le cache avant de le scanner. On reproduit la procédure manuelle validée :

    cd $HOME/venv/scripts && source activate
    export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
    export SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt
    set -a; sudo -s source /path/to/.env_secrets; set +a
    hf download <model-editor/modelname>      # -> $HOME/.cache/huggingface/hub/

Chemins surchargeables par variables d'environnement (pour un autre environnement).
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from typing import Optional

# Paramètres de l'environnement cloisonné (surchargeables sans toucher au code).
_VENV_DIR = os.environ.get("ABLATION_VENV_DIR", "$HOME/venv/scripts")
_CA_BUNDLE = os.environ.get("ABLATION_CA_BUNDLE", "/etc/ssl/certs/ca-bundle.crt")
_ENV_SECRETS = os.environ.get("ABLATION_ENV_SECRETS", "/path/to/.env_secrets")
# Motifs à NE PAS télécharger : par défaut les GGUF (les repos « mixtes »
# safetensors+gguf, ex. DreamFast/qwen3-8b-heretic, embarquent des blobs GGUF que
# `from_pretrained` ne charge pas ici — inutile de saturer le disque).
# Surchargeable (vider pour tout prendre) : ABLATION_DOWNLOAD_EXCLUDE="*.gguf *.pt".
_DOWNLOAD_EXCLUDE = os.environ.get("ABLATION_DOWNLOAD_EXCLUDE", "*.gguf").split()


def is_model_cached(model_id: str) -> bool:
    """True si `model_id` est déjà disponible hors-ligne : chemin local existant,
    ou snapshot présent dans le cache HF ($HF_HOME / ~/.cache/huggingface/hub)."""
    if os.path.isdir(model_id):
        return True
    try:
        from huggingface_hub import snapshot_download

        snapshot_download(model_id, local_files_only=True)
        return True
    except Exception:
        return False


def download_command(model_id: str) -> str:
    """Script bash reproduisant la procédure box (certs + secrets + `hf download`).

    `$HOME` est laissé non quoté (expansion shell voulue dans `cd "$HOME/..."`) ;
    le reste est échappé."""
    excludes = " ".join(f"--exclude {shlex.quote(p)}" for p in _DOWNLOAD_EXCLUDE)
    dl = f"hf download {shlex.quote(model_id)}"
    if excludes:
        dl += f" {excludes}"
    return "\n".join([
        "set -e",
        f'cd "{_VENV_DIR}"',
        "source activate",
        f"export REQUESTS_CA_BUNDLE={shlex.quote(_CA_BUNDLE)}",
        f"export SSL_CERT_FILE={shlex.quote(_CA_BUNDLE)}",
        "set -a",
        f"sudo -s source {shlex.quote(_ENV_SECRETS)}",
        "set +a",
        dl,
    ])


def _hf_hub_cache() -> str:
    """Répertoire des repos du cache HF (`.../hub`), robuste aux surcharges env."""
    try:
        from huggingface_hub.constants import HF_HUB_CACHE

        if HF_HUB_CACHE:
            return HF_HUB_CACHE
    except Exception:
        pass
    base = os.environ.get("HF_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache", "huggingface")
    return os.path.join(base, "hub")


def _repo_cache_dir(model_id: str) -> str:
    """Dossier de cache d'un repo : `<hub>/models--org--name` (convention HF)."""
    return os.path.join(_hf_hub_cache(), "models--" + model_id.replace("/", "--"))


def _purge_partial_cache(model_id: str) -> int:
    """Nettoie les résidus d'un download interrompu (ENOSPC) pour `model_id`.

    Comble le trou de `delete_revisions` (API), qui ne voit QUE les révisions
    COMPLÈTES : un download coupé laisse des blobs `*.incomplete` et un snapshot
    partiel (shard manquant) que l'API ignore -> l'espace fuit run après run et
    le repo cassé re-échoue au chargement suivant (`incomplete_download`).

    Stratégie : (1) supprimer les blobs `*.incomplete` ; (2) si le repo n'est plus
    chargeable hors-ligne (snapshot cassé/partiel), supprimer le dossier de repo
    entier pour forcer un re-téléchargement propre. Renvoie les octets récupérés.

    Garde-fous : on n'agit QUE dans un dossier `models--…` situé SOUS le cache hub
    (jamais un chemin local de l'utilisateur, déjà exclu par l'appelant)."""
    repo_dir = _repo_cache_dir(model_id)
    hub = os.path.abspath(_hf_hub_cache())
    if not (os.path.isdir(repo_dir)
            and os.path.basename(repo_dir).startswith("models--")
            and os.path.abspath(repo_dir).startswith(hub + os.sep)):
        return 0
    freed = 0
    # (1) blobs `.incomplete` : transfert coupé en plein vol (typique ENOSPC).
    blobs = os.path.join(repo_dir, "blobs")
    if os.path.isdir(blobs):
        for f in os.listdir(blobs):
            if f.endswith(".incomplete"):
                p = os.path.join(blobs, f)
                try:
                    freed += os.path.getsize(p)
                    os.remove(p)
                except OSError:
                    pass
    # (2) repo non chargeable hors-ligne (snapshot partiel) -> on nuke le dossier.
    if not is_model_cached(model_id):
        for root, _dirs, files in os.walk(repo_dir):
            for f in files:
                try:
                    freed += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        shutil.rmtree(repo_dir, ignore_errors=True)
    if freed:
        print(f"[hf] purge partiel : libère ~{freed / 1e9:.2f} Go "
              f"(blobs .incomplete / snapshot cassé) ({model_id})")
    return freed


def purge_model_cache(model_id: str) -> bool:
    """Supprime `model_id` du cache HF — nettoyage post-scan (disque de la box).

    No-op si `model_id` est un chemin local (on ne touche JAMAIS aux fichiers de
    l'utilisateur). Deux passes complémentaires :
      1. API officielle `scan_cache_dir().delete_revisions(...).execute()` pour les
         révisions COMPLÈTES ;
      2. `_purge_partial_cache` pour les résidus d'un download interrompu (blobs
         `*.incomplete`, snapshot partiel) que l'API n'attrape pas — sinon fuite
         d'espace run après run (cf. re-scan 2026-07-01 : ENOSPC en cascade).
    Renvoie True si quelque chose a été supprimé.

    ⚠ N'appeler que sur un modèle que ce run a lui-même téléchargé : un cache
    partagé (ex. vLLM lu en place) ne doit pas être purgé."""
    if os.path.isdir(model_id):
        return False
    freed_any = False
    # --- passe 1 : révisions complètes via l'API officielle ---
    try:
        from huggingface_hub import scan_cache_dir

        cache = scan_cache_dir()
        hashes = [rev.commit_hash for repo in cache.repos if repo.repo_id == model_id
                  for rev in repo.revisions]
        if hashes:
            strategy = cache.delete_revisions(*hashes)
            print(f"[hf] purge cache : libère ~{strategy.expected_freed_size_str} "
                  f"({model_id})")
            strategy.execute()
            freed_any = True
        else:
            print(f"[hf] rien à purger (API, révisions complètes) pour : {model_id}")
    except Exception as e:  # API absente / cache illisible -> on tente la passe 2
        print(f"[hf] purge cache (API) impossible : {e}")
    # --- passe 2 : résidus d'un download interrompu (ENOSPC) ---
    try:
        if _purge_partial_cache(model_id) > 0:
            freed_any = True
    except Exception as e:  # nettoyage best-effort : ne jamais casser le run
        print(f"[hf] purge partiel KO ({model_id}) : {e}")
    return freed_any


def ensure_model_downloaded(model_id: str, *, force: bool = False,
                            timeout: Optional[float] = None) -> bool:
    """Télécharge `model_id` via la procédure box s'il est absent du cache HF.

    Renvoie True si le modèle est disponible (déjà en cache ou téléchargé OK),
    False si le téléchargement a échoué. Ne lève pas : l'appelant tentera de
    toute façon de charger le modèle (erreur plus parlante en cas d'échec).

    Anti-blocage (le piège : `sudo` qui attend un mot de passe peut figer le
    process des heures) :
      - **stdin coupé** (`DEVNULL`) -> `sudo` échoue VITE au lieu de bloquer ;
      - **timeout** (défaut 1 h, `$ABLATION_DOWNLOAD_TIMEOUT`) -> coupe un proxy
        qui traîne ;
      - la sortie de `hf download` reste visible (barres de progression)."""
    if not force and is_model_cached(model_id):
        print(f"[hf] modèle déjà en cache : {model_id}", flush=True)
        return True
    if timeout is None:
        try:
            timeout = float(os.environ.get("ABLATION_DOWNLOAD_TIMEOUT", "3600"))
        except ValueError:
            timeout = 3600.0
    print(f"[hf] modèle absent du cache -> téléchargement (peut être long ; "
          f"timeout {int(timeout)}s) : {model_id}", flush=True)
    print("[hf] --- sortie de `hf download` ci-dessous ---", flush=True)
    try:
        r = subprocess.run(["bash", "-lc", download_command(model_id)],
                           stdin=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"[hf] téléchargement INTERROMPU après {int(timeout)}s (timeout). "
              f"Le proxy/sudo bloque probablement. Télécharge le modèle À LA MAIN "
              f"une fois (`hf download {model_id}`) puis relance le scan, ou "
              f"ajuste $ABLATION_DOWNLOAD_TIMEOUT.", flush=True)
        return False
    except FileNotFoundError:
        print("[hf] `bash` introuvable -> téléchargement impossible ici.", flush=True)
        return False
    if r.returncode == 0:
        print(f"[hf] téléchargement OK : {model_id}", flush=True)
        return True
    print(f"[hf] téléchargement KO (exit {r.returncode}) : {model_id}. "
          f"Cause fréquente : `sudo` réclame un mot de passe (stdin est coupé "
          f"EXPRÈS pour ne PAS bloquer le scan). Solution : configure un sudo "
          f"NOPASSWD pour la source des secrets, ou source-les avant de lancer, "
          f"puis relance. Le scan tente quand même de charger le modèle.",
          flush=True)
    return False
