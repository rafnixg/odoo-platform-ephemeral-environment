# Mini-Runbot for Odoo 16

Mini-Runbot turns authorized Git revisions and a module list into an isolated, tested, temporary
Odoo 16 environment. It is a single-host proof of concept for trusted code.

## What it provides

- Resolves Git refs to immutable commits and creates separate checkouts.
- Combines up to ten configured repositories with deterministic addon priority.
- Installs modules, runs their tests, starts Odoo, and checks the HTTP preview.
- Stores states, timings, revisions, failures, and logs in SQLite.
- Exposes the same lifecycle through a dashboard, FastAPI API, and Typer CLI.
- Isolates every build with its own Compose project, network, database, volumes, and port.

## Main flow

```text
NEW -> CHECKING_OUT -> PREPARING -> INSTALLING -> TESTING -> STARTING -> RUNNING
                                  \ validation or execution error -> FAILED
RUNNING -> EXPIRED -> DESTROYING -> DESTROYED
```

A build reaches `RUNNING` only after its modules are installed, tests report no failures, the server
starts, and the healthcheck returns a valid response.

## Next step

[Install Mini-Runbot](getting-started.md){ .md-button .md-button--primary }
[Understand the architecture](architecture.md){ .md-button }

!!! warning "Security boundary"
    Docker and input validation reduce accidents, but Mini-Runbot is not a security boundary for
    hostile code. Only use operator-configured, trusted repositories.
