# UV Workspace with Hatchling: Structure & Best Practices

## Directory Structure Diagram

A workspace with three packages: a shared library (`core-lib`), a data layer (`data-models`), and an application (`voice-agent`).

```
my-workspace/                          # Workspace root
├── pyproject.toml                     # Root config: workspace members, shared deps
├── uv.lock                           # Single lockfile for entire workspace
├── .python-version                   # Pinned Python version (e.g. 3.12)
├── .gitignore
├── README.md
│
├── packages/
│   ├── core-lib/                     # Shared utility library
│   │   ├── pyproject.toml            # Package config + hatchling build
│   │   ├── src/
│   │   │   └── core_lib/
│   │   │       ├── __init__.py
│   │   │       ├── config.py
│   │   │       └── utils.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_utils.py
│   │
│   ├── data-models/                  # Data layer / Pydantic models
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── data_models/
│   │   │       ├── __init__.py
│   │   │       ├── menu.py
│   │   │       └── order.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_menu.py
│   │
│   └── voice-agent/                  # Application package
│       ├── pyproject.toml
│       ├── src/
│       │   └── voice_agent/
│       │       ├── __init__.py
│       │       ├── agent.py
│       │       └── graph.py
│       └── tests/
│           ├── __init__.py
│           └── test_agent.py
│
└── .venv/                            # Single shared virtualenv (gitignored)
```

Key points about this layout:

- **`packages/` directory** groups all workspace members under one folder
- **src-layout** (`src/package_name/`) in each member prevents accidental imports and keeps tests isolated
- **Single `.venv/`** at the workspace root, shared by all members
- **Single `uv.lock`** at the root ensures consistent dependency versions across all packages

---

## Configuration Files

### Root `pyproject.toml`

The root defines the workspace and optionally acts as a virtual package (no build output).

```toml
[project]
name = "my-workspace"
version = "0.1.0"
description = "Voice AI workspace"
requires-python = ">=3.12"
dependencies = []

[tool.uv.workspace]
members = ["packages/*"]

# Map workspace member names to workspace resolution
[tool.uv.sources]
core-lib = { workspace = true }
data-models = { workspace = true }
voice-agent = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**`[tool.uv.workspace].members`** accepts glob patterns. Every matched directory must contain a `pyproject.toml` with a `[project]` table.

**`[tool.uv.sources]`** at the root level applies to all members. This tells uv to resolve these package names from the workspace instead of PyPI.

---

### Member: `packages/core-lib/pyproject.toml`

A standalone library with no workspace dependencies.

```toml
[project]
name = "core-lib"
version = "0.1.0"
description = "Shared utilities"
requires-python = ">=3.12"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/core_lib"]
```

---

### Member: `packages/data-models/pyproject.toml`

Depends on `core-lib` (a sibling workspace member) and an external package.

```toml
[project]
name = "data-models"
version = "0.1.0"
description = "Pydantic data models"
requires-python = ">=3.12"
dependencies = [
    "core-lib",
    "pydantic>=2.0",
]

[tool.uv.sources]
core-lib = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/data_models"]
```

---

### Member: `packages/voice-agent/pyproject.toml`

The application layer. Depends on both sibling packages plus external deps.

```toml
[project]
name = "voice-agent"
version = "0.1.0"
description = "Voice ordering agent"
requires-python = ">=3.12"
dependencies = [
    "core-lib",
    "data-models",
    "langgraph>=0.2",
    "langfuse>=2.0",
]

[tool.uv.sources]
core-lib = { workspace = true }
data-models = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/voice_agent"]
```

---

## Dependency Flow

```
voice-agent
├── core-lib        (workspace)
├── data-models     (workspace)
│   └── core-lib    (workspace, shared)
├── langgraph       (PyPI)
└── langfuse        (PyPI)

data-models
├── core-lib        (workspace)
└── pydantic        (PyPI)

core-lib
└── (no dependencies)
```

All workspace member dependencies are installed as **editable** automatically. Changes to `core-lib` source code are immediately visible to `data-models` and `voice-agent` without reinstalling.

---

## Hatchling Build Backend

### Why Hatchling

- Default build backend for `uv init` projects
- Supports src-layout via `[tool.hatch.build.targets.wheel]`
- Extensible with plugins (e.g. `hatch-vcs` for git-based versioning)
- Handles both pure Python and extension modules

### The Critical Setting

With src-layout, hatchling needs to know where your packages live:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]
```

Without this, hatchling won't find your code inside `src/`.

### Optional: Dynamic Versioning from Git Tags

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "core-lib"
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"
```

### Optional: File Include/Exclude

```toml
[tool.hatch.build]
include = ["src/**/*.py", "README.md"]
exclude = ["tests/", "*.json"]
```

---

## Common Workflows

```bash
# Install all workspace dependencies
uv sync --all-packages

# Sync only a specific package and its deps
uv sync --package voice-agent

# Add a dependency to a specific member
cd packages/voice-agent
uv add httpx

# Run code in a specific member's context
uv run --package voice-agent python -m voice_agent

# Run tests for one member
uv run --package data-models pytest

# Build a distributable wheel for one member
uv build --package core-lib

# Lock dependencies (always workspace-wide)
uv lock

# Create a new member package
uv init --package packages/new-service
```

---

## Best Practices Summary

| Practice | Why |
|---|---|
| **src-layout** (`src/pkg/`) in every member | Prevents accidental imports; clean test isolation |
| **`[tool.uv.sources]` at root** for all members | Single place to declare workspace resolution; applies to all members |
| **Repeat `[tool.uv.sources]` in members** that depend on siblings | Makes each member self-documenting; works if extracted from workspace |
| **One `requires-python`** across workspace | uv enforces the intersection of all members; keep them consistent |
| **Commit `uv.lock`** | Reproducible installs across machines and CI |
| **Gitignore `.venv/`, `dist/`, `*.egg-info/`** | Build artifacts don't belong in version control |
| **Use `uv add` not manual edits** | Ensures compatible versions and updates the lockfile |
| **Keep root `dependencies` minimal** | Root is for workspace config; real deps live in members |

---

## Common Pitfalls

**Package name vs directory name**: The `name` field in `[project]` is what you reference in dependencies and `[tool.uv.sources]`, not the directory name. Directory `data-models/` contains package name `data-models` with Python module `data_models`.

**Missing `[tool.hatch.build.targets.wheel]`**: Without the `packages` key, hatchling won't find code inside `src/`. Builds will produce empty wheels.

**Conflicting dependency versions**: Workspace members share one lockfile. If two members need incompatible versions of the same package, use path dependencies instead of a workspace.

**Running commands from wrong context**: `uv run pytest` uses the package context of your current directory. Use `--package <name>` to be explicit.
