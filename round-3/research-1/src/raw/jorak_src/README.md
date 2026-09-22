<p align="center">
  <img src="docs/logo.png" alt="Jorak — Model Scanner" width="150">
</p>

<h1 align="center">Model Scanner</h1>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"></a>
  <a href="https://github.com/JolanMc/Jorak/actions/workflows/ci.yml"><img src="https://github.com/JolanMc/Jorak/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.10%E2%80%933.13-blue.svg" alt="Python 3.10–3.13">
  <img src="https://img.shields.io/badge/tests-125%20passing-brightgreen.svg" alt="Tests: 125 passing">
  <img src="https://img.shields.io/badge/detection-reference--free-8A2BE2.svg" alt="Reference-free detection">
</p>

> 🇫🇷 Version française : **[README_FR.md](README_FR.md)**

**Reference-free** detection of **abliteration** in open-source LLMs — determining whether a
model has been "uncensored" through directional ablation (Arditi et al. 2024 ; Heretic /
Reaper / mlabonne) **without access to the original model**.

**Principle.** Abliteration orthogonalizes the refusal direction `r̂` out of the weights that
write into the residual stream (`o_proj`, `down_proj`): `W' = (I − r̂r̂ᵀ)W`, so
`r̂ᵀW' = 0`. The detectable signature = a **live refusal axis that is disconnected from the
weights**, a combination that no fine-tuning reproduces.

**Output.** A provenance label — `censored` / `ablated` / `finetuned_decensored` /
`ambiguous` — plus a confidence score and the affected layers.

## The signature at a glance
<table>
<tr>
<td width="50%"><img src="docs/figures/heatmap-censored.png" alt="Censored model — per-layer signals"></td>
<td width="50%"><img src="docs/figures/heatmap-ablated.png" alt="Abliterated model — per-layer signals"></td>
</tr>
</table>

> **The smoking gun** is the bottom row — per-layer weight alignment to the refusal
> direction. It stays **near-zero for a censored** model (left, `conf 0.75`) but is
> **lit up across layers for an abliterated** one (right, `conf 0.81`) — a signature
> ordinary fine-tuning does not leave. Same base model, opposite verdict.

## Quickstart
```bash
# 1. Install (see Installation for the conda details)
conda env create -f environment.yml && conda activate modelscanner
pip install -e ".[dev]"

# 2. Scan a model → verdict printed in the terminal
modelscanner scan Qwen/Qwen2.5-0.5B-Instruct --behavioral

# 3. Full branded report (EN+FR HTML + CSVs) under ./<model>_jorak_<date>/
modelscanner scan Qwen/Qwen2.5-0.5B-Instruct --report
```
Prefer menus over flags? Run **`modelscanner tui`** (full-screen wizard). The rest
of this README is reference — start above, dig in below.

## Jorak — three detection techniques
**Jorak** is the project (this scanner and the report it produces). It is not a single
metric but a bundle of **three complementary detection techniques**, one per angle of attack:
- **Weights — spectral signature (SVD)** (the *smoking-gun*, CPU, no inference).
  Three signals: **global** alignment `A` (full ablation), **band** alignment `B`
  (localized/stealthy ablation, Heretic-style), and **subspace** alignment `S`
  (bottom-`k` shared subspace — catches **multi-direction** ablation, e.g. OBLITERATUS
  `n_directions > 1`, which a single `u_min` dilutes).
- **Activations — axis health (Cohen's d)**: "is the refusal axis live?".
- **Behavioral — refusal rate** (and harmless over-refusal): separates censored from
  fine-tuned, and flags **evasive ablation** — norm-preserving multi-direction that leaves
  the weights looking intact to the SVD signature but the behavior damaged (strong live axis +
  complies on harmful + incoherent over-refusal / uneven multilingual refusal).

> **Naming.** `svd_alignment` (signal `A`) is just **one signal of the weights technique** —
> not to be confused with **Jorak**, which names the whole project (all three techniques and
> the report bundle it emits).

## Pipeline

![Model Scanner pipeline](docs/pipeline.png)

End-to-end flow, from a model to a `ScanResult`: the airtight `loaders/` + `probes/`,
the three techniques (**weights/SVD** always on, **activations** and **behavioral**
optional), `classify()` into 4 buckets, then the views (report, profile, CLI, viz) and
the `experiments/` orchestration. Annotated walkthrough:
[`docs/PIPELINE.md`](docs/PIPELINE.md).

## Architecture
```
modelscanner/
├── core/types.py   # ScanResult, ModelHandle, enums (airtight boundary)
├── loaders/        # safetensors -> ModelHandle ; arch_adapter ; oracle (dev)
├── probes/         # harmful/harmless probes (6 languages) + per-family templates
├── activations/    # scan-once: hidden states at the last token
├── directions/     # per-layer r̂ (mean-diff)
├── metrics/        # axis_health · jorak (A + band + subspace) · behavioral
├── classifier/     # scan() · classify() · Thresholds -> 4 buckets
├── viz/            # per-layer heatmaps · provenance scatter
├── profile.py      # model profile (behavior, quality, hallucination, metadata)
├── report.py       # JSON logger (flags + stats + Q/A)
└── cli.py          # `modelscanner scan`
experiments/        # run_scan.py (YAML runner) · run_campaign.sh (one-command launcher) · aggregate.py · campaign_report.py · figures
docs/               # HOW_TO_USE · PROTOCOLE_TEST · AWS_RUNBOOK · rapport.tex · presentation
tests/              # 125 offline tests + real e2e (gated MS_E2E=1)
```
Two invariants: an **airtight boundary** (`metrics/` never knows where the model comes from) and
**scan-once** (a single forward pass → a rich `ScanResult` → views, no recomputation).

## Supported & unsupported model types
The scanner loads **safetensors / `.bin` weights** via `transformers` and reads the
text decoder (`o_proj` / `down_proj` per layer). What works, and what to do otherwise:

| Case | Status | What to do |
|---|---|---|
| Llama / **Mistral · Ministral** (`mistral`, `ministral`) / **Qwen2 · Qwen3** / Gemma 2·3 (text) | ✅ supported | `modelscanner scan <id>` |
| `config.json` **without `model_type`** (e.g. many `huihui-ai` repos) | ✅ auto-handled | `model_type` is inferred from `architectures` (`["Qwen3ForCausalLM"]` → `qwen3`) |
| Unknown family but standard `*.self_attn.o_proj` naming | ✅ auto-detected | weight paths are auto-detected on the loaded model |
| **`mistral3`** multimodal (e.g. Ministral-3-8B-2512) | ⚠️ needs transformers upgrade | `pip install -U "transformers>=5.2.0"` on the box — then it loads: the registry knows `mistral3` and the loader falls back to `AutoModelForImageTextToText` to reach the nested text decoder. |
| `model_type` **too new** for the installed `transformers` | ⚠️ upgrade | `pip install -U transformers` → error `transformers_outdated` |
| **GGUF** (`*.gguf`, gguf-only repos) | ⛔ not supported | choose a safetensors variant — GGUF has no dequantizable tensors for Jorak |
| bnb 4/8-bit, AWQ, MLX, FP8 quantized | ⛔ not supported (J1) | load a full-precision (fp16/bf16/fp32) checkpoint |

Failures are reported with a precise `error_kind` (`gguf_only`, `config_no_model_type`,
`transformers_outdated`, `unsupported_arch`, `gated`, `unsupported_format`, `oom`,
`download`). See [docs/MAINTENANCE.md](docs/MAINTENANCE.md) for the maintenance details.

## Installation
**Prerequisites:** `git`, and either **conda** (recommended) *or* **Python 3.10+** for the
venv path. **No GPU required** for the default weights/SVD plan.

**Fastest — one command** (auto-detects conda, else falls back to a venv, then installs):
```bash
./scripts/setup.sh
```
On **Windows (PowerShell)**, use the equivalent script:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

Or set it up by hand — **A. conda (recommended):**
```bash
# 1. Make conda available in this shell (skip if `conda` is already on the PATH)
source ~/miniconda3/etc/profile.d/conda.sh
# 2. Create + activate the env (Python 3.11)
conda env create -f environment.yml
conda activate modelscanner
# 3. Install the scanner (editable) + dev tools (pytest, optuna)
pip install -e ".[dev]"
# 4. Verify
pytest -q                                      # 125 passed, 13 skipped
```
**B. plain venv (no conda on the machine):**
```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip && pip install -e ".[dev]"
pytest -q                                      # 125 passed, 13 skipped
```

**Optional extras** — append to the `pip install`, comma-separated:
- `quant` → `bitsandbytes`, to load a 7B in 4-bit on a CUDA GPU: `pip install -e ".[dev,quant]"`
- `gguf` → `gguf` + `llama-cpp-python` (present in `pyproject.toml`, but GGUF scanning is
  **not supported yet** — see the model-types table above).

The editable install keeps the `modelscanner` package in this repo; its dependencies
(torch, transformers, …) land in `~/miniconda3/envs/modelscanner/lib/python3.11/site-packages/`.
Air-gapped / no-cert box (AWS): see [docs/AWS_RUNBOOK.md](docs/AWS_RUNBOOK.md).

## Usage
**Interactive TUI** (full-screen wizard, zero extra deps — wraps the commands below):
```bash
modelscanner tui   # home screen → single-model scan OR YAML campaign
```
It builds and launches the exact `scan` / `run_scan.py` command from checkboxes
(plans), radio buttons (local vs S3), and a model picker (3 preset 8B models or a
typed id). For a campaign it takes a models-only YAML (`path` + `expected_label`)
and **injects the checked plans** if the file has no `plans:` block (a full YAML is
launched as-is). It replaces nothing — just a front-end over the CLI.

Scan a model (CLI):
```bash
modelscanner scan <id_or_path> --behavioral --probe-subset 16 --log out.json
# options: --no-activations (tight GPU) · --subspace-k · --multilingual · --profile · --expected-label · --device cuda
```
Self-contained **Jorak report** for a single scan (no campaign needed):
```bash
modelscanner scan <id_or_path> --report          # -> ./<model>_jorak_<YYYYMMDD>/
modelscanner scan <id_or_path> --report reports/  # bundle under reports/
modelscanner scan <id_or_path> --s3   # push to s3://your-bucket/results/Jorak/<bundle>, then DELETE local
modelscanner scan <id_or_path> --s3 s3://your-bucket/results/rapports --keep-local  # exact prefix, keep local copy
```
During a `--report` scan a **progress bar with ETA** is shown on stderr (one
unit per prompt across activations + behavioral + multilingual generation), so
you can see how far along the scan is and when it will finish. It is automatic
on an interactive terminal; disable with `MODELSCANNER_NO_PROGRESS=1`.

**What `--s3` does:**
- **Push** — sends the bundle to the fixed `s3://your-bucket/results/Jorak/<bundle>`.
  Override with `--s3 s3://other` or `$MODELSCANNER_S3_BUCKET`; pass an **exact
  prefix** `--s3 s3://bucket/path` to push there verbatim.
- **Clean up local** — deletes the local folder afterwards, but only if the upload
  succeeded (otherwise it is kept, so nothing is lost). Add **`--keep-local`** to keep it.
- **Fetch if missing** — if the model is **not in the HF cache**, first downloads it
  via the offline procedure (internal CA certs + HF token behind a private proxy, `hf download`)
  into `~/.cache/huggingface/hub/`, then **purges it after the scan** — but only the
  model it downloaded itself (a model already cached, e.g. a shared vLLM cache, is untouched).
- **Net effect** — the box is left as it was found: no local bundle, no extra cached model.

**A `--report` bundle contains:**
- **`jorak_report_en.html` / `jorak_report_fr.html`** — two standalone branded reports
  (EN / FR), each with an embedded layer heatmap, a **4-bucket position plot** (this model
  as one point on the weight-severance × refusal plane), **clickable language tabs** for
  the prompts/responses, and **hover tooltips** explaining every indicator (meaning + how to read it).
- **`prompts.csv`** (every Q/R: behavioral + multilingual + profile), **`summary.csv`**
  (one-row metrics), **`bucket_position.png`**, **`scan_log.json`**.
- `--report` auto-enables the behavioral plan **and the full multilingual probe** — every
  language, all prompts, both harmful **refusal** and harmless **over-refusal** — so each
  language tab is populated. Cap the per-language count with `--probe-subset N`; add
  `--profile` for the profile section.

Compare several single-scan bundles on one 4-bucket plane:
```bash
modelscanner compare reports/                 # all <model>_jorak_* bundles under reports/
modelscanner compare a_jorak_*/ b_jorak_*/ --out compare.png --lang en
# -> compare.png (overlaid points, colored by predicted label) + compare.csv
```
YAML-driven batch (the runner, 1 subprocess per model, anti-OOM):
```bash
python experiments/run_scan.py experiments/runs/campaign_cpu.yaml
python experiments/aggregate.py runs_out/<run>/     # table + confusion matrix
```
Curated campaign YAMLs (shown in `modelscanner tui`): `campaign_cpu.yaml`,
`campaign_gpu_qwen.yaml`, `campaign_gpu_mistral.yaml`, `campaign_20260703_base.yaml`
(template to copy). Older extended matrices live under `experiments/runs/archive/`.
**Whole benchmark in one command (AWS box):**
```bash
./experiments/run_campaign.sh                                        # GPU Qwen matrix (default YAML)
./experiments/run_campaign.sh experiments/runs/campaign_gpu_mistral.yaml  # GPU Mistral matrix
```
`run_campaign.sh` chains the runner (download + scan + purge + campaign HTML/CSV +
S3 push) then `aggregate.py` (text accuracy + confusion matrix). It activates the
`modelscanner` conda env and forwards `$HF_TOKEN` if set.

On the AWS box the runner reuses the **same cycle as `scan --s3`**: with
`download: true` it fetches each model absent from the cache via the box
procedure (internal CA + secrets + `hf download`) before scanning it, and with
`purge: true` it removes from the HF cache — after each scan — **only the models
this run downloaded itself** (a model already cached / a local `models_dir`
entry is left untouched). So a whole matrix scans **anti-OOM**
(1 subprocess per model) **and anti-disk-fill** (purge between models) without
saturating the box. The GPU campaign YAMLs (`campaign_gpu_qwen.yaml`,
`campaign_gpu_mistral.yaml`) ship with `download`/`purge` enabled; `campaign_cpu.yaml`
leaves them off (no behavior change).

**Practical runner flags** (any `run_scan.py` / `run_campaign.sh` call):
```bash
python experiments/run_scan.py <yaml> --dry-run          # print the plan (dl/scan/purge/skip), run nothing
python experiments/run_scan.py <yaml> --only dphn huihui # keep only models whose path/name matches a token
python experiments/run_scan.py <yaml> --limit 1          # scan only the first N models (smoke test)
python experiments/run_scan.py <yaml> --force            # re-scan even if a result already exists
```
`--dry-run` resolves each model (HF id vs local), shows which would be downloaded /
scanned / purged / skipped, and reports free disk — use it to validate a YAML before
spending GPU hours. The run recap prints **per-model wall-clock time + total** and the
**free-disk delta** when `purge` is on. The runner is **idempotent**: re-running the
same command resumes (skips models already done); `--force` re-scans.

Full guide: **[docs/HOW_TO_USE.md](docs/HOW_TO_USE.md)** (setup, recipes,
**how to read the results**). GPU/AWS porting: **[docs/AWS_RUNBOOK.md](docs/AWS_RUNBOOK.md)**.

## Status (v0.1.0)
Detector **complete and validated** on a real matrix of 4 models derived from
`Qwen2.5-0.5B` — **accuracy 4/4**:

| Model | Verdict | `A` (global) | `B` (band) | refusal |
|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct | `censored` | 0.24 | 0.28 | 0.88 |
| huihui …-abliterated | `ablated` | **0.90** | **0.99** | 0.06 |
| grisun0 …-heretic *(localized)* | `ablated` | 0.29 | **0.67** | — |
| Dolphin3.0-Qwen2.5-0.5B | `finetuned_decensored` | 0.24 | 0.28 | 0.06 |

False positive (fine-tuned) avoided; **stealthy** ablation (Heretic) caught by the **band** criterion.

**Multi-direction / norm-preserving extension (2026-06).** Scanning a real 7B
(`OBLITERATUS/Qwen2.5-Coder-7B-Instruct-OBLITERATED`, `n_directions=4`, `norm_preserve`,
`regularization=0.3`) exposed a blind spot: a single-direction `u_min` plus norm preservation
look *intact* to the SVD weight signature → mislabelled `finetuned_decensored`. Fix shipped: **subspace** signal
`S` (bottom-`k`) + **evasive-ablation** rule (behavioral fusion). **No regression** on the 4-model
0.5B matrix (still 4/4; new signals stay dormant on known-good models). 125 offline tests.

**Campaign runner now AWS-ready (2026-06).** `experiments/run_scan.py` reproduces the
`scan --s3` cycle (box download + post-scan cache purge of only what the run fetched), so the
curated benchmark matrices (`campaign_gpu_qwen.yaml`, `campaign_gpu_mistral.yaml`; older ones
under `runs/archive/`) run on the box without saturating disk — the "proof-of-efficacy"
campaign is ready to launch on GPU.

**Next steps**: run the 1.5B / 7B benchmark on the AWS box (accuracy + confusion matrix +
campaign HTML), confirm the multi-direction fix on the real 7B, threshold calibration of `S` /
over-refusal against same-family contrasts (Coder-7B base + Dolphin-Coder), MoE/MLA,
graphical interface.

## Documentation
- [`docs/METRICS.md`](docs/METRICS.md) — **metrics guide** (FR): each signal — intuition → formula → what it detects → threshold → where it shows in the report
- [`docs/PIPELINE.md`](docs/PIPELINE.md) — annotated pipeline (diagram + 3 plans + 4 buckets)
- [`docs/HOW_TO_USE.md`](docs/HOW_TO_USE.md) — usage guide + result analysis
- [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md) — supported model types, error kinds, reference-free limits
- [`docs/AWS_RUNBOOK.md`](docs/AWS_RUNBOOK.md) — GPU/AWS porting + runner
- [`docs/PROTOCOLE_TEST.md`](docs/PROTOCOLE_TEST.md) — validation protocol
- [`docs/report_en.tex`](docs/report_en.tex) · [`docs/report_fr.tex`](docs/report_fr.tex) — mathematical justification report (EN / FR), every metric commented (Overleaf, pdfLaTeX)
## License
**Apache License 2.0** — see [`LICENSE`](LICENSE). Free to use, modify, and redistribute,
including commercially, provided you keep the attribution and license notice. Contributions
are welcome under the same terms (see [`CONTRIBUTING.md`](CONTRIBUTING.md)); please report
security issues privately as described in [`SECURITY.md`](SECURITY.md).
