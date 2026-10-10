# Changelog

## 0.3.0 — 2026-10-10

- Add `odoo_versions` image profiles so each build runs on its own Odoo series, selected with
  `--odoo-version`, the dashboard, the API, or the Git reference name.
- Verify real builds on Odoo 16.0, 17.0, 18.0, 19.0, and 20.0.
- Bind the preview server to every container interface so Odoo 20 previews are reachable.
- Request demo data explicitly on Odoo 19 and later, where it is no longer loaded by default.
- Fail the `install` stage when Odoo leaves a requested module uninstalled instead of reporting
  a successful build.
- Make the demo addon manifest version valid on every supported series.
- Fix `mini-runbot serve` exiting on Windows when its output is redirected.
- Keep CI aligned with the error and log evidence returned for unrecognized Odoo image banners.

## 0.2.1 — 2026-09-20

- License the project under AGPL-3.0-or-later.
- Include the license expression and license file in Python distribution metadata.
- Strengthen the distribution check so wheels must contain the AGPL metadata and `LICENSE`.

## 0.2.0 — 2026-09-20

- First PyPI release as the self-contained `mini-runbot` CLI application.
- Add `mini-runbot init` and packaged runtime resources.
