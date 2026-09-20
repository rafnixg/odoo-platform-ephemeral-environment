# CI/CD y seguridad automatizada

Los workflows validan código, dependencias y documentación. Las pruebas Docker/Odoo reales siguen
siendo explícitas porque requieren daemon, imágenes y más tiempo que el CI básico.

## Workflows

| Workflow | Eventos | Responsabilidad |
| --- | --- | --- |
| `ci.yml` | Push y PR a `master` | Ruff, pytest sin Docker, JavaScript, wheel/sdist y whitespace. |
| `docs.yml` | Cambios documentales, push/PR y manual | Paridad bilingüe, builds estrictos y despliegue Pages. |
| `codeql.yml` | Push, PR y lunes programado | Análisis de Python, JavaScript/TypeScript y Actions. |
| `dependency-review.yml` | PR a `master` | Rechaza nuevas dependencias con vulnerabilidad alta o crítica. |
| `publish.yml` | Tag `v*` | Verifica versión, pruebas y wheel; publica en PyPI mediante OIDC. |

Todos usan permisos mínimos y acciones compatibles con el runtime Node actual de GitHub Actions.
El CI sin Docker corre hoy en Ubuntu; la matriz Windows/Linux está planificada en el
[roadmap](roadmap.md).

## Publicación de documentación

En pull requests se construyen ambos idiomas sin desplegar. En pushes a `master`, el job genera un
único artefacto con español en `/` e inglés en `/en/`; el job `deploy` lo publica mediante el
environment `github-pages` y OIDC.

La primera vez, un administrador debe configurar:

1. **Settings → Pages → Build and deployment → Source → GitHub Actions**.
2. **Settings → Security → Code security and analysis → Dependency graph**.

Sin Pages habilitado, `configure-pages` devuelve `Not Found`. Sin Dependency Graph, Dependency
Review no puede comparar manifests. Ninguno de los dos casos se arregla agregando un PAT.

## Dependabot

Dependabot revisa semanalmente:

- pip: agrupa actualizaciones minor/patch, ignora majors automáticos y limita cinco PR abiertos;
- GitHub Actions: actualiza acciones y limita cinco PR abiertos.

Una actualización mayor debe revisarse manualmente por compatibilidad. Que un PR provenga de
Dependabot no sustituye CI, revisión de changelog ni validación de comportamiento.

## Publicación en PyPI

El proyecto se distribuye como aplicación CLI. El workflow solo acepta tags que coincidan
exactamente con `v<project.version>`, construye wheel y sdist en aislamiento y comprueba que el
entry point, dashboard, plantilla Compose y ejemplo de configuración estén incluidos.

Antes de la primera publicación, un administrador debe:

1. elegir y añadir la licencia del proyecto;
2. crear el environment protegido `pypi` en GitHub;
3. configurar en PyPI un Trusted Publisher para este repositorio y workflow;
4. revisar la versión y crear el tag, por ejemplo `v0.2.0`.

Trusted Publishing usa OIDC y evita almacenar un token PyPI en GitHub Secrets.

## Comprobaciones locales equivalentes

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

## Cobertura y límites

- CodeQL es análisis estático; no demuestra aislamiento contra repositorios hostiles.
- Dependency Review solo evalúa cambios presentes en el PR y requiere datos de GitHub.
- El E2E Docker se ejecuta localmente con opt-in; un workflow manual/programado está planificado.
- Mermaid se renderiza en el navegador, por lo que el build MkDocs valida el bloque pero no toda la
  semántica gráfica.

## Archivos relacionados

- [Workflows](https://github.com/rafnixg/odoo-platform-ephemeral-environment/tree/master/.github/workflows)
- [Dependabot](https://github.com/rafnixg/odoo-platform-ephemeral-environment/blob/master/.github/dependabot.yml)
- [Validador bilingüe](https://github.com/rafnixg/odoo-platform-ephemeral-environment/blob/master/scripts/check_docs.py)
- [Validador de distribución](https://github.com/rafnixg/odoo-platform-ephemeral-environment/blob/master/scripts/check_distribution.py)
