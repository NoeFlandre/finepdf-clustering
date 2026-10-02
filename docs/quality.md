# Quality gates

GitHub Actions runs `scripts/quality_gate.sh` for each branch push. It also runs the script for each pull request that targets `main`. You can run the same script on your computer.

```sh
bash scripts/quality_gate.sh
```

## Checks

The gate does these checks:

1. It checks the committed `uv.lock`.
2. It runs the configured pre-commit hooks.
3. It checks the types in `src` and `tests`.
4. It runs pytest.

Pytest must pass with **100% line coverage and 100% branch coverage** for `src/finepdf_clustering`.

## CRAP score

The CRAP checker reads the coverage JSON report. Each function in `src/finepdf_clustering` must have a CRAP score **strictly below 6**. The checker uses the cyclomatic complexity from Radon. It also uses the executed lines and the missing lines from coverage.py.

## Documentation and mutation tests

The gate builds the documentation in MkDocs strict mode.

The gate runs mutation tests on a temporary copy of the repository. **The tests must kill each generated mutant.** The gate fails when a mutant is in one of these states:

- survived
- skipped
- untested
- timed out
- interrupted
- suspicious
- incomplete

## Output

The reports, the mutation caches, and the built documentation stay in temporary directories. The gate does not leave generated QA files in the checkout.
