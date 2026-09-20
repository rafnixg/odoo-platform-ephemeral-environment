# Getting started

## Requirements

- Windows with PowerShell.
- Python 3.12.
- Git.
- Docker Desktop using Linux containers for real builds.

## Installation

From the repository root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Copy `config.example.yaml` to a local file ignored by Git, configure the allowed repositories, and
export its absolute path:

```powershell
Copy-Item config.example.yaml config.local.yaml
$env:MINI_RUNBOT_CONFIG = (Resolve-Path config.local.yaml)
mini-runbot doctor
```

`doctor` checks Python, Git, Docker, Compose, the daemon, the builds directory, and configured Git
origins.

## Start the dashboard

```powershell
mini-runbot serve --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The dashboard creates and filters builds,
tracks stages, reads logs, opens previews, and destroys runtimes.

## First build

The `custom` alias must exist in your [configuration](configuration.md):

```powershell
mini-runbot build create `
  --repo custom `
  --ref 16.0 `
  --modules sale,website `
  --run
```

Keep the displayed ID. Inspect it with `mini-runbot build get BUILD_ID` and destroy its runtime with
`mini-runbot build destroy BUILD_ID`.

!!! note
    Without `--run`, the CLI only creates the record. The API instead returns `202 Accepted` and
    automatically dispatches the build to the local executor.
