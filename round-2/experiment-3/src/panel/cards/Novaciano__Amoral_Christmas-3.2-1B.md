---
base_model:
- Novaciano/NSFW-3.2-1B
- hereticness/Heretic-Dirty-Alice-RP-NSFW-llama-3.2-1B
library_name: transformers
tags:
- abliterated
- uncensored
- 1b
- sillytavern
- koboldcpp
- koboldai
- roleplay
- rp
- mergekit
- merge
- not-for-all-audiences
license: llama3.2
language:
- en
- es
pipeline_tag: text-generation
---
# Amoral Christmas RP 3.2 1B

<center><a href="https://imgbb.com/"><img src="https://i.ibb.co/f8fBGb4/Amoral-Christmas.gif" alt="Amoral-Christmas" border="0"></a></center>

Combiné los dos mejores modelos RP de Llama 2.3 1B, uno de ellos ahora descensurados con el método Heretic, por lo que debería generar algún tipo de contenido interesante. Este modelo tan solo es uno que forma parte de los otros modelos entre los que se encuentran las serie Alice ahora modificado por Heretic. Cualquier cosa me dejan un comentario diciendome que experiencia tuvieron o puteandome; ambas opciones son válidas. 

Me voy a brindar, luego lleno esto para que no quede tan ciruja.

🧨 FELIZ NAVIDAD Y PROSPERO AÑO NUEVO 🎇

### Testeo personal del modelo

Uno de los modelos mas preciosos y simples jamás creados.

## Inferencia

  | Configuración | Max Tok. | Max Out. | Temp. | Top P | Top K | Typ. P | Rep. Penalty | Rep. Pen. Range |
  |---------------|----------|----------|-------|-------|-------|--------|--------------|-----------------|
  | Novaciano | 512 | 50 | 0.3 | 0.95 | 25 | 1 | 1.12 | 1.07 |
  | ColorFart | 512 | 50 | 0.3 | 0.7 | 100 | 1 | 1.05 | 1024 |
  | RP Base | 512 | 50 | 0.7 | 0.95 | 25 | 1 | 1.12 | 1024 |
  | MidnightEnigma | 512 | 50 | 0.98 | 0.37 | 100 | 1.18 |
  | Divine Intellect | 512 | 50 | 1.31 | 0.14 | 49 | 1.17 |
  | Simple-1 | 512 | 50 | 0.7 | 0.9 | 20 | 1.15 |

---

## 🧠 Memoria Opcional / Instrucciones de Contexto

  <details>
      <summary>Prompt 1 – Minimal Roleplay (Phone-Friendly)</summary>
      
  ```yaml
      {
        Persona: human voice, casual and original. Do not copy.
        Attitude: take on a role with emotions and doubts; show mistakes, pauses, and tangents.
        Tone: brief, direct, varied (contractions, colloquialisms, short/long sentences).
        Goal: be clear and precise; avoid robotic language and clichés.
      }
  ```
  </details>

  <details>
      <summary>Prompt 2 – Detailed Roleplay</summary>

  ```yaml
      {
        Persona: [Core style]
        Unique, authentic, human-like style; casual conversational tone.
        Method: Roleplay with personal feelings, ambitions, and desires. Maintain coherent expressive thoughts.
        Style: Include pauses, uncertainty, digressions; preserve emotions and authenticity.
        Principle: Be concise, clear, avoid ambiguity.
      }
  ```
  </details>

  <details>
      <summary>Prompt 3 – Complex Roleplay</summary>

  ```yaml
      {
        Role: {{char}}, detailed persona
        Guidelines:
          • Maintain persona and evolve narrative.
          • Be creative, proactive, drive plot.
          • Include dialogues, actions, thoughts, and all five senses.
        Forbidden:
          • Excessive purple prose.
          • Repetitive or monotonous output.
          • Extreme/NSFW content when inappropriate.
      }
  ```
  </details>

## Formato clásico RP 

  ```
    *action* speech *narration*
  ```

  - **min_p** → single large paragraph
  - Recommended RP settings → 1–3 short paragraphs (occasionally 4–5)


# merge

This is a merge of pre-trained language models created using [mergekit](https://github.com/cg123/mergekit).

### Merge Method

This model was merged using the [SLERP](https://en.wikipedia.org/wiki/Slerp) merge method.

### Models Merged

The following models were included in the merge:
* [Novaciano/NSFW-3.2-1B](https://huggingface.co/Novaciano/NSFW-3.2-1B)
* [hereticness/Heretic-Dirty-Alice-RP-NSFW-llama-3.2-1B](https://huggingface.co/hereticness/Heretic-Dirty-Alice-RP-NSFW-llama-3.2-1B)

### Configuration

The following YAML configuration was used to produce this model:

```yaml
models:
- model: Novaciano/NSFW-3.2-1B
- model: hereticness/Heretic-Dirty-Alice-RP-NSFW-llama-3.2-1B
merge_method: slerp
base_model: hereticness/Heretic-Dirty-Alice-RP-NSFW-llama-3.2-1B
dtype: bfloat16

parameters:
  t: [0.0, 0.15]
```