# Options for Multi-Stage Project Organization

## Current State

- Single `pyproject.toml` at repo root with all dependencies lumped together
- `src/stage_1/` already exists with its own code
- All stages will live under `src/` but need independent configs/dependencies

---

## Option A: uv Workspaces (Recommended if deps are compatible)

**How it works:** A root `pyproject.toml` declares workspace members. Each stage gets its own `pyproject.toml` with its own dependencies. One shared `uv.lock` and one shared `.venv`.

**Directory structure:**
```
mcdonalds-data-model/
├── pyproject.toml          # workspace root (shared dev deps, tooling config)
├── uv.lock                 # single lockfile for all stages
├── .venv/                  # single venv
├── menus/                  # shared data
├── src/
│   ├── models/             # shared data models package
│   │   ├── pyproject.toml
│   │   └── src/models/
│   │       ├── __init__.py
│   │       ├── enums.py
│   │       └── models.py
│   ├── stage_1/
│   │   ├── pyproject.toml  # stage_1's own deps
│   │   └── src/stage_1/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── graph.py
│   │       └── main.py
│   ├── stage_2/
│   │   ├── pyproject.toml  # stage_2's own deps
│   │   └── src/stage_2/
│   │       └── ...
│   └── stage_3/
│       ├── pyproject.toml
│       └── src/stage_3/
│           └── ...
```

**Root pyproject.toml:**
```toml
[project]
name = "mcdonalds-voice-ai"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []  # no app deps at root, just coordination

[tool.uv.workspace]
members = ["src/*"]

[dependency-groups]
dev = [
    "pre-commit>=4.5.1",
    "ruff>=0.14.14",
    "ty>=0.0.15",
]

[tool.ruff]
line-length = 88
target-version = "py312"
```

**Stage member pyproject.toml (e.g. src/stage_2/pyproject.toml):**
```toml
[project]
name = "stage-2"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "models",            # shared models via workspace
    "langgraph>=1.0.7",
    "langfuse>=3.12.1",
    "langchain-mistralai>=1.1.1",
]

[tool.uv.sources]
models = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Running commands:**
```bash
uv run --package stage-1 python -m stage_1.main
uv run --package stage-2 python -m stage_2.main
uv sync --package stage-2        # sync just stage_2's deps
uv sync --all-packages           # sync everything
```

**Pros:**
- Single lockfile = consistent dependency versions across stages
- `--package` flag makes it easy to target a specific stage
- Workspace members auto-installed as editable packages
- Stages can depend on shared packages (like `models`) trivially

**Cons:**
- All stages must have **compatible** dependency versions (e.g., can't have stage_1 on langchain 0.2 and stage_2 on langchain 0.3 if they conflict)
- Single shared venv — a stage might accidentally import another stage's deps
- Slightly more setup (each stage needs a build-system and proper package structure)

---

## Option B: Fully Separate Projects (--directory flag)

**How it works:** Each stage is a completely independent project with its own `pyproject.toml`, `uv.lock`, and `.venv`. No formal workspace relationship.

**Directory structure:**
```
mcdonalds-data-model/
├── pyproject.toml          # root project (shared models only)
├── uv.lock
├── menus/
├── src/
│   ├── enums.py
│   ├── models.py
│   ├── stage_1/
│   │   ├── pyproject.toml  # fully independent
│   │   ├── uv.lock         # own lockfile
│   │   ├── .venv/          # own venv
│   │   └── ...
│   ├── stage_2/
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   ├── .venv/
│   │   └── ...
```

**Running commands:**
```bash
uv run --directory src/stage_1 python -m stage_1.main
uv sync --directory src/stage_2
uv add --directory src/stage_2 langchain-openai
```

**Stage pyproject.toml:**
```toml
[project]
name = "stage-2"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcdonalds-data-model",  # shared models via path dep
    "langgraph>=1.0.7",
]

[tool.uv.sources]
mcdonalds-data-model = { path = "../..", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Pros:**
- Total isolation — conflicting deps between stages are fine
- Each stage has its own lockfile and venv
- Simplest mental model: each stage is just a standalone project
- Easy to delete/archive a stage without affecting others

**Cons:**
- Multiple lockfiles to manage
- Shared code via path dependencies is slightly more manual
- No `--package` flag — must use `--directory` or `cd` into each stage
- `uv sync` must be run separately per stage

---

## Option C: Hybrid — Workspace + Shared Models Package

**How it works:** Like Option A but the root project itself is a "virtual" coordinator (no installable package), and the shared data models are extracted into their own workspace member.

This is the same as Option A structurally. The distinction is that you keep the root `pyproject.toml` non-installable by not giving it a build-system, and put ALL actual code into workspace members.

**Root pyproject.toml:**
```toml
[project]
name = "mcdonalds-voice-ai"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv.workspace]
members = ["src/*"]

[dependency-groups]
dev = ["pre-commit>=4.5.1", "ruff>=0.14.14", "ty>=0.0.15"]

# No [build-system] — root is not installable
```

This is essentially Option A refined. Stages that don't need the shared models simply don't list them as dependencies.

---

## Option D: Simple Directory Convention (No Workspaces)

**How it works:** Keep a single `pyproject.toml` with ALL dependencies. Stages are just directories under `src/`. Use environment variables or config files to select the active stage. Simplest possible approach.

**Directory structure:**
```
mcdonalds-data-model/
├── pyproject.toml          # all deps for all stages
├── uv.lock
├── src/
│   ├── enums.py
│   ├── models.py
│   ├── stage_1/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── graph.py
│   ├── stage_2/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── graph.py
```

**Running:**
```bash
uv run python -m stage_1.main
uv run python -m stage_2.main
```

**Pros:**
- Zero setup cost — closest to what you have now
- Single `uv sync` installs everything
- No package structure changes needed
- All imports just work (e.g., `from models import Item`)

**Cons:**
- `pyproject.toml` dependencies grow with every stage (bloated venv)
- No isolation at all — can't tell which stage needs which deps
- If stages need conflicting deps, this breaks entirely
- Hardest to maintain long-term

---

## Recommendation

| Criteria | A: Workspaces | B: Separate | C: Hybrid | D: Simple |
|----------|:---:|:---:|:---:|:---:|
| Setup effort | Medium | Medium | Medium | None |
| Dep isolation | Partial | Full | Partial | None |
| Conflicting deps OK | No | Yes | No | No |
| Shared code easy | Yes | OK | Yes | Yes |
| Long-term maintainability | Good | Good | Good | Poor |
| Closest to current setup | No | No | No | Yes |

**If stages will likely share similar deps** (LangGraph, Langfuse, etc. just at different versions that are compatible): **Option A or C** (workspaces).

**If stages might need fundamentally different deps** (e.g., one uses LangGraph, another uses CrewAI, another uses raw OpenAI SDK): **Option B** (fully separate).

**If you just want to get going now and refactor later**: **Option D** (simple convention) — this is essentially what you have today.

My suggestion: **Start with Option A (workspaces)** since your stages are all LangGraph-based voice AI agents that will share similar deps. If you hit a dep conflict down the road, migrating from A to B is straightforward.
