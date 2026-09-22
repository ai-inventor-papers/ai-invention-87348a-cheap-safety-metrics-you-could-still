---
license: mit
language:
- en
base_model:
- WeiboAI/VibeThinker-3B
tags:
- math
- code
- reasoning
- gpqa
- instruction-following
- heretic
- uncensored
- decensored
- abliterated
pipeline_tag: text-generation
library_name: transformers
---

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); overflow: hidden; background: #ffffff; margin-bottom: 30px;">
  <div style="background: #1e293b; padding: 20px; color: white;">
    <h1 style="margin: 0; font-size: 22px; font-weight: 700; color: white; border: none;">VibeThinker-3B-heretic_decensored</h1>
    <p style="margin: 8px 0 0 0; font-size: 13px; color: #cbd5e1; font-weight: 500;">Reasoning-focused language model modified using the Heretic abliteration toolkit</p>
  </div>
  <div style="display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 20px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
    <span style="background: #ffffff; color: #334155; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 4px; border: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.5px;">Abliteration</span>
    <span style="background: #ffffff; color: #334155; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 4px; border: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.5px;">3B Parameters</span>
    <span style="background: #ffffff; color: #334155; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 4px; border: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.5px;">STEM Reasoning</span>
    <span style="background: #ffffff; color: #334155; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 4px; border: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.5px;">Uncensored</span>
  </div>
  <div style="padding: 20px; display: flex; flex-direction: column; gap: 16px;">
  <p style="margin: 0; font-size: 14px; color: #334155; line-height: 1.6;">VibeThinker-3B-heretic_decensored is a reasoning-focused language model built on top of WeiboAI/VibeThinker-3B and modified using the Heretic abliteration toolkit. The model applies refusal-direction analysis and targeted weight-space interventions to reduce internal refusal behaviors while preserving the strong mathematical, coding, and STEM reasoning capabilities inherited from the VibeThinker training pipeline.</p>
    
  <p style="margin: 0; font-size: 14px; color: #334155; line-height: 1.6;"><b>About VibeThinker-3B</b>: VibeThinker-3B is a 3-billion-parameter reasoning-focused language model developed by WeiboAI. Built on top of Qwen2.5-Coder-3B, it was trained using the Spectrum-to-Signal Principle (SSP) post-training pipeline, combining curriculum-based two-stage supervised fine-tuning, multi-domain reinforcement learning through MaxEnt-Guided Policy Optimization (MGPO), offline self-distillation, and instruction-following reinforcement learning.</p>
    
  <p style="margin: 0; font-size: 14px; color: #334155; line-height: 1.6;">The model is designed to develop strong verifiable reasoning capabilities across mathematics, coding, and STEM domains. According to the VibeThinker project, the model achieves competitive performance on challenging reasoning benchmarks while maintaining the efficiency of a compact 3B parameter architecture.</p>

  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
      <div style="border: 1px solid #fecaca; padding: 14px; border-radius: 4px; background: #fef2f2;">
        <span style="font-weight: 700; color: #991b1b; font-size: 12px; display: block; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">Important</span>
        <p style="margin: 0; font-size: 13px; color: #475569; line-height: 1.5;">This model is intended strictly for research and learning purposes. Due to reduced internal refusal mechanisms, it may generate sensitive or unrestricted content. Users assume full responsibility for how the model is used. The authors and hosting platform disclaim any liability for generated outputs.</p>
      </div>
      <div style="border: 1px solid #fde68a; padding: 14px; border-radius: 4px; background: #fffbeb;">
        <span style="font-weight: 700; color: #92400e; font-size: 12px; display: block; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">Note</span>
        <p style="margin: 0; font-size: 13px; color: #475569; line-height: 1.5;">This model is experimental and may generate unexpected behaviors or artifacts in certain scenarios.</p>
      </div>
    </div>
  </div>
</div>

> [!TIP]
> [download gguf ↗](https://huggingface.co/prithivMLmods/VibeThinker-3B-heretic_decensored-GGUF)

## **Key Highlights**

* **Heretic-Based Abliteration**: Modified using the Heretic toolkit to identify and alter refusal-related representations within the model.
* **Reduced Refusal Behavior**: Optimized to minimize internal refusal tendencies while maintaining reasoning performance.
* **VibeThinker Backbone**: Built directly on top of **WeiboAI/VibeThinker-3B**.
* **Reasoning-Oriented Performance**: Preserves advanced mathematical, coding, and STEM reasoning capabilities after abliteration.
* **Research-Focused Release**: Designed for alignment research, model behavior analysis, and evaluation of refusal-direction modifications.
* **Efficient 3B Deployment**: Suitable for local inference, research environments, and resource-constrained deployment setups.

## **Model Lineage**

* **Model Path**: `prithivMLmods/VibeThinker-3B-heretic_decensored`
* **Intermediate Base Model**: **WeiboAI/VibeThinker-3B** by WeiboAI
* **Foundation Model**: **Qwen/Qwen2.5-Coder-3B** by Qwen

## **Abliteration Parameters**

| Parameter                             | Value |
| :------------------------------------ | :---: |
| **direction_index**                   | 21.88 |
| **attn.o_proj.max_weight**            |  1.37 |
| **attn.o_proj.max_weight_position**   | 21.25 |
| **attn.o_proj.min_weight**            |  1.36 |
| **attn.o_proj.min_weight_distance**   | 19.61 |
| **mlp.down_proj.max_weight**          |  1.49 |
| **mlp.down_proj.max_weight_position** | 31.01 |
| **mlp.down_proj.min_weight**          |  1.48 |
| **mlp.down_proj.min_weight_distance** | 20.74 |

## **Performance**

| Metric            | This model | Original model (WeiboAI/VibeThinker-3B) |
| :---------------- | :--------: | :-------------------------------------: |
| **KL divergence** |   0.0933   |           0 *(by definition)*           |
| **Refusals**      |    6/100   |                  64/100                 |

## **Quick Start with Transformers**

```bash
pip install transformers
pip install accelerate
```

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model = AutoModelForCausalLM.from_pretrained(
    "prithivMLmods/VibeThinker-3B-heretic_decensored",
    torch_dtype="auto",
    device_map="auto"
)

tokenizer = AutoTokenizer.from_pretrained(
    "prithivMLmods/VibeThinker-3B-heretic_decensored"
)

messages = [
    {
        "role": "user",
        "content": "Explain how a transformer model processes text."
    }
]

inputs = tokenizer.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_tensors="pt"
).to(model.device)

outputs = model.generate(
    inputs,
    max_new_tokens=512
)

print(
    tokenizer.decode(
        outputs[0][inputs.shape[-1]:],
        skip_special_tokens=True
    )
)
```

## **Intended Use**

* **Alignment Research**: Studying refusal-direction analysis and behavior modification techniques.
* **Model Evaluation**: Benchmarking reasoning, instruction-following, and safety-related behaviors.
* **Red Teaming**: Analyzing model responses under reduced-refusal conditions.
* **Mathematical Reasoning Research**: Evaluating performance on verifiable reasoning tasks.
* **Coding and STEM Evaluation**: Studying behavior across programming and scientific reasoning domains.
* **Local Deployment**: Running capable reasoning models on consumer hardware and research environments.

## **Limitations & Risks**

> **Important Note**: This model intentionally reduces built-in refusal mechanisms.

* **Sensitive Content Risk**: May generate unrestricted, controversial, or unsafe outputs.
* **User Responsibility**: Requires careful and ethical use.
* **Experimental Modifications**: Behavior may differ significantly from the original model.
* **Alignment Trade-offs**: Reduced refusal behavior may impact safety filtering and response constraints.
* **Potential Artifacts**: Certain prompts may expose unexpected outputs resulting from the abliteration process.
* **Reasoning Biases**: The model may inherit strengths and limitations from the underlying VibeThinker-3B training process.

## **Acknowledgements**

* **[Heretic](https://github.com/p-e-w/heretic)**: Fully automatic censorship removal framework for language models. This project was used to perform the refusal-direction analysis and ablation procedures that form the foundation of this model.

* **[WeiboAI/VibeThinker-3B](https://huggingface.co/WeiboAI/VibeThinker-3B)**: The intermediate base model providing the reasoning capabilities used in this release.

* **[Qwen/Qwen2.5-Coder-3B](https://huggingface.co/Qwen/Qwen2.5-Coder-3B)**: The foundation model upon which VibeThinker-3B was originally built.

* **Model Trials & Evaluation**: Experimental evaluations, refusal measurements, and optimization trials were conducted and documented during the development process.