# =============================================================================
# Session Review - Makefile
# =============================================================================
# A streamlined, variable-based Makefile for the Session Review project.
#
# Quick Reference:
#   make help              - Show all commands with examples
#   make dev ACTION=up     - Start Docker services
#   make test SCOPE=api    - Run API tests
#   make run CMD=logs ID=abc123  - Run CLI tool
#
# Variables:
#   SCOPE  - Target scope: api, frontend, cli, e2e, bdd, all (default: all)
#   ACTION - Docker action: up, down, logs, build, clean, ps, health (default: up)
#   CMD    - CLI command: logs, spans, logs-detail, logs-summary, etc.
#   ID     - Session ID for CLI commands
#   ARGS   - Pass-through arguments for underlying tools
# =============================================================================

.PHONY: help setup dev test lint format typecheck run clean

.DEFAULT_GOAL := help

# -----------------------------------------------------------------------------
# Colors
# -----------------------------------------------------------------------------
BLUE   := \033[0;34m
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
BOLD   := \033[1m
NC     := \033[0m

# -----------------------------------------------------------------------------
# Default Variables
# -----------------------------------------------------------------------------
SCOPE  ?= all
ACTION ?= up
CMD    ?=
ID     ?=
ARGS   ?=

# =============================================================================
# HELP
# =============================================================================
help: ## Show available commands with usage examples
	@echo ""
	@echo "$(BOLD)$(BLUE)Session Review - Development Commands$(NC)"
	@echo "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(BOLD)setup$(NC) - Install dependencies"
	@echo "  $(GREEN)make setup$(NC)                  Install all (Python + frontend)"
	@echo "  $(GREEN)make setup SCOPE=api$(NC)        Install Python/API deps only"
	@echo "  $(GREEN)make setup SCOPE=frontend$(NC)   Install frontend deps only"
	@echo "  $(GREEN)make setup SCOPE=e2e$(NC)        Install Playwright browsers"
	@echo ""
	@echo "$(BOLD)dev$(NC) - Docker environment management"
	@echo "  $(GREEN)make dev$(NC)                    Start services (ACTION=up)"
	@echo "  $(GREEN)make dev ACTION=down$(NC)        Stop and remove services"
	@echo "  $(GREEN)make dev ACTION=logs$(NC)        View service logs (follow)"
	@echo "  $(GREEN)make dev ACTION=build$(NC)       Rebuild images (no cache)"
	@echo "  $(GREEN)make dev ACTION=ps$(NC)          Show container status"
	@echo "  $(GREEN)make dev ACTION=health$(NC)      Check service health"
	@echo "  $(GREEN)make dev ACTION=clean$(NC)       Remove containers + volumes"
	@echo "  $(GREEN)make dev ACTION=shell SCOPE=api$(NC)     Shell into backend"
	@echo "  $(GREEN)make dev ACTION=shell SCOPE=frontend$(NC) Shell into frontend"
	@echo ""
	@echo "$(BOLD)test$(NC) - Run tests"
	@echo "  $(GREEN)make test$(NC)                   Run all tests (api + frontend + e2e)"
	@echo "  $(GREEN)make test SCOPE=api$(NC)         Run pytest API tests"
	@echo "  $(GREEN)make test SCOPE=api ARGS=\"-k login\"$(NC)  Filter pytest tests"
	@echo "  $(GREEN)make test SCOPE=frontend$(NC)    Run Jest frontend tests"
	@echo "  $(GREEN)make test SCOPE=frontend ARGS=\"SearchBar\"$(NC)  Filter Jest"
	@echo "  $(GREEN)make test SCOPE=cli$(NC)         Run CLI tool tests"
	@echo "  $(GREEN)make test SCOPE=e2e$(NC)         Run Playwright E2E tests"
	@echo "  $(GREEN)make test SCOPE=e2e ARGS=ui$(NC) Run E2E with interactive UI"
	@echo "  $(GREEN)make test SCOPE=e2e-s3$(NC)      Run E2E against S3 storage"
	@echo "  $(GREEN)make test SCOPE=bdd$(NC)         Run Behave BDD tests"
	@echo "  $(GREEN)make test SCOPE=integration$(NC) Run integration tests"
	@echo ""
	@echo "$(BOLD)lint$(NC) - Check code quality"
	@echo "  $(GREEN)make lint$(NC)                   Lint all (api + frontend)"
	@echo "  $(GREEN)make lint SCOPE=api$(NC)         Run ruff on Python code"
	@echo "  $(GREEN)make lint SCOPE=frontend$(NC)    Run ESLint on TypeScript"
	@echo ""
	@echo "$(BOLD)format$(NC) - Auto-format code"
	@echo "  $(GREEN)make format$(NC)                 Format all (api + frontend)"
	@echo "  $(GREEN)make format SCOPE=api$(NC)       Format Python with ruff"
	@echo "  $(GREEN)make format SCOPE=frontend$(NC)  Format TypeScript with Prettier"
	@echo "  $(GREEN)make format ARGS=check$(NC)      Check formatting without changes"
	@echo ""
	@echo "$(BOLD)typecheck$(NC) - Static type checking"
	@echo "  $(GREEN)make typecheck$(NC)              Run ty type checker on Python"
	@echo ""
	@echo "$(BOLD)run$(NC) - CLI tool runner (requires CMD and usually ID)"
	@echo "  $(GREEN)make run CMD=logs ID=abc123$(NC)          Get session logs"
	@echo "  $(GREEN)make run CMD=spans ID=abc123$(NC)         Get session spans"
	@echo "  $(GREEN)make run CMD=logs-detail ID=abc123$(NC)   Get detailed logs"
	@echo "  $(GREEN)make run CMD=logs-summary ID=abc123$(NC)  Get logs summary"
	@echo "  $(GREEN)make run CMD=order-history ID=abc123$(NC) Get order history"
	@echo "  $(GREEN)make run CMD=list-files ID=abc123$(NC)    List session files"
	@echo "  $(GREEN)make run CMD=transcript ID=abc123$(NC)    Generate transcript"
	@echo "  $(GREEN)make run CMD=search-recent$(NC)           Recent sessions"
	@echo "  $(GREEN)make run CMD=search-annotated$(NC)        Annotated sessions"
	@echo "  $(GREEN)make run CMD=secrets-init$(NC)            Init AWS secrets"
	@echo "  $(GREEN)make run CMD=secrets-export$(NC)          Export AWS secrets"
	@echo ""
	@echo "$(BOLD)clean$(NC) - Reset environment"
	@echo "  $(GREEN)make clean$(NC)                  Stop services, remove volumes"
	@echo ""
	@echo "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""

# =============================================================================
# SETUP - Install dependencies
# =============================================================================
setup: ## Install dependencies (SCOPE: all, api, frontend, e2e)
	@case "$(SCOPE)" in \
		all) \
			echo "$(BLUE)==> Installing all dependencies...$(NC)"; \
			uv sync --extra dev; \
			cd frontend && npm install; \
			echo "$(GREEN)==> All dependencies installed!$(NC)"; \
			;; \
		api) \
			echo "$(BLUE)==> Installing Python/API dependencies...$(NC)"; \
			uv sync --extra dev; \
			echo "$(GREEN)==> Python dependencies installed!$(NC)"; \
			;; \
		frontend) \
			echo "$(BLUE)==> Installing frontend dependencies...$(NC)"; \
			cd frontend && npm install; \
			echo "$(GREEN)==> Frontend dependencies installed!$(NC)"; \
			;; \
		e2e) \
			echo "$(BLUE)==> Installing Playwright browsers...$(NC)"; \
			cd frontend && npx playwright install; \
			echo "$(GREEN)==> Playwright browsers installed!$(NC)"; \
			;; \
		*) \
			echo "$(YELLOW)Unknown SCOPE: $(SCOPE)$(NC)"; \
			echo "Usage: make setup SCOPE=[all|api|frontend|e2e]"; \
			exit 1; \
			;; \
	esac

# =============================================================================
# DEV - Docker environment management
# =============================================================================
dev: ## Docker management (ACTION: up, down, logs, build, clean, ps, health, shell)
	@case "$(ACTION)" in \
		up) \
			echo "$(BLUE)==> Starting Docker services...$(NC)"; \
			docker compose up -d; \
			echo "$(GREEN)==> Services started!$(NC)"; \
			echo "  Backend:  http://localhost:8000"; \
			echo "  Frontend: http://localhost:4000"; \
			echo "  API Docs: http://localhost:8000/docs"; \
			;; \
		down) \
			echo "$(BLUE)==> Stopping Docker services...$(NC)"; \
			docker compose down; \
			echo "$(GREEN)==> Services stopped!$(NC)"; \
			;; \
		logs) \
			docker compose logs -f $(if $(filter api,$(SCOPE)),backend,$(if $(filter frontend,$(SCOPE)),frontend,)); \
			;; \
		build) \
			echo "$(BLUE)==> Rebuilding Docker images (no cache)...$(NC)"; \
			docker compose down; \
			docker compose build --no-cache; \
			docker compose up -d; \
			echo "$(GREEN)==> Rebuild complete!$(NC)"; \
			echo "  Backend:  http://localhost:8000"; \
			echo "  Frontend: http://localhost:4000"; \
			echo "  API Docs: http://localhost:8000/docs"; \
			;; \
		clean) \
			echo "$(YELLOW)==> Cleaning Docker resources (containers + volumes)...$(NC)"; \
			docker compose down -v --remove-orphans; \
			echo "$(GREEN)==> Cleanup complete!$(NC)"; \
			;; \
		ps) \
			docker compose ps; \
			;; \
		health) \
			echo "$(BLUE)==> Checking service health...$(NC)"; \
			echo "Backend:"; \
			curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "  Not responding"; \
			echo ""; \
			echo "Frontend:"; \
			curl -s -o /dev/null -w "  HTTP Status: %{http_code}\n" http://localhost:4000/ 2>/dev/null || echo "  Not responding"; \
			;; \
		shell) \
			if [ "$(SCOPE)" = "api" ]; then \
				docker compose exec backend /bin/bash; \
			elif [ "$(SCOPE)" = "frontend" ]; then \
				docker compose exec frontend /bin/sh; \
			else \
				echo "$(YELLOW)Specify SCOPE=api or SCOPE=frontend for shell$(NC)"; \
				exit 1; \
			fi; \
			;; \
		*) \
			echo "$(YELLOW)Unknown ACTION: $(ACTION)$(NC)"; \
			echo "Usage: make dev ACTION=[up|down|logs|build|clean|ps|health|shell]"; \
			exit 1; \
			;; \
	esac

# =============================================================================
# TEST - Run tests
# =============================================================================
test: ## Run tests (SCOPE: all, api, frontend, cli, e2e, bdd, integration)
	@case "$(SCOPE)" in \
		all) \
			echo "$(BLUE)==> Running all tests...$(NC)"; \
			$(MAKE) test SCOPE=api; \
			$(MAKE) test SCOPE=frontend; \
			$(MAKE) test SCOPE=integration; \
			$(MAKE) test SCOPE=e2e; \
			echo "$(GREEN)==> All tests complete!$(NC)"; \
			;; \
		api) \
			echo "$(BLUE)==> Running API tests (pytest)...$(NC)"; \
			if [ -n "$(ARGS)" ]; then \
				uv run --extra dev python -m pytest packages/api/tests/ $(ARGS) -v; \
			else \
				uv run --extra dev python -m pytest packages/api/tests/ -v; \
			fi; \
			echo "$(GREEN)==> API tests complete!$(NC)"; \
			;; \
		frontend) \
			echo "$(BLUE)==> Running frontend tests (Jest)...$(NC)"; \
			if [ -n "$(ARGS)" ]; then \
				cd frontend && npm test -- $(ARGS) --runInBand; \
			else \
				cd frontend && npm test -- --runInBand; \
			fi; \
			echo "$(GREEN)==> Frontend tests complete!$(NC)"; \
			;; \
		cli) \
			echo "$(BLUE)==> Running CLI tests...$(NC)"; \
			uv run --extra dev pytest packages/cli/tests/ -v; \
			echo "$(GREEN)==> CLI tests complete!$(NC)"; \
			;; \
		e2e) \
			echo "$(BLUE)==> Running E2E tests (Playwright)...$(NC)"; \
			VITE_API_URL=http://localhost:8000/api/v1 $(MAKE) backend-stop; \
			if [ "$(ARGS)" = "ui" ]; then \
				cd frontend && VITE_API_URL=http://localhost:8000/api/v1 npm run test:e2e:ui; \
			elif [ "$(ARGS)" = "debug" ]; then \
				cd frontend && VITE_API_URL=http://localhost:8000/api/v1 npm run test:e2e:debug; \
			else \
				cd frontend && VITE_API_URL=http://localhost:8000/api/v1 npm run test:e2e -- $(ARGS); \
			fi; \
			echo "$(GREEN)==> E2E tests complete!$(NC)"; \
			;; \
		e2e-s3) \
			echo "$(BLUE)==> Running E2E tests (Playwright) against S3...$(NC)"; \
			$(MAKE) backend-stop; \
			cd frontend && PLAYWRIGHT_PROJECT=chromium-s3 VITE_API_URL=http://localhost:8000/api/v1 npm run test:e2e -- --project=chromium-s3; \
			echo "$(GREEN)==> E2E S3 tests complete!$(NC)"; \
			;; \
		bdd) \
			echo "$(BLUE)==> Running BDD tests (Behave)...$(NC)"; \
			if [ -n "$(ARGS)" ]; then \
				uv run python -m behave tests/features/ --tags=$(ARGS); \
			else \
				uv run python -m behave tests/features/; \
			fi; \
			echo "$(GREEN)==> BDD tests complete!$(NC)"; \
			;; \
		integration) \
			echo "$(BLUE)==> Running integration tests...$(NC)"; \
			uv run --extra dev pytest packages/api/tests/integration/ -v -m integration; \
			echo "$(GREEN)==> Integration tests complete!$(NC)"; \
			;; \
		*) \
			echo "$(YELLOW)Unknown SCOPE: $(SCOPE)$(NC)"; \
			echo "Usage: make test SCOPE=[all|api|frontend|cli|e2e|bdd|integration]"; \
			exit 1; \
			;; \
	esac

# =============================================================================
# LINT - Check code quality
# =============================================================================
lint: ## Check code quality (SCOPE: all, api, frontend)
	@case "$(SCOPE)" in \
		all) \
			$(MAKE) lint SCOPE=api; \
			$(MAKE) lint SCOPE=frontend; \
			;; \
		api) \
			echo "$(BLUE)==> Linting Python code (ruff)...$(NC)"; \
			ruff check packages/ tests/; \
			echo "$(GREEN)==> Python linting complete!$(NC)"; \
			;; \
		frontend) \
			echo "$(BLUE)==> Linting TypeScript code (ESLint)...$(NC)"; \
			cd frontend && npm run lint; \
			echo "$(GREEN)==> TypeScript linting complete!$(NC)"; \
			;; \
		*) \
			echo "$(YELLOW)Unknown SCOPE: $(SCOPE)$(NC)"; \
			echo "Usage: make lint SCOPE=[all|api|frontend]"; \
			exit 1; \
			;; \
	esac

# =============================================================================
# FORMAT - Auto-format code
# =============================================================================
format: ## Format code (SCOPE: all, api, frontend; ARGS: check)
	@case "$(SCOPE)" in \
		all) \
			$(MAKE) format SCOPE=api ARGS="$(ARGS)"; \
			$(MAKE) format SCOPE=frontend ARGS="$(ARGS)"; \
			;; \
		api) \
			if [ "$(ARGS)" = "check" ]; then \
				echo "$(BLUE)==> Checking Python formatting...$(NC)"; \
				ruff format --check packages/ tests/; \
			else \
				echo "$(BLUE)==> Formatting Python code (ruff)...$(NC)"; \
				ruff format packages/ tests/; \
				echo "$(GREEN)==> Python formatting complete!$(NC)"; \
			fi; \
			;; \
		frontend) \
			if [ "$(ARGS)" = "check" ]; then \
				echo "$(BLUE)==> Checking TypeScript formatting...$(NC)"; \
				cd frontend && npm run format:check; \
			else \
				echo "$(BLUE)==> Formatting TypeScript code (Prettier)...$(NC)"; \
				cd frontend && npm run format; \
				echo "$(GREEN)==> TypeScript formatting complete!$(NC)"; \
			fi; \
			;; \
		*) \
			echo "$(YELLOW)Unknown SCOPE: $(SCOPE)$(NC)"; \
			echo "Usage: make format SCOPE=[all|api|frontend] [ARGS=check]"; \
			exit 1; \
			;; \
	esac

# =============================================================================
# TYPECHECK - Static type checking
# =============================================================================
typecheck: ## Run type checker on Python code
	@echo "$(BLUE)==> Running type checker (ty)...$(NC)"
	uv run --extra dev ty check packages/ tests/features/ --color auto
	@echo "$(GREEN)==> Type checking complete!$(NC)"

# =============================================================================
# RUN - CLI Tool Runner
# =============================================================================
run: ## Run CLI tools (CMD: logs, spans, logs-detail, etc. ID: session ID)
	@if [ -z "$(CMD)" ]; then \
		echo "$(YELLOW)Error: CMD is required$(NC)"; \
		echo ""; \
		echo "Usage: make run CMD=<command> [ID=<session-id>] [ARGS=\"...\"]"; \
		echo ""; \
		echo "Commands requiring ID:"; \
		echo "  logs, spans, logs-detail, logs-summary, order-history, list-files, transcript"; \
		echo ""; \
		echo "Commands without ID:"; \
		echo "  search-recent, search-annotated, secrets-init, secrets-export"; \
		exit 1; \
	fi
	@case "$(CMD)" in \
		logs) \
			if [ -z "$(ID)" ]; then echo "$(YELLOW)Error: ID required for logs$(NC)"; exit 1; fi; \
			echo "$(BLUE)==> Getting logs for session: $(ID)$(NC)"; \
			uv run sr-logs $(ID) $(ARGS); \
			;; \
		spans) \
			if [ -z "$(ID)" ]; then echo "$(YELLOW)Error: ID required for spans$(NC)"; exit 1; fi; \
			echo "$(BLUE)==> Getting spans for session: $(ID)$(NC)"; \
			uv run sr-spans $(ID) $(ARGS); \
			;; \
		logs-detail) \
			if [ -z "$(ID)" ]; then echo "$(YELLOW)Error: ID required for logs-detail$(NC)"; exit 1; fi; \
			echo "$(BLUE)==> Getting detailed logs for session: $(ID)$(NC)"; \
			uv run sr-logs-detail $(ID) $(ARGS); \
			;; \
		logs-summary) \
			if [ -z "$(ID)" ]; then echo "$(YELLOW)Error: ID required for logs-summary$(NC)"; exit 1; fi; \
			echo "$(BLUE)==> Getting logs summary for session: $(ID)$(NC)"; \
			uv run sr-logs-summary $(ID) $(ARGS); \
			;; \
		order-history) \
			if [ -z "$(ID)" ]; then echo "$(YELLOW)Error: ID required for order-history$(NC)"; exit 1; fi; \
			echo "$(BLUE)==> Getting order history for session: $(ID)$(NC)"; \
			uv run sr-order-history $(ID) $(ARGS); \
			;; \
		list-files) \
			if [ -z "$(ID)" ]; then echo "$(YELLOW)Error: ID required for list-files$(NC)"; exit 1; fi; \
			echo "$(BLUE)==> Listing files for session: $(ID)$(NC)"; \
			uv run sr-list-files $(ID) $(ARGS); \
			;; \
		transcript) \
			if [ -z "$(ID)" ]; then echo "$(YELLOW)Error: ID required for transcript$(NC)"; exit 1; fi; \
			echo "$(BLUE)==> Generating transcript for session: $(ID)$(NC)"; \
			uv run sr-generate-transcript $(ID) $(ARGS); \
			;; \
		search-recent) \
			echo "$(BLUE)==> Searching for recently modified sessions...$(NC)"; \
			uv run sr-search-recent $(ARGS); \
			;; \
		search-annotated) \
			echo "$(BLUE)==> Searching for recently annotated sessions...$(NC)"; \
			uv run sr-search-annotated-recent $(ARGS); \
			;; \
		secrets-init) \
			echo "$(BLUE)==> Initializing AWS Secrets Manager...$(NC)"; \
			uv run sr-secrets-init $(ARGS); \
			;; \
		secrets-export) \
			echo "$(BLUE)==> Exporting AWS Secrets Manager secrets...$(NC)"; \
			uv run sr-secrets-export $(ARGS); \
			;; \
		*) \
			echo "$(YELLOW)Unknown CMD: $(CMD)$(NC)"; \
			echo ""; \
			echo "Available commands:"; \
			echo "  logs, spans, logs-detail, logs-summary, order-history,"; \
			echo "  list-files, transcript, search-recent, search-annotated,"; \
			echo "  secrets-init, secrets-export"; \
			exit 1; \
			;; \
	esac

# =============================================================================
# CLEAN - Reset environment
# =============================================================================
clean: ## Stop services, remove containers, networks, and volumes
	@echo "$(YELLOW)==> Cleaning up all Docker resources...$(NC)"
	docker compose down -v --remove-orphans
	@echo "$(GREEN)==> Cleanup complete!$(NC)"

# =============================================================================
# HOOKS - Git pre-commit setup
# =============================================================================
hooks: ## Setup git pre-commit hooks
	@echo "$(BLUE)==> Setting up git hooks...$(NC)"
	uv run pre-commit install
	@echo "$(GREEN)==> Git hooks configured!$(NC)"

pre-commit: ## Run pre-commit on all files
	@echo "$(BLUE)==> Running pre-commit on all files...$(NC)"
	uv run pre-commit run --all-files
	@echo "$(GREEN)==> Pre-commit checks complete!$(NC)"

# PID file for tracking backend process
BACKEND_PID_FILE := .backend.pid
BACKEND_PORT := $(or $(PORT),8000)

# =============================================================================
# BACKEND-START - Start API backend locally (for E2E)
# =============================================================================
backend-start: ## Start backend service in the background (PORT=8000 HOST=0.0.0.0)
	@HOST=$${HOST:-0.0.0.0}; \
	PORT=$${PORT:-8000}; \
	if [ -f $(BACKEND_PID_FILE) ] && kill -0 $$(cat $(BACKEND_PID_FILE)) 2>/dev/null; then \
		echo "$(YELLOW)Backend is already running (PID: $$(cat $(BACKEND_PID_FILE)))$(NC)"; \
		exit 0; \
	fi; \
	EXISTING_PID=$$(lsof -ti:$$PORT 2>/dev/null); \
	if [ -n "$$EXISTING_PID" ]; then \
		echo "$(YELLOW)Killing existing process on port $$PORT (PID: $$EXISTING_PID)$(NC)"; \
		echo "$$EXISTING_PID" | xargs kill -9 2>/dev/null || true; \
		sleep 1; \
	fi; \
	rm -f $(BACKEND_PID_FILE); \
	echo "$(BLUE)Starting backend service in background...$(NC)"; \
	nohup uv run uvicorn session_review_api.main:app --host $$HOST --port $$PORT > .backend.log 2>&1 & \
	echo $$! > $(BACKEND_PID_FILE); \
	sleep 2; \
	if kill -0 $$(cat $(BACKEND_PID_FILE)) 2>/dev/null; then \
		echo "$(GREEN)Backend started! (PID: $$(cat $(BACKEND_PID_FILE)))$(NC)"; \
		echo "  Backend: http://$$HOST:$$PORT"; \
		echo "  API Docs: http://$$HOST:$$PORT/docs"; \
		echo "  Logs: tail -f .backend.log"; \
	else \
		echo "$(YELLOW)Backend failed to start. Check .backend.log for details$(NC)"; \
		rm -f $(BACKEND_PID_FILE); \
		exit 1; \
	fi

backend-stop: ## Stop the background backend service (also kills any process on PORT)
	@PORT=$${PORT:-8000}; \
	STOPPED=0; \
	if [ -f $(BACKEND_PID_FILE) ]; then \
		PID=$$(cat $(BACKEND_PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			echo "$(BLUE)Stopping backend service (PID: $$PID)...$(NC)"; \
			kill $$PID 2>/dev/null || true; \
			STOPPED=1; \
		else \
			echo "$(YELLOW)Backend process not running (stale PID file)$(NC)"; \
		fi; \
		rm -f $(BACKEND_PID_FILE); \
	fi; \
	EXISTING_PID=$$(lsof -ti:$$PORT 2>/dev/null); \
	if [ -n "$$EXISTING_PID" ]; then \
		echo "$(YELLOW)Killing process on port $$PORT (PID: $$EXISTING_PID)$(NC)"; \
		echo "$$EXISTING_PID" | xargs kill -9 2>/dev/null || true; \
		STOPPED=1; \
	fi; \
	if [ "$$STOPPED" = "1" ]; then \
		echo "$(GREEN)Backend stopped!$(NC)"; \
	else \
		echo "$(YELLOW)No backend process found.$(NC)"; \
	fi

backend-run: ## Start backend service in foreground (for Playwright)
	uv run uvicorn session_review_api.main:app --host 0.0.0.0 --port 8000
