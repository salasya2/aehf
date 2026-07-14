# Contributing to aehf

Thanks for your interest in contributing!

## Setup

```bash
git clone https://github.com/salasya2/aehf.git
cd aehf
python -m venv .venv
.venv/Scripts/activate      # Windows
source .venv/bin/activate   # macOS/Linux
pip install -e ".[dev]"
```

## Before you open a PR

All three must pass — CI runs them on every push:

```bash
ruff check src tests
mypy src tests
pytest
```

Notes:

- mypy runs in `strict` mode. New code must be fully typed.
- Tests in `tests/test_live_anthropic.py` hit the real Anthropic API and need
  `ANTHROPIC_API_KEY` set. Everything else runs offline — use `FakeAgent` and
  the mock/replay tool providers so tests stay free and deterministic.

## Design decisions

Non-trivial design choices (and the alternatives you rejected) go in
[docs/decision.md](docs/decision.md). If your PR picks between two reasonable
approaches, add an entry.

## Pull requests

- Keep PRs small and focused — one change per PR.
- Include a test that fails without your change.
- Reference the issue you're addressing, if there is one.

## Reporting bugs

Open a GitHub issue with the command you ran, what you expected, and what
happened instead. For judge/calibration issues, include the transcript JSONL
line if you can.
