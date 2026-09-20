# Development and tests

## Environment

=== "Windows · PowerShell"

    ```powershell
    py -3.12 -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -e ".[dev,docs]"
    ```

=== "Linux · Bash"

    ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev,docs]"
    ```

## Local checks

The following commands use `/` and work unchanged in PowerShell and Bash:

```console
python -m pytest -m "not docker"
python -m ruff check .
node --check src/mini_runbot/web/app.js
python -m build
python scripts/check_distribution.py dist
python scripts/check_docs.py
python -m mkdocs build --strict --config-file gh-docs/mkdocs.es.yml --site-dir ../site
python -m mkdocs build --strict --config-file gh-docs/mkdocs.en.yml --site-dir ../site/en
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

```console
python -m mkdocs serve --config-file gh-docs/mkdocs.es.yml
```

Pull requests build both languages. Pushes to `master` create one artifact and deploy it through the
`github-pages` environment.

Before the first deployment, an administrator must select **GitHub Actions** under
**Settings → Pages → Build and deployment → Source**. The Dependency Review workflow also requires
**Dependency graph** under **Settings → Security → Code security and analysis** to compare
manifests. These are one-time repository settings and do not require adding a PAT to the workflows.

## Conventions

Preserve dependency direction, use `pathlib.Path`, and maintain compatibility with both PowerShell
on Windows and Bash on Linux. Never commit secrets or generated state. Commits should be focused,
imperative Conventional Commits.
