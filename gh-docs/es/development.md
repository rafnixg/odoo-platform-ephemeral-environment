# Desarrollo y pruebas

## Entorno

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,docs]"
```

## Comprobaciones locales

```powershell
python -m pytest -m "not docker"
python -m ruff check .
node --check src\mini_runbot\web\app.js
python scripts\check_docs.py
python -m mkdocs build --strict --config-file gh-docs\mkdocs.es.yml --site-dir ..\site
python -m mkdocs build --strict --config-file gh-docs\mkdocs.en.yml --site-dir ..\site\en
git diff --check
```

El script de documentación exige el mismo conjunto de páginas Markdown bajo `gh-docs/es` y
`gh-docs/en`. Ambos builds estrictos deben terminar sin advertencias.

## Pruebas

- `tests/unit`: dominio, validaciones, pipeline y componentes aislados.
- `tests/integration`: API, SQLite, Git local y asignación concurrente de puertos.
- `tests/e2e`: ciclo real Odoo; las pruebas marcadas `docker` requieren daemon e imágenes.

Cuando cambie checkout, Compose, instalación, pruebas, arranque, healthchecks, puertos, volúmenes o
cleanup, ejecute también un build real. Compruebe módulos instalados, resultado de pruebas Odoo y
HTTP 200 del preview; contenedores iniciados no bastan.

## Documentación

El español se publica en la raíz y el inglés en `/en/`. Edite la misma ruta relativa en ambos
árboles. Para previsualizar español:

```powershell
python -m mkdocs serve --config-file gh-docs\mkdocs.es.yml
```

Los pull requests construyen ambos idiomas. Los pushes a `master` producen un único artefacto y lo
despliegan mediante el environment `github-pages`.

Antes del primer despliegue, un administrador debe seleccionar **GitHub Actions** en
**Settings → Pages → Build and deployment → Source**. Para que el workflow Dependency Review pueda
comparar manifests, también debe habilitar **Dependency graph** en **Settings → Security → Code
security and analysis**. Son activaciones únicas del repositorio y no requieren añadir un PAT a los
workflows.

## Convenciones

Mantenga la dirección de dependencias, use `pathlib.Path`, preserve compatibilidad PowerShell y no
incluya secretos o estado generado. Los commits deben ser enfocados, imperativos y seguir
Conventional Commits.
