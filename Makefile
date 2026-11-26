.DEFAULT_GOAL := help
.PHONY: help up up-full down build ps logs restart migrate revision create-admin shell test test-unit lint fmt \
	fe-dev fe-test fe-lint gen-api

COMPOSE := docker compose
BACKEND := cd backend && uv run

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

up: ## Start the stack (API on http://localhost:18000)
	$(COMPOSE) up -d --build

up-full: ## Everything in containers incl. nginx frontend on http://localhost:18080
	$(COMPOSE) --profile web up -d --build

down: ## Stop the stack, keep data volumes
	$(COMPOSE) --profile web down

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

create-admin: ## Create an admin account: make create-admin email=you@example.com
	@test -n "$(email)" || (echo 'usage: make create-admin email=you@example.com' && exit 1)
	$(COMPOSE) exec backend python -m app.modules.users.cli create-admin "$(email)"

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

fe-dev: ## Frontend dev server on http://localhost:5173 (needs `make up`)
	cd frontend && npm run dev

fe-test: ## Frontend unit tests
	cd frontend && npx vitest run

fe-lint: ## Frontend lint + type-check
	cd frontend && npm run lint && npm run type-check

gen-api: ## Regenerate frontend API types from the running backend's OpenAPI
	cd frontend && npm run gen:api
