# Mini-Runbot for Odoo 16 (PoC)

[![CI](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/ci.yml/badge.svg)](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/ci.yml)
[![Documentation](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/docs.yml/badge.svg)](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/docs.yml)
[![CodeQL](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/codeql.yml/badge.svg)](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/codeql.yml)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/rafnixg/odoo-platform-ephemeral-environment)

Mini-Runbot turns configured Git revisions and Odoo module lists into isolated, tested, temporary
Odoo 16 environments. It is a local, single-host proof of concept for trusted repositories, not a
security boundary for hostile code.

## Documentation

- [Documentación en español](https://rafnixg.github.io/odoo-platform-ephemeral-environment/)
- [English documentation](https://rafnixg.github.io/odoo-platform-ephemeral-environment/en/)
- [Documentation sources](gh-docs/es/index.md)
- [Explore the codebase in DeepWiki](https://deepwiki.com/rafnixg/odoo-platform-ephemeral-environment)

The bilingual portal is the canonical project documentation. It covers installation on Windows and
Linux, configuration, dashboard and CLI usage, the HTTP API, operations, security limits, testing,
the roadmap, and architecture decisions. Its technical guides connect behavior to the current
implementation:

- [Domain model and lifecycle](gh-docs/en/domain-model.md)
- [Eight-stage build pipeline](gh-docs/en/build-pipeline.md)
- [Concurrency, cleanup, and recovery](gh-docs/en/concurrency-recovery.md)
- [Ports and adapters](gh-docs/en/adapters.md)
- [Troubleshooting and operator runbook](gh-docs/en/troubleshooting.md)
- [CI/CD and automated security](gh-docs/en/ci-cd.md)
- [Glossary](gh-docs/en/glossary.md)

DeepWiki provides a generated, code-oriented view that complements the maintained portal; when the
two differ, the repository documentation and implementation are authoritative.

## Quick start

Python 3.12, Git, and Docker Compose v2 are required. On Windows, use Docker Desktop with Linux
containers; on Linux, use Docker Engine with the Compose v2 plugin.

### PyPI application

Mini-Runbot is packaged as a CLI application. After the first PyPI release, install it in an
isolated environment with `pipx`:

```console
pipx install mini-runbot
mini-runbot init
```

Until that release, clone the repository and run `pipx install .`, or use the development setup
below. `init` asks for runtime and allowed-repository settings and refuses to overwrite an existing
`config.local.yaml`. Use `mini-runbot init --defaults` for the bundled example values.

### Development installation

#### Windows · PowerShell

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
mini-runbot init
$env:MINI_RUNBOT_CONFIG = (Resolve-Path config.local.yaml)
mini-runbot doctor
mini-runbot serve --reload
```

#### Linux · Bash

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
mini-runbot init
export MINI_RUNBOT_CONFIG="$(realpath config.local.yaml)"
mini-runbot doctor
mini-runbot serve --reload
```

Open `http://127.0.0.1:8000`, or create a build from the CLI:

```console
mini-runbot build create --repo custom --ref 16.0 --modules module_a,module_b --run
```

Repository inputs are configured aliases, never arbitrary URLs or filesystem paths supplied by a
client.

## Local checks

The same commands work in an activated PowerShell or Bash environment:

```console
python -m pip install -e ".[dev,docs]"
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

Docker-marked end-to-end tests remain an explicit local check because they require a working daemon,
image registry access, and real Odoo startup.
