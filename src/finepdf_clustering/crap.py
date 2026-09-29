"""Calculate and enforce CRAP scores for project functions."""

from __future__ import annotations

import argparse
import ast
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from radon.complexity import cc_visit
from radon.visitors import Function

MAX_CRAP_SCORE = 6.0


@dataclass(frozen=True)
class FunctionScore:
    """Complexity, coverage, and CRAP score for one Python function."""

    path: str
    name: str
    line: int
    complexity: int
    line_coverage: float
    crap: float


def calculate_crap_score(complexity: int, line_coverage: float) -> float:
    """Return the CRAP score for a function's complexity and line coverage."""
    if complexity < 1:
        raise ValueError("complexity must be at least 1")
    if not math.isfinite(line_coverage) or not 0.0 <= line_coverage <= 1.0:
        raise ValueError("line coverage must be finite and between 0 and 1")

    return complexity**2 * (1.0 - line_coverage) ** 3 + complexity


def function_statement_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> frozenset[int]:
    """Return statement lines owned by a function, excluding nested bodies."""
    lines: set[int] = set()
    statements = list(node.body)

    while statements:
        statement = statements.pop()
        lines.add(statement.lineno)
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        statements.extend(
            child
            for child in ast.iter_child_nodes(statement)
            if isinstance(child, ast.stmt)
        )

    return frozenset(lines)


def _coverage_for_source(
    source_path: Path,
    coverage_files: Mapping[str, Any],
    project_root: Path,
) -> Mapping[str, Any]:
    """Find one source file's coverage record, accepting relative report paths."""
    resolved_source = source_path.resolve()
    for coverage_path, record in coverage_files.items():
        candidate = (project_root / coverage_path).resolve()
        if candidate == resolved_source:
            if not isinstance(record, dict):
                raise ValueError(
                    f"Coverage record for {coverage_path} must be an object"
                )
            return record

    relative_path = source_path.relative_to(project_root)
    raise ValueError(f"coverage data is missing for {relative_path.as_posix()}")


def _function_nodes(
    syntax_tree: ast.Module,
) -> dict[tuple[str, int], ast.FunctionDef | ast.AsyncFunctionDef]:
    """Index function AST nodes by their name and definition line."""
    return {
        (node.name, node.lineno): node
        for node in ast.walk(syntax_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def score_source_file(
    source_path: Path,
    coverage_record: Mapping[str, Any],
    project_root: Path | None = None,
) -> list[FunctionScore]:
    """Calculate scores for every function in one source file."""
    source_path = source_path.resolve()
    root = (project_root or source_path.parent).resolve()
    source = source_path.read_bytes().decode()
    syntax_tree = ast.parse(source, filename=str(source_path))
    function_nodes = _function_nodes(syntax_tree)
    executed_lines = set(coverage_record.get("executed_lines", []))
    missing_lines = set(coverage_record.get("missing_lines", []))
    executable_lines = executed_lines | missing_lines
    relative_path = source_path.relative_to(root).as_posix()
    scores: list[FunctionScore] = []

    for block in cc_visit(source):
        if not isinstance(block, Function):
            continue

        scores.append(
            _score_function(
                block,
                function_nodes,
                executable_lines,
                executed_lines,
                relative_path,
            )
        )

    return scores


def _score_function(
    block: Function,
    function_nodes: Mapping[tuple[str, int], ast.FunctionDef | ast.AsyncFunctionDef],
    executable_lines: set[int],
    executed_lines: set[int],
    relative_path: str,
) -> FunctionScore:
    """Score one Radon function block against its matching AST node."""
    node = function_nodes.get((block.name, block.lineno))
    if node is None:
        raise ValueError(
            f"Could not match function {block.name} at {relative_path}:{block.lineno}"
        )
    statement_lines = function_statement_lines(node) & executable_lines
    if not statement_lines:
        raise ValueError(
            f"{relative_path}:{block.lineno} {block.name} has no executable "
            "coverage lines"
        )

    line_coverage = len(statement_lines & executed_lines) / len(statement_lines)
    return FunctionScore(
        path=relative_path,
        name=block.name,
        line=block.lineno,
        complexity=block.complexity,
        line_coverage=line_coverage,
        crap=calculate_crap_score(block.complexity, line_coverage),
    )


def score_project(
    project_root: Path, coverage_report: Mapping[str, Any]
) -> list[FunctionScore]:
    """Calculate CRAP scores for all Python functions under ``src``."""
    root = project_root.resolve()
    files = coverage_report.get("files")
    if not isinstance(files, dict):
        raise ValueError("Coverage JSON must contain a files object")

    source_root = root / "src" / "finepdf_clustering"
    scores: list[FunctionScore] = []
    for source_path in sorted(source_root.rglob("*.py")):
        coverage_record = _coverage_for_source(source_path, files, root)
        scores.extend(score_source_file(source_path, coverage_record, root))

    if not scores:
        raise ValueError(f"No Python functions found under {source_root}")
    return scores


def _load_coverage(path: Path) -> Mapping[str, Any]:
    report = json.loads(path.read_bytes().decode())
    if not isinstance(report, dict):
        raise ValueError("Coverage JSON must contain an object")
    return report


def _print_scores(scores: Sequence[FunctionScore]) -> None:
    for score in scores:
        print(
            f"{score.path}:{score.line} {score.name}: "
            f"CC={score.complexity} line_coverage={score.line_coverage:.1%} "
            f"CRAP={score.crap:.3f}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CRAP gate against a coverage.py JSON report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--coverage-json", type=Path, required=True)
    arguments = parser.parse_args(argv)

    try:
        scores = score_project(arguments.root, _load_coverage(arguments.coverage_json))
    except (OSError, json.JSONDecodeError, SyntaxError, TypeError, ValueError) as error:
        print(f"Unable to calculate CRAP scores: {error}", file=sys.stderr)
        return 2

    _print_scores(scores)
    failing_scores = [score for score in scores if score.crap >= MAX_CRAP_SCORE]
    if failing_scores:
        print("CRAP score must be below 6 for every function", file=sys.stderr)
        return 1

    print(f"CRAP gate passed: all {len(scores)} functions score below 6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # pragma: no cover
