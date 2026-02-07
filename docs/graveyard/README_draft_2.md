# Stage 1: Simple Chatbot

Single-node LangGraph chatbot. Mistral AI for generation, Langfuse for tracing.

## How It Works

```mermaid
graph LR
    ENV[".env"] -->|loads| Config["config.py<br/>Settings"]
    Config --> Graph["graph.py"]

    subgraph Graph["graph.py"]
        direction TB
        SYS["System Prompt"] --> CB["chatbot node"]
        CB --> LLM["ChatMistralAI<br/>mistral-small-latest"]
    end

    Graph --> LF["Langfuse<br/>Traces"]
    Graph --> CLI["main.py<br/>CLI Interface"]
    CLI <-->|"streamed I/O"| User((User))
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
        U->>M: input text
        M->>G: stream(messages, callbacks=[langfuse])
        G->>AI: invoke with system + history
        AI-->>M: token stream
        M-->>U: print tokens
        G--)T: trace (async)
    end
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
