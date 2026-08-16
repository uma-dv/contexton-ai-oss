# Contributing to ContextOn.AI OSS

Thanks for your interest! This project is intentionally small and
focused. Please keep contributions in that spirit.

## Development Setup

```bash
pip install -e ".[dev]"
pytest
```

The test suite lives in `tests/test_core.py` (23 tests covering graph
building, confidence, failure learning, entity resolution, and quality
badges).

## What We Welcome

- Bug fixes with a failing test first
- Improvements to retrieval, entity resolution, or failure learning
- Documentation and example improvements
- Issues that describe real problems with reproduction steps

## Scope Notes

- This is the **open-source lite version**. Do not implement or reference
  proprietary platform features (isolation engine, quality scoring formulas, drift
  detection, multi-tenant architecture, compliance reporting, enterprise
  connectors).
- Keep the package dependency-free in the core; optional features
  (e.g. MCP) live behind optional dependencies.
- Core code style: Python 3.10+, type hints on public APIs, docstrings
  on public methods.

## Before Submitting

1. `python -m pytest tests/ -v` — all tests pass
2. `node tests/web_demo_test.mjs` — browser tests for the web demo pass
   (drives real headless Chrome over CDP; requires Node 22+ and Chrome;
   set `CHROME_PATH` if Chrome isn't auto-detected)
3. `python -m examples.failure_learning_demo` — demo runs
4. Keep changes focused; explain the why in the PR description
