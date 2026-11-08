# Sajjad — atajos de desarrollo.
# `make` a secas lista los comandos disponibles.

COMPOSE := docker compose -f backend/docker-compose.yml

.DEFAULT_GOAL := help
.PHONY: help up down restart logs ps test test-backend test-engine \
        test-frontend lint fmt security migrate revision shell redis \
        build clean

help:  ## Muestra esta ayuda
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk -F':.*?## ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ── Stack de desarrollo ──────────────────────────────────────

up:  ## Levanta el stack (postgres, redis, api, worker, beat)
	$(COMPOSE) up -d
	@echo "API:  http://localhost:8000/docs"

down:  ## Detiene el stack
	$(COMPOSE) down

restart:  ## Reconstruye y reinicia api, worker y beat
	$(COMPOSE) up -d --build api worker beat

logs:  ## Sigue los logs de la API
	$(COMPOSE) logs -f api

ps:  ## Estado de los contenedores
	$(COMPOSE) ps

# ── Tests ────────────────────────────────────────────────────

test: test-engine test-backend test-frontend  ## Corre todos los tests

test-frontend:  ## Tests del frontend (vitest)
	cd frontend && npm test

test-engine:  ## Tests del motor de escaneo (scoring, dedup, modelos)
	uv run pytest tests -q

test-backend:  ## Tests del backend (requiere postgres corriendo)
	@$(COMPOSE) exec -T postgres \
	  psql -U sajjad -tc "SELECT 1 FROM pg_database \
	  WHERE datname='sajjad_test'" | grep -q 1 \
	  || $(COMPOSE) exec -T postgres createdb -U sajjad sajjad_test
	cd backend && uv run --extra dev pytest -q

# ── Calidad ──────────────────────────────────────────────────

lint:  ## ruff + tsc + eslint
	uvx ruff@0.15.16 check backend/app sajjad tests backend/tests
	cd frontend && npx tsc -b && npx eslint src/

security:  ## Comprueba los guardarraíles de alcance ético
	@if grep -rEq --include="*.py" "trial-scan|public/scan" backend/app/; then \
	  echo "FALLO: endpoint de escaneo sin autenticar."; \
	  echo "Sajjad sólo escanea dominios verificados por su dueño."; \
	  exit 1; \
	fi
	@if ! grep -q "exclude-tags" sajjad/scanners/vulns.py; then \
	  echo "FALLO: nuclei debe excluir dos/fuzz/intrusive."; \
	  exit 1; \
	fi
	@echo "OK: sólo dominios verificados, nuclei en modo seguro."

fmt:  ## Arregla lo que ruff pueda arreglar solo
	uvx ruff@0.15.16 check --fix backend/app sajjad tests backend/tests

# ── Base de datos ────────────────────────────────────────────

migrate:  ## Aplica las migraciones pendientes
	$(COMPOSE) run --rm migrate

revision:  ## Crea una migración: make revision m="descripción"
	cd backend && uv run alembic revision -m "$(m)"

shell:  ## Abre psql en la base de datos
	$(COMPOSE) exec postgres psql -U sajjad sajjad_db

redis:  ## Abre redis-cli
	$(COMPOSE) exec redis redis-cli

# ── Frontend ─────────────────────────────────────────────────

build:  ## Compila el frontend para producción
	cd frontend && npm run build

clean:  ## Borra cachés y artefactos de build
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache backend/.pytest_cache \
	       backend/.ruff_cache frontend/dist
