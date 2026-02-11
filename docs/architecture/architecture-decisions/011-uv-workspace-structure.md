# ADR-011: uv Workspace with Independent Member Packages

**Status:** Accepted

[Back to ADR Index](./adr.md)

---

## Context

The project is designed to evolve through multiple stages (orchestrator, voice integration, multi-location support, etc.). Each stage may have different dependencies. The build system needs to support:
- Independent packages with their own dependencies
- A shared lockfile for reproducibility
- Shared dev tools (ruff, ty, pytest) across all packages
- Running package-specific commands (`uv run --package orchestrator ...`)

**Options considered:**
1. **Single package** — One `pyproject.toml` with all dependencies
2. **Monorepo with separate lockfiles** — Independent packages, each with their own `uv.lock`
3. **uv workspace** — Single root with member packages, one lockfile

## Decision

Use a **uv workspace** with the orchestrator as the first member package.

### Workspace layout

```
mcdonalds-drive-thru-bot/
├── pyproject.toml                 # Workspace root
├── uv.lock                        # Single lockfile
├── src/
│   └── orchestrator/              # Workspace member
│       ├── pyproject.toml         # Member dependencies
│       └── orchestrator/          # Python package
│           ├── __init__.py
│           ├── config.py
│           ├── enums.py
│           ├── models.py
│           ├── tools.py
│           ├── graph.py
│           ├── main.py
│           └── logging.py
├── menus/                         # Shared data
├── tests/                         # Tests (outside packages)
├── scripts/                       # Utilities
└── logs/                          # Runtime logs
```

### Root pyproject.toml (workspace config)

```toml
[project]
name = "mcdonalds-voice-ai"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []                  # Root has no runtime dependencies

[tool.uv.workspace]
members = ["src/orchestrator"]     # Future: src/voice, src/locations, etc.

[dependency-groups]
dev = [
    "langgraph-cli[inmem]>=0.4.12",
    "ruff>=0.14.14",
    "ty>=0.0.15",
    "pre-commit>=4.5.1",
]
```

### Member pyproject.toml (orchestrator)

```toml
[project]
name = "orchestrator"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "langchain>=1.2.9",
    "langchain-mistralai>=1.1.1",
    "langfuse>=3.12.1",
    "langgraph>=1.0.7",
    "loguru>=0.7.3",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.12.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Module exports — no graph in `__init__.py`

```python
# __init__.py
from .enums import CategoryName, Size
from .models import Item, Location, Menu, Modifier, Order
from .tools import add_item_to_order, finalize_order, get_current_order, lookup_menu_item

# graph is NOT exported — avoids triggering lazy LLM init on import
```

This is a deliberate consequence of [ADR-007](./007-lazy-llm-initialization.md). While the LLM itself is lazy-initialized, the graph module still imports `langchain_mistralai`, `langgraph`, and other heavy dependencies. Keeping `graph` out of `__init__.py` means `from orchestrator import Item` doesn't pull in the entire LangChain stack.

**Why single package was rejected:**
- All dependencies in one `pyproject.toml` creates coupling between stages
- Adding a voice stage would force the orchestrator to depend on audio libraries

**Why separate lockfiles were rejected:**
- Dependency version conflicts between packages are discovered at install time, not at resolution time
- Multiple lockfiles are harder to maintain

## Consequences

**Benefits:**
- Clean dependency isolation: each stage declares only what it needs
- Single `uv.lock` ensures all packages use compatible dependency versions
- Dev tools (ruff, ty, pre-commit) are shared via the root `dependency-groups.dev`
- Easy to add new stages: create `src/new-stage/`, add to `members`, add dependencies
- `uv run --package orchestrator` scopes execution to the correct dependency set

**Tradeoffs:**
- uv workspace is a newer feature — tooling support may lag behind pip/poetry
- The `src/orchestrator/orchestrator/` double-nesting is verbose (required by hatchling conventions)
- Tests live outside packages (`tests/orchestrator/`) — they must be run with `uv run --package orchestrator pytest`

---

[Back to ADR Index](./adr.md)
