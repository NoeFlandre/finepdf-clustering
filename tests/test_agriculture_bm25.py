from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, ClassVar

import pytest

import finepdf_clustering.agriculture_bm25 as agriculture_bm25
from finepdf_clustering.agriculture_bm25 import (
    AGRICULTURE_QUERY,
    collect_documents,
    main,
    score_documents,
    select_fields,
    tokenize,
)


def test_select_fields_uses_extracted_text_and_optional_url() -> None:
    assert select_fields({"text": str, "url": str, "id": str}) == ("text", "url")
    assert select_fields({"text": str, "id": str}) == ("text", None)


def test_select_fields_requires_extracted_text() -> None:
    with pytest.raises(ValueError, match="text field 'text'"):
        select_fields({"content": str})


def test_select_fields_reports_exact_missing_text_error() -> None:
    with pytest.raises(ValueError) as error:
        select_fields({"content": str})

    assert str(error.value) == (
        "FinePDFs schema must contain the extracted text field 'text'"
    )


def test_tokenize_lowercases_and_splits_words() -> None:
    assert tokenize("WHEAT crop-based; soil!") == ["wheat", "crop", "based", "soil"]


def test_collect_documents_reads_only_the_requested_prefix() -> None:
    rows = [{"id": str(index)} for index in range(5)]

    assert collect_documents(iter(rows), limit=3) == rows[:3]


def test_collect_documents_closes_a_partially_consumed_generator() -> None:
    class TrackedIterator:
        def __init__(self) -> None:
            self.index = 0
            self.closed = False

        def __iter__(self) -> TrackedIterator:
            return self

        def __next__(self) -> dict[str, str]:
            if self.index == 5:
                raise StopIteration
            row = {"id": str(self.index)}
            self.index += 1
            return row

        def close(self) -> None:
            self.closed = True

    iterator = TrackedIterator()

    assert collect_documents(iterator, limit=3) == [
        {"id": "0"},
        {"id": "1"},
        {"id": "2"},
    ]
    assert iterator.closed is True


def test_write_results_uses_portable_csv_open_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "results.csv"
    original_open = Path.open
    open_calls: list[tuple[str, str | None, str | None]] = []

    def record_open(
        path: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ):
        open_calls.append((mode, encoding, newline))
        return original_open(path, mode, buffering, encoding, errors, newline)

    monkeypatch.setattr(Path, "open", record_open)
    agriculture_bm25.write_results([], output_path)

    assert open_calls == [("w", "utf-8", "")]


def test_score_documents_ranks_agriculture_text_and_limits_preview() -> None:
    matching_text = f"{AGRICULTURE_QUERY} {'x' * 350}"
    documents = [
        {"text": "unrelated astronomy document", "url": "https://example.test/0.pdf"},
        {"text": "unrelated history document", "url": "https://example.test/1.pdf"},
        {"text": matching_text, "url": "https://example.test/agriculture.pdf"},
        {"text": "unrelated geography document"},
        *[{"text": "unrelated reference material"} for _ in range(6)],
    ]

    results = score_documents(documents, "text", "url", top_k=1)

    assert len(results) == 1
    assert results[0].pdf_url == "https://example.test/agriculture.pdf"
    assert results[0].bm25_score > 0
    assert results[0].text_preview == matching_text[:300]


def test_score_documents_keeps_input_order_for_tied_scores() -> None:
    documents = [{"text": "neutral", "url": str(index)} for index in range(4)]

    results = score_documents(documents, "text", "url", top_k=2)

    assert [result.pdf_url for result in results] == ["0", "1"]
    assert [result.bm25_score for result in results] == [0.0, 0.0]


def test_score_documents_handles_empty_input() -> None:
    assert score_documents([], "text", "url") == []


def test_score_documents_handles_missing_url_field() -> None:
    documents = [
        {"text": AGRICULTURE_QUERY, "url": "must-not-be-used"},
        *[{"text": "unrelated document"} for _ in range(9)],
    ]

    results = score_documents(documents, "text", None, top_k=1)

    assert results[0].pdf_url == ""
    assert results[0].text_preview == AGRICULTURE_QUERY


def test_main_help_describes_output_argument(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class EmptyStream(list[dict[str, Any]]):
        features: ClassVar[dict[str, type[str]]] = {"text": str, "url": str}

    monkeypatch.setattr(
        agriculture_bm25,
        "load_dataset",
        lambda *_args, **_kwargs: EmptyStream(),
    )
    with pytest.raises(SystemExit) as error:
        main(["--help"])

    assert error.value.code == 0
    help_text = capsys.readouterr().out
    assert (
        "Stream 5,000 FinePDFs records and keep agriculture BM25 p99 results."
        in help_text
    )
    assert "--output OUTPUT" in help_text
    assert "Path for the filtered result CSV." in help_text
    assert "--metrics-output METRICS_OUTPUT" in help_text
    assert "Path for run timing metadata." in help_text
    assert any(
        line.endswith("Path for the filtered result CSV.")
        for line in help_text.splitlines()
    )
    assert any(
        line.endswith("Path for run timing metadata.")
        for line in help_text.splitlines()
    )


def test_main_accepts_custom_output_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeStream(list[dict[str, Any]]):
        features: ClassVar[dict[str, type[str]]] = {"text": str, "url": str}

    stream = FakeStream(
        [{"text": "neutral document", "url": "https://example.test/doc.pdf"}]
    )
    monkeypatch.setattr(
        agriculture_bm25,
        "load_dataset",
        lambda *_args, **_kwargs: stream,
    )
    output_path = tmp_path / "custom.csv"
    metrics_path = tmp_path / "custom.metrics.json"

    assert (
        main(["--output", str(output_path), "--metrics-output", str(metrics_path)]) == 0
    )
    assert output_path.is_file()
    assert metrics_path.is_file()


def test_main_uses_documented_default_output_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class EmptyStream(list[dict[str, Any]]):
        features: ClassVar[dict[str, type[str]]] = {"text": str, "url": str}

    monkeypatch.setattr(
        agriculture_bm25, "load_dataset", lambda *_args, **_kwargs: EmptyStream()
    )
    monkeypatch.chdir(tmp_path)

    assert main([]) == 0

    output_path = tmp_path / "agriculture_bm25_p99_5000.csv"
    metrics_path = tmp_path / "agriculture_bm25_p99_5000.metrics.json"
    assert output_path.is_file()
    assert metrics_path.is_file()
    output = capsys.readouterr().out
    assert "Saved 0 results to agriculture_bm25_p99_5000.csv" in output
    assert "Saved run metrics to agriculture_bm25_p99_5000.metrics.json" in output


def test_main_uses_safe_throughput_when_run_clock_has_zero_duration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeStream(list[dict[str, Any]]):
        features: ClassVar[dict[str, type[str]]] = {"text": str, "url": str}

    monkeypatch.setattr(
        agriculture_bm25,
        "load_dataset",
        lambda *_args, **_kwargs: FakeStream([{"text": "crop", "url": "crop.pdf"}]),
    )
    monkeypatch.setattr(agriculture_bm25, "perf_counter", lambda: 1.0)
    monkeypatch.setattr(
        agriculture_bm25,
        "score_documents",
        lambda *_args, **_kwargs: [
            agriculture_bm25.SearchResult(1.0, "crop.pdf", "crop")
        ],
    )
    output_path = tmp_path / "zero-duration.csv"
    metrics_path = tmp_path / "zero-duration.json"

    assert (
        main(["--output", str(output_path), "--metrics-output", str(metrics_path)]) == 0
    )

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["timing_seconds"]["total"] == 0.0
    assert metrics["timing_seconds"]["documents_per_second"] == 1_000_000_000.0


def test_print_results_flattens_preview_and_marks_missing_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    agriculture_bm25.print_results(
        [agriculture_bm25.SearchResult(1.25, "", "first line\nsecond line")]
    )

    assert capsys.readouterr().out == (
        "Rank\tBM25 score\tPDF URL\tText preview\n"
        "1\t1.2500\tunavailable\tfirst line second line\n"
    )


def test_main_streams_only_first_5000_and_writes_p99_filtered_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FakeStream(list[dict[str, Any]]):
        features: ClassVar[dict[str, type[str]]] = {"text": str, "url": str}

    rows = [
        {
            "text": AGRICULTURE_QUERY,
            "url": f"https://example.test/agriculture-{index}.pdf",
        }
        for index in range(50)
    ]
    rows.extend(
        {"text": "neutral document", "url": f"https://example.test/{index}.pdf"}
        for index in range(50, 5000)
    )
    rows.append(
        {
            "text": AGRICULTURE_QUERY,
            "url": "https://example.test/5000-too-late.pdf",
        }
    )
    dataset = FakeStream(rows)
    calls: list[tuple[str, str, str, bool]] = []
    score_calls: list[tuple[int, int]] = []
    original_score_documents = agriculture_bm25.score_documents

    def fake_load_dataset(
        dataset_name: str, config: str, *, split: str, streaming: bool
    ) -> FakeStream:
        calls.append((dataset_name, config, split, streaming))
        return dataset

    def record_score_documents(
        documents: list[dict[str, Any]],
        text_field: str,
        url_field: str | None,
        top_k: int,
    ) -> list[agriculture_bm25.SearchResult]:
        score_calls.append((len(documents), top_k))
        return original_score_documents(documents, text_field, url_field, top_k)

    monkeypatch.setattr(agriculture_bm25, "load_dataset", fake_load_dataset)
    monkeypatch.setattr(agriculture_bm25, "score_documents", record_score_documents)
    clock_values = iter((10.0, 10.1234564, 11.2345679, 15.9876548, 16.1111112))
    monkeypatch.setattr(agriculture_bm25, "perf_counter", lambda: next(clock_values))
    monkeypatch.chdir(tmp_path)
    output_path = tmp_path / "filtered.csv"
    metrics_path = tmp_path / "metrics.json"

    assert (
        main(["--output", str(output_path), "--metrics-output", str(metrics_path)]) == 0
    )

    captured = capsys.readouterr().out
    assert calls == [("HuggingFaceFW/finepdfs", "eng_Latn", "train", True)]
    assert score_calls == [(5000, 5000)]
    assert captured.index("Schema:") < captured.index("Scored 5000 documents")
    assert "5000-too-late.pdf" not in captured
    assert "p99 cutoff" in captured
    assert "kept 50" in captured
    assert "Top 20 kept results:" in captured
    assert "Saved 50 results to" in captured
    assert (
        "Timing (seconds): dataset_init=0.123; stream_documents=1.111; "
        "bm25_score_and_filter=4.753; csv_write=0.123; total=6.111; "
        "throughput=818.2 documents/s"
    ) in captured
    assert f"Saved run metrics to {metrics_path}" in captured
    with output_path.open(newline="", encoding="utf-8") as result_file:
        results = list(csv.DictReader(result_file))
    assert len(results) == 50
    assert results[0]["pdf_url"] == "https://example.test/agriculture-0.pdf"
    assert all("5000-too-late" not in result["pdf_url"] for result in results)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert set(metrics) == {
        "dataset_id",
        "config",
        "split",
        "documents_scored",
        "score_percentile",
        "score_threshold",
        "documents_retained",
        "timing_seconds",
    }
    assert metrics["dataset_id"] == "HuggingFaceFW/finepdfs"
    assert metrics["config"] == "eng_Latn"
    assert metrics["split"] == "train"
    assert metrics["documents_scored"] == 5000
    assert metrics["documents_retained"] == 50
    assert metrics["score_percentile"] == 99.0
    assert metrics["score_threshold"] > 0
    assert metrics["timing_seconds"] == {
        "dataset_init": 0.123456,
        "stream_documents": 1.111111,
        "bm25_score_and_filter": 4.753087,
        "csv_write": 0.123456,
        "total": 6.111111,
        "documents_per_second": 818.182,
    }
