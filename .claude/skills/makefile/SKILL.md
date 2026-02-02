---
name: makefile
description: Standards for creating and maintaining streamlined, variable-based Makefiles. Use when adding new targets, refactoring existing Makefiles, or creating new build automation.
---

# Makefile Organization Standards

This skill establishes standards for project `Makefiles` to ensure they remain maintainable, discoverable, and user-friendly.

## When to Use This Skill

- Creating a new Makefile from scratch
- Adding new targets to an existing Makefile
- Refactoring complex or unwieldy Makefiles
- Reviewing Makefile quality and maintainability
- Ensuring consistent patterns across project automation
- Teaching others about Makefile best practices

## Philosophy: Less is More

**The best Makefile is the shortest one that meets the user's needs.**

Before creating or adding any target, challenge yourself:
- Can I use an existing target with a variable instead?
- Will users actually run this command frequently?
- Is this worth maintaining, or should it just be documented?

Default to **5-8 core targets** for most projects:
1. `help` (always)
2. 1-2 primary execution targets (`dev`, `console`, `run`)
3. `setup` (installation)
4. `test`
5. `format` and/or `lint`
6. `clean` (if needed)

Only add additional targets when explicitly requested or clearly essential.

## Core Principles

1. **Minimum Targets Philosophy**: Create the **absolute minimum number of targets** needed. Unless explicitly instructed otherwise, resist the urge to add targets. Use variables (`SCOPE`, `ARGS`, `ACTION`) instead of proliferating similar targets.

2. **Importance-First Ordering**: Place the most important and frequently-used targets at the **top** of the Makefile (immediately after `help`). Order targets by user priority:
   - Most common commands first (e.g., `dev`, `test`, `console`)
   - Setup/configuration second (e.g., `setup`, `install`)
   - Code quality tools third (e.g., `format`, `lint`)
   - Utilities and cleanup last (e.g., `clean`, `download-files`)

3. **Variable-Based Scope**: Use a single target with a `SCOPE` variable instead of creating many similar targets (e.g., `make test SCOPE=api` instead of `make test-api`, `make test-frontend`, etc.).

4. **Consolidated Functional Targets**: Group actions under a few high-level functional targets:
   - `dev` or `run`: Primary execution commands
   - `test`: All testing activities (use `SCOPE` for variants)
   - `setup` or `install`: Dependency installation
   - `format` / `lint`: Code quality
   - `clean`: Cleanup operations

5. **Usage Hints & Error Handling**: Always provide helpful usage instructions if required variables are missing or incorrect.

6. **Self-Documenting Help**: Maintain a robust `make help` target that provides both command descriptions and example usage.

## Implementation Patterns

### 1. Variable Defaults and Scope Selection

Always use `?=` for variables to allow overrides from the environment or command line.

```makefile
SCOPE  ?= all
ACTION ?= up
ARGS   ?=

test:
	@case "$(SCOPE)" in \
		all) $(MAKE) test SCOPE=api; $(MAKE) test SCOPE=frontend ;; \
		api) uv run pytest $(ARGS) ;; \
		frontend) cd frontend && npm test -- $(ARGS) ;; \
		*) echo "Usage: make test SCOPE=[all|api|frontend]"; exit 1 ;; \
	esac
```

### 2. User-Friendly Help Output

Use a visually clean help format with examples.

```makefile
BLUE   := \033[0;34m
GREEN  := \033[0;32m
NC     := \033[0m

help:
	@echo "$(BLUE)Available Commands:$(NC)"
	@echo "  $(GREEN)make test SCOPE=api$(NC)  Run backend tests"
	@echo "  $(GREEN)make dev ACTION=up$(NC)   Start services"
```

### 3. Argument Pass-Through

Use an `ARGS` variable to pass flags to the underlying tools.

```makefile
# Usage: make test SCOPE=api ARGS="-k login"
api:
	uv run pytest $(ARGS)
```

### 4. Color Coding for Output

Use ANSI color codes to improve readability:

```makefile
# Color codes
BLUE   := \033[0;34m   # For informational messages
GREEN  := \033[0;32m   # For success messages
YELLOW := \033[0;33m   # For warnings
CYAN   := \033[0;36m   # For section headers
BOLD   := \033[1m      # For emphasis
NC     := \033[0m      # Reset (No Color)
```

### 5. Target Ordering

**CRITICAL**: Order targets by importance and frequency of use, NOT alphabetically or by function type.

The typical ordering should be:

1. **Help** (always first after variables)
2. **Primary commands** (most frequently used, e.g., `dev`, `console`, `run`)
3. **Setup/Installation** (e.g., `setup`, `install`)
4. **Testing** (e.g., `test`)
5. **Code quality** (e.g., `format`, `lint`)
6. **Utilities** (e.g., `clean`, `download-files`)

Example:
```makefile
help:       # Always first
dev:        # Most used command
console:    # Second most used
setup:      # Installation
test:       # Testing
format:     # Code quality
lint:       # Code quality
clean:      # Utilities
```

### 6. File Organization

Structure your Makefile with clear sections in importance order:

```makefile
# =============================================================================
# Project Name - Makefile
# =============================================================================
# Quick Reference: Show the 3-5 most important commands only
# =============================================================================

.PHONY: help dev console setup test format lint clean  # Order by importance
.DEFAULT_GOAL := help

# -----------------------------------------------------------------------------
# Colors
# -----------------------------------------------------------------------------
[Color definitions]

# -----------------------------------------------------------------------------
# Default Variables
# -----------------------------------------------------------------------------
[Variable definitions]

# =============================================================================
# HELP
# =============================================================================
[Help target - always first]

# =============================================================================
# PRIMARY COMMANDS (Most frequently used)
# =============================================================================
[dev, console, run, or other primary targets]

# =============================================================================
# SETUP - Installation and configuration
# =============================================================================
[setup, install targets]

# =============================================================================
# TEST - Testing
# =============================================================================
[test target]

# =============================================================================
# CODE QUALITY - Formatting and Linting
# =============================================================================
[format, lint targets]

# =============================================================================
# UTILITIES
# =============================================================================
[clean, download-files, and other utilities]
```

## Prohibited Patterns

- **Target Proliferation (CRITICAL)**: Do NOT create discrete targets like `test-api`, `test-frontend`, `test-e2e`, `test-unit`, `test-api-integration`, `dev-backend`, `dev-frontend`, etc. This is the #1 anti-pattern. Instead:
  - ✗ `test-api`, `test-frontend`, `test-e2e` → ✓ `make test SCOPE=api|frontend|e2e`
  - ✗ `dev-up`, `dev-down`, `dev-restart` → ✓ `make dev ACTION=up|down|restart`
  - ✗ `lint`, `lint-fix`, `lint-check` → ✓ `make lint ARGS="--fix"` or use sensible defaults

- **Unnecessary Utility Targets**: Avoid creating targets for one-off operations that are rarely used. If a command is used only once or twice, document it in the README rather than adding a target.

- **Local Process Backgrounding**: Avoid `nohup` or `&` in Makefiles for long-running services. Prefer Docker or explicit foreground processes.

- **Redundant Aliases**: Avoid creating multiple names for the same action (e.g., `nuke` vs `clean`, `ci` vs `test`).

- **Complex Dynamic Logic**: Avoid complex `MAKECMDGOALS` parsing that makes the Makefile hard to read.

## Best Practices

### Error Handling

Always validate required variables and provide clear error messages:

```makefile
run:
	@if [ -z "$(CMD)" ]; then \
		echo "$(YELLOW)Error: CMD is required$(NC)"; \
		echo "Usage: make run CMD=<command> [ARGS=\"...\"]"; \
		exit 1; \
	fi
```

### Consistent Messaging

Use consistent color-coded output:
- `BLUE` for "Starting..." messages
- `GREEN` for "Complete!" messages
- `YELLOW` for warnings and errors
- `CYAN` for section dividers

### Documentation

Each target should:
1. Include a `##` comment for the help system
2. Provide usage hints when called incorrectly
3. Echo informative messages during execution

## Summary Checklist for New Targets

Before adding ANY new target, ask:

- [ ] **Is this target truly necessary?** Can I use an existing target with `SCOPE` or `ARGS` instead?
- [ ] **Is this a frequently-used command?** If not, should it be documented in README instead?
- [ ] Uses `SCOPE` if applicable to multiple services/scopes?
- [ ] Provides pass-through via `ARGS` for flexibility?
- [ ] Includes a clear usage hint for invalid inputs?
- [ ] Added to `make help` with a realistic example?
- [ ] Uses consistent color coding for output?
- [ ] Properly validates required variables?
- [ ] Follows the established naming conventions?
- [ ] **Placed in importance-order** (not alphabetically)?
- [ ] Placed in the appropriate section (PRIMARY, SETUP, TEST, etc.)?

## Example: Refactoring a Bloated Makefile

**BEFORE (12 targets, hard to navigate):**
```makefile
test-unit:
	pytest tests/unit

test-integration:
	pytest tests/integration

test-e2e:
	pytest tests/e2e

test-all:
	pytest tests/

dev-api:
	uvicorn api.main:app --reload

dev-frontend:
	cd frontend && npm start

dev-all:
	$(MAKE) dev-api & $(MAKE) dev-frontend

setup-api:
	pip install -r requirements.txt

setup-frontend:
	cd frontend && npm install

setup-all:
	$(MAKE) setup-api && $(MAKE) setup-frontend
```

**AFTER (4 targets, clear and flexible):**
```makefile
.DEFAULT_GOAL := help

help:
	@echo "Primary Commands:"
	@echo "  make dev SCOPE=api|frontend|all"
	@echo "  make test SCOPE=unit|integration|e2e|all"
	@echo "  make setup SCOPE=api|frontend|all"

dev:
	@case "$(SCOPE)" in \
		api) uvicorn api.main:app --reload ;; \
		frontend) cd frontend && npm start ;; \
		all) $(MAKE) dev SCOPE=api & $(MAKE) dev SCOPE=frontend ;; \
		*) echo "Usage: make dev SCOPE=[api|frontend|all]"; exit 1 ;; \
	esac

test:
	@case "$(SCOPE)" in \
		unit) pytest tests/unit $(ARGS) ;; \
		integration) pytest tests/integration $(ARGS) ;; \
		e2e) pytest tests/e2e $(ARGS) ;; \
		all) pytest tests/ $(ARGS) ;; \
		*) echo "Usage: make test SCOPE=[unit|integration|e2e|all]"; exit 1 ;; \
	esac

setup:
	@case "$(SCOPE)" in \
		api) pip install -r requirements.txt ;; \
		frontend) cd frontend && npm install ;; \
		all) $(MAKE) setup SCOPE=api && $(MAKE) setup SCOPE=frontend ;; \
		*) echo "Usage: make setup SCOPE=[api|frontend|all]"; exit 1 ;; \
	esac
```

## Example: Well-Structured Makefile

For a complete reference implementation, see [references/Makefile](references/Makefile) which demonstrates:

- Minimal target count (5-8 targets)
- Importance-first target ordering
- Variable-based scoping
- Comprehensive help documentation
- Color-coded output
- Error handling with helpful messages
- Argument pass-through
- Consistent patterns across all targets

## Related Documentation

- [makefile-organization.mdc](makefile-organization.mdc) - Detailed organization standards
- [references/Makefile](references/Makefile) - Complete working example
