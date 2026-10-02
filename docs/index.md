# FinePDF Clustering

This project explores the [FinePDFs dataset](https://huggingface.co/datasets/HuggingFaceFW/finepdfs). It finds the documents that are relevant to a chosen domain. See the [glossary](glossary.md) for the project terms.

## Current scope

The current proof of concept reads the first 5,000 records of the English training split in streaming mode. It ranks the records against one agriculture query with BM25. It keeps the records with a positive score at or above the 99th-percentile cutoff of the run.

The proof of concept uses the extracted `text` field. It includes a PDF URL when one is available. It records the streaming time and the scoring time. It does not download the source dataset.

Run the proof of concept from the project root:

```sh
PYTHONPATH=src uv run --locked python -m finepdf_clustering.agriculture_bm25
```

## Development tools

Install the locked development tools with `uv sync --locked`. Then run the formatting and lint checks:

```sh
uv run --locked pre-commit run --all-files
uv run --locked ty check src tests
uv run mkdocs serve
```

Run the complete test and CI gate on your computer:

```sh
bash scripts/quality_gate.sh
```

Refer to [Quality gates](quality.md) for the coverage, CRAP, mutation, and documentation thresholds that the gate enforces.
