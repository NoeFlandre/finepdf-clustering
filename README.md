# FinePDF Clustering

This project explores the [FinePDFs dataset](https://huggingface.co/datasets/HuggingFaceFW/finepdfs) to identify documents relevant to a chosen domain. Its current proof of concept ranks agriculture-related PDFs with BM25.

## Agriculture BM25 proof of concept

The command streams the English `eng_Latn` training split with Hugging Face `datasets`, inspects the schema, and reads only the first 5,000 documents from the `text` field. It scores all 5,000 with `rank-bm25`, computes the linearly interpolated 99th-percentile score, and keeps positive scores at or above that cutoff. It prints the top 20 kept documents with their PDF URL (when present) and a 300-character preview. It does not download the dataset.

```sh
PYTHONPATH=src uv run --locked python -m finepdf_clustering.agriculture_bm25
```

The command writes every passing row to `agriculture_bm25_p99_5000.csv` and its timing summary to `agriculture_bm25_p99_5000.metrics.json`. Timings separate dataset initialization, reading, BM25 scoring/filtering, CSV output, and total elapsed time; total includes CSV output and excludes console and metrics-file output. The fixed query is `agriculture crop wheat maize rice soil irrigation plant disease farming harvest`.

## Toolchain

- [uv](https://docs.astral.sh/uv/) manages the project environment, dependencies, and lockfile.
- Hugging Face [datasets](https://huggingface.co/docs/datasets/stream) streams the source dataset; [rank-bm25](https://pypi.org/project/rank-bm25/) scores the documents.
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
