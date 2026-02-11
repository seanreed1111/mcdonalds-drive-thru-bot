# =============================================================================
# McDonald's Drive-Thru Bot - Makefile
# =============================================================================
# Quick Reference:
#   make chat                  Run CLI chatbot
#   make dev                   Run LangGraph Studio
#   make test                  Run smoke tests (default)
#   make test SCOPE=all        Run all tests
#   make typecheck             Run ty type checker
#   make setup                 Install all workspace dependencies
# =============================================================================

.PHONY: help chat dev setup test typecheck eval-seed eval
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
# Variables
# -----------------------------------------------------------------------------
SCOPE ?= smoke
ARGS  ?=

# =============================================================================
# HELP
# =============================================================================
help:
	@echo ""
	@echo "$(BOLD)$(BLUE)McDonald's Drive-Thru Bot - Development Commands$(NC)"
	@echo "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(BOLD)chat$(NC) - Run CLI chatbot"
	@echo "  $(GREEN)make chat$(NC)"
	@echo ""
	@echo "$(BOLD)dev$(NC) - Run LangGraph Studio"
	@echo "  $(GREEN)make dev$(NC)"
	@echo ""
	@echo "$(BOLD)setup$(NC) - Install dependencies"
	@echo "  $(GREEN)make setup$(NC)"
	@echo ""
	@echo "$(BOLD)test$(NC) - Run tests"
	@echo "  $(GREEN)make test$(NC)                   Run smoke tests (default)"
	@echo "  $(GREEN)make test SCOPE=smoke$(NC)       Run smoke tests"
	@echo "  $(GREEN)make test SCOPE=all$(NC)         Run all tests"
	@echo ""
	@echo "$(BOLD)typecheck$(NC) - Static type checking"
	@echo "  $(GREEN)make typecheck$(NC)              Run ty type checker"
	@echo ""
	@echo "$(BOLD)eval-seed$(NC) - Seed evaluation dataset in Langfuse"
	@echo "  $(GREEN)make eval-seed$(NC)"
	@echo ""
	@echo "$(BOLD)eval$(NC) - Run evaluation experiment"
	@echo "  $(GREEN)make eval$(NC)                   Run with auto-generated name"
	@echo "  $(GREEN)make eval ARGS='--run-name my-run'$(NC)   Run with custom name"
	@echo ""
	@echo "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""

# =============================================================================
# PRIMARY COMMANDS
# =============================================================================
chat: ## Run CLI chatbot
	@echo "$(BLUE)==> Running chatbot...$(NC)"
	uv run --package orchestrator python -m orchestrator.main $(ARGS)

dev: ## Run LangGraph Studio
	@echo "$(BLUE)==> Running LangGraph Studio...$(NC)"
	uv run langgraph dev $(ARGS)

# =============================================================================
# SETUP
# =============================================================================
setup: ## Install all workspace dependencies
	@echo "$(BLUE)==> Installing all packages...$(NC)"
	uv sync --all-packages
	@echo "$(GREEN)==> All packages installed!$(NC)"

# =============================================================================
# TEST
# =============================================================================
test: ## Run tests (SCOPE: smoke, all)
	@case "$(SCOPE)" in \
		smoke) \
			echo "$(BLUE)==> Running smoke tests...$(NC)"; \
			uv run --package orchestrator pytest tests/orchestrator $(ARGS); \
			echo "$(GREEN)==> Smoke tests complete!$(NC)"; \
			;; \
		all) \
			echo "$(BLUE)==> Running all tests...$(NC)"; \
			uv run --package orchestrator pytest tests $(ARGS); \
			echo "$(GREEN)==> All tests complete!$(NC)"; \
			;; \
		*) \
			echo "$(YELLOW)Unknown SCOPE: $(SCOPE)$(NC)"; \
			echo "Usage: make test SCOPE=[smoke|all]"; \
			exit 1; \
			;; \
	esac

# =============================================================================
# CODE QUALITY
# =============================================================================
typecheck: ## Run ty type checker
	@echo "$(BLUE)==> Running type checker (ty)...$(NC)"
	uv run ty check
	@echo "$(GREEN)==> Type checking complete!$(NC)"

# =============================================================================
# EVALUATION
# =============================================================================
eval-seed: ## Seed evaluation dataset in Langfuse
	@echo "$(BLUE)==> Seeding evaluation dataset...$(NC)"
	uv run --package orchestrator python scripts/seed_eval_dataset.py
	@echo "$(GREEN)==> Dataset seeded!$(NC)"

eval: ## Run evaluation experiment
	@echo "$(BLUE)==> Running evaluation experiment...$(NC)"
	uv run --package orchestrator python scripts/run_eval.py $(ARGS)
	@echo "$(GREEN)==> Evaluation complete!$(NC)"
