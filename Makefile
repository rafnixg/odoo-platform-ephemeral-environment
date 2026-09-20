.PHONY: install test lint docs-check docs-build docs-serve doctor api demo

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m ruff check .

docs-check:
	python scripts/check_docs.py
	python -m mkdocs build --strict --config-file gh-docs/mkdocs.es.yml --site-dir ../site
	python -m mkdocs build --strict --config-file gh-docs/mkdocs.en.yml --site-dir ../site/en

docs-build: docs-check

docs-serve:
	python -m mkdocs serve --config-file gh-docs/mkdocs.es.yml

doctor:
	python -m mini_runbot.cli.main doctor

api:
	uvicorn mini_runbot.api.app:app --reload

demo:
	powershell -ExecutionPolicy Bypass -File scripts/demo.ps1
