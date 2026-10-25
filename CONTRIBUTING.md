# Contributing

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # needs Java 17+ for PySpark
make check                   # ruff, tests, JSON/YAML validation
```

## Workflow

1. Branch from `main` (`feat/...`, `fix/...`, `docs/...`).
2. Keep transformation logic in `src/retail360/` as pure DataFrame functions so it can be unit
   tested on a local Spark session; job entry points and the DLT pipeline stay thin.
3. New or changed quality rules go in `src/retail360/quality.py`; they are shared by the DLT
   pipeline, the DQ job and the tests.
4. Infrastructure changes: run `terraform fmt` and attach the plan to the pull request.
5. Open a pull request. CI must be green and a code owner must approve.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`).

## Architecture decisions

Significant choices are recorded as ADRs in [docs/adr](docs/adr). Add a new numbered file when
you change something the ADRs describe.
