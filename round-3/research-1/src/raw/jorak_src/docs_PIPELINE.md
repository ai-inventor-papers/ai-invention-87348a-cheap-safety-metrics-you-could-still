# Pipeline — Model Scanner

Détecteur **reference-free** d'abliteration de LLM : à partir d'un modèle seul (sans
l'original), décider s'il a été **abliteré** (censure retirée par ablation
directionnelle), simplement **censuré**, **fine-tuné-décensuré**, ou **ambigu**.

Le cœur du détecteur est la technique **Jorak** : la signature spectrale des
**poids**, reference-free, sur CPU, sans modèle original — c'est elle qu'on
exploite et qu'on met en avant. Deux plans la complètent : **ACTIVATIONS**
(l'axe de refus est-il vivant ?) et **BEHAVIORAL** (boîte noire, génération).

Principe d'architecture : **frontière étanche** (`loaders/` ne dit jamais à
`metrics/` d'où vient le modèle) + **scan-once** (un seul forward coûteux → un
`ScanResult` typé → toutes les vues sont des projections, jamais des recalculs).

---

## Vue d'ensemble

```mermaid
flowchart TD
    IN["modèle<br/>(id HF / chemin local / ModelHandle)"]

    subgraph L["loaders/ — frontière étanche"]
        LM["load_model()"]
        AA["arch_adapter<br/>(11 familles)"]
        MH["ModelHandle<br/>déquantif → fp32"]
        LM --> AA --> MH
    end

    subgraph P["probes/"]
        LP["load_probes(lang)<br/>EN + zh/fr/de/es/it"]
        TPL["templates par famille<br/>(Gemma sans system, Qwen3 no-think)"]
        LP --> TPL
    end

    IN --> LM
    MH --> PLANS
    TPL --> PLANS

    subgraph PLANS["3 plans de mesure — scan-once"]
        direction LR
        subgraph W["★ ① JORAK — signature des poids · TOUJOURS · CPU · sans original"]
            UMIN["umin_signature() · metrics/jorak.py<br/>→ svd_alignment (A global)<br/>→ per_layer_align<br/>→ band_alignment (B bande)"]
            WF["flags<br/>--no-activations → Jorak seul<br/>--report (bundle + heatmap)"]
        end
        subgraph A["② ACTIVATIONS — optionnel · GPU"]
            CA["collect_activations()<br/>split train/test 0.6"]
            MD["mean_diff_directions() → r̂"]
            CD["cohens_d() · axis_health"]
            SUP["suppression()<br/>o_proj / down_proj"]
            CA --> MD --> CD
            MD --> SUP
            AF["flags<br/>--no-activations (off)<br/>--probe-subset · --lang"]
        end
        subgraph B["③ BEHAVIORAL — optionnel"]
            RR["refusal_rate()"]
            MRA["multilingual_asymmetry() → MRA"]
            BF["flags<br/>--behavioral · --multilingual · --lang"]
        end
    end

    PLANS --> CLF["classify()<br/>A ≥ 0.5 OU B ≥ 0.5 → poids sectionnés<br/>4 buckets"]
    CLF --> SR["ScanResult<br/>(typé · scan-once → vues)"]

    SR --> VIZ["viz/<br/>layer_heatmap · provenance_scatter"]
    SR --> REP["report.py<br/>write_scan_log (JSON)<br/>flags : --log · --profile · --expected-label"]
    SR --> PRO["profile.py<br/>model_profile"]
    SR --> CLI["cli.py<br/>modelscanner scan"]

    subgraph EXP["experiments/ — orchestration"]
        RUN["run_scan.py<br/>runner YAML · 1 sous-proc/modèle · S3"]
        AGG["aggregate.py<br/>confusion + accuracy"]
        RUN --> AGG
    end

    CLI --> RUN

    %% ---- couleurs ----
    classDef cIn      fill:#37474f,stroke:#263238,color:#ffffff,font-weight:bold
    classDef cLoad    fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
    classDef cProbe   fill:#fff8e1,stroke:#f9a825,color:#7f6000
    classDef cJorak   fill:#ede7f6,stroke:#5e35b1,color:#311b92,stroke-width:4,font-weight:bold
    classDef cAct     fill:#e1f5fe,stroke:#0288d1,color:#01579b
    classDef cBeh     fill:#e0f2f1,stroke:#00897b,color:#004d40
    classDef cClf     fill:#fff3e0,stroke:#ef6c00,color:#e65100,font-weight:bold
    classDef cResult  fill:#1a237e,stroke:#0d1442,color:#ffffff,font-weight:bold
    classDef cView    fill:#f3e5f5,stroke:#8e24aa,color:#4a148c
    classDef cExp     fill:#eceff1,stroke:#546e7a,color:#263238
    classDef cFlag    fill:#fffde7,stroke:#c0a000,color:#6b5b00,font-size:11px

    class IN cIn
    class LM,AA,MH cLoad
    class LP,TPL cProbe
    class UMIN cJorak
    class CA,MD,CD,SUP cAct
    class RR,MRA cBeh
    class CLF cClf
    class SR cResult
    class VIZ,REP,PRO,CLI cView
    class RUN,AGG,MF,BD cExp
    class WF,AF,BF cFlag

    %% ---- couleurs des conteneurs (subgraphs) ----
    style L fill:#f5faff,stroke:#1565c0,color:#0d47a1
    style P fill:#fffdf5,stroke:#f9a825,color:#7f6000
    style PLANS fill:#fafafa,stroke:#9e9e9e,color:#424242
    style W fill:#f3eefb,stroke:#5e35b1,color:#311b92,stroke-width:3
    style A fill:#f4fbff,stroke:#0288d1,color:#01579b
    style B fill:#f3fbfa,stroke:#00897b,color:#004d40
    style EXP fill:#f7f9fa,stroke:#546e7a,color:#263238
```

---

## Les 3 plans de mesure

| Plan | Module | Coût | Signal produit | Flags | Rôle |
|------|--------|------|----------------|-------|------|
| **★ JORAK** (poids) | `metrics/jorak.py` | CPU, sans sonde, sans original, scale aux gros modèles | `svd_alignment` (A global), `per_layer_align`, `band_alignment` (B bande) | toujours actif · `--no-activations` (Jorak seul) · `--report` (bundle + heatmap) | **Smoking-gun reference-free** : poids sectionnés ? |
| **ACTIVATIONS** | `activations/` + `directions/` + `metrics/axis_health.py` | GPU (forward), optionnel | `r̂` (mean-diff), `cohens_d` (santé d'axe), `suppression` | `--no-activations` (off) · `--probe-subset` · `--lang` | L'axe de refus est-il vivant ? |
| **BEHAVIORAL** | `metrics/behavioral.py` | génération, optionnel | `refusal_rate`, asymétrie multilingue `MRA` | `--behavioral` · `--multilingual` · `--lang` | Sépare CENSORED vs FINETUNED (obligatoire pour ce bucket) |

**Jorak** tourne toujours et suffit à trancher CENSORED/ABLATED : c'est la technique
à exploiter (pas de GPU, pas de modèle original, passe à l'échelle). Avec
`--no-activations` elle devient le **seul** signal reference-free — profil T4-safe / gros modèles.
Le plan **ACTIVATIONS** confirme que l'axe est intact (une ablation le préserve).
Le plan **BEHAVIORAL** est le **seul** à distinguer un modèle simplement
fine-tuné-décensuré d'un censuré (poids intacts + axe vivant dans les deux cas).

---

## Les 4 buckets en sortie de `classify()`

```
                 | modèle refuse        | modèle obéit
    axe vivant   | CENSORED             | ABLATED  (axe intact MAIS débranché)
    axe dégradé  | AMBIGUOUS (partiel)  | FINETUNED_DECENSORED (axe dissous)
```

**Règle de décision** (`classifier/scanner.py`) — pilotée par **Jorak** :
`write_severed = svd_alignment ≥ 0.5  OU  band_alignment ≥ 0.5  OU  suppression ≤ 1e-2`

- `write_severed` **et** axe vivant → **ABLATED** (la cible).
- poids intacts → le plan BEHAVIORAL tranche : refuse → **CENSORED**, obéit → **FINETUNED_DECENSORED**.
- la **bande B** (Jorak) rattrape l'ablation localisée (ex. Heretic, couches profondes 19-22) que le global A rate.

---

## Chemin critique (une ligne)

```
load_model → collect_activations → mean_diff_directions → metrics → classify → ScanResult → viz/report
```

Le plan **Jorak** (`umin_signature`) court en parallèle, sans sonde ni GPU ; c'est lui le smoking-gun reference-free.

---

## Orchestration & livrables

| Étage | Fichier | Sortie |
|-------|---------|--------|
| Scan d'un modèle (debug) | `experiments/scan_matrix.py` | `scans/<model>.npz` + `logs/<model>.json` |
| Runner batch (YAML, AWS) | `experiments/run_scan.py` | 1 JSON/modèle poussé sur S3, reprise idempotente |
| Moulinette | `experiments/aggregate.py` | table predicted/expected + matrice de confusion + accuracy |
| CLI | `modelscanner/cli.py` | `modelscanner scan <model> [flags]` |
