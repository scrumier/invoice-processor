# invoice-processor
#   make setup   install dependencies (once)
#   make watch   watch the invoice folder and process what lands in it
#   make run     serve the results table
#   make demo    generate fake invoices to try it with
#   make test    run the test suite
#   make lint    lint and format check

-include local.mk
HOST ?= 127.0.0.1
PORT ?= 5052

.PHONY: help setup watch run demo test lint

help:
	@echo ""
	@echo "  make setup   install dependencies (needs poppler-utils on the system)"
	@echo "  make watch   watch the invoice folder"
	@echo "  make run     results table  ->  http://$(HOST):$(PORT)"
	@echo "  make demo    generate fake invoices to try it with"
	@echo "  make test    run the test suite"
	@echo "  make lint    lint and format check"
	@echo ""

setup:
	@uv sync --quiet
	@echo "==> Ready. Copy .env.example to .env and add your OPENROUTER_API_KEY."

watch:
	@uv run python watch.py

run:
	@echo "==> http://$(HOST):$(PORT)   (Ctrl+C to stop)"
	@FLASK_HOST=$(HOST) FLASK_PORT=$(PORT) uv run python viewer.py

demo:
	@uv run python generate_sample_invoices.py

test:
	@uv run pytest -q

lint:
	@uv run ruff check .
	@uv run ruff format --check .
