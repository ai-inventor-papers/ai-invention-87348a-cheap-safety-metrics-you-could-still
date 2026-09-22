# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Public open-source release under the Apache License 2.0.**
- Repository engineering for professional access: `LICENSE` (Apache-2.0),
  `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`,
  GitHub issue/PR templates, `CODEOWNERS`.
- Continuous integration: GitHub Actions running `ruff` (lint + format) and the
  full `pytest` suite across Python 3.10–3.13.
- `pre-commit` configuration and `ruff` configuration in `pyproject.toml`.
- Dependabot configuration for dependencies and GitHub Actions.

### Changed
- Renamed the default branch from `master` to `main`.
- Packaging metadata (`pyproject.toml`): authors, URLs, license, classifiers.

### Removed
- Stray `modelscanner/cli.zip` backup artifact from version control.

## [0.1.0] - 2026-06

### Added
- Reference-free detection of directional ablation (abliteration) in
  open-source LLMs — the **Jorak** framework with three complementary detection
  techniques: weights (spectral SVD signature), activations (axis health,
  Cohen's d), and behavioral (refusal rate).
- `classify()` into four provenance buckets: `censored`, `ablated`,
  `finetuned_decensored`, `ambiguous`.
- CLI (`modelscanner scan`) and full-screen curses TUI (`modelscanner tui`).
- Branded bilingual HTML report (EN + FR) plus CSV exports.
- Model loaders (safetensors, GGUF), architecture adapters, and vLLM/HF cache
  resolution.
- AWS/S3 campaign runner for batch scanning.
- English localization of the CLI, TUI, and progress UI.

[Unreleased]: https://github.com/JolanMc/Jorak/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/JolanMc/Jorak/releases/tag/v0.1.0
