# Stage 1: Simple Chatbot

A single-node LangGraph chatbot with Mistral AI and Langfuse observability.

## Architecture

```mermaid
graph LR
    subgraph LangGraph
        START((START)) --> chatbot[chatbot]
        chatbot --> END((END))
    end
```

## Component Overview

```mermaid
graph TB
    subgraph stage_1["stage_1 package"]
        main["main.py<br/>CLI chat loop"]
        graph_mod["graph.py<br/>Graph + LLM setup"]
        config["config.py<br/>Settings from .env"]
    end

    subgraph External Services
        mistral["Mistral AI<br/>mistral-small-latest"]
        langfuse["Langfuse<br/>Observability"]
    end

    main --> graph_mod
    graph_mod --> config
    graph_mod --> mistral
    graph_mod --> langfuse
```

## Data Flow

```mermaid
sequenceDiagram
    actor User
    participant CLI as main.py
    participant Graph as LangGraph
    participant Node as chatbot node
    participant LLM as Mistral AI
    participant LF as Langfuse

    User->>CLI: text input
    CLI->>Graph: stream(messages)
    Graph->>Node: MessagesState
    Note over Node: Prepend system prompt<br/>if not present
    Node->>LLM: invoke(messages)
    LLM-->>Node: AIMessageChunk (streamed)
    Node-->>Graph: {"messages": [response]}
    Graph-->>CLI: stream chunks
    CLI-->>User: printed tokens
    Graph--)LF: trace via callback
```

## Message Handling

```mermaid
graph TD
    A[User types input] --> B{Empty or quit?}
    B -- quit --> C[Flush Langfuse & exit]
    B -- empty --> A
    B -- valid --> D[Append HumanMessage]
    D --> E[Stream graph response]
    E --> F{Stream error?}
    F -- yes --> G[Remove orphaned message]
    G --> A
    F -- no --> H[Append AIMessage to history]
    H --> A
```

## Running

```bash
make chat            # or: uv run --package stage-1 python -m stage_1.main
make dev             # LangGraph Studio
```

## Required Environment Variables

| Variable | Purpose |
|---|---|
| `MISTRAL_API_KEY` | Mistral AI API access |
| `LANGFUSE_SECRET_KEY` | Langfuse auth |
| `LANGFUSE_PUBLIC_KEY` | Langfuse auth |
| `LANGFUSE_BASE_URL` | Langfuse host (default: `https://us.cloud.langfuse.com`) |
