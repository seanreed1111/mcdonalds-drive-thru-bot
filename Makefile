.PHONY: chat dev test-smoke typecheck help

# Default target
help:
	@echo "Available targets:"
	@echo "  make chat       - Run CLI chatbot"
	@echo "  make dev        - Run LangGraph Studio"
	@echo "  make test-smoke - Verify imports and graph compilation"
	@echo "  make typecheck  - Run ty type checker"
	@echo "  make help       - Show this help"

# Run CLI chatbot
chat:
	uv run python -m stage_1.main

# Run LangGraph Studio (requires langgraph.json)
dev:
	uv run langgraph dev

# Type check with ty
typecheck:
	uv run ty check

# Smoke test - verify imports work and graph compiles
test-smoke:
	@echo "Testing imports..."
	uv run python -c "from stage_1.config import get_settings; print('Config: OK')"
	uv run python -c "from stage_1.graph import graph; print('Graph: OK')"
	uv run python -c "from stage_1.graph import get_langfuse_client; print('Langfuse auth:', get_langfuse_client().auth_check())"
	@echo "All smoke tests passed!"
