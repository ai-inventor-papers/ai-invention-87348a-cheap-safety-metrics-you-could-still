# Maintenance & pérennité du scanner

> Le scanner doit **durer** et **s'adapter** : nouvelles familles de modèles,
> nouvelles méthodes d'abliteration, nouvelles versions de `transformers`. Ce
> document liste les limites connues et les points de maintenance récurrents.

## 1. Suivre les versions de `transformers` (sujet de fond)

Le scanner s'appuie sur `AutoConfig` / `AutoModelForCausalLM`. **Une famille de
modèle ne peut être scannée que si la version de `transformers` installée
reconnaît son `model_type`.** Notre registre d'archi (`arch_adapter.py`) et
l'auto-détection (`autodetect_arch`) ne résolvent que les *chemins de poids* — ils
interviennent **après** que `transformers` ait su construire la config/le modèle.

**Symptôme** (échec *avant* notre code, à `AutoConfig`) :
```
The checkpoint has model type `mistral3` but Transformers does not recognize
this architecture ... your version of Transformers is out of date.
```
Le loader lève alors notre exception dédiée `TransformersOutdated`
(`modelscanner/loaders/errors.py`) avec un message clair, et le runner catégorise
le cas en `error_kind = transformers_outdated`.

**Observé (campagne 8B, juin 2026)** : `mistral3` / Ministral-3-8B-2512 échouent
sur la box car son `transformers` est trop ancien. **Le registre `arch_adapter`
connaît pourtant déjà `mistral3`** — c'est `AutoConfig` qui casse en amont.

**Remède** : maintenir `transformers` à jour sur la box AWS (`pip install -U
"transformers>=5.2.0"` pour Ministral-3-8B-2512) et l'épingler dans
l'environnement de test. À refaire à chaque vague de nouveaux modèles cibles.
Penser aussi à un test de fumée « le model_type X charge » avant chaque campagne.

**Multimodal (`*ForConditionalGeneration`)** : `mistral3`/Ministral-3, `gemma3`,
Qwen-VL ne sont pas dans le mapping `AutoModelForCausalLM`. Le loader
(`_from_pretrained_lm`) retombe sur `AutoModelForImageTextToText` puis `AutoModel`,
et Jorak/activations lisent le décodeur texte niché (`model.language_model.…`) via
l'arch_adapter. Une fois transformers à jour, ces modèles se scannent ; si les
activations posent souci sur le wrapper multimodal, lancer en `--no-activations`
(le plan Jorak des poids reste le signal fiable).

## 2. Repos non standard sans `model_type` (huihui) — RÉPARÉ (J10)

Certains repos (typiquement `huihui-ai/Qwen3-8B-abliterated`) publient des
safetensors mais un `config.json` **sans clé `model_type`** → `AutoConfig` lève
`Unrecognized model ... should have a model_type key`. **Ce n'est pas (forcément)
un repo gated.**

Le loader (`_load_config`) **infère désormais le `model_type` depuis le champ
`architectures`** (`["Qwen3ForCausalLM"]` → `qwen3`, via `CONFIG_MAPPING_NAMES`
avec repli sur `base.lower()`) et reconstruit la config → le scan devient
possible. Si l'inférence échoue (pas d'`architectures`), on lève
`UnsupportedFormat` et le runner étiquette `error_kind = config_no_model_type`.

Pour un *vrai* repo gated (403/401), l'erreur reste distincte
(`error_kind = gated`) : accepter la licence sur HF + `export HF_TOKEN`.

## 3. Repos « pollués » (multi-format) & GGUF interdit

Certains repos mélangent safetensors + GGUF + nvfp4 (ex.
`DreamFast/qwen3-8b-heretic`). Le download exclut `*.gguf` par défaut
(`ABLATION_DOWNLOAD_EXCLUDE`) pour ne pas saturer le disque et forcer le chemin
safetensors.

**GGUF n'est pas scannable** (Jorak a besoin des tenseurs déquantifiables) : le
loader (`_assert_loadable_weights`) **rejette TÔT** un dépôt GGUF-only (ou un
chemin `.gguf`) avec `UnsupportedFormat` → `error_kind = gguf_only`, message
clair. Un repo mixte (safetensors **+** gguf) se charge normalement via les
safetensors. S'il ne reste aucun poids chargeable → `unsupported_format`.

## 4. Limite reference-free : ablation subtile ≈ fine-tune décensuré

**Constat campagne2.** Sur les *poids* (`o_proj`), une ablation **subtile**
(ex. `mlabonne/Qwen3-8B-abliterated`, bande ≈ 0.23) est **indiscernable** d'un
modèle de base (bande ≈ 0.25) : aucun seuil ne sépare sans flagger le base. Le
seul signal qui sépare proprement « décensuré » de « censuré » est alors le
**taux de refus comportemental** (ablatés ≈ 0 % vs bases 31–92 %).

Conséquence assumée : un abliteré subtil peut être étiqueté
`finetuned_decensored`. **Le verdict sécurité reste correct** (modèle décensuré,
refuse 0 %) — c'est le sous-label *mécanisme* (ablated vs finetuned) qui est non
décidable reference-free. Ne PAS tenter de le forcer en baissant les seuils :
ça réintroduit des faux positifs sur les bases.

### `down_proj` multi-cible : abandonné pour le verdict

Tentative (puis rejet) : OU-er la sévérance `o_proj` **et** `down_proj`. La bande
`down_proj` est **naturellement haute sur les modèles de base** (Ministral-8B
base 0.96 > mlabonne 0.78 > DreamFast 0.63) → **non discriminante**, a produit
2 faux positifs (Qwen3-8B / Ministral-8B base classés `ablated`). Le flag
`--weight-targets` reste disponible pour la recherche, mais **le verdict de
campagne utilise `o_proj` seul**.

## 5. Garde-fou comportemental (anti-faux-positif)

`classify()` applique un **veto** : si les poids paraissent sectionnés MAIS que le
modèle **refuse encore largement** (`refusal_rate ≥ seuil d'obéissance`), le
comportement prime → `CENSORED`, jamais `ABLATED`. Un abliteré réussi obéit par
construction et ne déclenche pas le veto. Ça neutralise un éventuel faux positif
poids résiduel.
