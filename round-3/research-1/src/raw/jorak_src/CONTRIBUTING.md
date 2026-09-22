# Contributing to Model Scanner

Thanks for your interest! This project is open source under the
**Apache License 2.0** (see [`LICENSE`](LICENSE)). Contributions are welcome —
bug reports, fixes, tests, docs, and new detection ideas. By submitting a
contribution you confirm you have the right to do so and agree it is licensed
under the same Apache-2.0 terms as the project.

## Development setup

**Prerequisites:** `git`, and either **conda** (recommended) *or* Python 3.10+.
No GPU is required for the default weights/SVD plan.

```bash
git clone <repo-url> && cd Jorak

# conda (recommended)
conda env create -f environment.yml && conda activate modelscanner
pip install -e ".[dev]"

# or plain venv
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Verify the install:

```bash
modelscanner --help
pytest
```

## Workflow

1. Branch off `main`: `git checkout -b <type>/<short-description>`
   (`type` ∈ `feat`, `fix`, `docs`, `refactor`, `test`, `chore`).
2. Make focused changes; keep the diff minimal and match the surrounding style.
3. Run the checks locally (see below).
4. Open a pull request against `main`. CI must be green and at least one
   review is required before merge. Direct pushes to `main` are disabled.

## Quality gates (must pass before merge)

```bash
ruff check .   # lint (F/I/W); the compact one-liner style is intentional and not reformatted
pytest         # full test suite
```

Installing [`pre-commit`](https://pre-commit.com/) runs the fast checks
automatically on every commit:

```bash
pre-commit install
```

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):
`feat: …`, `fix: …`, `docs: …`, `refactor: …`, `test: …`, `chore: …`.
Keep the subject line ≤ 72 chars, imperative mood.

## Tests

- New behaviour needs a test under `tests/`.
- Bug fixes should add a regression test.
- Prefer small, fast, CPU-only tests. Avoid downloading real models in the
  test suite — use the fixtures / mocks already present.

## Documentation

User-facing docs live in `docs/` and the bilingual `README.md` / `README_FR.md`.
Keep both language versions in sync when you change user-facing behaviour.
