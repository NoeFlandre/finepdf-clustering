# Quality gates

GitHub Actions runs `scripts/quality_gate.sh` for every branch push and for pull requests targeting `main`. The same script is available locally.

```sh
bash scripts/quality_gate.sh
```

The gate checks the committed `uv.lock`, runs the configured pre-commit hooks, and type-checks `src` and `tests`. Pytest must pass with **100% line coverage and 100% branch coverage** for `src/finepdf_clustering`.

The coverage JSON report feeds the CRAP checker. Every function in `src/finepdf_clustering` must have a CRAP score **strictly below 6**. The checker uses Radon's cyclomatic complexity and coverage.py's executed and missing lines.

The gate also builds the documentation with MkDocs strict mode. Mutation testing runs against a temporary copy of the repository; **every generated mutant must be killed by the tests**. Surviving, skipped, untested, timed out, interrupted, suspicious, or otherwise incomplete mutants fail the gate.

Reports, mutation caches, and the built documentation stay in temporary directories, so the gate leaves no generated QA artifacts in the checkout.
