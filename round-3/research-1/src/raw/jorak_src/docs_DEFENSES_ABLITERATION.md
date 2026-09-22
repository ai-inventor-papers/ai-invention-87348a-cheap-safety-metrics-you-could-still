# Défenses vs Ablation — rapport complet

> Panorama des **attaques par ablation** (abliteration & co.) et des **défenses**, dans
> l'ordre chronologique, avec la dialectique « qui répond à quoi », et une synthèse de
> ce que les **éditeurs de modèles open-weight** déploient réellement.
>
> Contexte projet : Jorak **détecte** l'ablation (plans POIDS / ACTIVATIONS / BEHAVIORAL).
> Ce document ouvre la voie **défense / robustesse**. Voir aussi `METRICS.md`, `PIPELINE.md`.
> Dernière mise à jour : 2026-06-30.

---

## 0. Synthèse exécutive (TL;DR)

1. **L'ablation gagne sur les poids ouverts.** En l'état de l'art 2026, un modèle
   open-weight standard est décensurable en **quelques minutes** avec des outils gratuits
   (enquête FT, mai 2026 : Llama, Gemma dépouillés de leurs garde-fous). Le refus est une
   propriété **superficielle** des poids (« shallow safety », Qi 2024) → facile à retirer.

2. **Le modèle de menace tue les défenses *inference-time*.** L'attaquant a les poids et
   tourne sa propre inférence. Donc Llama Guard / ShieldGemma / steering ne protègent **pas
   le modèle de base** : ce sont des défenses *système*, pour celui qui déploie, pas pour
   empêcher l'ablation des poids publiés.

3. **Trois familles de défense « dans les poids » seulement comptent** : (a) **diffuser/
   relocaliser le refus** (Extended-Refusal/ESD, Circuit Breakers, deep safety) ; (b)
   **rendre les poids tamper-resistant** (TAR, RepNoise, LAT) ; (c) **retirer la
   connaissance dangereuse** (unlearning RMU/WMDP, filtrage de pré-entraînement « Deep
   Ignorance ») pour qu'il n'y ait *rien à déverrouiller*.

4. **La dialectique est une course aux armements** : chaque défense single-direction
   appelle une attaque multi-direction (ESD → DBDI/CRA), chaque tamper-resistance appelle
   un fine-tuning adaptatif (TAR → « One Step to the Side »). Aucune défense in-weights
   n'est prouvée durable.

5. **Ce que font vraiment les boîtes** : très peu de durcissement *du refus* dans les poids.
   La stratégie réelle = **defense-in-depth système** (classifieurs externes) + **gating
   pré-release** (ne pas publier la capacité dangereuse) + montée de l'**unlearning de
   connaissances**. ESD est la rare défense anti-abliteration *in-weights* simple et
   efficace — utile mais non suffisante seule.

---

## 1. Cadre & modèle de menace

| | |
|---|---|
| **Cible** | un modèle open-weight aligné (refuse les requêtes nuisibles). |
| **Attaquant** | possède les **poids complets**, accès **white-box**, calcule activations/SVD, modifie les poids, refait son inférence. |
| **But attaquant** | supprimer le **refus** (décensure) sans casser les capacités. |
| **But défenseur (éditeur)** | publier des poids dont le refus **survit** à l'ablation/au fine-tuning. |
| **But défenseur (auditeur, ex. un OEM / intégrateur)** | **scorer la fragilité** d'un modèle tiers / **détecter** une ablation déjà faite → c'est Jorak. |

> Corollaire central : une défense ne « compte » contre l'ablation **que si elle est gravée
> dans les poids publiés**. Tout ce qui vit au moment de l'inférence est contournable par
> l'attaquant white-box.

---

## 2. Les attaques par ablation — généalogie chronologique

L'« abliteration » (ablation + obliteration) = identifier la **direction de refus** dans
l'espace des activations puis la **retirer des poids** par projection orthogonale
`W' = (I − r̂r̂ᵀ)W`. Le modèle garde ses capacités mais ne refuse plus.

| Date | Méthode / outil | Idée clé | Réf |
|---|---|---|---|
| Oct 2023 | **Fine-tuning attack** (Qi et al.) | un FT court (même bénin) défait l'alignement → pose le problème open-weight | [2310.03693](https://arxiv.org/abs/2310.03693) |
| Mai 2024 | **Abliteration « pratique »** (mlabonne, FailSpy `abliterator`) | mean-diff harmful−benign → orthogonalisation des poids ; outil grand public | blog mlabonne |
| Juin 2024 | **Refusal = Single Direction** (Arditi et al.) | *la science* : le refus est médié par **une** direction linéaire ; ablation = la retirer | [2406.11717](https://arxiv.org/abs/2406.11717) |
| 2024-25 | **Explosion d'outils** : huihui-ai, ErisForge, DECCP, llm-abliteration, obliteratus, abliterix | variantes mean-diff + sélection de couche/direction | divers HF |
| 2025 | **Heretic** | abliteration **auto-optimisée** (Optuna/TPE bayésien) : règle direction, couche, force pour max décensure ∧ min dégradation | outil |
| 2025 | **Multi-direction / Gabliteration** (`n_directions>1`) | retire un **sous-espace** de k directions, pas un seul axe | outils |
| Nov 2025 | **DBDI** (Differentiated Bi-Directional Intervention) | décompose le refus en **2 directions** (détection du danger + exécution du refus) → jusqu'à **97 % ASR** | [2511.06852](https://arxiv.org/abs/2511.06852) |
| Déc 2025 | **Comparative Analysis** (Young) | banc d'essai inter-architectures de 4 outils (Heretic, DECCP, ErisForge, FailSpy) ; le raisonnement math est le plus sensible | [2512.13655](https://arxiv.org/abs/2512.13655) |
| Avr 2026 | **CRA** (Contextual Representation Ablation) | ablation **inference-time** d'un **sous-espace low-rank** des hidden states, sans toucher les poids | [2604.07835](https://arxiv.org/abs/2604.07835) |

**Tendance** : single-direction → **multi-direction / sous-espace** → optimisé (bayésien) →
fonctionnellement décomposé (DBDI). Chaque génération invalide les défenses calibrées sur la
précédente.

---

## 3. Les défenses — généalogie chronologique

Classées par **famille** (cf. §4 pour le « répond à quoi »).

| Date | Défense | Famille | Idée clé | Réf |
|---|---|---|---|---|
| 2023 | **Self-Destructing Models** (Henderson et al.) | tamper-cost | augmenter le **coût** d'un détournement | [2211.14946](https://arxiv.org/abs/2211.14946) |
| Mar 2024 | **RMU + WMDP** (Li et al.) | unlearning | **désapprendre la connaissance dangereuse** (bio/chem/cyber) ; rien à déverrouiller | [2403.03218](https://arxiv.org/abs/2403.03218) |
| Mai 2024 | **RepNoise** (Rosati et al.) | repr. / tamper-resist | pousser les représentations nuisibles vers du **bruit gaussien** | [2405.14577](https://arxiv.org/abs/2405.14577) |
| Juin 2024 | **Circuit Breakers / RR** (Zou et al., Gray Swan) | repr. relocalisation | **rerouter** les représentations nuisibles vers un état incohérent (LoRRA) | [2406.04313](https://arxiv.org/abs/2406.04313) |
| Juin 2024 | **Deep Safety** (Qi et al.) | refus profond | *la théorie* : l'alignement n'est profond que de **quelques tokens** → le rendre profond | [2406.05946](https://arxiv.org/abs/2406.05946) |
| Juil 2024 | **LAT** (Sheshadri et al.) | adversarial latent | entraîner **contre des perturbations latentes** (≈ ablations simulées) → voies redondantes | [2407.15549](https://arxiv.org/abs/2407.15549) |
| Aoû 2024 | **TAR** (Tamirisa et al.) | tamper-resist (meta) | **méta-apprentissage** : poids tels que des centaines de pas de FT ne défont pas la sûreté | [2408.00761](https://arxiv.org/abs/2408.00761) |
| 2024 | **Vaccine / Booster / Lisa** (Huang et al.) | anti-harmful-FT | régularisations qui stabilisent l'alignement sous fine-tuning | [2402.01109](https://arxiv.org/abs/2402.01109) |
| Déc 2024 | **Durability eval** (Qi, Henderson et al.) | *méta-critique* | montre que TAR/RepNoise/… sont **fragiles** sous attaque adaptative | [2412.07097](https://arxiv.org/abs/2412.07097) |
| **Mai 2025** | **Extended-Refusal / ESD** (Abu Shairah et al., KAUST) | **refus diffus** | refus **long et justifié** (survol+refus+raison) → signal **réparti** sur de nombreux tokens/directions → ablation single-dir inefficace (**−10 %** vs −70/80 %) | [2505.19056](https://arxiv.org/abs/2505.19056) |
| Aoû 2025 | **Deep Ignorance** (EleutherAI/UK AISI) | unlearning amont | **filtrer les données de pré-entraînement** → le modèle n'apprend jamais le savoir dangereux (le plus robuste) | [2508.06601](https://arxiv.org/abs/2508.06601) |
| Oct 2025 | **SARSteer** | inference-time | re-steering du refus à l'inférence (utile côté déployeur, **pas** contre l'ablation des poids) | [2510.17633](https://arxiv.org/abs/2510.17633) |
| 2026 | **One Step to the Side** / TamperBench | *méta-critique* | les défenses anti-FT cèdent sous **adversaires adaptatifs** ; besoin de stress-tests | [2605.14605](https://arxiv.org/abs/2605.14605) |

---

## 4. Le « jeu » attaque ↔ défense (dialectique chronologique)

Lire de haut en bas = course aux armements. **A**=attaque, **D**=défense.

```
2023  A  Fine-tuning défait l'alignement (Qi)           ── pose le problème open-weight
       └─D  Self-Destructing Models / (plus tard) TAR, RepNoise, LAT, Vaccine
              → rendre le minimum de sûreté difficile à quitter par FT
                 └─A  "One Step to the Side" (2026) : FT adaptatif les recasse

2024  A  Refusal = Single Direction (Arditi) → abliteration (mlabonne/FailSpy)
       │   "le refus tient sur 1 axe, je le retire"
       ├─D  Deep Safety (Qi, tokens-deep) : ne pas concentrer la sûreté sur les 1ers tokens
       ├─D  Circuit Breakers (Zou) : relocaliser le refus vers un état incohérent
       └─D  Extended-Refusal / ESD (2025) : étaler le refus sur N tokens/directions
              → l'axe unique ablaté ne porte plus tout le refus (−10 % seulement)
                 └─A  Multi-direction / Gabliteration, puis DBDI (2 dir.), CRA (sous-espace)
                       → "le refus tient sur k>1 axes, j'ablate le sous-espace" (97 % ASR)
                          └─D  ? défense multi-direction encore ouverte (LAT k-dir, mix)

2024  A  Le modèle SAIT des choses dangereuses (même décensuré)
       ├─D  RMU/WMDP (unlearning) : retirer la connaissance dangereuse
       │     └─A  "Prompt attacks / relearning" : la connaissance unlearnée se récupère
       └─D  Deep Ignorance (2025) : ne jamais l'apprendre (filtrage pré-train) ← plus robuste
```

**Trois leçons de la dialectique :**

- **L'attaque suit la dimension.** Toute défense qui « diffuse contre 1 direction » (ESD) est
  re-cassée par une attaque qui ablate **k directions** (DBDI/CRA). La robustesse réelle se
  mesure en **rang** du signal de refus, pas en présence/absence d'un axe.
- **Tamper-resistance ⇒ fragile sous adaptatif.** TAR/RepNoise impressionnent sur attaque
  fixe mais cèdent quand l'attaquant *adapte* son FT (Durability eval 2024, One Step 2026).
- **Le plus durable n'est pas le refus mais l'ignorance.** Si la capacité n'existe pas dans
  les poids (Deep Ignorance), il n'y a **rien à abliterer**. C'est la seule branche où la
  défense a structurellement l'avantage.

---

## 5. Ce que les entreprises open-weight utilisent réellement

**Constat de réalité (enquête FT, mai 2026) :** les garde-fous de modèles Meta (Llama) et
Google (Gemma) sont retirés **en ~10 minutes** avec des outils publics. Conclusion crue :
**le durcissement *du refus* dans les poids n'est PAS déployé en production** sur les
releases open-weight courantes.

Ce qu'elles font à la place, par couche :

### a) Defense-in-depth **système** (hors modèle de base)
- **Meta** : Llama Guard / Purple Llama (classifieur entrée/sortie), Prompt Guard, Code Shield.
- **Google** : ShieldGemma (2B/9B/27B, classification de contenu en 4 catégories).
- **IBM** : Granite Guardian. **NVIDIA** : NeMo Guardrails.
- → Protègent **le pipeline du déployeur**, pas les poids publiés. Inutiles contre l'ablation
  du modèle de base (l'attaquant ne charge pas le classifieur).

### b) **Gating pré-release** (la vraie « défense »)
- Meta (**Frontier AI Framework**) : évaluation de capacité avant publication ; un modèle jugé
  « risque catastrophique » **n'est pas publié** sans mitigation suffisante.
- → La défense dominante est *organisationnelle* : **ne pas libérer la capacité dangereuse**,
  pas durcir le refus.

### c) **Unlearning / ignorance de connaissances** (la branche in-weights crédible)
- **RMU/WMDP** : désapprendre bio/chem/cyber dangereux → même décensuré, le modèle ne *sait*
  pas aider. Adopté dans certaines évaluations/releases de sûreté.
- **Deep Ignorance** (EleutherAI + UK AI Safety Institute) : filtrer le pré-entraînement —
  la version la plus robuste, car rien à récupérer. Tendance montante côté labos publics.

### d) **Refus durci in-weights** (rare, surtout recherche)
- **Circuit Breakers** (Gray Swan) : commercialisé, parfois intégré ; **ESD** : académique,
  simple, efficace contre l'abliteration single-direction. Peu d'éditeurs grand public les
  embarquent par défaut aujourd'hui.

**Synthèse honnête :** l'industrie a, de fait, **concédé** qu'on ne garde pas le refus dans
des poids ouverts face à un abliterator déterminé. Le centre de gravité s'est déplacé vers
**(b) gating** + **(c) ignorance de capacités** + **(a) garde-fous système**. ESD et les
circuit breakers sont les meilleurs candidats *si* l'objectif est précisément de **préserver
le refus dans les poids** — ce qui reste un objectif de niche, mais directement aligné avec un
travail anti-abliteration.

---


## Références (arXiv)

**Attaques :** Fine-tuning compromises safety [2310.03693] · Refusal single direction
(Arditi) [2406.11717] · DBDI [2511.06852] · Comparative analysis [2512.13655] · CRA
[2604.07835].

**Défenses :** Self-Destructing Models [2211.14946] · WMDP/RMU [2403.03218] · RepNoise
[2405.14577] · Circuit Breakers [2406.04313] · Deep Safety (tokens-deep) [2406.05946] · LAT
[2407.15549] · TAR [2408.00761] · Vaccine [2402.01109] · Durability eval [2412.07097] ·
**Extended-Refusal / ESD [2505.19056]** · Deep Ignorance [2508.06601] · SARSteer [2510.17633]
· One Step to the Side [2605.14605].
