# CLI reference

The CLI and API use the same `BuildManager`, validations, and transitions.

## Initialize configuration

```console
mini-runbot init
mini-runbot init --defaults
mini-runbot init --output another-config.yaml
```

Without `--defaults`, the wizard asks about SQLite, workspaces, images, ports, timeouts,
concurrency, cleanup, retention, and up to ten allowed repositories. Creation is exclusive: when
the target exists, the command exits without modifying it. It then shows how to export
`MINI_RUNBOT_CONFIG` in PowerShell and Bash.

## Builds

Single-line commands work the same in PowerShell and Bash:

```console
# Create and execute
mini-runbot build create --repo custom --ref 16.0 --modules module_a,module_b --run

# Add repositories
mini-runbot build create --repo custom --ref feature/x --extra-repo oca=16.0 --modules module_a --run

# Inspect
mini-runbot build list
mini-runbot build list --status running
mini-runbot build get BUILD_ID
mini-runbot build logs BUILD_ID --stage test

# Execute a new record and destroy a runtime
mini-runbot build run BUILD_ID
mini-runbot build destroy BUILD_ID
```

`create`, `get`, `list`, `run`, and `destroy` accept `--json` for integrations. Repeat
`--extra-repo ALIAS=REF` up to the domain repository limit.

## Service and diagnostics

```console
mini-runbot serve --host 127.0.0.1 --port 8000 --reload
mini-runbot doctor
mini-runbot recover
```

Run `recover` after confirming an orchestrator restart. It classifies interrupted work, reconciles
leases, and retries pending destruction.

## Cleanup

```console
mini-runbot cleanup --expired
mini-runbot cleanup --retained
mini-runbot cleanup --expired --retained --json
```

`--expired` destroys runtimes past their TTL. `--retained` permanently removes destroyed audit rows
and logs older than `destroyed_retention_seconds`; it does nothing when retention is zero.
