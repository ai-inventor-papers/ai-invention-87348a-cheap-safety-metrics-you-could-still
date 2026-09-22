<p align="center">
  <img src="docs/logo.png" alt="Jorak — Model Scanner" width="150">
</p>

<h1 align="center">Model Scanner</h1>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="Licence : Apache 2.0"></a>
  <a href="https://github.com/JolanMc/Jorak/actions/workflows/ci.yml"><img src="https://github.com/JolanMc/Jorak/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.10%E2%80%933.13-blue.svg" alt="Python 3.10–3.13">
  <img src="https://img.shields.io/badge/tests-125%20passing-brightgreen.svg" alt="Tests : 125 passing">
  <img src="https://img.shields.io/badge/detection-reference--free-8A2BE2.svg" alt="Détection reference-free">
</p>

> 🇬🇧 English version: **[README.md](README.md)**

Détection **reference-free** de l'**abliteration** des LLM open-source — déterminer si un
modèle a été « décensuré » par ablation directionnelle (Arditi et al. 2024 ; Heretic /
Reaper / mlabonne) **sans disposer du modèle d'origine**.

**Principe.** L'abliteration orthogonalise la direction de refus `r̂` hors des poids qui
écrivent dans le residual stream (`o_proj`, `down_proj`) : `W' = (I − r̂r̂ᵀ)W`, donc
`r̂ᵀW' = 0`. La signature détectable = **axe de refus vivant ET débranché des poids**,
combinaison qu'aucun fine-tuning ne reproduit.

**Sortie.** Un label de provenance — `censored` / `ablated` / `finetuned_decensored` /
`ambiguous` — + un score de confiance + les couches touchées.

## La signature en un coup d'œil
<table>
<tr>
<td width="50%"><img src="docs/figures/heatmap-censored.png" alt="Modèle censuré — signaux par couche"></td>
<td width="50%"><img src="docs/figures/heatmap-ablated.png" alt="Modèle abliteré — signaux par couche"></td>
</tr>
</table>

> **Le smoking-gun**, c'est la ligne du bas — l'alignement des poids à la direction de refus,
> couche par couche. Il reste **quasi nul pour un modèle censuré** (à gauche, `conf 0.75`)
> mais **s'illumine sur toutes les couches pour un modèle abliteré** (à droite, `conf 0.81`) —
> une signature qu'aucun fine-tuning ordinaire ne laisse. Même modèle de base, verdict opposé.

## Démarrage rapide
```bash
# 1. Installer (détails conda dans la section Installation)
conda env create -f environment.yml && conda activate modelscanner
pip install -e ".[dev]"

# 2. Scanner un modèle → verdict affiché dans le terminal
modelscanner scan Qwen/Qwen2.5-0.5B-Instruct --behavioral

# 3. Rapport complet brandé (HTML EN+FR + CSV) sous ./<model>_jorak_<date>/
modelscanner scan Qwen/Qwen2.5-0.5B-Instruct --report
```
Plutôt les menus que les flags ? Lancez **`modelscanner tui`** (assistant plein
écran). Le reste de ce README est une référence — commencez ci-dessus, creusez ci-dessous.

## Jorak — trois techniques de détection
**Jorak** est le projet (ce scanner et le rapport qu'il produit). Ce n'est pas une métrique
unique mais un ensemble de **trois techniques de détection complémentaires**, une par angle d'attaque :
- **Poids — signature spectrale (SVD)** (le *smoking-gun*, CPU, sans inférence).
  Trois signaux : alignement **global** `A` (ablation totale), alignement de **bande** `B`
  (ablation localisée/furtive, type Heretic) et alignement de **sous-espace** `S`
  (sous-espace bottom-`k` partagé — capte l'ablation **multi-direction**, ex. OBLITERATUS
  `n_directions > 1`, que le seul `u_min` dilue).
- **Activations — santé de l'axe (Cohen's d)** : « l'axe de refus est-il vivant ? ».
- **Comportement — taux de refus** (et sur-refus du harmless) : sépare censuré de fine-tuné,
  et signale l'**ablation furtive** — norm-preserving multi-direction qui laisse les poids
  *intacts* aux yeux de la signature SVD mais le comportement abîmé (axe fortement vivant + obéit
  sur le harmful + sur-refus incohérent / refus inégal selon la langue).

> **Nommage.** `svd_alignment` (signal `A`) n'est qu'**un signal de la technique des poids** —
> à ne pas confondre avec **Jorak**, qui désigne le projet entier (les trois techniques et le
> bundle de rapport qu'il émet).

## Pipeline

![Pipeline Model Scanner](docs/pipeline.png)

Flux de bout en bout, du modèle au `ScanResult` : la frontière étanche `loaders/` +
`probes/`, les trois techniques (**poids/SVD** toujours active, **activations** et
**comportement** optionnels), `classify()` en 4 buckets, puis les vues (report, profile,
CLI, viz) et l'orchestration `experiments/`. Explication détaillée :
[`docs/PIPELINE.md`](docs/PIPELINE.md).

## Architecture
```
modelscanner/
├── core/types.py   # ScanResult, ModelHandle, enums (frontière étanche)
├── loaders/        # safetensors -> ModelHandle ; arch_adapter ; oracle (dev)
├── probes/         # sondes harmful/harmless (6 langues) + templates par famille
├── activations/    # scan-once : hidden states au dernier token
├── directions/     # r̂ par couche (mean-diff)
├── metrics/        # axis_health · jorak (A + bande + sous-espace) · behavioral
├── classifier/     # scan() · classify() · Thresholds -> 4 buckets
├── viz/            # heatmaps couches · scatter de provenance
├── profile.py      # profil modèle (comportement, qualité, hallucination, métadonnées)
├── report.py       # logger JSON (flags + stats + Q/R)
└── cli.py          # `modelscanner scan`
experiments/        # run_scan.py (runner YAML) · run_campaign.sh (lanceur 1 commande) · aggregate.py · campaign_report.py · figures
docs/               # HOW_TO_USE · PROTOCOLE_TEST · AWS_RUNBOOK · rapport.tex · présentation
tests/              # 125 tests offline + e2e réels (gated MS_E2E=1)
```
Deux invariants : **frontière étanche** (`metrics/` ne sait jamais d'où vient le modèle) et
**scan-once** (un seul forward → `ScanResult` riche → vues, pas de recalcul).

## Modèles supportés & non supportés
Le scanner charge des **poids safetensors / `.bin`** via `transformers` et lit le
décodeur texte (`o_proj` / `down_proj` par couche). Ce qui marche, et quoi faire sinon :

| Cas | Statut | Quoi faire |
|---|---|---|
| Llama / **Mistral · Ministral** (`mistral`, `ministral`) / **Qwen2 · Qwen3** / Gemma 2·3 (texte) | ✅ supporté | `modelscanner scan <id>` |
| `config.json` **sans `model_type`** (ex. nombreux dépôts `huihui-ai`) | ✅ auto-géré | le `model_type` est inféré depuis `architectures` (`["Qwen3ForCausalLM"]` → `qwen3`) |
| Famille inconnue mais nommage standard `*.self_attn.o_proj` | ✅ auto-détecté | les chemins de poids sont auto-détectés sur le modèle chargé |
| **`mistral3`** multimodal (ex. Ministral-3-8B-2512) | ⚠️ besoin transformers à jour | `pip install -U "transformers>=5.2.0"` sur la box — ensuite il charge : le registre connaît `mistral3` et le loader retombe sur `AutoModelForImageTextToText` pour atteindre le décodeur texte niché. |
| `model_type` **trop récent** pour le `transformers` installé | ⚠️ mettre à jour | `pip install -U transformers` → erreur `transformers_outdated` |
| **GGUF** (`*.gguf`, dépôts gguf-only) | ⛔ non supporté | choisir une variante safetensors — le GGUF n'a pas de tenseurs déquantifiables pour Jorak |
| bnb 4/8-bit, AWQ, MLX, FP8 quantifiés | ⛔ non supporté (J1) | charger un checkpoint pleine précision (fp16/bf16/fp32) |

Les échecs sont reportés avec un `error_kind` précis (`gguf_only`, `config_no_model_type`,
`transformers_outdated`, `unsupported_arch`, `gated`, `unsupported_format`, `oom`,
`download`). Détails de maintenance dans [docs/MAINTENANCE.md](docs/MAINTENANCE.md).

## Installation
**Prérequis :** `git`, et soit **conda** (recommandé), *soit* **Python 3.10+** pour la
voie venv. **Aucun GPU requis** pour le plan poids/SVD par défaut.

**Le plus rapide — une commande** (auto-détecte conda, sinon retombe sur un venv, puis installe) :
```bash
./scripts/setup.sh
```
Sous **Windows (PowerShell)**, utilise le script équivalent :
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

Ou à la main — **A. conda (recommandé) :**
```bash
# 1. Rendre conda disponible dans ce shell (sauter si `conda` est déjà dans le PATH)
source ~/miniconda3/etc/profile.d/conda.sh
# 2. Créer + activer l'env (Python 3.11)
conda env create -f environment.yml
conda activate modelscanner
# 3. Installer le scanner (editable) + outils de dev (pytest, optuna)
pip install -e ".[dev]"
# 4. Vérifier
pytest -q                                      # 125 passed, 13 skipped
```
**B. venv standard (pas de conda sur la machine) :**
```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip && pip install -e ".[dev]"
pytest -q                                      # 125 passed, 13 skipped
```

**Extras optionnels** — à ajouter au `pip install`, séparés par des virgules :
- `quant` → `bitsandbytes`, pour charger un 7B en 4-bit sur GPU CUDA : `pip install -e ".[dev,quant]"`
- `gguf` → `gguf` + `llama-cpp-python` (présents dans `pyproject.toml`, mais le scan GGUF
  **n'est pas encore supporté** — voir la table des types de modèles ci-dessus).

L'install editable garde le paquet `modelscanner` dans ce dépôt ; ses dépendances
(torch, transformers, …) vont dans `~/miniconda3/envs/modelscanner/lib/python3.11/site-packages/`.
Box air-gapped / sans certificat (AWS) : voir [docs/AWS_RUNBOOK.md](docs/AWS_RUNBOOK.md).

## Utilisation
**TUI interactive** (assistant plein écran, zéro dépendance — surcouche des commandes ci-dessous) :
```bash
modelscanner tui   # écran d'accueil → scan d'un modèle unique OU campagne YAML
```
Construit et lance la commande `scan` / `run_scan.py` exacte à partir de cases à
cocher (plans), boutons radio (local vs S3) et d'un sélecteur de modèle (3 modèles
8B préréglés ou un id saisi). Pour une campagne, elle prend un YAML « liste de
modèles » (`path` + `expected_label`) et **injecte les plans cochés** si le fichier
n'a pas de bloc `plans:` (un YAML complet est lancé tel quel). Elle ne remplace
rien — c'est juste une façade au-dessus de la CLI.

Scanner un modèle (CLI) :
```bash
modelscanner scan <id_ou_chemin> --behavioral --probe-subset 16 --log out.json
# options : --no-activations (GPU serré) · --subspace-k · --multilingual · --profile · --expected-label · --device cuda
```
**Rapport Jorak** autonome pour un scan unique (sans campagne) :
```bash
modelscanner scan <id_ou_chemin> --report           # -> ./<model>_jorak_<AAAAMMJJ>/
modelscanner scan <id_ou_chemin> --report rapports/  # bundle sous rapports/
modelscanner scan <id_ou_chemin> --s3   # push vers s3://your-bucket/results/Jorak/<bundle>, puis SUPPRIME le local
modelscanner scan <id_ou_chemin> --s3 s3://your-bucket/results/rapports --keep-local  # préfixe exact, garde le local
```
Pendant un scan `--report`, une **barre de progression avec ETA** s'affiche sur
stderr (une unité par prompt : activations + comportemental + génération
multilingue) — on voit l'avancement du scan et **l'estimation de la fin**.
Automatique sur un terminal interactif ; coupable avec `MODELSCANNER_NO_PROGRESS=1`.

**Ce que fait `--s3` :**
- **Push** — envoie le bundle à l'emplacement fixe `s3://your-bucket/results/Jorak/<bundle>`.
  Surcharge : `--s3 s3://autre` ou `$MODELSCANNER_S3_BUCKET` ; passer un **préfixe exact**
  `--s3 s3://bucket/chemin` pour pousser tel quel.
- **Nettoyage local** — supprime ensuite le dossier local, mais seulement si l'upload
  a réussi (sinon il est conservé, rien n'est perdu). Ajouter **`--keep-local`** pour le garder.
- **Télécharge si absent** — si le modèle n'est **pas dans le cache HF**, il le récupère
  d'abord via la procédure hors-ligne (certificats internes + token HF derrière un
  proxy privé, `hf download`) dans `~/.cache/huggingface/hub/`, puis **le purge après le
  scan** — mais
  uniquement le modèle qu'il a lui-même téléchargé (un modèle déjà en cache, ex. cache vLLM
  partagé, n'est pas touché).
- **Bilan** — la box est laissée comme trouvée : ni bundle local, ni modèle en cache en plus.

**Un bundle `--report` contient :**
- **`jorak_report_en.html` / `jorak_report_fr.html`** — deux rapports autonomes au branding
  pro (EN / FR), chacun avec heatmap couches embarquée, un **plan « position 4-buckets »**
  (ce modèle = 1 point sur le plan sévérance des poids × refus), **onglets de langue
  cliquables** pour les prompts/réponses et **infobulles au survol** expliquant chaque
  indicateur (signification + interprétation).
- **`prompts.csv`** (toutes les Q/R : comportemental + multilingue + profil), **`summary.csv`**
  (une ligne de métriques), **`bucket_position.png`**, **`scan_log.json`**.
- `--report` active automatiquement le plan comportemental **et la sonde multilingue complète**
  — toutes les langues, tous les prompts, avec le **refus** (harmful) **et le sur-refus**
  (harmless) — pour remplir chaque onglet. Bornez le nombre par langue avec `--probe-subset N` ;
  ajoutez `--profile` pour la section profil.

Comparer plusieurs bundles mono-scan sur un même plan 4-buckets :
```bash
modelscanner compare rapports/                # tous les bundles <model>_jorak_* sous rapports/
modelscanner compare a_jorak_*/ b_jorak_*/ --out compare.png --lang fr
# -> compare.png (points superposés, couleur = label prédit) + compare.csv
```
Batch piloté par YAML (le runner, 1 sous-process/modèle, anti-OOM) :
```bash
python experiments/run_scan.py experiments/runs/campaign_cpu.yaml
python experiments/aggregate.py runs_out/<run>/     # table + matrice de confusion
```
YAML de campagne curés (proposés dans `modelscanner tui`) : `campaign_cpu.yaml`,
`campaign_gpu_qwen.yaml`, `campaign_gpu_mistral.yaml`, `campaign_20260703_base.yaml`
(gabarit à copier). Les anciennes matrices étendues sont sous `experiments/runs/archive/`.
**Toute la campagne en une commande (box AWS) :**
```bash
./experiments/run_campaign.sh                                        # matrice GPU Qwen (YAML par défaut)
./experiments/run_campaign.sh experiments/runs/campaign_gpu_mistral.yaml  # matrice GPU Mistral
```
`run_campaign.sh` enchaîne le runner (download + scan + purge + rapport HTML/CSV de
campagne + push S3) puis `aggregate.py` (accuracy + matrice de confusion en texte).
Il active l'env conda `modelscanner` et transmet `$HF_TOKEN` s'il est défini.

Sur la box AWS le runner réutilise le **même cycle que `scan --s3`** : avec
`download: true` il récupère chaque modèle absent du cache via la procédure box
(CA interne + secrets + `hf download`) avant de le scanner, et avec `purge: true`
il supprime du cache HF — après chaque scan — **uniquement les modèles que ce run
a téléchargés lui-même** (un modèle déjà en cache / une entrée locale de
`models_dir` est laissée intacte). Une matrice entière se scanne
donc **anti-OOM** (1 sous-process/modèle) **et anti-saturation disque** (purge
entre les modèles). Les YAML de campagne GPU (`campaign_gpu_qwen.yaml`,
`campaign_gpu_mistral.yaml`) activent `download`/`purge` ; `campaign_cpu.yaml` les
laisse désactivés (aucun changement).

**Flags pratiques du runner** (tout appel `run_scan.py` / `run_campaign.sh`) :
```bash
python experiments/run_scan.py <yaml> --dry-run          # affiche le plan (dl/scan/purge/skip), n'exécute rien
python experiments/run_scan.py <yaml> --only dphn huihui # ne garde que les modèles dont le path/nom matche un motif
python experiments/run_scan.py <yaml> --limit 1          # ne scanne que les N premiers modèles (test rapide)
python experiments/run_scan.py <yaml> --force            # re-scanner même si un résultat existe déjà
```
`--dry-run` résout chaque modèle (id HF vs local), montre lesquels seraient
téléchargés / scannés / purgés / sautés, et affiche l'espace disque libre — à
utiliser pour valider un YAML avant de dépenser des heures GPU. Le récap affiche le
**temps par modèle + total** et le **delta d'espace disque** quand `purge` est actif.
Le runner est **idempotent** : relancer la même commande reprend (saute les modèles
déjà faits) ; `--force` re-scanne.

Guide complet : **[docs/HOW_TO_USE.md](docs/HOW_TO_USE.md)** (setup, recettes,
**comment analyser les résultats**). Portage GPU/AWS : **[docs/AWS_RUNBOOK.md](docs/AWS_RUNBOOK.md)**.

## État (v0.1.0)
Détecteur **complet et validé** sur une matrice réelle de 4 modèles dérivés de
`Qwen2.5-0.5B` — **accuracy 4/4** :

| Modèle | Verdict | `A` (global) | `B` (bande) | refus |
|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct | `censored` | 0.24 | 0.28 | 0.88 |
| huihui …-abliterated | `ablated` | **0.90** | **0.99** | 0.06 |
| grisun0 …-heretic *(localisé)* | `ablated` | 0.29 | **0.67** | — |
| Dolphin3.0-Qwen2.5-0.5B | `finetuned_decensored` | 0.24 | 0.28 | 0.06 |

Faux positif (fine-tuné) évité ; ablation **furtive** (Heretic) rattrapée par le critère de **bande**.

**Extension multi-direction / norm-preserving (2026-06).** Le scan d'un vrai 7B
(`OBLITERATUS/Qwen2.5-Coder-7B-Instruct-OBLITERATED`, `n_directions=4`, `norm_preserve`,
`regularization=0.3`) a révélé un angle mort : le `u_min` mono-direction + la préservation de
norme paraissent *intacts* à la signature SVD des poids → mal classé `finetuned_decensored`. Correctif livré : signal
de **sous-espace** `S` (bottom-`k`) + règle d'**ablation furtive** (fusion comportementale).
**Aucune régression** sur la matrice 0.5B à 4 modèles (toujours 4/4 ; les nouveaux signaux
restent dormants sur les modèles connus). 125 tests offline.

**Runner de campagne désormais AWS-ready (2026-06).** `experiments/run_scan.py` reproduit le
cycle de `scan --s3` (téléchargement box + purge du cache après scan, uniquement de ce que le run
a récupéré) : les matrices de benchmark curées (`campaign_gpu_qwen.yaml`, `campaign_gpu_mistral.yaml` ;
anciennes sous `runs/archive/`) tournent sur la box sans saturer le disque — la campagne
« preuve d'efficacité » est prête à lancer sur GPU.

**Prochaines étapes** : lancer le benchmark 1.5B / 7B sur la box AWS (accuracy + matrice de
confusion + rapport HTML de campagne), confirmer le correctif multi-direction sur le vrai 7B,
calibration des seuils de `S` / sur-refus contre des contrastes même famille (Coder-7B base +
Dolphin-Coder), MoE/MLA, interface graphique.

## Documentation
- [`docs/METRICS.md`](docs/METRICS.md) — **guide des métriques** (FR) : chaque signal — intuition → formule → ce que ça détecte → seuil → où ça apparaît dans le rapport
- [`docs/PIPELINE.md`](docs/PIPELINE.md) — pipeline annoté (diagramme + 3 plans + 4 buckets)
- [`docs/HOW_TO_USE.md`](docs/HOW_TO_USE.md) — guide d'utilisation + analyse des résultats
- [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md) — modèles supportés, types d'erreur, limites reference-free
- [`docs/AWS_RUNBOOK.md`](docs/AWS_RUNBOOK.md) — portage GPU/AWS + runner
- [`docs/PROTOCOLE_TEST.md`](docs/PROTOCOLE_TEST.md) — protocole de validation
- [`docs/report_fr.tex`](docs/report_fr.tex) · [`docs/report_en.tex`](docs/report_en.tex) — rapport de justification mathématique (FR / EN), chaque métrique commentée (Overleaf, pdfLaTeX)
## Licence
**Apache License 2.0** — voir [`LICENSE`](LICENSE). Libre d'utilisation, de modification et
de redistribution, y compris à usage commercial, à condition de conserver l'attribution et
la notice de licence. Les contributions sont bienvenues sous les mêmes termes (voir
[`CONTRIBUTING.md`](CONTRIBUTING.md)) ; merci de signaler les failles de sécurité en privé
comme décrit dans [`SECURITY.md`](SECURITY.md).
