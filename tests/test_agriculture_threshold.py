from __future__ import annotations

import json
from pathlib import Path

import pytest

from finepdf_clustering.agriculture_bm25 import (
    SearchResult,
    is_eligible_score,
    percentile_threshold,
    select_by_percentile,
    write_metrics,
)


def test_percentile_threshold_interpolates_sorted_scores() -> None:
    assert percentile_threshold([30.0, 0.0, 20.0, 10.0], 50.0) == 15.0


def test_percentile_threshold_supports_percentile_edges() -> None:
    assert percentile_threshold([3.0, 1.0, 2.0], 0.0) == 1.0
    assert percentile_threshold([3.0, 1.0, 2.0], 100.0) == 3.0


def test_percentile_threshold_interpolates_before_upper_bound() -> None:
    assert percentile_threshold([1.0, 2.0, 3.0], 75.0) == 2.5


def test_percentile_threshold_rejects_empty_scores() -> None:
    with pytest.raises(ValueError) as error:
        percentile_threshold([], 99.0)

    assert str(error.value) == "percentile calculation requires at least one score"


@pytest.mark.parametrize("percentile", [-0.1, 100.1])
def test_percentile_threshold_rejects_out_of_range_percentile(
    percentile: float,
) -> None:
    with pytest.raises(ValueError) as error:
        percentile_threshold([1.0], percentile)

    assert str(error.value) == "percentile must be between 0 and 100"


def test_select_by_percentile_excludes_zeroes_and_keeps_cutoff_ties() -> None:
    results = [
        SearchResult(float(score), str(score), str(score))
        for score in (0, 0, 0, 2, 2, 3)
    ]

    threshold, selected = select_by_percentile(results, 50.0)

    assert threshold == 1.0
    assert [result.bm25_score for result in selected] == [2.0, 2.0, 3.0]


def test_select_by_percentile_handles_no_results() -> None:
    assert select_by_percentile([], 99.0) == (0.0, [])


@pytest.mark.parametrize(
    ("score", "threshold", "expected"),
    [
        (0.0, 0.0, False),
        (1.0, 1.0, True),
        (1.0, 2.0, False),
        (2.0, 2.0, True),
    ],
)
def test_is_eligible_score_requires_positive_score_at_cutoff(
    score: float, threshold: float, expected: bool
) -> None:
    assert is_eligible_score(score, threshold) is expected


def test_write_metrics_uses_stable_json_format_and_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "metrics.json"
    metrics = {"zulu": 1, "café": "é"}
    original_open = Path.open
    open_calls: list[tuple[str, str | None]] = []

    def record_open(
        path: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ):
        open_calls.append((mode, encoding))
        return original_open(path, mode, buffering, encoding, errors, newline)

    monkeypatch.setattr(Path, "open", record_open)

    write_metrics(metrics, output_path)

    assert open_calls == [("w", "utf-8")]
    assert output_path.read_text(encoding="utf-8") == (
        '{\n  "caf\\u00e9": "\\u00e9",\n  "zulu": 1\n}\n'
    )
    assert json.loads(output_path.read_text(encoding="utf-8")) == metrics
