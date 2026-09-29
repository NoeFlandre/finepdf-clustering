# FinePDF Clustering

This project will explore the FinePDFs dataset to identify documents relevant to a chosen domain.

This initial setup contains project metadata, development tools, and documentation scaffolding only. It does not include dataset processing, a command-line workflow, or clustering code.

## Toolchain

- [uv](https://docs.astral.sh/uv/) manages the project environment, development dependencies, and lockfile.
- [Ruff](https://docs.astral.sh/ruff/) lints Python code and checks import order.
- [ty](https://docs.astral.sh/ty/) checks Python types.
- [pytest](https://docs.pytest.org/) and [coverage.py](https://coverage.readthedocs.io/) enforce full line and branch coverage.
- [mutmut](https://mutmut.readthedocs.io/) checks that the tests detect behavioral changes.
- [pre-commit](https://pre-commit.com/) runs the configured formatting and lint hooks.
- [MkDocs](https://www.mkdocs.org/) builds the project documentation.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then sync the development tools:

```sh
export UV_CACHE_DIR="$PWD/.uv-cache/cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.uv-cache/python"
export UV_PYTHON_BIN_DIR="$PWD/.uv-cache/bin"
export TMPDIR="$PWD/.tmp"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
export PYTHONDONTWRITEBYTECODE=1
uv sync
```

The UV cache is configured in `pyproject.toml` under `.uv-cache/cache`. These settings keep UV-managed runtimes, launchers, package cache, the virtual environment, bytecode, and temporary files in this checkout.

## Tool commands

```sh
uv run --locked pre-commit run --all-files
uv run --locked ty check src tests
uv run mkdocs serve
```

Run the complete local QA gauntlet with the same command used in CI:

```sh
bash scripts/quality_gate.sh
```

The gate checks the lockfile, formatting and lint, types, 100% line and branch coverage, a CRAP score below 6 for every source function, strict documentation builds, and mutation results with every generated mutant killed. See [the quality gate details](docs/quality.md).
