from __future__ import annotations

import csv
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
    assert "Stream a small FinePDFs sample and rank documents with BM25." in help_text
    assert "  --output OUTPUT  Path for the top-20 CSV output.\n" in help_text


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

    assert main(["--output", str(output_path)]) == 0
    assert output_path.is_file()


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


def test_main_streams_only_first_1000_and_writes_top_20(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FakeStream(list[dict[str, Any]]):
        features: ClassVar[dict[str, type[str]]] = {"text": str, "url": str}

    rows = [
        {"text": "neutral document", "url": f"https://example.test/{index}.pdf"}
        for index in range(1000)
    ]
    rows.append(
        {
            "text": AGRICULTURE_QUERY,
            "url": "https://example.test/1000-agriculture.pdf",
        }
    )
    dataset = FakeStream(rows)
    calls: list[tuple[str, str, str, bool]] = []

    def fake_load_dataset(
        dataset_name: str, config: str, *, split: str, streaming: bool
    ) -> FakeStream:
        calls.append((dataset_name, config, split, streaming))
        return dataset

    monkeypatch.setattr(agriculture_bm25, "load_dataset", fake_load_dataset)
    monkeypatch.chdir(tmp_path)
    output_path = tmp_path / "agriculture_bm25_top20.csv"

    assert main([]) == 0

    captured = capsys.readouterr().out
    assert calls == [("HuggingFaceFW/finepdfs", "eng_Latn", "train", True)]
    assert captured.index("Schema:") < captured.index("Scored 1000 documents")
    assert "1000-agriculture.pdf" not in captured
    assert "Saved 20 results to agriculture_bm25_top20.csv" in captured
    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as result_file:
        results = list(csv.DictReader(result_file))
    assert len(results) == 20
    assert list(results[0]) == ["bm25_score", "pdf_url", "text_preview"]
    assert results[0]["pdf_url"] == "https://example.test/0.pdf"
