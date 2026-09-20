# Functional guide

## Create a build

A build needs repositories, Git refs, Odoo modules, and optionally a TTL. Repository inputs are
operator-defined aliases; neither the API nor CLI accepts arbitrary URLs or paths.

Use the dashboard to select repositories and refs, add modules, and submit the form. From the CLI:

```powershell
mini-runbot build create `
  --repo custom --ref feature/catalog `
  --extra-repo oca=16.0 `
  --modules custom_sale,website_sale `
  --ttl-seconds 14400 `
  --run
```

Each alias's `addons_priority` determines `addons_path` order; payload order does not.

## Read statuses and stages

| Status | Meaning |
| --- | --- |
| `new` | Persisted and not executed yet. |
| `checking_out` | Resolving and checking out Git revisions. |
| `preparing` | Rendering and validating Docker Compose. |
| `installing` | Creating the database and installing modules. |
| `testing` | Running Odoo tests. |
| `starting` | Starting the server and running the healthcheck. |
| `running` | Preview available. |
| `failed` | A stage failed and evidence was retained. |
| `expired` | The TTL ended and cleanup is pending. |
| `destroying` / `destroyed` | Runtime removal in progress / completed. |

Each stage records start, finish, duration, exit code, summary, and a log path when applicable.

## Inspect and diagnose

- Use dashboard filters or `mini-runbot build list --status failed`.
- Open a build to inspect its timeline and failure message.
- Read one stage with `mini-runbot build logs BUILD_ID --stage test`.
- Timestamps are stored in UTC and displayed in the browser's local time zone.

## Destroy and clean up

`build destroy` removes the Compose containers, network, and volumes while retaining the audit row
and logs. It is idempotent. Scheduled cleanup can destroy expired builds and, when positive
retention is configured, purge old audit data.

A build cannot be destroyed while its local worker is still executing it.
