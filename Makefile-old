# =============================================================================
# McDonald's Breakfast Menu - Makefile
# =============================================================================
# Quick Reference:
#   make chat SCOPE=1         Run stage_1 CLI chatbot
#   make dev SCOPE=1          Run LangGraph Studio for stage_1
#   make test SCOPE=smoke     Run smoke tests
#   make typecheck            Run ty type checker
# =============================================================================

.PHONY: help chat dev setup test typecheck
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
SCOPE ?= 1
ARGS  ?=

# =============================================================================
# HELP
# =============================================================================
help:
	@echo ""
	@echo "$(BOLD)$(BLUE)McDonald's Breakfast Menu - Development Commands$(NC)"
	@echo "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(BOLD)chat$(NC) - Run CLI chatbot"
	@echo "  $(GREEN)make chat$(NC)                   Run stage_1 chatbot (default)"
	@echo "  $(GREEN)make chat SCOPE=2$(NC)           Run stage_2 chatbot"
	@echo ""
	@echo "$(BOLD)dev$(NC) - Run LangGraph Studio"
	@echo "  $(GREEN)make dev$(NC)                    Run LangGraph Studio for stage_1 (default)"
	@echo "  $(GREEN)make dev SCOPE=2$(NC)            Run LangGraph Studio for stage_2"
	@echo ""
	@echo "$(BOLD)setup$(NC) - Install dependencies"
	@echo "  $(GREEN)make setup$(NC)                  Install all packages"
	@echo "  $(GREEN)make setup SCOPE=1$(NC)          Install stage_1 only"
	@echo "  $(GREEN)make setup SCOPE=2$(NC)          Install stage_2 only"
	@echo ""
	@echo "$(BOLD)test$(NC) - Run tests"
	@echo "  $(GREEN)make test$(NC)                   Run smoke tests (default)"
	@echo "  $(GREEN)make test SCOPE=smoke$(NC)       Run smoke tests"
	@echo ""
	@echo "$(BOLD)typecheck$(NC) - Static type checking"
	@echo "  $(GREEN)make typecheck$(NC)              Run ty type checker"
	@echo ""
	@echo "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""

# =============================================================================
# PRIMARY COMMANDS
# =============================================================================
chat: ## Run CLI chatbot (SCOPE: 1, 2)
	@case "$(SCOPE)" in \
		1) \
			echo "$(BLUE)==> Running stage_1 chatbot...$(NC)"; \
			uv run --package stage-1 python -m stage_1.main $(ARGS); \
			;; \
		2) \
			echo "$(BLUE)==> Running stage_2 chatbot...$(NC)"; \
			uv run --package stage-2 python -m stage_2.main $(ARGS); \
			;; \
		*) \
			echo "$(YELLOW)Unknown SCOPE: $(SCOPE)$(NC)"; \
			echo "Usage: make chat SCOPE=[1|2]"; \
			exit 1; \
			;; \
	esac

dev: ## Run LangGraph Studio (SCOPE: 1, 2)
	@case "$(SCOPE)" in \
		1) \
			echo "$(BLUE)==> Running LangGraph Studio for stage_1...$(NC)"; \
			uv run langgraph dev $(ARGS); \
			;; \
		2) \
			echo "$(BLUE)==> Running LangGraph Studio for stage_2...$(NC)"; \
			uv run langgraph dev $(ARGS); \
			;; \
		*) \
			echo "$(YELLOW)Unknown SCOPE: $(SCOPE)$(NC)"; \
			echo "Usage: make dev SCOPE=[1|2]"; \
			exit 1; \
			;; \
	esac

# =============================================================================
# SETUP - Install dependencies
# =============================================================================
setup: ## Install dependencies (SCOPE: all, 1, 2, 3)
	@case "$(SCOPE)" in \
		all) \
			echo "$(BLUE)==> Installing all packages...$(NC)"; \
			uv sync --all-packages; \
			echo "$(GREEN)==> All packages installed!$(NC)"; \
			;; \
		1) \
			echo "$(BLUE)==> Installing stage_1 dependencies...$(NC)"; \
			uv sync --package stage-1; \
			echo "$(GREEN)==> stage_1 installed!$(NC)"; \
			;; \
		2) \
			echo "$(BLUE)==> Installing stage_2 dependencies...$(NC)"; \
			uv sync --package stage-2; \
			echo "$(GREEN)==> stage_2 installed!$(NC)"; \
			;; \
		3) \
			echo "$(BLUE)==> Installing stage_3 dependencies...$(NC)"; \
			uv sync --package stage-3; \
			echo "$(GREEN)==> stage_3 installed!$(NC)"; \
			;; \
		*) \
			echo "$(YELLOW)Unknown SCOPE: $(SCOPE)$(NC)"; \
			echo "Usage: make setup SCOPE=[all|1|2|3]"; \
			exit 1; \
			;; \
	esac

# =============================================================================
# TEST - Run tests
# =============================================================================
test: ## Run tests (SCOPE: smoke)
	@case "$(SCOPE)" in \
		smoke|1) \
			echo "$(BLUE)==> Running smoke tests...$(NC)"; \
			echo "Testing stage_1 imports..."; \
			uv run --package stage-1 python -c "from stage_1.config import get_settings; print('Config: OK')"; \
			uv run --package stage-1 python -c "from stage_1.graph import graph; print('Graph: OK')"; \
			uv run --package stage-1 python -c "from stage_1.graph import get_langfuse_client; print('Langfuse auth:', get_langfuse_client().auth_check())"; \
			echo "Testing stage_3 imports..."; \
			uv run --package stage-3 python -c "from stage_3.models import Item; print('Models: OK')"; \
			uv run --package stage-3 python -c "from stage_3.enums import Size, CategoryName; print('Enums: OK')"; \
			echo "$(GREEN)==> All smoke tests passed!$(NC)"; \
			;; \
		*) \
			echo "$(YELLOW)Unknown SCOPE: $(SCOPE)$(NC)"; \
			echo "Usage: make test SCOPE=[smoke]"; \
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
