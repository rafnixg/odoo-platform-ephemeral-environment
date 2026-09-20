# Mini-Runbot for Odoo 16 (PoC)

[![CI](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/ci.yml/badge.svg)](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/ci.yml)
[![Documentation](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/docs.yml/badge.svg)](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/docs.yml)
[![CodeQL](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/codeql.yml/badge.svg)](https://github.com/rafnixg/odoo-platform-ephemeral-environment/actions/workflows/codeql.yml)

Mini-Runbot turns configured Git revisions and Odoo module lists into isolated, tested, temporary
Odoo 16 environments. It is a local, single-host proof of concept for trusted repositories, not a
security boundary for hostile code.

## Documentation

- [Documentación en español](https://rafnixg.github.io/odoo-platform-ephemeral-environment/)
- [English documentation](https://rafnixg.github.io/odoo-platform-ephemeral-environment/en/)
- [Documentation sources](gh-docs/es/index.md)

The portal covers installation, configuration, dashboard and CLI usage, the HTTP API, architecture,
operations, security limits, testing, the roadmap, and architecture decisions.

## Quick start

Python 3.12, Git, and Docker Compose v2 are required. On Windows, use Docker Desktop with Linux
containers; on Linux, use Docker Engine with the Compose v2 plugin.

### Windows · PowerShell

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item config.example.yaml config.local.yaml
$env:MINI_RUNBOT_CONFIG = (Resolve-Path config.local.yaml)
mini-runbot doctor
mini-runbot serve --reload
```

### Linux · Bash

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp config.example.yaml config.local.yaml
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
python scripts/check_docs.py
python -m mkdocs build --strict --config-file gh-docs/mkdocs.es.yml --site-dir ../site
python -m mkdocs build --strict --config-file gh-docs/mkdocs.en.yml --site-dir ../site/en
git diff --check
```

Docker-marked end-to-end tests remain an explicit local check because they require a working daemon,
image registry access, and real Odoo startup.
