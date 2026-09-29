#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_ROOT="${TMPDIR:-/tmp}"
RUN_ROOT="$(mktemp -d "${TEMP_ROOT%/}/finepdf-clustering-qa.XXXXXX")"
trap 'rm -rf "$RUN_ROOT"' EXIT

export UV_CACHE_DIR="${UV_CACHE_DIR:-${TEMP_ROOT%/}/finepdf-clustering-uv-cache}"
export UV_PROJECT_ENVIRONMENT="$RUN_ROOT/venv"
export COVERAGE_FILE="$RUN_ROOT/.coverage"
export PYTHONDONTWRITEBYTECODE=1

cd "$ROOT"

echo "==> Checking the uv lockfile"
uv lock --check

echo "==> Installing locked development dependencies"
uv sync --locked --all-groups

echo "==> Checking QA script syntax"
bash -n scripts/quality_gate.sh

echo "==> Running pre-commit lint and format hooks"
uv run --locked pre-commit run --all-files

echo "==> Checking Python types"
uv run --locked ty check src tests

echo "==> Running tests with 100% line and branch coverage"
COVERAGE_JSON="$RUN_ROOT/coverage.json"
uv run --locked pytest \
  --cov=finepdf_clustering \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report="json:$COVERAGE_JSON"

echo "==> Enforcing CRAP below 6 for every source function"
PYTHONPATH="$ROOT/src" uv run --locked python -m finepdf_clustering.crap \
  --root "$ROOT" \
  --coverage-json "$COVERAGE_JSON"

echo "==> Building documentation in strict mode"
uv run --locked mkdocs build --strict --site-dir "$RUN_ROOT/site"

echo "==> Creating a disposable copy for mutation testing"
MUTATION_ROOT="$RUN_ROOT/mutation-project"
uv run --locked python - "$ROOT" "$MUTATION_ROOT" <<'PY'
from __future__ import annotations

import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
ignored = shutil.ignore_patterns(
    ".git",
    ".venv",
    ".uv-cache",
    ".tmp",
    ".ruff_cache",
    ".ty_cache",
    "__pycache__",
    ".coverage*",
    ".DS_Store",
    "site",
    "dist",
    "build",
    "*.egg-info",
    "mutants",
)
shutil.copytree(source, destination, ignore=ignored)
PY

echo "==> Running all configured mutants"
MUTATION_LOG="$RUN_ROOT/mutmut.log"
(
  cd "$MUTATION_ROOT"
  if ! uv run --locked mutmut run --max-children 2 >"$MUTATION_LOG" 2>&1; then
    tail -n 60 "$MUTATION_LOG"
    exit 1
  fi
  uv run --locked mutmut export-cicd-stats
  uv run --locked python - "mutants/mutmut-cicd-stats.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

stats = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
total = int(stats.get("total", 0))
killed = int(stats.get("killed", 0))
incomplete = {
    name: int(stats.get(name, 0))
    for name in (
        "survived",
        "no_tests",
        "skipped",
        "suspicious",
        "timeout",
        "check_was_interrupted_by_user",
        "segfault",
    )
    if int(stats.get(name, 0)) != 0
}
print(f"Mutation results: killed={killed}, total={total}")
if incomplete:
    print(f"Mutation gate rejected incomplete or surviving results: {incomplete}")
if total == 0 or killed != total or incomplete:
    raise SystemExit(1)
PY
)

echo "==> All quality gates passed"
