# CLI reference

The CLI and API use the same `BuildManager`, validations, and transitions.

## Builds

```powershell
# Create and execute
mini-runbot build create --repo custom --ref 16.0 --modules module_a,module_b --run

# Add repositories
mini-runbot build create --repo custom --ref feature/x --extra-repo oca=16.0 `
  --modules module_a --run

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

```powershell
mini-runbot serve --host 127.0.0.1 --port 8000 --reload
mini-runbot doctor
mini-runbot recover
```

Run `recover` after confirming an orchestrator restart. It classifies interrupted work, reconciles
leases, and retries pending destruction.

## Cleanup

```powershell
mini-runbot cleanup --expired
mini-runbot cleanup --retained
mini-runbot cleanup --expired --retained --json
```

`--expired` destroys runtimes past their TTL. `--retained` permanently removes destroyed audit rows
and logs older than `destroyed_retention_seconds`; it does nothing when retention is zero.
