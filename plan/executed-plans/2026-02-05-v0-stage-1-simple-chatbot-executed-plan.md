# v0-stage-1: Simple Chatbot Implementation Plan

> **Status:** COMPLETED

## Table of Contents

- [Overview](#overview)
- [Current State Analysis](#current-state-analysis)
- [Desired End State](#desired-end-state)
- [What We're NOT Doing](#what-were-not-doing)
- [Implementation Approach](#implementation-approach)
- [Dependencies](#dependencies)
- [Phase 1: Configuration Setup](#phase-1-configuration-setup)
- [Phase 2: LangGraph Chatbot](#phase-2-langgraph-chatbot)
- [Phase 3: Langfuse Observability](#phase-3-langfuse-observability)
- [Phase 4: CLI and Makefile](#phase-4-cli-and-makefile)
- [Phase 5: LangGraph Platform Deployment](#phase-5-langgraph-platform-deployment)
- [Testing Strategy](#testing-strategy)
- [References](#references)

## Overview

v0-stage-1 is a minimal working chatbot that establishes the foundation for future stages. It is a general-purpose conversational assistant with no McDonald's-specific functionality. The goal is to validate the tech stack integration: LangGraph + Mistral AI + Langfuse observability + LangGraph Platform deployment.

## Current State Analysis

**What exists:**
- Python 3.12 project with `uv` package management
- Pydantic models for menu items in `src/models.py` and `src/enums.py`
- Dependencies already installed: `langgraph`, `langfuse`, `langchain-mistralai`, `pydantic-settings`
- `.env` file with: `MISTRAL_API_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_BASE_URL`

**What's missing:**
- No `src/__init__.py` (required for Python package imports)
- No package configuration in `pyproject.toml` (required for `uv` to recognize `src/` packages)
- No LangGraph graph implementation
- No config module using pydantic_settings
- No Langfuse integration
- No `langgraph.json` for deployment
- No Makefile

## Desired End State

A working chatbot that:
1. Loads configuration from `.env` via pydantic_settings
2. Runs a simple LangGraph conversation graph with Mistral AI
3. Streams responses token-by-token for real-time feedback
4. Traces all interactions to Langfuse
5. Can be run locally via `make chat`
6. Can be deployed to LangGraph Platform

**Success Criteria:**
- [ ] `make chat` starts an interactive CLI conversation
- [ ] Conversations are visible in Langfuse dashboard
- [ ] `langgraph dev` runs the graph in LangGraph Studio
- [ ] Graph can be deployed to LangGraph Platform

**How to Verify:**
1. Run `make chat`, have a multi-turn conversation, verify responses stream token-by-token
2. Check Langfuse dashboard for traces with session/user IDs
3. Run `langgraph dev` and interact via Studio UI
4. Deploy with `langgraph deploy`

## What We're NOT Doing

- No McDonald's menu functionality
- No structured outputs or intent classification
- No persistence/checkpointing (stateless for now)
- No tests (deferred to later stage)
- No custom prompts in Langfuse prompt management

## Implementation Approach

Build incrementally:
1. Config module first (foundation for all other code)
2. Graph with Mistral (core chatbot logic)
3. Add Langfuse observability (wrap existing graph)
4. CLI entry point + Makefile (local testing)
5. LangGraph Platform config (deployment)

## Dependencies

**Execution Order:**

1. Phase 1: Configuration Setup (no dependencies)
2. Phase 2: LangGraph Chatbot (depends on Phase 1)
3. Phase 3: Langfuse Observability (depends on Phase 2)
4. Phase 4: CLI and Makefile (depends on Phase 3)
5. Phase 5: LangGraph Platform Deployment (depends on Phase 2)

**Dependency Graph:**

```
Phase 1 (Config)
    │
    ├──► Phase 2 (Graph)
    │        │
    │        ├──► Phase 3 (Langfuse)
    │        │        │
    │        │        └──► Phase 4 (CLI + Makefile)
    │        │
    │        └──► Phase 5 (LangGraph Platform)
```

**Parallelization:**
- Phases 1-4 must be sequential
- Phase 5 can start after Phase 2 (parallel with Phases 3-4)

---

## Phase 1: Configuration Setup

### Overview

Create a config module using pydantic_settings to load environment variables.

### Context

Before starting, read these files:
- `src/` - Understand existing module structure
- `.env` - Verify environment variable names
- `pyproject.toml` - Confirm pydantic-settings is installed

**Note on imports:** This project uses `uv` with a src-layout package configuration. The `pyproject.toml` is configured with `[tool.setuptools.package-dir]` to recognize `src/` as the package root. After running `uv sync`, imports use `from stage_1.xxx import` (not `from src.stage_1.xxx`). This configuration is set up in step 1.0 below.

### Dependencies

**Depends on:** None
**Required by:** Phase 2, Phase 3, Phase 4, Phase 5

### Changes Required

#### 1.0: Configure pyproject.toml for src-layout

**File:** `pyproject.toml`

Add the following sections to configure `uv` to recognize `src/` as the package directory:

```toml
[tool.setuptools.package-dir]
"" = "src"

[tool.setuptools.packages.find]
where = ["src"]
```

After adding this, run `uv sync` to update the environment.

**Rationale:** This tells setuptools (and `uv`) that packages live in `src/`. Without this, `from stage_1.xxx import` won't work because Python won't find `stage_1` as a top-level package.

#### 1.1: Create src package (if not exists)

**File:** `src/__init__.py`

```python
"""Source package for McDonald's drive-thru ordering system."""
```

**Rationale:** Python requires `__init__.py` for package recognition. Without this file, imports like `from stage_1.config import get_settings` will fail.

#### 1.2: Create stage_1 package

**File:** `src/stage_1/__init__.py`

```python
"""v0-stage-1: Simple chatbot with Langfuse observability."""
```

#### 1.3: Create config module

**File:** `src/stage_1/config.py`

```python
"""Configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mistral AI
    mistral_api_key: str

    # Langfuse
    langfuse_secret_key: str
    langfuse_public_key: str
    langfuse_base_url: str = "https://us.cloud.langfuse.com"


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

**Rationale:** Centralizes all configuration. Uses pydantic_settings for validation and type safety. The `extra="ignore"` allows other env vars (like `COHERE_API_KEY`) without errors.

### Success Criteria

#### Automated Verification:
- [x] Run `uv sync` after pyproject.toml changes (required for package discovery)
- [x] Module imports without error: `uv run python -c "from stage_1.config import get_settings; print(get_settings())"`

#### Manual Verification:
- [x] Settings object shows all expected values (keys redacted)

---

## Phase 2: LangGraph Chatbot

### Overview

Create a simple LangGraph graph that uses Mistral AI for conversation.

### Context

Before starting, read these files:
- `src/stage_1/config.py` - Settings class structure
- LangGraph docs on `StateGraph` and `MessagesState`
- langchain-mistralai docs for `ChatMistralAI`

### Dependencies

**Depends on:** Phase 1
**Required by:** Phase 3, Phase 4, Phase 5

### Changes Required

#### 2.1: Create graph module

**File:** `src/stage_1/graph.py`

```python
"""LangGraph chatbot graph using Mistral AI."""

from langchain_core.messages import SystemMessage
from langchain_mistralai import ChatMistralAI
from langgraph.graph import START, END, StateGraph, MessagesState

from stage_1.config import get_settings

SYSTEM_PROMPT = """You are a helpful, friendly assistant. Be concise and helpful.
If you don't know something, say so. Keep responses brief unless asked for detail."""


def create_chat_model() -> ChatMistralAI:
    """Create Mistral chat model."""
    settings = get_settings()
    return ChatMistralAI(
        model="mistral-small-latest",
        api_key=settings.mistral_api_key,
        temperature=0.7,
    )


def chatbot(state: MessagesState) -> dict:
    """Process messages and generate response.

    Returns partial state update (dict), not full MessagesState.
    """
    llm = create_chat_model()

    # Prepend system message if not present
    messages = state["messages"]
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = llm.invoke(messages)
    return {"messages": [response]}


def create_graph() -> StateGraph:
    """Create the chatbot graph."""
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    return graph_builder.compile()


# Export compiled graph for LangGraph Platform
graph = create_graph()
```

**Rationale:**
- Uses `MessagesState` (LangGraph's built-in message handling)
- Simple single-node graph that can be extended later
- `graph` exported at module level for LangGraph Platform deployment
- Node returns `dict` (partial state update), not full `MessagesState`
- `END` edge ensures graph terminates properly

### Success Criteria

#### Automated Verification:
- [x] Graph compiles: `uv run python -c "from stage_1.graph import graph; print(graph)"`

#### Manual Verification:
- [x] N/A (tested via CLI in Phase 4)

---

## Phase 3: Langfuse Observability

### Overview

Add Langfuse callback handler to trace all LLM calls and graph executions.

### Context

Before starting, read these files:
- `src/stage_1/config.py` - Langfuse credentials
- `src/stage_1/graph.py` - Current graph structure (from Phase 2)
- `thoughts/langfuse-observability-v0.md` - (Optional) Background on observability patterns

### Dependencies

**Depends on:** Phase 2
**Required by:** Phase 4

### Changes Required

#### 3.1: Update graph module with Langfuse

**File:** `src/stage_1/graph.py`

**Action:** Replace the entire `src/stage_1/graph.py` file with the following:

```python
"""LangGraph chatbot graph using Mistral AI with Langfuse observability."""

import atexit

from langchain_core.messages import SystemMessage
from langchain_mistralai import ChatMistralAI
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langgraph.graph import START, END, StateGraph, MessagesState

from stage_1.config import get_settings

SYSTEM_PROMPT = """You are a helpful, friendly assistant. Be concise and helpful.
If you don't know something, say so. Keep responses brief unless asked for detail."""


def get_langfuse_client() -> Langfuse:
    """Get Langfuse client instance."""
    settings = get_settings()
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_base_url,
    )


def get_langfuse_handler(
    session_id: str | None = None,
    user_id: str | None = None,
) -> CallbackHandler:
    """Get Langfuse callback handler for tracing."""
    settings = get_settings()
    return CallbackHandler(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_base_url,
        session_id=session_id,
        user_id=user_id,
    )


def create_chat_model() -> ChatMistralAI:
    """Create Mistral chat model."""
    settings = get_settings()
    return ChatMistralAI(
        model="mistral-small-latest",
        api_key=settings.mistral_api_key,
        temperature=0.7,
    )


def chatbot(state: MessagesState) -> dict:
    """Process messages and generate response.

    Returns partial state update (dict), not full MessagesState.
    """
    llm = create_chat_model()

    # Prepend system message if not present
    messages = state["messages"]
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = llm.invoke(messages)
    return {"messages": [response]}


def create_graph() -> StateGraph:
    """Create the chatbot graph."""
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    return graph_builder.compile()


# Export compiled graph for LangGraph Platform
graph = create_graph()

# Register flush on shutdown
_langfuse = get_langfuse_client()
atexit.register(_langfuse.flush)
```

**Rationale:**
- `get_langfuse_handler()` returns a callback handler that can be passed to graph invocations
- Session/user IDs are optional parameters for grouping traces
- `atexit.register` ensures traces are flushed before process exit

### Success Criteria

#### Automated Verification:
- [x] Langfuse auth check passes: `uv run python -c "from stage_1.graph import get_langfuse_client; print(get_langfuse_client().auth_check())"`

#### Manual Verification:
- [ ] After running chat (Phase 4), traces appear in Langfuse dashboard

---

## Phase 4: CLI and Makefile

### Overview

Create a CLI chat loop and Makefile target for running the chatbot locally.

### Context

Before starting, read these files:
- `src/stage_1/graph.py` - Graph and Langfuse handler
- Project root - Check if Makefile exists

### Dependencies

**Depends on:** Phase 3
**Required by:** None

### Changes Required

#### 4.1: Create CLI entry point

**File:** `src/stage_1/main.py`

```python
"""CLI chat interface for stage-1 chatbot with streaming responses."""

import uuid

from langchain_core.messages import AIMessage, HumanMessage, AIMessageChunk

from stage_1.graph import graph, get_langfuse_handler, get_langfuse_client


def run_chat() -> None:
    """Run interactive chat loop with streaming responses."""
    # Generate session and user IDs for tracing
    session_id = f"cli-session-{uuid.uuid4().hex[:8]}"
    user_id = f"cli-user-{uuid.uuid4().hex[:8]}"

    print("Stage-1 Chatbot (type 'quit' to exit)")
    print(f"Session: {session_id}")
    print("-" * 40)

    # Get Langfuse handler for this session
    langfuse_handler = get_langfuse_handler(
        session_id=session_id,
        user_id=user_id,
    )

    messages = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Add user message
        messages.append(HumanMessage(content=user_input))

        # Stream response with Langfuse tracing
        print("\nAssistant: ", end="", flush=True)

        full_response = ""
        try:
            for chunk, metadata in graph.stream(
                {"messages": messages},
                config={"callbacks": [langfuse_handler]},
                stream_mode="messages",
            ):
                # Only process AI message chunks
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    print(chunk.content, end="", flush=True)
                    full_response += chunk.content
        except Exception as e:
            print(f"\nError: {e}")
            # Remove the failed user message from history
            messages.pop()
            continue

        print()  # Newline after streaming completes

        # Add complete response to message history
        messages.append(AIMessage(content=full_response))

    # Flush traces before exit
    langfuse = get_langfuse_client()
    langfuse.flush()


if __name__ == "__main__":
    run_chat()
```

**Rationale:**
- Uses `graph.stream()` with `stream_mode="messages"` for token-by-token streaming
- Prints each token as it arrives for real-time feedback
- Accumulates full response for conversation history
- Generates unique session/user IDs for each chat session (traceable in Langfuse)
- Maintains conversation history across turns
- Graceful handling of Ctrl+C and EOF
- Error handling for API failures (rate limits, timeouts)
- Explicit flush at exit

#### 4.2: Create Makefile

**File:** `Makefile`

> **IMPORTANT:** Makefile recipes require literal TAB characters for indentation, not spaces. If you use spaces, you'll get `*** missing separator. Stop.` errors. Most editors have a setting to insert tabs in Makefiles.

```makefile
.PHONY: chat dev test-smoke help

# Default target
help:
	@echo "Available targets:"
	@echo "  make chat       - Run CLI chatbot"
	@echo "  make dev        - Run LangGraph Studio"
	@echo "  make test-smoke - Verify imports and graph compilation"
	@echo "  make help       - Show this help"

# Run CLI chatbot
chat:
	uv run python -m stage_1.main

# Run LangGraph Studio (requires langgraph.json)
dev:
	uv run langgraph dev

# Smoke test - verify imports work and graph compiles
test-smoke:
	@echo "Testing imports..."
	uv run python -c "from stage_1.config import get_settings; print('Config: OK')"
	uv run python -c "from stage_1.graph import graph; print('Graph: OK')"
	uv run python -c "from stage_1.graph import get_langfuse_client; print('Langfuse auth:', get_langfuse_client().auth_check())"
	@echo "All smoke tests passed!"
```

**Rationale:**
- `make chat` runs the CLI chatbot
- `make dev` runs LangGraph Studio (after Phase 5)
- `make test-smoke` provides quick automated verification
- Simple and extensible for future stages

### Success Criteria

#### Automated Verification:
- [x] `make help` shows available targets (NOTE: make not available on Windows - use direct commands)
- [x] `make test-smoke` passes all checks (verified via direct uv commands)

#### Manual Verification:
- [ ] `make chat` starts interactive conversation
- [ ] Responses stream token-by-token (not all at once)
- [ ] Multi-turn conversation works (context maintained)
- [ ] Type 'quit' exits cleanly
- [ ] Traces visible in Langfuse dashboard with session_id

---

## Phase 5: LangGraph Platform Deployment

### Overview

Configure the project for LangGraph Platform (formerly LangGraph Cloud) deployment.

### Context

Before starting, read these files:
- `src/stage_1/graph.py` - Graph export
- LangGraph Platform docs on `langgraph.json`

### Dependencies

**Depends on:** Phase 2
**Required by:** None

### Changes Required

#### 5.1: Create langgraph.json

**File:** `langgraph.json`

```json
{
  "dependencies": ["."],
  "graphs": {
    "chatbot": "./src/stage_1/graph.py:graph"
  },
  "env": ".env"
}
```

**Rationale:**
- `dependencies` includes the project root, which installs the package using the `pyproject.toml` configuration (allows imports from `stage_1`)
- `graphs` maps the graph name to the module path and variable
- `env` loads environment variables from `.env`

**Note:** This relies on the `pyproject.toml` package configuration from Phase 1 (step 1.0). LangGraph Platform will install the project as a package, making `from stage_1.xxx` imports work.

### Success Criteria

#### Automated Verification:
- [x] `uv run langgraph dev` starts without errors

#### Manual Verification:
- [x] LangGraph Studio UI loads at http://localhost:2024
- [x] Can send messages and receive responses in Studio
- [x] Traces appear in Langfuse

---

## Testing Strategy

**Unit tests deferred to later stage.** For v0-stage-1, smoke tests and manual verification are sufficient:

**Automated (smoke test):**
```bash
make test-smoke
```
This verifies imports work and Langfuse authentication passes.

**Manual verification:**
1. Run `make chat` and have a multi-turn conversation (done via graph+while loop, not a new graph)
2. Verify traces in Langfuse dashboard (check session_id grouping)
3. Run `make dev` and test via LangGraph Studio

---

## References

- Thought docs: `thoughts/langgraph-state-design-v0.md`, `thoughts/langfuse-observability-v0.md`
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- Langfuse Python SDK: https://langfuse.com/docs/sdk/python
- LangGraph Platform: https://langchain-ai.github.io/langgraph/cloud/
