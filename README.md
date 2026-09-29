# FinePDF Clustering

This project will explore the FinePDFs dataset to identify documents relevant to a chosen domain.

This initial setup contains project metadata, development tools, and documentation scaffolding only. It does not include dataset processing, a command-line workflow, or clustering code.

## Toolchain

- [uv](https://docs.astral.sh/uv/) manages the project environment, development dependencies, and lockfile.
- [Ruff](https://docs.astral.sh/ruff/) lints Python code and checks import order.
- [ty](https://docs.astral.sh/ty/) checks Python types.
- [MkDocs](https://www.mkdocs.org/) builds the project documentation.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then sync the development tools:

```sh
export UV_PYTHON_INSTALL_DIR="$PWD/.uv-cache/python"
export TMPDIR="$PWD/.tmp"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
uv sync
```

The UV cache is configured in `pyproject.toml` under `.uv-cache/cache`. These settings keep the Python runtime, package cache, virtual environment, and temporary files in this checkout.

## Tool commands

```sh
uv run ruff check .
uv run ty check
uv run mkdocs serve
```

Build the documentation with:

```sh
uv run mkdocs build --strict
```
