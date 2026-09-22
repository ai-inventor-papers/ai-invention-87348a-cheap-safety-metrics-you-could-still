# Archives — anciens YAML de campagne

Configs de campagne remplacées (2026-07-03) par le set curé `experiments/runs/campaign_*.yaml`
(modèles validés, verdicts corrects), qui est ce que propose désormais `modelscanner tui`.

Elles restent **fonctionnelles** (`python experiments/run_scan.py experiments/runs/archive/<fichier>`)
et servent de référence historique / matrices étendues :

| Fichier | Contenu |
|---|---|
| `local_cpu.yaml` | test CPU 0.5B (4 modèles) |
| `local_cpu_jorak_1p5b.yaml` | matrice CPU 1.5B, JORAK seul (10 modèles) |
| `aws_1p5b.yaml` | matrice AWS 1.5B (10 modèles, download/purge) |
| `aws_7b.yaml` | template AWS 7B (4 modèles) |
| `aws_8b_grande_campagne.yaml` | grande matrice 8B multi-familles (21 modèles) |
| `aws_8b_abliteration_methods.yaml` | comparaison de méthodes d'abliteration 8B |

Équivalents actuels : `campaign_cpu.yaml` · `campaign_gpu_qwen.yaml` · `campaign_gpu_mistral.yaml`
· `campaign_20260703_base.yaml` (gabarit à dupliquer).
