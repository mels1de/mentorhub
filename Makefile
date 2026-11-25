.DEFAULT_GOAL := help
.PHONY: help up down build ps logs restart migrate revision shell test test-unit lint fmt

COMPOSE := docker compose
BACKEND := cd backend && uv run

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

up: ## Start the stack (API on http://localhost:18000)
	$(COMPOSE) up -d --build

down: ## Stop the stack, keep data volumes
	$(COMPOSE) down

build: ## Rebuild backend images
	$(COMPOSE) build migrate

ps: ## Show service status
	$(COMPOSE) ps -a

logs: ## Follow logs: make logs [s=backend]
	$(COMPOSE) logs -f --tail=100 $(s)

restart: ## Restart services: make restart [s=worker]
	$(COMPOSE) restart $(s)

migrate: ## Apply migrations
	$(COMPOSE) run --rm migrate

revision: ## Autogenerate a migration: make revision m="add users"
	@test -n "$(m)" || (echo 'usage: make revision m="message"' && exit 1)
	$(COMPOSE) run --rm migrate alembic revision --autogenerate -m "$(m)"

shell: ## Shell in the API container
	$(COMPOSE) exec backend sh

test: ## All backend tests (integration ones need `make up`)
	$(BACKEND) pytest

test-unit: ## Backend tests without real services
	$(BACKEND) pytest -m "not integration"

lint: ## Ruff + format check + mypy
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .
	$(BACKEND) mypy .

fmt: ## Auto-fix lint and format
	$(BACKEND) ruff check --fix .
	$(BACKEND) ruff format .
