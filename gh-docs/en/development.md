# Development and tests

## Environment

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,docs]"
```

## Local checks

```powershell
python -m pytest -m "not docker"
python -m ruff check .
node --check src\mini_runbot\web\app.js
python scripts\check_docs.py
python -m mkdocs build --strict --config-file gh-docs\mkdocs.es.yml --site-dir ..\site
python -m mkdocs build --strict --config-file gh-docs\mkdocs.en.yml --site-dir ..\site\en
git diff --check
```

The documentation script requires the same Markdown paths under `gh-docs/es` and `gh-docs/en`.
Both strict builds must finish without warnings.

## Test suites

- `tests/unit`: domain, validation, pipeline, and isolated components.
- `tests/integration`: API, SQLite, local Git, and concurrent port allocation.
- `tests/e2e`: real Odoo lifecycle; tests marked `docker` require a daemon and images.

When checkout, Compose, install, tests, startup, healthchecks, ports, volumes, or cleanup change, run
a real build too. Confirm installed modules, Odoo test results, and an HTTP 200 preview; running
containers alone are not sufficient.

## Documentation

Spanish is published at the site root and English under `/en/`. Edit the same relative path in both
trees. Preview Spanish with:

```powershell
python -m mkdocs serve --config-file gh-docs\mkdocs.es.yml
```

Pull requests build both languages. Pushes to `master` create one artifact and deploy it through the
`github-pages` environment.

## Conventions

Preserve dependency direction, use `pathlib.Path`, keep PowerShell compatibility, and never commit
secrets or generated state. Commits should be focused, imperative Conventional Commits.
