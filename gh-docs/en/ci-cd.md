# CI/CD and automated security

Workflows validate code, dependencies, and documentation. Real Docker/Odoo tests remain explicit
because they require a daemon, images, and more time than the baseline CI job.

## Workflows

| Workflow | Events | Responsibility |
| --- | --- | --- |
| `ci.yml` | Push and PR to `master` | Ruff, non-Docker pytest, JavaScript, wheel/sdist, and whitespace. |
| `docs.yml` | Documentation changes, push/PR, and manual | Translation parity, strict builds, and Pages deployment. |
| `codeql.yml` | Push, PR, and scheduled Monday run | Python, JavaScript/TypeScript, and Actions analysis. |
| `dependency-review.yml` | PR to `master` | Rejects new dependencies with high or critical vulnerabilities. |
| `publish.yml` | `v*` tag | Verifies version, tests, and wheel; publishes to PyPI through OIDC. |

All use minimal permissions and actions compatible with GitHub Actions' current Node runtime. The
non-Docker CI currently runs on Ubuntu; a Windows/Linux matrix is planned in the
[roadmap](roadmap.md).

## Documentation publishing

Pull requests build both languages without deploying. On pushes to `master`, the job creates one
artifact with Spanish at `/` and English at `/en/`; the `deploy` job publishes it through the
`github-pages` environment and OIDC.

For the first deployment, an administrator must configure:

1. **Settings → Pages → Build and deployment → Source → GitHub Actions**.
2. **Settings → Security → Code security and analysis → Dependency graph**.

Without Pages, `configure-pages` returns `Not Found`. Without Dependency Graph, Dependency Review
cannot compare manifests. Adding a PAT does not fix either repository setting.

## Dependabot

Dependabot checks weekly:

- pip: groups minor/patch updates, ignores automated majors, and limits open PRs to five;
- GitHub Actions: updates actions and limits open PRs to five.

Major updates require manual compatibility review. A Dependabot author does not replace CI,
changelog review, or behavior validation.

## Publishing to PyPI

The project is distributed as a CLI application. The workflow only accepts tags that exactly match
`v<project.version>`, builds the wheel and sdist in isolation, and verifies that the entry point,
dashboard, Compose template, and example configuration are included.

Before each publication, an administrator should:

1. confirm the AGPL-3.0-or-later metadata and `LICENSE` file;
2. keep the protected `pypi` environment in GitHub;
3. keep the PyPI Trusted Publisher restricted to this repository and workflow;
4. review the version and create the matching tag, for example `v0.2.1`.

Trusted Publishing uses OIDC and avoids storing a PyPI token in GitHub Secrets. The dashboard also
shows the AGPL notice and a source-code link for remote users.

## Equivalent local checks

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

## Coverage and limits

- CodeQL is static analysis; it does not prove isolation from hostile repositories.
- Dependency Review only evaluates changes in the PR and requires GitHub dependency data.
- Docker E2E is opt-in locally; a manual/scheduled workflow is planned.
- Mermaid renders in the browser, so MkDocs validates the block but not all diagram semantics.

## Related files

- [Workflows](https://github.com/rafnixg/odoo-platform-ephemeral-environment/tree/master/.github/workflows)
- [Dependabot](https://github.com/rafnixg/odoo-platform-ephemeral-environment/blob/master/.github/dependabot.yml)
- [Translation checker](https://github.com/rafnixg/odoo-platform-ephemeral-environment/blob/master/scripts/check_docs.py)
- [Distribution checker](https://github.com/rafnixg/odoo-platform-ephemeral-environment/blob/master/scripts/check_distribution.py)
