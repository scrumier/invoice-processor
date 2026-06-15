# invoice-processor — launcher autonome.
#   make setup   <- une fois : venv + deps (uv)
#   make run     <- démarre le viewer  ->  http://127.0.0.1:5052
# Bind Tailscale uniquement, jamais exposé publiquement.
# NB : l'ancien service systemd doit être arrêté pour libérer le port 5052.

-include local.mk
TS ?= 127.0.0.1
PORT := 5052

.PHONY: help setup run

help:
	@echo ""
	@echo "  invoice-processor   ->  http://$(TS):$(PORT)"
	@echo "    make setup   installe les deps (une fois)"
	@echo "    make run     démarre le viewer"
	@echo ""

setup:
	@echo "==> uv sync..."
	@uv sync --quiet
	@echo "==> Prêt. Lancer :  make run"

run:
	@echo ""
	@echo "==> Ouvre sur ton Mac :  http://$(TS):$(PORT)      (Ctrl+C pour arrêter)"
	@echo ""
	@FLASK_HOST=$(TS) FLASK_PORT=$(PORT) uv run python viewer.py
