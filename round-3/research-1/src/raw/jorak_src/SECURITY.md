# Security Policy

Model Scanner (Jorak) is a **defensive security research tool**: it detects
directional ablation ("abliteration") in open-source LLM weights. We take the
security of the tool itself seriously.

## Reporting a vulnerability

**Do not open a public issue for security vulnerabilities.**

Report privately to **jolan.mocanu@gmail.com** with:

- a description of the issue and its impact,
- steps to reproduce (or a proof of concept),
- affected version / commit,
- any suggested remediation.

You will receive an acknowledgement within **5 business days**. We aim to
provide a remediation plan within **30 days** of confirmation. Please allow us
reasonable time to fix the issue before any public disclosure
(coordinated disclosure).

## Scope

In scope:

- Code execution, path traversal, or unsafe deserialization when loading
  untrusted model files (`.safetensors`, `.gguf`, `config.json`, chat
  templates).
- Injection or credential leakage in the CLI / TUI / S3 upload paths.
- Denial of service triggered by crafted model inputs.

Out of scope:

- The *findings* a scan produces about a third-party model (that is the
  tool's intended output, not a vulnerability).
- Issues in upstream dependencies (report those upstream; tell us so we can
  pin/patch).

## Supported versions

Only the latest released version on the default branch (`main`) receives
security fixes.

## Handling untrusted models

Model Scanner may be pointed at attacker-controlled artifacts. Treat every
scanned model as **untrusted input** and run scans in an isolated environment
(container / VM / dedicated box) when analysing unknown models.
