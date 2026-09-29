"""Stream a small FinePDFs sample and rank documents with BM25."""

from __future__ import annotations

import argparse
import csv
import re
from collections.abc import Iterable, Mapping, Sequence
from itertools import islice
from pathlib import Path
from typing import Any, NamedTuple

from datasets import load_dataset
from rank_bm25 import BM25Okapi

DATASET_ID = "HuggingFaceFW/finepdfs"
DATASET_CONFIG = "eng_Latn"
DATASET_SPLIT = "train"
AGRICULTURE_QUERY = (
    "agriculture crop wheat maize rice soil irrigation plant disease farming harvest"
)
MAX_DOCUMENTS = 1000
TOP_K = 20
PREVIEW_CHARS = 300


class SearchResult(NamedTuple):
    """One ranked document with a short display preview."""

    bm25_score: float
    pdf_url: str
    text_preview: str


def select_fields(features: Mapping[str, object]) -> tuple[str, str | None]:
    """Select the extracted text field and the optional source URL field."""
    if "text" not in features:
        raise ValueError("FinePDFs schema must contain the extracted text field 'text'")
    return "text", "url" if "url" in features else None


def tokenize(text: str) -> list[str]:
    """Lowercase text and split it into simple word tokens."""
    return re.findall(r"\b\w+\b", text.lower())


def collect_documents(
    documents: Iterable[Mapping[str, Any]], limit: int
) -> list[Mapping[str, Any]]:
    """Read at most ``limit`` records from an iterable stream."""
    return list(islice(documents, limit))


def score_documents(
    documents: Sequence[Mapping[str, Any]],
    text_field: str,
    url_field: str | None,
    top_k: int = TOP_K,
) -> list[SearchResult]:
    """Score every document and return the highest scoring previews."""
    if not documents:
        return []

    tokenized_documents = [
        tokenize(str(document[text_field])) for document in documents
    ]
    bm25 = BM25Okapi(tokenized_documents)
    scores = bm25.get_scores(tokenize(AGRICULTURE_QUERY))
    ranked_indices = sorted(
        range(len(documents)), key=lambda index: (-scores[index], index)
    )[:top_k]

    return [
        SearchResult(
            bm25_score=float(scores[index]),
            pdf_url=(str(documents[index][url_field]) if url_field is not None else ""),
            text_preview=str(documents[index][text_field])[:PREVIEW_CHARS],
        )
        for index in ranked_indices
    ]


def write_results(results: Sequence[SearchResult], output_path: Path) -> None:
    """Write the ranked results as a small CSV file."""
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=["bm25_score", "pdf_url", "text_preview"],
        )
        writer.writeheader()
        writer.writerows(result._asdict() for result in results)


def print_results(results: Sequence[SearchResult]) -> None:
    """Print the top results with scores, URLs, and short text previews."""
    print("Rank\tBM25 score\tPDF URL\tText preview")
    for rank, result in enumerate(results, start=1):
        preview = result.text_preview.replace("\n", " ")
        print(
            f"{rank}\t{result.bm25_score:.4f}\t"
            f"{result.pdf_url or 'unavailable'}\t{preview}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the streaming agriculture retrieval proof of concept."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("agriculture_bm25_top20.csv"),
        help="Path for the top-20 CSV output.",
    )
    arguments = parser.parse_args(argv)

    stream = load_dataset(
        DATASET_ID,
        DATASET_CONFIG,
        split=DATASET_SPLIT,
        streaming=True,
    )
    features = stream.features or {}
    print(f"Schema: {features}")
    text_field, url_field = select_fields(features)
    documents = collect_documents(stream, MAX_DOCUMENTS)
    results = score_documents(documents, text_field, url_field)

    print(f"Scored {len(documents)} documents; top {len(results)} results:")
    print_results(results)
    write_results(results, arguments.output)
    print(f"Saved {len(results)} results to {arguments.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
