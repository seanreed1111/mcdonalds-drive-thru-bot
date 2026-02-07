# Stage 1: Simple Chatbot

## The Graph

```mermaid
graph LR
    START((START)) -->|MessagesState| chatbot --> END((END))
```

One node. Messages in, response out.

## Stack

```mermaid
block-beta
    columns 3
    LangGraph:3
    Mistral["Mistral AI"] Langfuse["Langfuse"] PydanticSettings["Pydantic Settings"]
    LLM["mistral-small-latest"] Traces[".env config"]  EnvFile[".env file"]
```

## End-to-End Flow

```mermaid
flowchart TB
    subgraph Init["Startup"]
        direction LR
        env[".env"] --> settings["Settings<br/>(pydantic-settings)"]
        settings --> lf_init["Langfuse singleton"]
        settings --> llm_init["ChatMistralAI"]
    end

    subgraph Loop["Chat Loop"]
        direction TB
        input["User input"] --> check{quit?}
        check -- yes --> flush["Flush Langfuse"]
        check -- no --> append["Append HumanMessage"]
        append --> stream["graph.stream()"]
        stream --> print["Print AI chunks"]
        print --> save["Append AIMessage"]
        save --> input

        stream -. "error" .-> rollback["Pop failed message"]
        rollback --> input
    end

    subgraph Trace["Observability"]
        direction LR
        cb["CallbackHandler"] --> session["session_id"]
        cb --> user["user_id"]
    end

    Init --> Loop
    Loop -.-> Trace
```

## Modules

```mermaid
classDiagram
    class config {
        +Settings : BaseSettings
        +get_settings() Settings
    }

    class graph {
        +SYSTEM_PROMPT : str
        +chatbot(MessagesState) dict
        +create_graph() CompiledStateGraph
        +graph : CompiledStateGraph
    }

    class main {
        +run_chat() None
    }

    main --> graph : imports graph, handlers
    graph --> config : imports get_settings

    class MistralAI {
        <<external>>
        mistral-small-latest
    }

    class Langfuse {
        <<external>>
        tracing + callbacks
    }

    graph --> MistralAI
    graph --> Langfuse
```

## Run

```bash
make chat   # CLI
make dev    # LangGraph Studio
```
