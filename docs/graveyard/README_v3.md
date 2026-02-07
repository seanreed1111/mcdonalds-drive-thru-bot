# Stage 2: Two-Bot Interview

Multi-node LangGraph graph where two AI personas interview each other. Mistral AI for generation, Langfuse for prompt management and tracing.

## Table of Contents

- [Introduction](#introduction)
- [Tech Stack](#tech-stack)
- [Architectural Decisions](#architectural-decisions)
- [System Overview](#system-overview)
- [The Graph](#the-graph)
- [Conversation Example](#conversation-example)
- [Persona System](#persona-system)
- [Prompt Pipeline](#prompt-pipeline)
- [State Schema](#state-schema)
- [Message Rewriting](#message-rewriting)
- [File Map](#file-map)
- [Run](#run)

## Introduction

Stage 2 evolves the single-bot chatbot into a two-bot conversation system. Two AI personas — an initiator and a responder — take turns speaking on a user-provided topic. Persona definitions are stored in Langfuse as managed chat prompts, so behavior can be tweaked without code changes. The graph alternates between the two bots until a configurable turn limit is reached, producing an interview-style transcript streamed to the CLI.

## Tech Stack

The graph runs on **LangGraph** (v1.0+) with two nodes wired in a conditional loop. The LLM is **Mistral AI** (`mistral-small-latest`) via `langchain-mistralai`. Prompt templates are managed in **Langfuse** (v3) as versioned chat prompts — fetched at runtime, compiled with persona variables, and linked back to traces for full observability. Persona presets are defined in Python as a `StrEnum` + dictionary so new pairings can be added without touching graph logic. Configuration uses **Pydantic Settings**, and the project is packaged with **uv** workspaces and **Hatchling** builds.

## Architectural Decisions

**Two-node conditional loop.** The graph has two nodes (`initiator`, `responder`) connected by conditional edges that check turn counts. This is the minimal structure for a multi-turn two-agent conversation — each node is symmetric and built by the same factory function.

**Langfuse prompt management.** System prompts live in Langfuse as `interview/initiator` and `interview/responder` chat prompts, not in source code. Each invocation fetches the latest prompt version, compiles it with persona variables, and attaches `langfuse_prompt` metadata so traces link back to the exact prompt version used.

**Node factory pattern.** `_build_node_fn(role, prompt_name)` returns a closure for either role. This eliminates duplication — the initiator and responder nodes differ only in which persona they load and which turn counter they increment.

**Message rewriting for Mistral.** Mistral requires strict user/assistant alternation. Since both bots produce `AIMessage`s, each node rewrites the other bot's messages to `HumanMessage`s before invoking the LLM. This keeps the conversation history valid from each bot's perspective.

## System Overview

```mermaid
flowchart LR
    ENV[".env"] -->|loads| Config["config.py<br/>Settings"]
    Config --> GraphMod

    subgraph GraphMod["graph.py"]
        direction TB
        LFP["Langfuse Prompts<br/>interview/initiator<br/>interview/responder"] --> INIT["initiator node"]
        LFP --> RESP["responder node"]
        INIT --> LLM["ChatMistralAI<br/>mistral-small-latest"]
        RESP --> LLM
    end

    PER["personas.py<br/>Preset Definitions"] --> GraphMod
    GraphMod --> LF["Langfuse<br/>Traces"]
    GraphMod --> CLI["main.py<br/>CLI Interface"]
    CLI <-->|"streamed updates"| User((User))

    style ENV fill:#374151,stroke:#9ca3af,stroke-width:2px,color:#e5e7eb
    style Config fill:#374151,stroke:#9ca3af,stroke-width:2px,color:#e5e7eb
    style GraphMod fill:#14532d,stroke:#34d399,stroke-width:2px
    style LFP fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff
    style INIT fill:#065f46,stroke:#10b981,stroke-width:3px,color:#d1fae5
    style RESP fill:#065f46,stroke:#10b981,stroke-width:3px,color:#d1fae5
    style LLM fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#dbeafe
    style PER fill:#374151,stroke:#9ca3af,stroke-width:2px,color:#e5e7eb
    style LF fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff
    style CLI fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style User fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
```

## The Graph

```mermaid
stateDiagram-v2
    [*] --> initiator
    initiator --> responder : responder_turns < max
    initiator --> [*] : responder_turns >= max
    responder --> initiator : initiator_turns < max
    responder --> [*] : initiator_turns >= max

    state initiator {
        [*] --> FetchPrompt_I
        FetchPrompt_I --> CompilePersona_I
        CompilePersona_I --> RewriteHistory_I
        RewriteHistory_I --> InvokeMistral_I
        InvokeMistral_I --> ReturnResponse_I
        ReturnResponse_I --> [*]
    }

    state responder {
        [*] --> FetchPrompt_R
        FetchPrompt_R --> CompilePersona_R
        CompilePersona_R --> RewriteHistory_R
        RewriteHistory_R --> InvokeMistral_R
        InvokeMistral_R --> ReturnResponse_R
        ReturnResponse_R --> [*]
    }

    classDef active fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    classDef llm fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#dbeafe
    classDef prompt fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff

    class FetchPrompt_I,FetchPrompt_R prompt
    class CompilePersona_I,CompilePersona_R active
    class RewriteHistory_I,RewriteHistory_R active
    class InvokeMistral_I,InvokeMistral_R llm
    class ReturnResponse_I,ReturnResponse_R active
```

## Conversation Example

A 3-turn interview with the `reporter-politician` preset, showing how the graph alternates between nodes.

```mermaid
sequenceDiagram
    participant U as User
    participant M as main.py
    participant G as Graph
    participant LF as Langfuse Prompts
    participant AI as Mistral AI
    participant T as Langfuse Traces

    U->>+M: enter topic
    M->>+G: stream(topic + preset, callbacks=[langfuse])

    loop max_turns per bot
        G->>+LF: get_prompt("interview/initiator")
        LF-->>-G: compiled system prompt
        G->>+AI: initiator invoke
        AI-->>-G: AIMessage (initiator)
        G-->>M: update: initiator spoke
        M-->>U: print [Initiator]: ...

        G->>+LF: get_prompt("interview/responder")
        LF-->>-G: compiled system prompt
        G->>+AI: responder invoke
        AI-->>-G: AIMessage (responder)
        G-->>M: update: responder spoke
        M-->>U: print [Responder]: ...
    end

    G-->>-M: stream complete
    M-->>-U: "Interview complete."
    G--)T: traces (async)

    Note over M,T: Session ID passed via metadata
```

## Persona System

Four preset pairings ship out of the box. Each preset defines an initiator (drives the conversation) and responder (reacts).

```mermaid
flowchart TB
    subgraph Presets["Persona Presets (personas.py)"]
        direction TB
        RP["reporter-politician"]
        RB["reporter-boxer"]
        DP["donor-politician"]
        BP["bartender-patron"]
    end

    subgraph Roles["Each Preset Contains"]
        direction LR
        I["Initiator<br/>persona_name<br/>persona_description<br/>persona_behavior"]
        R["Responder<br/>persona_name<br/>persona_description<br/>persona_behavior"]
    end

    RP --> Roles
    RB --> Roles
    DP --> Roles
    BP --> Roles

    I -->|compiled into| LFI["Langfuse Prompt<br/>interview/initiator"]
    R -->|compiled into| LFR["Langfuse Prompt<br/>interview/responder"]

    style Presets fill:#374151,stroke:#9ca3af,stroke-width:2px
    style Roles fill:#14532d,stroke:#34d399,stroke-width:2px
    style RP fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style RB fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style DP fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style BP fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style I fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style R fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style LFI fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff
    style LFR fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff
```

## Prompt Pipeline

Each node invocation follows this pipeline to go from a Langfuse prompt template to a Mistral LLM call.

```mermaid
flowchart TD
    A["1. Fetch Prompt<br/>langfuse.get_prompt(name)"] --> B["2. Compile with Persona<br/>lf_prompt.compile(<br/>  persona_name,<br/>  persona_description,<br/>  persona_behavior,<br/>  other_persona<br/>)"]
    B --> C["3. Extract System Content<br/>compiled_messages[0]['content']"]
    C --> D["4. Rewrite History<br/>Other bot's AIMessages<br/>become HumanMessages"]
    D --> E["5. Build ChatPromptTemplate<br/>system + MessagesPlaceholder<br/>+ langfuse_prompt metadata"]
    E --> F["6. Chain & Invoke<br/>prompt | ChatMistralAI<br/>→ AIMessage response"]
    F --> G["7. Return State Update<br/>messages: [response]<br/>role_turns: +1"]

    style A fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff
    style B fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff
    style C fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style D fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style E fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style F fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#dbeafe
    style G fill:#374151,stroke:#9ca3af,stroke-width:2px,color:#e5e7eb
```

## State Schema

```mermaid
classDiagram
    class MessagesState {
        messages: list[BaseMessage]
    }

    class InputState {
        max_turns: int
        preset: Preset
        initiator_name: str
        responder_name: str
    }

    class InterviewState {
        initiator_turns: Annotated[int, add]
        responder_turns: Annotated[int, add]
    }

    MessagesState <|-- InputState : extends
    InputState <|-- InterviewState : extends

    class Preset {
        <<StrEnum>>
        REPORTER_POLITICIAN
        REPORTER_BOXER
        DONOR_POLITICIAN
        BARTENDER_PATRON
    }

    InputState --> Preset : uses

    style MessagesState fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#dbeafe
    style InputState fill:#065f46,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style InterviewState fill:#065f46,stroke:#10b981,stroke-width:3px,color:#d1fae5
    style Preset fill:#374151,stroke:#9ca3af,stroke-width:2px,color:#e5e7eb
```

## Message Rewriting

Mistral requires strict user/assistant alternation. Both bots produce `AIMessage`s, so each node must rewrite the other bot's messages before invoking the LLM.

```mermaid
flowchart LR
    subgraph SharedState["Shared Message History"]
        direction TB
        H1["HumanMessage<br/>'Interview topic: ...'"]
        A1["AIMessage<br/>name='Reporter'<br/>'First question...'"]
        A2["AIMessage<br/>name='Politician'<br/>'Well, let me say...'"]
        A3["AIMessage<br/>name='Reporter'<br/>'But the numbers show...'"]
    end

    subgraph InitView["Initiator's View"]
        direction TB
        IH1["HumanMessage<br/>'Interview topic: ...'"]
        IH2["HumanMessage<br/>'First question...'"]
        IH3["HumanMessage<br/>'Well, let me say...'"]
        IH4["HumanMessage<br/>'But the numbers show...'"]
    end

    subgraph RespView["Responder's View"]
        direction TB
        RH1["HumanMessage<br/>'Interview topic: ...'"]
        RH2["HumanMessage<br/>'First question...'"]
        RH3["HumanMessage<br/>'Well, let me say...'"]
        RH4["HumanMessage<br/>'But the numbers show...'"]
    end

    SharedState -->|"rewrite for<br/>initiator node"| InitView
    SharedState -->|"rewrite for<br/>responder node"| RespView

    style SharedState fill:#374151,stroke:#9ca3af,stroke-width:2px
    style InitView fill:#14532d,stroke:#34d399,stroke-width:2px
    style RespView fill:#14532d,stroke:#34d399,stroke-width:2px
    style H1 fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style A1 fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#dbeafe
    style A2 fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#dbeafe
    style A3 fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#dbeafe
    style IH1 fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style IH2 fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style IH3 fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style IH4 fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style RH1 fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style RH2 fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style RH3 fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    style RH4 fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
```

All `AIMessage`s are converted to `HumanMessage`s from each bot's perspective, so Mistral always sees a flat sequence of `HumanMessage`s after the system prompt. This satisfies the alternation requirement since the bot only ever produces one `AIMessage` (its own response) per turn.

## File Map

```mermaid
mindmap
  root((stage_2))
    config.py
      BaseSettings
      .env loader
      API keys
    graph.py
      StateGraph
      initiator node
      responder node
      Node factory
      Conditional edges
      Langfuse prompts
    main.py
      CLI + argparse
      Node-by-node streaming
      Session IDs
    personas.py
      Preset enum
      4 persona pairings
      Persona variables
```

## Run

```bash
make chat SCOPE=2                              # CLI (default preset)
make chat SCOPE=2 -- --preset bartender-patron  # CLI with preset
make dev SCOPE=2                                # LangGraph Studio
```
