# FinePDF Clustering

The goal of this project is to explore the [FinePDFs dataset](https://huggingface.co/datasets/HuggingFaceFW/finepdfs) and find documents relevant to a chosen domain.

## Current scope

This repository currently contains a minimal Python project setup and documentation site. Dataset ingestion, relevance methods, and clustering will be designed separately before implementation.

## Development tools

Set `UV_PYTHON_INSTALL_DIR` and the temporary-directory variables as shown in the repository README before running `uv sync`; the UV cache and managed Python runtime will then stay in the project checkout. Run the configured tools with:

```sh
uv run ruff check .
uv run ty check
uv run mkdocs serve
```

To check that the documentation builds:

```sh
uv run mkdocs build --strict
```
