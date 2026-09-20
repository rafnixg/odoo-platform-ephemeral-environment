# Getting started

## Requirements

Mini-Runbot uses the same code and lifecycle on both systems:

- Python 3.12 and Git.
- Docker Compose v2, available as `docker compose`.
- Write access to `builds_root` and access to the Docker daemon.

=== "Windows"

    - Windows 10/11 with PowerShell.
    - Docker Desktop configured for Linux containers.
    - Virtualization and WSL 2 enabled when required by Docker Desktop.

=== "Linux"

    - A Linux distribution with Bash.
    - Docker Engine and the Docker Compose v2 plugin.
    - The user must be able to access the Docker socket. Membership in the `docker` group grants
      elevated control over the host; follow your team's security policy.

## Installation

From the repository root:

=== "Windows · PowerShell"

    ```powershell
    py -3.12 -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -e ".[dev]"
    ```

=== "Linux · Bash"

    ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev]"
    ```

Copy `config.example.yaml` to a local file ignored by Git, configure the allowed repositories, and
export its absolute path:

=== "Windows · PowerShell"

    ```powershell
    Copy-Item config.example.yaml config.local.yaml
    $env:MINI_RUNBOT_CONFIG = (Resolve-Path config.local.yaml).Path
    mini-runbot doctor
    ```

=== "Linux · Bash"

    ```bash
    cp config.example.yaml config.local.yaml
    export MINI_RUNBOT_CONFIG="$(realpath config.local.yaml)"
    mini-runbot doctor
    ```

`doctor` checks Python, Git, Docker, Compose, the daemon, the builds directory, and configured Git
origins. Resolve every failed check before creating a real build.

## Start the dashboard

The command is the same in PowerShell and Bash:

```console
mini-runbot serve --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The dashboard creates and filters builds,
tracks stages, reads logs, opens previews, and destroys runtimes.

## First build

The `custom` alias must exist in your [configuration](configuration.md):

```console
mini-runbot build create --repo custom --ref 16.0 --modules sale,website --run
```

Keep the displayed ID. Inspect it with `mini-runbot build get BUILD_ID` and destroy its runtime with
`mini-runbot build destroy BUILD_ID`.

!!! note
    Without `--run`, the CLI only creates the record. The API instead returns `202 Accepted` and
    automatically dispatches the build to the local executor.

## Controlled demo

The demo uses `config.demo.yaml`, resolves this repository's `HEAD`, and installs the
`mini_runbot_demo` module.

=== "Windows · PowerShell"

    ```powershell
    powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1
    ```

=== "Linux · Bash"

    ```bash
    export MINI_RUNBOT_CONFIG="$(realpath config.demo.yaml)"
    python -m mini_runbot.cli.main doctor
    python -m mini_runbot.cli.main build create \
      --repo demo --ref HEAD --modules mini_runbot_demo --run
    ```

The demo intentionally leaves the preview running. Destroy the reported build ID when finished.
