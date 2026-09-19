.PHONY: install test lint doctor api demo

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m ruff check .

doctor:
	python -m mini_runbot.cli.main doctor

api:
	uvicorn mini_runbot.api.app:app --reload

demo:
	powershell -ExecutionPolicy Bypass -File scripts/demo.ps1
