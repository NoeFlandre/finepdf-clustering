from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from radon.visitors import Function

import finepdf_clustering.crap as crap
from finepdf_clustering.crap import (
    calculate_crap_score,
    function_statement_lines,
    main,
    score_project,
    score_source_file,
)


@pytest.mark.parametrize(
    ("complexity", "coverage", "expected"),
    [(1, 0.0, 2.0), (4, 0.5, 6.0), (5, 1.0, 5.0)],
)
def test_calculate_crap_score(
    complexity: int, coverage: float, expected: float
) -> None:
    assert calculate_crap_score(complexity, coverage) == expected


@pytest.mark.parametrize(
    ("complexity", "coverage"),
    [(0, 1.0), (-1, 0.5), (1, -0.1), (1, 1.1), (1, float("nan"))],
)
def test_calculate_crap_score_rejects_invalid_inputs(
    complexity: int, coverage: float
) -> None:
    with pytest.raises(ValueError) as error:
        calculate_crap_score(complexity, coverage)
    expected_message = (
        "complexity must be at least 1"
        if complexity < 1
        else "line coverage must be finite and between 0 and 1"
    )
    assert str(error.value) == expected_message


def test_function_statement_lines_excludes_nested_function_and_class_bodies() -> None:
    source = """\
def outer(enabled):
    def inner():
        if enabled:
            return 10
        return 5
    class Nested:
        def method(self):
            return 20
    if enabled:
        return inner()
    return 0
"""
    outer = ast.parse(source).body[0]

    assert isinstance(outer, ast.FunctionDef)
    assert function_statement_lines(outer) == frozenset({2, 6, 9, 10, 11})


def test_score_source_file_uses_function_body_line_coverage(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        "def classify(value: int) -> str:\n"
        "    if value > 0:\n"
        "        return 'positive'\n"
        "    return 'nonpositive'\n",
        encoding="utf-8",
    )

    scores = score_source_file(
        source,
        {"executed_lines": [1, 2, 4], "missing_lines": [3]},
    )

    assert len(scores) == 1
    assert scores[0].name == "classify"
    assert scores[0].path == "sample.py"
    assert scores[0].line == 1
    assert scores[0].complexity == 2
    assert scores[0].line_coverage == pytest.approx(2 / 3)
    assert scores[0].crap == pytest.approx(2 + 4 / 27)


def test_score_source_file_scores_methods_and_skips_class_blocks(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        "class Answer:\n    def value(self) -> int:\n        return 42\n",
        encoding="utf-8",
    )

    scores = score_source_file(
        source,
        {"executed_lines": [1, 2, 3], "missing_lines": []},
    )

    assert [(score.name, score.complexity) for score in scores] == [("value", 1)]


def test_score_source_file_rejects_functions_with_no_coverage_statements(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")

    with pytest.raises(ValueError, match="has no executable coverage lines"):
        score_source_file(source, {"executed_lines": [1], "missing_lines": []})


def test_score_source_file_reports_unmatched_complexity_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")
    monkeypatch.setattr(
        crap,
        "cc_visit",
        lambda _: [Function("missing", 1, 0, 2, False, None, [], 1)],
    )

    with pytest.raises(ValueError, match="Could not match function missing"):
        score_source_file(source, {"executed_lines": [1, 2], "missing_lines": []})


def test_score_source_file_reports_source_filename_for_syntax_errors(
    tmp_path: Path,
) -> None:
    source = tmp_path / "broken.py"
    source.write_text("def answer(:\n    return 42\n", encoding="utf-8")

    with pytest.raises(SyntaxError) as error:
        score_source_file(source, {"executed_lines": [], "missing_lines": []})

    assert error.value.filename == str(source)


def test_score_source_file_defaults_missing_coverage_lines_to_empty(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")

    with pytest.raises(ValueError, match="has no executable coverage lines"):
        score_source_file(source, {})


def test_score_project_finds_relative_coverage_paths(tmp_path: Path) -> None:
    source = tmp_path / "src/finepdf_clustering/sample.py"
    source.parent.mkdir(parents=True)
    source.write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")
    coverage = {
        "files": {
            "other.py": {"executed_lines": [], "missing_lines": []},
            "src/finepdf_clustering/sample.py": {
                "executed_lines": [1, 2],
                "missing_lines": [],
            },
        }
    }

    scores = score_project(tmp_path, coverage)

    assert [score.name for score in scores] == ["answer"]
    assert scores[0].line_coverage == 1.0


def test_score_project_rejects_non_object_coverage_record(tmp_path: Path) -> None:
    source = tmp_path / "src/finepdf_clustering/sample.py"
    source.parent.mkdir(parents=True)
    source.write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        score_project(
            tmp_path,
            {"files": {"src/finepdf_clustering/sample.py": []}},
        )
    assert str(error.value) == (
        "Coverage record for src/finepdf_clustering/sample.py must be an object"
    )


def test_score_project_rejects_non_object_files_value(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as error:
        score_project(tmp_path, {"files": []})
    assert str(error.value) == "Coverage JSON must contain a files object"


def test_score_project_rejects_missing_coverage_file(tmp_path: Path) -> None:
    source = tmp_path / "src/finepdf_clustering/sample.py"
    source.parent.mkdir(parents=True)
    source.write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")

    with pytest.raises(ValueError, match="coverage data is missing"):
        score_project(tmp_path, {"files": {}})


def test_score_project_rejects_source_tree_without_functions(tmp_path: Path) -> None:
    source = tmp_path / "src/finepdf_clustering/__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text('"""Package marker."""\n', encoding="utf-8")

    with pytest.raises(ValueError, match="No Python functions found"):
        score_project(
            tmp_path,
            {
                "files": {
                    "src/finepdf_clustering/__init__.py": {
                        "executed_lines": [1],
                        "missing_lines": [],
                    }
                }
            },
        )


def test_main_passes_when_every_crap_score_is_below_six(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "src/finepdf_clustering/sample.py"
    source.parent.mkdir(parents=True)
    source.write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "files": {
                    "src/finepdf_clustering/sample.py": {
                        "executed_lines": [1, 2],
                        "missing_lines": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = main(["--root", str(tmp_path), "--coverage-json", str(coverage_path)])

    assert result == 0
    output = capsys.readouterr().out
    assert "src/finepdf_clustering/sample.py:1 answer: CC=1" in output
    assert "line_coverage=100.0% CRAP=1.000" in output
    assert "CRAP gate passed" in output


def test_main_help_includes_the_tool_description(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--help"])

    assert error.value.code == 0
    assert "Calculate and enforce CRAP scores" in capsys.readouterr().out


def test_main_requires_coverage_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--root", str(tmp_path)])

    assert error.value.code == 2
    assert "the following arguments are required: --coverage-json" in (
        capsys.readouterr().err
    )


def test_main_uses_current_directory_as_default_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "src/finepdf_clustering/sample.py"
    source.parent.mkdir(parents=True)
    source.write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "files": {
                    "src/finepdf_clustering/sample.py": {
                        "executed_lines": [1, 2],
                        "missing_lines": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert main(["--coverage-json", str(coverage_path)]) == 0
    assert "CRAP gate passed" in capsys.readouterr().out


def test_main_fails_when_crap_score_is_six_or_higher(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "src/finepdf_clustering/sample.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def complex_function(value):\n"
        "    if value > 0: value += 1\n"
        "    if value > 1: value += 1\n"
        "    if value > 2: value += 1\n"
        "    if value > 3: value += 1\n"
        "    if value > 4: value += 1\n"
        "    return value\n",
        encoding="utf-8",
    )
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "files": {
                    "src/finepdf_clustering/sample.py": {
                        "executed_lines": list(range(1, 8)),
                        "missing_lines": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = main(["--root", str(tmp_path), "--coverage-json", str(coverage_path)])

    assert result == 1
    assert capsys.readouterr().err == "CRAP score must be below 6 for every function\n"


def test_main_reports_invalid_coverage_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_coverage = tmp_path / "missing.json"

    result = main(["--root", str(tmp_path), "--coverage-json", str(missing_coverage)])

    assert result == 2
    assert "Unable to calculate CRAP scores" in capsys.readouterr().err


def test_main_rejects_coverage_json_that_is_not_an_object(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    invalid_coverage = tmp_path / "invalid.json"
    invalid_coverage.write_text("[]", encoding="utf-8")

    result = main(["--root", str(tmp_path), "--coverage-json", str(invalid_coverage)])

    assert result == 2
    assert capsys.readouterr().err == (
        "Unable to calculate CRAP scores: Coverage JSON must contain an object\n"
    )
