"""Stream 5,000 FinePDFs records and keep agriculture BM25 p99 results."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from itertools import islice
from pathlib import Path
from time import perf_counter
from typing import Any, NamedTuple

from datasets import load_dataset
from rank_bm25 import BM25Okapi

DATASET_ID = "HuggingFaceFW/finepdfs"
DATASET_CONFIG = "eng_Latn"
DATASET_SPLIT = "train"
AGRICULTURE_QUERY = (
    "agriculture crop wheat maize rice soil irrigation plant disease farming harvest"
)
MAX_DOCUMENTS = 5000
SCORE_PERCENTILE = 99.0
TOP_K = 20
PREVIEW_CHARS = 300


class SearchResult(NamedTuple):
    """One ranked document with a short display preview."""

    bm25_score: float
    pdf_url: str
    text_preview: str


def percentile_threshold(scores: Sequence[float], percentile: float) -> float:
    """Return a linearly interpolated score percentile from 0 to 100."""
    if not scores:
        raise ValueError("percentile calculation requires at least one score")
    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be between 0 and 100")

    ordered_scores = sorted(scores)
    position = (len(ordered_scores) - 1) * percentile / 100
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered_scores) - 1)
    weight = position - lower_index
    return (
        ordered_scores[lower_index] * (1 - weight)
        + ordered_scores[upper_index] * weight
    )


def select_by_percentile(
    results: Sequence[SearchResult], percentile: float
) -> tuple[float, list[SearchResult]]:
    """Keep positive-scoring results at or above the selected percentile."""
    if not results:
        return 0.0, []

    threshold = percentile_threshold(
        [result.bm25_score for result in results], percentile
    )
    selected = [
        result for result in results if is_eligible_score(result.bm25_score, threshold)
    ]
    return threshold, selected


def is_eligible_score(score: float, threshold: float) -> bool:
    """Check that a score is positive and meets the percentile cutoff."""
    return score > 0 and score >= threshold


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
    iterator = iter(documents)
    try:
        return list(islice(iterator, limit))
    finally:
        close = getattr(iterator, "close", None)
        if callable(close):
            close()


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


def write_metrics(metrics: Mapping[str, Any], output_path: Path) -> None:
    """Write one JSON object describing the processed sample and its timing."""
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(metrics, output_file, indent=2, sort_keys=True)
        output_file.write("\n")


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
    """Stream, score, filter, and time the first 5,000 FinePDFs records."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("agriculture_bm25_p99_5000.csv"),
        help="Path for the filtered result CSV.",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("agriculture_bm25_p99_5000.metrics.json"),
        help="Path for run timing metadata.",
    )
    arguments = parser.parse_args(argv)

    started = perf_counter()
    stream = load_dataset(
        DATASET_ID,
        DATASET_CONFIG,
        split=DATASET_SPLIT,
        streaming=True,
    )
    dataset_ready = perf_counter()
    features = stream.features or {}
    print(f"Schema: {features}")
    text_field, url_field = select_fields(features)
    documents = collect_documents(stream, MAX_DOCUMENTS)
    del stream
    documents_read = perf_counter()
    ranked_results = score_documents(
        documents, text_field, url_field, top_k=len(documents)
    )
    threshold, filtered_results = select_by_percentile(ranked_results, SCORE_PERCENTILE)
    scored = perf_counter()
    write_results(filtered_results, arguments.output)
    csv_written = perf_counter()

    total_seconds = csv_written - started
    timing_seconds = {
        "dataset_init": round(dataset_ready - started, 6),
        "stream_documents": round(documents_read - dataset_ready, 6),
        "bm25_score_and_filter": round(scored - documents_read, 6),
        "csv_write": round(csv_written - scored, 6),
        "total": round(total_seconds, 6),
        "documents_per_second": round(len(documents) / max(total_seconds, 1e-9), 3),
    }
    metrics = {
        "dataset_id": DATASET_ID,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "documents_scored": len(documents),
        "score_percentile": SCORE_PERCENTILE,
        "score_threshold": threshold,
        "documents_retained": len(filtered_results),
        "timing_seconds": timing_seconds,
    }
    write_metrics(metrics, arguments.metrics_output)

    print(
        f"Scored {len(documents)} documents; p99 cutoff "
        f"{threshold:.6f}; kept {len(filtered_results)}."
    )
    print(f"Top {min(TOP_K, len(filtered_results))} kept results:")
    print_results(filtered_results[:TOP_K])
    print(f"Saved {len(filtered_results)} results to {arguments.output}")
    print(
        "Timing (seconds): "
        f"dataset_init={timing_seconds['dataset_init']:.3f}; "
        f"stream_documents={timing_seconds['stream_documents']:.3f}; "
        f"bm25_score_and_filter={timing_seconds['bm25_score_and_filter']:.3f}; "
        f"csv_write={timing_seconds['csv_write']:.3f}; "
        f"total={timing_seconds['total']:.3f}; "
        f"throughput={timing_seconds['documents_per_second']:.1f} documents/s"
    )
    print(f"Saved run metrics to {arguments.metrics_output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
