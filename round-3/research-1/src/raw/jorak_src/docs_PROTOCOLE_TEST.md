# Protocole de test — Model Scanner

> Validation reproductible du détecteur d'abliteration *reference-free*.
> v1 — banc d'essai ancré Qwen2.5-0.5B (contrainte matérielle), extensible.

---

## 0. Objectif

Quantifier **dans quelle mesure et jusqu'où** le scanner distingue les quatre
provenances (`censored` / `ablated` / `finetuned_decensored` / `ambiguous`)
sans accès au modèle original, et **tracer où il casse**.

On ne valide pas « ça marche / ça marche pas » : on mesure des **taux**, des
**séparations de signaux**, une **calibration de confiance** et une **courbe de
difficulté**.

---

## 1. Questions de recherche

| # | Question | Expérience |
|---|----------|-----------|
| Q1 | Le scanner classe-t-il correctement les 4 buckets ? | E1 (matrice) |
| Q2 | Le verdict reference-free coïncide-t-il avec la vérité-terrain par diff de poids ? | E2 (oracle) |
| Q3 | Jusqu'à quelle « finesse » d'ablation (rank-k, norm-preserve, sparsity) reste-t-il détectable ? | E3 (courbe de difficulté) |
| Q4 | La signature survit-elle à la quantification (bf16 / 4-bit / GGUF) ? | E4 (quant) |
| Q5 | Le détecteur généralise-t-il aux autres familles (Mistral, Gemma) ? | E5 (archi) |
| Q6 | Une ablation EN laisse-t-elle un refus détectable en FR ? | E6 (multilingue) |

---

## 2. Variables

- **Indépendantes** : provenance, famille, taille, niveau de quantif, force/rang
  d'ablation, langue des sondes.
- **Dépendantes (mesurées)** : label prédit, confiance, `svd_alignment`,
  `cohens_d` (sur sondes **held-out**), `weight_axis_align` par couche,
  `refusal_rate`, temps & RAM.
- **Contrôlées (fixées)** : jeu de sondes (`refusal_v1`), chat template par
  famille, seed, `max_new_tokens`, versions torch/transformers, `dtype` de
  chargement, position de lecture (dernier token, `add_generation_prompt=True`).

---

## 3. Banc d'essai (matrice de vérité-terrain)

Tout ancré sur la même base `Qwen2.5-0.5B` (même archi/taille → comparaison propre).

| Bucket attendu | Modèle | Tier | Statut |
|---|---|---|---|
| `censored` | `Qwen/Qwen2.5-0.5B-Instruct` | base | ✅ testé |
| `ablated` | `huihui-ai/Qwen2.5-0.5B-Instruct-abliterated` | brut | ✅ testé |
| `finetuned_decensored` | `dphn/Dolphin3.0-Qwen2.5-0.5B` | faux-positif | ✅ testé |
| `ablated` (dur) | forge maison (rank-k, norm-preserve) | dur contrôlé | ⏳ E3 |
| `ablated` (réel dur) | `hereticness/Heretic-Dolphin3.0-Qwen2.5-1.5B` | Heretic réel | ⏳ |
| hybride | `huihui-ai/Qwen2.5-0.5B-Instruct-abliterated-SFT` | abliteré→re-finetuné | ⏳ |

**Paires appariées** (pour E2, oracle) : `base ↔ huihui-abliterated` ;
`base ↔ forge(base)`.

**Montée en charge (matériel permettant)** : 0.5B → 1.5B → 3B (CPU/2060) →
7B-4bit (T4). Familles : + Mistral-7B-Instruct, + Gemma-3-1b-it.

---

## 4. Métriques & critères de succès

| Métrique | Définition | Critère de succès v1 |
|---|---|---|
| **Accuracy / bucket** | bonne classe / total | ≥ 0.90 global |
| **Faux-positif fine-tuné** | un fine-tuné classé `ablated` | **= 0** (bloquant) |
| **Séparation `svd_align`** | AUC abliteré vs non-abliteré | ≈ 1.0 ; seuil 0.5 robuste |
| **`cohens_d` held-out** | d sur sondes de test | « axe vivant » > 1.0 sur tous (sauf cas dégénéré) |
| **Séparation comportementale** | AUC refuse vs obéit | nette ; seuil 0.5 |
| **Accord oracle** | `layers_touched` reference-free ∩ oracle | recouvrement ≥ 0.8 |
| **Calibration** | confiance vs justesse | confiance plus haute quand correct |
| **Stabilité quant** | label inchangé fp32→4-bit | label conservé jusqu'à 4-bit |
| **Seuil de rupture** | force d'ablation où `svd_align` < 0.5 | documenté (courbe) |

---

## 5. Protocole expérimental

> Préalable : env `modelscanner` actif, sondes `refusal_v1`, modèles en cache.
> Un modèle = un process (anti-OOM). Toutes les commandes loggent dans `runs/`.

### Contrôle transverse — split train/test des sondes (anti-circularité)
r̂ et Cohen's d calculés sur les **mêmes** sondes ⇒ d optimiste. **Obligatoire** :
calculer r̂ sur un **train split** (ex. 30 paires), évaluer `cohens_d` et
`refusal_rate` sur un **test split** disjoint (10 paires). *(Code à ajouter :
argument `train_idx/test_idx` à `collect_activations` / `scan`.)*

### E1 — Matrice de provenance (cœur)
- **But** : Q1. Confusion matrix 4×4.
- **Méthode** : scanner chaque modèle du banc avec `--behavioral`, répéter
  **k=5 fois** avec ré-échantillonnage des sondes (CI sur l'accuracy).
- **Commande** :
  ```bash
  python experiments/scan_matrix.py <hf-id> 32 beh   # sauve scans/*.npz
  ```
- **Sortie** : matrice de confusion, scatter de provenance, table
  (label, confiance, svd_align, d_test, refusal).

### E2 — Oracle (validation reference-free)
- **But** : Q2. Le smoking-gun reference-free dit-il vrai ?
- **Méthode** : sur `base ↔ huihui`, `weight_diff_oracle` → vraie direction
  retirée, `rank1_fraction`, `shared_alignment`, `layers_touched`. Comparer à
  `weight_axis_align` reference-free (recouvrement des couches touchées ;
  cos(u_min reference-free, direction oracle)).
- **Sortie** : table couches touchées (oracle vs reference-free), histogramme
  des cosinus.

### E3 — Courbe de difficulté (forge)
- **But** : Q3. Tracer la rupture.
- **Méthode** : sur la base, forger des ablations contrôlées en faisant varier
  **un bouton à la fois** : rang `k ∈ {1,2,4,8}`, `norm-preserve` (rescale L2
  on/off), `sparsity` (% petites entrées mises à 0), `partial-projection`
  (coeff α ∈ {1.0,0.8,0.5}). Pour chaque réglage : `scan` → relever
  `svd_alignment`. *(Prérequis : promouvoir la brique d'orthogonalisation des
  tests en module `forge/`.)*
- **Sortie** : courbe `svd_alignment` (et label) vs intensité de masquage ;
  **point de rupture** (passage sous 0.5).

### E4 — Robustesse à la quantification
- **But** : Q4. Seuils quant-aware.
- **Méthode** : même modèle abliteré chargé en `fp32`, `bf16`, `bnb-4bit`, puis
  via GGUF (`Q8_0`, `Q4_K_M`). Relever `svd_alignment` et le label.
- **Sortie** : `svd_alignment` vs bits ; glissement de seuil à documenter
  (hypothèse : signature inter-couches survit, bruit décorrélé entre couches).

### E5 — Généralité d'architecture
- **But** : Q5. L'`arch_adapter` + le détecteur tiennent-ils hors Qwen ?
- **Méthode** : répéter E1 (mini) sur paires Mistral et Gemma (base vs
  abliteré huihui correspondant).
- **Sortie** : E1 par famille ; vérifier auto-détection + chemins de poids.

### E6 — Asymétrie multilingue (recherche)
- **But** : Q6. Feature de détection d'ablation **partielle**.
- **Méthode** : sonde FR (à versionner `refusal_fr_v1`). Mesurer `refusal_rate`
  EN vs FR et `cohens_d` EN vs FR sur un abliteré-EN. Asymétrie (refuse encore
  en FR) ⇒ signal d'ablation partielle.
- **Sortie** : Δ(refusal EN, FR), Δ(d EN, FR).

---

## 6. Contrôles & pièges (à neutraliser)

- **In-sample bias** : split train/test des sondes (cf. §5). Non négociable.
- **Baseline aléatoire** : comparer `svd_align`/`suppression` au plancher d'une
  **direction aléatoire** (~`1/√d_model` ≈ 0.033 pour d=896). Un signal doit
  battre ce plancher.
- **Contrôle négatif** : labels harmful/harmless **mélangés** ⇒ `cohens_d` doit
  s'effondrer (sinon on mesure un artefact).
- **Chat template** : vérifier que le prompt finit pile au point de génération
  (sinon on mesure du formatage). Template par famille obligatoire.
- **Taille d'échantillon** : ≥ 30 paires pour un Cohen's d stable ; reporter un
  IC par bootstrap.
- **Suppression trompeuse** : `suppression(r̂_mean-diff)` ≈ identique
  censuré/abliteré sur les vrais modèles — **ne pas s'en servir comme preuve** ;
  signal de référence = `svd_alignment` (et `σ_min/‖W‖_F` probe-free en v2).
- **GQA/MLA** : vérifier les dimensions de `o_proj` (sortie = d_model) avant
  d'interpréter la suppression.

---

## 7. Reproductibilité

- Seed fixe (`numpy`, `torch`), `do_sample=False` (génération greedy).
- Logger par run : `model_id`, commit, versions torch/transformers, `dtype`,
  `device`, hash du jeu de sondes, seuils `Thresholds`.
- Artefacts par run : `scans/*.npz` (ScanResult complet),
  `runs/<date>_<model>.json`.

---

## 8. Livrables

1. **Matrice de confusion 4×4** (E1) + accuracy ± IC.
2. **Scatter de provenance**.
3. **Heatmaps couches×métriques** par modèle (le smoking-gun par couche).
4. **Courbe de difficulté** `svd_alignment` vs masquage (E3) — la figure « où ça
   casse ».
5. **Table de robustesse quant** (E4) + seuils quant-aware retenus.
6. **Table oracle vs reference-free** (E2).

---

## Annexe — Smoke test rapide (re-validation < 15 min)

```bash
# matrice 0.5B, 16 sondes, avec comportemental
for M in Qwen/Qwen2.5-0.5B-Instruct \
         huihui-ai/Qwen2.5-0.5B-Instruct-abliterated \
         dphn/Dolphin3.0-Qwen2.5-0.5B ; do
  HF_HUB_OFFLINE=1 python experiments/scan_matrix.py "$M" 16 beh
done
```
Attendu : `CENSORED` / `ABLATED` / `FINETUNED_DECENSORED`, faux-positif = 0.
