.PHONY: lint format test run
RUFF := .venv/bin/ruff
PYTEST := .venv/bin/pytest
PYTHON := .venv/bin/python

lint:
	$(RUFF) check

format:
	$(RUFF) check --fix
	$(RUFF) format .

test:
	$(PYTEST) tests/ --cov=. --cov-report=term

run:
	$(PYTHON) scripts/run_bot.py
