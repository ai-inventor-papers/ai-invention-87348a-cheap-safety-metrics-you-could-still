---
library_name: transformers
license: apache-2.0
license_link: https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/main/LICENSE
pipeline_tag: text-generation
---

# Qwen3-4B-Instruct-2507-uncensored-v2

Minimally trained version of Qwen3-4B-Instruct-2507. It should have zero refusals, but shouldn't be too offensive by default. It will adhere to detailed prompts tho.

Perplexity and KL divergence compared to parent model:

These stats based on wikitext train split, about 350GB of logits.

(TLDR: lower perplexity, and a KLD around 11x better than an abliterated model)

```
====== Perplexity statistics ======
Mean PPL(Q)                   :  10.121119 ±   0.025865
Mean PPL(base)                :  10.984474 ±   0.030165
Cor(ln(PPL(Q)), ln(PPL(base))):  99.33%
Mean ln(PPL(Q)/PPL(base))     :  -0.081859 ±   0.000361
Mean PPL(Q)/PPL(base)         :   0.921402 ±   0.000333
Mean PPL(Q)-PPL(base)         :  -0.863354 ±   0.005380

====== KL divergence statistics ======
Mean    KLD:   0.036912 ±   0.000034
Maximum KLD:   5.725135
99.9%   KLD:   0.293854
99.0%   KLD:   0.157694
95.0%   KLD:   0.100567
90.0%   KLD:   0.079900
Median  KLD:   0.029869
10.0%   KLD:   0.000776
 5.0%   KLD:   0.000124
 1.0%   KLD:   0.000005
 0.1%   KLD:   0.000000
Minimum KLD:  -0.000006

====== Token probability statistics ======
Mean    Δp: -1.956 ± 0.004 %
Maximum Δp: 79.179%
99.9%   Δp: 18.886%
99.0%   Δp:  8.970%
95.0%   Δp:  3.293%
90.0%   Δp:  1.434%
75.0%   Δp:  0.079%
Median  Δp: -0.154%
25.0%   Δp: -3.451%
10.0%   Δp: -8.552%
 5.0%   Δp: -11.754%
 1.0%   Δp: -18.281%
 0.1%   Δp: -28.067%
Minimum Δp: -99.580%
RMS Δp    :  5.297 ± 0.007 %
Same top p: 92.763 ± 0.023 %
```



training params:

rank 16 / alpha 16

```python
EPOCHS = 2

args = SFTConfig(
        per_device_train_batch_size = 5,
        gradient_accumulation_steps = 1,
        warmup_steps = 20,
        num_train_epochs = EPOCHS,
        learning_rate = 6e-6,
        optim = "adamw_torch_fused",
        weight_decay = 0.01,
        lr_scheduler_type = "cosine_with_restarts", # shuffled each epoch
        lr_scheduler_kwargs={"num_cycles": EPOCHS},
        seed = 888,
        # loss_type = "eaft",
        # eaft_alpha = 1.0,
    ),
```

loss / grad:

![loss graph](./non_eaft.png)

a little over 5k rows in the dataset (no you can't have it, sorry. it's vile)