# Phase 1: Foundation

<- [Back to Main Plan](./README.md)

## Table of Contents

- [Overview](#overview)
- [Context](#context)
- [Dependencies](#dependencies)
- [Changes Required](#changes-required)
- [Success Criteria](#success-criteria)

## Overview

Create the package `__init__.py` with public exports, `config.py` with pydantic-settings for managing API keys, model configuration, menu path, and Langfuse credentials, and `logging.py` for loguru configuration (stderr + rotating file sinks).

## Context

Before starting, read these files:
- `src/orchestrator/orchestrator/models.py` — Understand all model classes to export
- `src/orchestrator/orchestrator/enums.py` — Understand all enum classes to export
- `src/orchestrator/pyproject.toml` — Verify `pydantic-settings` is a dependency

## Dependencies

**Depends on:** None
**Required by:** Phase 2 (Tools), Phase 3 (Graph), Phase 4 (CLI + Langfuse)

## Changes Required

### 1.1: Create `__init__.py`
**File:** `src/orchestrator/orchestrator/__init__.py`
**Action:** CREATE

**What this does:** Provides a clean public API for the `orchestrator` package, exporting all models, enums, and (later) the graph.

```python
"""McDonald's Drive-Thru Orchestrator — LLM Orchestrator Pattern (v1)."""

from .enums import CategoryName, Size
from .models import Item, Location, Menu, Modifier, Order

__all__ = [
    "CategoryName",
    "Item",
    "Location",
    "Menu",
    "Modifier",
    "Order",
    "Size",
]
```

### 1.2: Create `config.py`
**File:** `src/orchestrator/orchestrator/config.py`
**Action:** CREATE

**What this does:** Centralizes all configuration using pydantic-settings. Reads from environment variables and `.env` file. Provides a cached `get_settings()` function so the settings object is created once.

```python
"""Application configuration via pydantic-settings.

Reads from environment variables and .env file at project root.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is 4 levels up from this file:
# src/orchestrator/orchestrator/config.py -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    mistral_api_key: str
    mistral_model: str = "mistral-small-latest"
    mistral_temperature: float = 0.0

    # --- Menu ---
    menu_json_path: str = str(
        PROJECT_ROOT / "menus" / "mcdonalds" / "breakfast-menu" / "json" / "breakfast-v2.json"
    )

    # --- Logging ---
    log_level: str = "DEBUG"

    # --- Langfuse ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance (created once)."""
    return Settings()
```

### 1.3: Create `logging.py`
**File:** `src/orchestrator/orchestrator/logging.py`
**Action:** CREATE

**What this does:** Centralizes loguru configuration. Provides a `setup_logging()` function that removes the default handler and adds two sinks: stderr (for real-time output) and a rotating log file. Log files rotate every 3 hours and are deleted after 1 day. Called once at application startup (in `main.py`).

```python
"""Loguru logging configuration.

Call setup_logging() once at application startup to configure sinks.
All other modules simply do `from loguru import logger` and log normally.
"""

import sys
from pathlib import Path

from loguru import logger

# Log directory at project root
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"


def setup_logging(level: str = "DEBUG") -> None:
    """Configure loguru with stderr and rotating file sinks.

    Args:
        level: Minimum log level (default DEBUG).
    """
    # Remove the default stderr handler so we can reconfigure it
    logger.remove()

    # Sink 1: stderr — human-readable, colored
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )

    # Sink 2: rotating log file — rotate every 3 hours, delete after 1 day
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOG_DIR / "orchestrator.log",
        level=level,
        rotation="3 hours",
        retention="1 day",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )
```

**Key design decisions:**
- `setup_logging()` is a function (not module-level side effect) so tests and imports don't trigger file I/O
- Other modules simply do `from loguru import logger` — no setup needed at the module level
- `LOG_DIR` defaults to `<project_root>/logs/`; the directory is auto-created
- stderr format is concise (time + level + module:function); file format adds date and line numbers

> **Note:** Add `logs/` to `.gitignore` if not already present.

### 1.4: Create `.env.local`
**File:** `.env.local`
**Action:** CREATE

**What this does:** Provides an example/template `.env` file showing users what environment variables are needed. This file is safe to commit (contains no real secrets).

```
# McDonald's Drive-Thru Bot — Environment Variables
# Copy this file to .env and fill in your values:
#   cp .env.local .env

# --- Required ---
MISTRAL_API_KEY=your-mistral-api-key

# --- Optional (defaults shown) ---
# MISTRAL_MODEL=mistral-small-latest
# MISTRAL_TEMPERATURE=0.0
# MENU_JSON_PATH=menus/mcdonalds/breakfast-menu/json/breakfast-v2.json

# --- Logging (optional — default DEBUG) ---
# LOG_LEVEL=DEBUG

# --- Langfuse (optional — leave empty to disable tracing) ---
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_SECRET_KEY=sk-lf-...
# LANGFUSE_HOST=https://cloud.langfuse.com
```

> **Note:** Verify that `.env` is in `.gitignore` (it should already be). Do NOT create or modify `.env` itself — the user manages their own secrets. Only create `.env.local` as a template.

## Success Criteria

### Automated Verification:
- [ ] File exists: `src/orchestrator/orchestrator/__init__.py`
- [ ] File exists: `src/orchestrator/orchestrator/config.py`
- [ ] File exists: `src/orchestrator/orchestrator/logging.py`
- [ ] Python can import the package: `uv run --package orchestrator python -c "from orchestrator import Item, Menu, Order, Size, CategoryName; print('OK')"`
- [ ] Config loads with env vars: `uv run --package orchestrator python -c "from orchestrator.config import get_settings; print(get_settings().mistral_model)"`
- [ ] Logging setup works: `uv run --package orchestrator python -c "from orchestrator.logging import setup_logging; setup_logging(); from loguru import logger; logger.info('test')"`
- [ ] Ruff passes: `uv run ruff check src/orchestrator/orchestrator/__init__.py src/orchestrator/orchestrator/config.py src/orchestrator/orchestrator/logging.py`

---

<- [Back to Main Plan](./README.md)
