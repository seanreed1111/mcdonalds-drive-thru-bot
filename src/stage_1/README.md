# Stage 1: Simple Chatbot

Single-node LangGraph chatbot. Mistral AI for generation, Langfuse for tracing.

## Table of Contents

- [Introduction](#introduction)
- [Tech Stack](#tech-stack)
- [Architectural Decisions](#architectural-decisions)
- [How It Works](#how-it-works)
- [The Graph](#the-graph)
- [Streaming Conversation Loop](#streaming-conversation-loop)
- [File Map](#file-map)
- [Run](#run)

## Introduction

Stage 1 is the simplest possible voice-AI chatbot — a single-node LangGraph graph backed by Mistral AI. It exists as a walking skeleton: a minimal end-to-end slice that proves the toolchain works (LangGraph orchestration, LLM calls, observability, CLI streaming) before later stages add menu knowledge, tool calling, and multi-agent flows. Everything here is intentionally bare so it can be extended without rework.

## Tech Stack

The chatbot is built on **LangGraph** (v1.0+), which provides graph-based orchestration on top of LangChain. The LLM is **Mistral AI** (`mistral-small-latest`) accessed through `langchain-mistralai`. Observability is handled by **Langfuse** (v3), which captures full LLM traces via a LangChain callback handler. Configuration uses **Pydantic Settings** to load API keys and endpoints from a `.env` file, and the project is packaged with **uv** workspaces and **Hatchling** builds so each stage stays independently installable.

## Architectural Decisions

**Single-node graph.** The graph contains one node (`chatbot`) wired START → chatbot → END. This is the minimal LangGraph structure — it keeps the code trivial while still exercising the full graph lifecycle so later stages can add nodes (tool use, routing) without changing the harness.

**System prompt prepended at runtime.** Rather than storing the system prompt in state, the `chatbot` node checks whether the first message is a `SystemMessage` and prepends one if missing. This avoids duplicating the prompt across turns and keeps state clean for the message-based reducer.

**Streaming-first CLI.** `main.py` uses `graph.stream(..., stream_mode="messages")` so tokens appear as they arrive. Session and user IDs are generated per run and passed through LangGraph's `config.metadata`, which Langfuse picks up automatically — no manual span wiring required.

**Module-level graph export.** `graph.py` compiles the graph at import time (`graph = create_graph()`) so that both the CLI and LangGraph Studio can import the same object without re-compilation.

## How It Works

```mermaid
flowchart LR
    ENV[".env"] -->|loads| Config["config.py<br/>Settings"]
    Config --> GraphMod

    subgraph GraphMod["graph.py"]
        direction TB
        SYS["System Prompt"] --> CB["chatbot node"]
        CB --> LLM["ChatMistralAI<br/>mistral-small-latest"]
    end

    GraphMod --> LF["Langfuse<br/>Traces"]
    GraphMod --> CLI["main.py<br/>CLI Interface"]
    CLI <-->|"streamed I/O"| User((User))

    style ENV fill:#374151,stroke:#9ca3af,stroke-width:2px,color:#e5e7eb
    style Config fill:#374151,stroke:#9ca3af,stroke-width:2px,color:#e5e7eb
    style GraphMod fill:#14532d,stroke:#34d399,stroke-width:2px
    style SYS fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style CB fill:#065f46,stroke:#10b981,stroke-width:3px,color:#d1fae5
    style LLM fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#dbeafe
    style LF fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff
    style CLI fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style User fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
```

## The Graph

```mermaid
stateDiagram-v2
    [*] --> chatbot
    chatbot --> [*]

    state chatbot {
        [*] --> PrependSystemPrompt
        PrependSystemPrompt --> InvokeMistral
        InvokeMistral --> ReturnResponse
        ReturnResponse --> [*]
    }

    classDef active fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    classDef llm fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#dbeafe

    class PrependSystemPrompt active
    class InvokeMistral llm
    class ReturnResponse active
```

## Streaming Conversation Loop

```mermaid
sequenceDiagram
    participant U as User
    participant M as main.py
    participant G as Graph
    participant AI as Mistral AI
    participant T as Langfuse

    loop conversation
        U->>+M: input text
        M->>+G: stream(messages, callbacks=[langfuse])
        G->>+AI: invoke with system + history
        AI-->>-G: AIMessageChunk stream
        G-->>-M: streamed chunks
        M-->>-U: print tokens
        G--)T: trace (async)
    end

    Note over M,T: Session and user IDs passed via metadata
```

## File Map

```mermaid
mindmap
  root((stage_1))
    config.py
      BaseSettings
      .env loader
      API keys
    graph.py
      StateGraph
      chatbot node
      Mistral LLM
      Langfuse init
    main.py
      CLI loop
      Streaming
      Session IDs
```

## Run

```bash
make chat   # CLI
make dev    # LangGraph Studio
```
