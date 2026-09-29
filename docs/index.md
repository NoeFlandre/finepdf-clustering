# FinePDF Clustering

This project explores the [FinePDFs dataset](https://huggingface.co/datasets/HuggingFaceFW/finepdfs) and finds documents relevant to a chosen domain.

## Current scope

The current proof of concept streams the English training split, reads its first 1,000 records, and ranks them against one agriculture query using BM25. It uses the schema's extracted `text` field and includes a PDF URL when available. Run it from the project root with `PYTHONPATH=src uv run --locked python -m finepdf_clustering.agriculture_bm25`.

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
