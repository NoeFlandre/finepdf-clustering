# FinePDF Clustering

The goal of this project is to explore the [FinePDFs dataset](https://huggingface.co/datasets/HuggingFaceFW/finepdfs) and find documents relevant to a chosen domain.

## Current scope

This repository currently contains a minimal Python project setup and documentation site. Dataset ingestion, relevance methods, and clustering will be designed separately before implementation.

## Development tools

Install the locked development tools with `uv sync --locked`. Run formatting and lint checks with:

```sh
uv run --locked pre-commit run --all-files
uv run --locked ty check src tests
uv run mkdocs serve
```

Run the complete test and CI gate locally:

```sh
bash scripts/quality_gate.sh
```

See [Quality gates](quality.md) for the enforced coverage, CRAP, mutation, and documentation thresholds.
