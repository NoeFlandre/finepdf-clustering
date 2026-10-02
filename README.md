# FinePDF Clustering

This project explores the [FinePDFs dataset](https://huggingface.co/datasets/HuggingFaceFW/finepdfs). It finds the documents that are relevant to a chosen domain. The current proof of concept ranks agriculture PDFs with BM25. See the [glossary](docs/glossary.md) for the project terms.

## Agriculture BM25 proof of concept

The command does these steps:

1. It reads the English `eng_Latn` training split in streaming mode with Hugging Face `datasets`.
2. It inspects the schema.
3. It reads only the first 5,000 documents from the `text` field.
4. It scores the 5,000 documents with `rank-bm25`.
5. It calculates the linearly interpolated 99th-percentile score.
6. It keeps the positive scores at or above that cutoff.
7. It prints the top 20 kept documents. Each line shows the PDF URL (when present) and a 300-character preview.

The command does not download the dataset.

```sh
PYTHONPATH=src uv run --locked python -m finepdf_clustering.agriculture_bm25
```

The command writes each passing row to `agriculture_bm25_p99_5000.csv`. It writes the timing summary to `agriculture_bm25_p99_5000.metrics.json`.

The timing summary gives separate times for these stages:

- dataset initialization
- reading
- BM25 scoring and filtering
- CSV output
- total elapsed time

The total time includes the CSV output. It excludes the console output and the metrics-file output.

The fixed query is `agriculture crop wheat maize rice soil irrigation plant disease farming harvest`.

## Toolchain

- [uv](https://docs.astral.sh/uv/) manages the project environment, the dependencies, and the lockfile.
- Hugging Face [datasets](https://huggingface.co/docs/datasets/stream) streams the source dataset.
- [rank-bm25](https://pypi.org/project/rank-bm25/) scores the documents.
- [Ruff](https://docs.astral.sh/ruff/) lints the Python code and checks the import order.
- [ty](https://docs.astral.sh/ty/) checks the Python types.
- [pytest](https://docs.pytest.org/) and [coverage.py](https://coverage.readthedocs.io/) enforce full line coverage and full branch coverage.
- [mutmut](https://mutmut.readthedocs.io/) checks that the tests detect changes in behavior.
- [pre-commit](https://pre-commit.com/) runs the configured formatting hooks and lint hooks.
- [MkDocs](https://www.mkdocs.org/) builds the project documentation.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). Then synchronize the development tools:

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

The UV cache is set in `pyproject.toml` to `.uv-cache/cache`. These settings keep these items in this checkout:

- the UV-managed runtimes and launchers
- the package cache
- the virtual environment
- the bytecode
- the temporary files

## Tool commands

```sh
uv run --locked pre-commit run --all-files
uv run --locked ty check src tests
uv run mkdocs serve
```

Run the complete local QA gate with the same command that CI uses:

```sh
bash scripts/quality_gate.sh
```

The gate does these checks:

- It checks the lockfile.
- It checks the formatting and lint.
- It checks the types.
- It checks for 100% line coverage and 100% branch coverage.
- It checks that each source function has a CRAP score below 6.
- It builds the documentation in strict mode.
- It checks that the tests kill each generated mutant.

Refer to [the quality gate details](docs/quality.md).
