# Runbook AWS — porter Model Scanner sur GPU (T4 / +)

> Objectif : faire tourner le scanner sur de gros modèles, sur une instance GPU AWS,
> avec transfert via S3. Inclut la compatibilité vLLM, les commandes GPU/process/S3,
> et la **liste de tests** à dérouler.

---

## 0. Compatibilité vLLM — verdict honnête

**Le code n'utilise PAS vLLM aujourd'hui** : il s'appuie sur `transformers`
(`from_pretrained` + `.generate` + `output_hidden_states`). Mais la question
« compatible vLLM ? » dépend du **plan** :

| Plan | Besoin | GPU ? | vLLM ? |
|------|--------|-------|--------|
| **JORAK** (poids · SVD/bande — le smoking-gun) | lire `o_proj`/`down_proj` (fp32) | ❌ **CPU** | ❌ inutile — lit les safetensors |
| **ACTIVATIONS** (Cohen's d) | `output_hidden_states` (forward HF) | ✅ (fp16 gros modèles) | ❌ **vLLM n'expose pas les hidden states** |
| **behavioral** (refus/profil/multilingue) | génération de texte | ✅ | ✅ **c'est là que vLLM aide** (vitesse) |

**Conséquences pratiques :**
- Le **détecteur principal (Jorak) ne dépend ni du GPU ni de vLLM** → il se porte trivialement, et **scale à de très gros modèles** (on lit les matrices couche par couche). C'est notre force.
- Le plan **activations** tourne sous HF (GPU fp16) — **pas portable sur vLLM** (pas d'API hidden-states).
- Le plan **comportemental** marche **tel quel** en HF `.generate` sur GPU. vLLM ne serait qu'une **optimisation de débit** (utile si on génère beaucoup / batch de modèles), et nécessiterait un **adaptateur de génération** (voir §7).

> **TL;DR** : oui ça tourne sur GPU AWS **tel quel** (via transformers). vLLM n'est
> **pas requis** ; c'est un *plus* de vitesse pour la génération, à brancher via un
> petit backend (à designer ensemble — le « grill »).

⚠️ **Quantif 4-bit (bnb)** : le plan Jorak ne sait pas encore déquantifier des poids
4-bit (garde-fou `NotImplementedError`). Sur T4, charge les gros modèles en **fp16**
(safetensors), pas en 4-bit, pour le plan Jorak.

### 0bis. vLLM ou HF (python) pour tester du 7-8B ? → **HF, pour le scan**
Recommandation tranchée, vu notre cas :
- **Le scan a besoin de HF, pas de vLLM.** Le plan Jorak lit les `.safetensors`
  bruts (vLLM stocke les poids dans son format interne, inexploitable) ; le plan
  ACTIVATIONS exige `output_hidden_states` (vLLM ne le donne pas). Donc **HF est
  obligatoire** pour la détection.
- **Piège T4 (16 Go)** : un 7-8B en fp16 ≈ 14-16 Go. On **ne peut pas** le charger
  à la fois dans HF (poids/activations) ET dans vLLM (génération) → **double
  chargement = OOM**. Donc on **ne mélange pas** HF+vLLM sur le même modèle sur T4.
- **vLLM n'a d'intérêt que pour une passe de génération DÉDIÉE et volumineuse**
  (gros benchmark comportemental sur des centaines de prompts, ou batch de modèles),
  lancée *séparément* — pas pendant le scan. Pour notre besoin (refus sur ~16-40
  prompts courts), **HF `.generate` suffit largement**.

**Profil de scan « T4-safe » pour un 7-8B :**
1. **Plan Jorak sur CPU** (lit les safetensors, jamais d'OOM) → verdict d'ablation.
2. **Plan behavioral** via HF `.generate` (peu de prompts) → censuré vs fine-tuné.
3. **Plan ACTIVATIONS** seulement si la VRAM le permet (sinon on le **désactive** :
   le plan Jorak suffit au verdict). C'est lui le gourmand en VRAM sur 7-8B.

→ Conclusion : **commence en HF/python (le plus pratique et complet)**. On gardera
vLLM en réserve pour une éventuelle passe de génération massive, en étape à part.

---

## 1. Pré-requis instance
- GPU NVIDIA T4 16 Go (ou A10G/L4 24 Go). **Deep Learning AMI** recommandée (drivers + CUDA + conda déjà là).
- Accès S3 (rôle IAM attaché à l'instance, ou `aws configure`).
- `HF_TOKEN` si modèles *gated* (Gemma…).

---

## 2. Vérifs GPU / NVIDIA  (à lancer EN PREMIER)
```bash
nvidia-smi                                   # GPU présent, VRAM, driver, CUDA, procs
nvidia-smi -L                                # liste des GPU
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu --format=csv
nvcc --version                               # version du toolkit CUDA (si installé)

# côté Python / framework
python -c "import torch; print('cuda', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0), '| CUDA', torch.version.cuda)"
python -c "import vllm; print('vllm', vllm.__version__)"   # seulement si vLLM voulu
```
Live monitoring GPU :
```bash
watch -n 1 nvidia-smi                         # rafraîchi chaque seconde
nvidia-smi dmon -s um                         # flux util + mémoire
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv   # quels procs tiennent la VRAM
```

---

## 3. Processus & système (monitoring)
```bash
htop                  # CPU/RAM interactif (sinon: top)
ps -ef | grep -i python | grep -v grep        # procs python en cours
ps aux --sort=-%mem | head                    # plus gros consommateurs RAM
free -h                                        # RAM libre/utilisée
df -h                                          # disque (⚠️ les modèles remplissent vite)
du -sh ~/.cache/huggingface/hub               # taille du cache HF
nproc                                          # nb de cœurs CPU
# tuer un run qui dérape :
pkill -f scan_matrix          # par motif
kill -9 <PID>                 # par PID (vu dans nvidia-smi / ps)
```
**Pour les runs longs : utiliser `tmux`** (la session survit à la déconnexion SSH) :
```bash
tmux new -s scan      # créer ; Ctrl-b d pour détacher ; tmux attach -t scan pour revenir
```

---

## 4. Transfert via S3  (bucket : `your-bucket`)
```bash
# --- D'ABORD : prendre l'identité qui a les droits AWS ---
sudo su s3-user          # bascule sur l'utilisateur autorisé (creds/rôle S3)
aws s3 ls s3://your-bucket         # vérifier l'accès

BUCKET=s3://your-bucket

# --- POSTE LOCAL : packager le projet (sans les gros/inutiles) puis pousser ---
cd ~/Jorak
tar czf modelscanner.tgz modelscanner pyproject.toml environment.yml tests experiments docs README.md
aws s3 cp modelscanner.tgz $BUCKET/modelscanner.tgz
# (alternative : sync direct, en excluant le superflu)
aws s3 sync . $BUCKET/Jorak --exclude 'autre/*' --exclude '*.npz' --exclude '*.pt2' \
      --exclude 'logs/*' --exclude '.git/*' --exclude '**/__pycache__/*'

# --- SUR AWS : récupérer ---
aws s3 ls $BUCKET/
aws s3 cp $BUCKET/modelscanner.tgz . && tar xzf modelscanner.tgz
# ou : aws s3 sync $BUCKET/Jorak ~/Jorak

# --- RÉCUPÉRER LES RÉSULTATS (scans/logs) en fin de run ---
aws s3 cp scans/  $BUCKET/results/scans/ --recursive
aws s3 cp logs/   $BUCKET/results/logs/  --recursive
# puis en local : aws s3 sync $BUCKET/results ./results_aws
```

---

## 5. Setup environnement (sur AWS)
```bash
cd ~/Jorak
conda create -y -n modelscanner python=3.11 && conda activate modelscanner
pip install -e ".[dev]"            # lib + tests
pip install -e ".[quant]"          # bitsandbytes (si 4-bit un jour)
pip install vllm                   # OPTIONNEL (génération rapide)
export HF_TOKEN=hf_xxx             # si modèles gated
export HF_HOME=~/Jorak/.hf_cache  # (optionnel) cache modèles sur le bon disque
```

---

## 5bis. Le runner (batch via YAML) — la façon recommandée
Au lieu de lancer `modelscanner scan` à la main, le **runner** lit un YAML et
enchaîne tout : **1 sous-process par modèle** (anti-OOM), **JSON poussé sur S3 au
fil de l'eau**, **reprise** de ce qui manque, **skip+log** si un modèle plante.
```bash
# 1) récupérer les modèles depuis S3 vers le disque
sudo su s3-user
aws s3 sync s3://your-bucket/models /data/models

# 2) lancer le batch (éditer experiments/runs/campaign_gpu_qwen.yaml d'abord)
python experiments/run_scan.py experiments/runs/campaign_gpu_qwen.yaml
#   -> 1 JSON/modèle dans runs_out/<run>/ ET sur s3://your-bucket/results/<run>/
#   -> récap "N OK / M échecs" + table attendu vs prédit
#   reprise après crash : relancer la MÊME commande (idempotent ; --force pour tout refaire)

# 3) agréger en table + matrice de confusion
python experiments/aggregate.py runs_out/<run>/
```
**Clés du YAML** : `device`, `plans:{behavioral, activations}`, `probe_subset`,
`multilingual`, `profile`, `models_dir`, `output_s3`, et la liste `models:` (chaque
entrée = `path` + `expected_label` optionnel). Exemples fournis :
`experiments/runs/campaign_cpu.yaml` (CPU) · `experiments/runs/campaign_gpu_qwen.yaml` (GPU) ·
`experiments/runs/campaign_20260703_base.yaml` (gabarit à dupliquer). Anciens : `runs/archive/`.
> Sur T4 16 Go, garder `activations: false` (le plan Jorak suffit au verdict, zéro OOM).

## 6. LISTE DE TESTS — à dérouler dans l'ordre
| # | Test | Commande | Attendu |
|---|------|----------|---------|
| **T0** | GPU visible | `nvidia-smi` + le `torch.cuda` du §2 | `cuda True`, VRAM listée |
| **T1** | Suite unitaire | `python -m pytest tests/ -q` | `45 passed` |
| **T2** | Scan GPU petit modèle | `modelscanner scan Qwen/Qwen2.5-0.5B-Instruct --device cuda --probe-subset 16 --log logs/t2.json` | `CENSORED` |
| **T3** | Matrice e2e (GPU) | `MS_E2E=1 python -m pytest tests/test_scan_e2e.py -v -s` | 4 buckets corrects |
| **T4** | Modèle moyen 3B fp16 | `modelscanner scan huihui-ai/Qwen2.5-3B-Instruct-abliterated --device cuda --behavioral` | `ABLATED` ; surveiller la VRAM (`watch nvidia-smi`) |
| **T5** | Gros modèle 7B fp16 | `modelscanner scan Qwen/Qwen2.5-7B-Instruct --device cuda --probe-subset 16` | tient sur T4 16 Go ? sinon OOM → §8 |
| **T6** | Plan Jorak sur gros modèle (timing SVD) | chronométrer T5 ; le plan Jorak est CPU | mesurer le temps SVD/couche |
| **T7** | Débit comportemental | `... --behavioral` sur 7B → temps de génération | décider si vLLM nécessaire |
| **T8** | Profil + multilingue (gros abliteré) | `modelscanner scan <abliteré-3B> --device cuda --profile --multilingual --log logs/t8.json` | profil rempli, MRA cohérent |
| **T9** | 1 modèle / process (anti-OOM) | boucle `scan_matrix.py <id> 16 beh` (un process par modèle) | pas d'OOM, logs/scans écrits |

**Règle d'or** : **un modèle = un processus** (sinon OOM, vu en local). Pour une
batterie de modèles, boucler en relançant le process à chaque fois.

---

## 7. Adaptations code identifiées (pour le runner AWS — à designer)
1. **Loader « weights-only »** : pour scanner un modèle ÉNORME sans le charger en
   entier, lire `o_proj`/`down_proj` directement depuis les `.safetensors` (lazy,
   couche par couche). Aujourd'hui `load_model` charge tout le modèle (nécessaire
   pour activations/génération, pas pour le plan Jorak).
2. **Backend de génération vLLM** : abstraire `handle.generate(prompts)` avec une
   implémentation vLLM (pour `refusal_rate`/`profile`/`multilingual`). Optionnel.
3. **Déquantif bnb 4-bit** du plan Jorak (J10) — sinon fp16 obligatoire pour les gros.
4. **Runner YAML** : un fichier décrivant {modèles, device, dtype, sondes/langues,
   seuils, sortie S3} → boucle un process par modèle → pousse les artefacts sur S3.

---

## 8. Si OOM (gros modèle sur T4 16 Go)
- 7B fp16 ≈ 14 Go de poids → tient à peine ; les activations peuvent faire déborder.
  → baisser `--probe-subset`, `batch_size`, ou **désactiver le plan activations**
  (le plan Jorak seul suffit pour le verdict d'ablation, et il est CPU).
- Lire le plan Jorak sur **CPU** (déjà le cas) même si le modèle est sur GPU.
- En dernier recours : 4-bit (nécessite l'adaptation §7.3) ou instance 24 Go (A10G/L4).

---

## Cheat-sheet (les commandes qui servent tout le temps)
```bash
nvidia-smi                                   # état GPU
watch -n1 nvidia-smi                          # GPU en direct
ps -ef | grep python | grep -v grep           # mes process
free -h ; df -h                               # RAM / disque
aws s3 sync . $BUCKET/Jorak --exclude 'autre/*'   # pousser le code
aws s3 cp logs/ $BUCKET/results/logs/ --recursive  # remonter les résultats
MS_E2E=1 python -m pytest tests/test_scan_e2e.py -v -s   # valider la matrice
modelscanner scan <id> --device cuda --behavioral --profile --multilingual --log out.json
```
