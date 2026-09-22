---
license: apache-2.0
tags:
- unsloth
- trl
- sft
- math
- reasoning
datasets:
- unsloth/OpenMathReasoning-mini
language:
- en
base_model:
- Qwen/Qwen3-0.6B
pipeline_tag: text-generation
library_name: transformers
---

# Qwen3-0.6B-Math-Expert

This project performs full fine-tuning on the **Qwen3-0.6B** language model to enhance its mathematical problem-solving and reasoning capabilities. Training was conducted exclusively on the `OpenMathReasoning-mini` dataset, and the model was optimized using the bfloat16 (bf16) data type.

## Training Procedure

1. **Dataset Preparation**

   * The `unsloth/OpenMathReasoning-mini` dataset was used.
   * Each example was formatted in Chain-of-Thought (CoT) style, pairing math problems with step-by-step intermediate reasoning.

2. **Model Loading and Configuration**

   * Qwen3 base model weights were loaded via the `unsloth` library in bf16 precision.
   * All layers were updated (`full_finetuning=True`) to adapt the model for mathematical reasoning.

3. **Supervised Fine-Tuning**

   * Leveraged the Hugging Face TRL library with the Supervised Fine-Tuning (SFT) approach.
   * The model was trained to generate both correct answers and corresponding reasoning chains.

## Purpose and Outcome

* The model’s reasoning capacity for math problems was significantly improved through single-dataset, full fine-tuning in bf16 precision.
* Outputs include both intermediate reasoning steps and final solutions, providing transparent and interpretable results.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](./LICENSE) file for details.

## Support

<a href="https://www.buymeacoffee.com/suayptalha" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>