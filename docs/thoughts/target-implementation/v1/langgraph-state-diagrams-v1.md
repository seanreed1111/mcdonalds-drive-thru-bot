# LangGraph Drive-Thru Bot: State Diagrams (v1 — LLM Orchestrator Pattern)

> **Reference Document:** [LangGraph State Design v1](./langgraph-state-design-v1.md)

> **v1 Change from v0:** Replaces the explicit state machine (12+ nodes, intent routing, conditional edges) with an **LLM orchestrator pattern** — a single reasoning node with tool-calling.

> **v1 Scope:** Same as v0 — customers can only **add items** to their order.

> **v1 Interface:** Chatbot (text-only). Same as v0.

---

## Table of Contents

- [v0 vs v1 Graph Comparison](#v0-vs-v1-graph-comparison)
- [v1 System Overview](#v1-system-overview)
- [v1 Graph Architecture](#v1-graph-architecture)
- [State Schema](#state-schema)
- [Tool Interaction Flow](#tool-interaction-flow)
- [Conversation Sequence: Simple Order](#conversation-sequence-simple-order)
- [Conversation Sequence: Multi-Intent](#conversation-sequence-multi-intent)
- [Conversation Sequence: Item Not Found](#conversation-sequence-item-not-found)
- [Orchestrator Decision Flow](#orchestrator-decision-flow)
- [Langfuse Trace Structure](#langfuse-trace-structure)

---

## v0 vs v1 Graph Comparison

Side-by-side showing the structural simplification.

### v0: Explicit State Machine (12+ nodes)

```mermaid
flowchart TD
    START([START]) --> LoadMenu
    LoadMenu --> Greet
    Greet --> AwaitInput

    AwaitInput --> ParseIntent
    ParseIntent --> IntentRouter{"Intent?"}

    IntentRouter -->|add_item| ParseItem
    IntentRouter -->|read_order| ReadOrder
    IntentRouter -->|done| ConfirmFinal
    IntentRouter -->|unclear| Clarify
    IntentRouter -->|greeting| RespondGreeting
    IntentRouter -->|question| AnswerQuestion

    ParseItem --> Validate{"Valid?"}
    Validate -->|Yes| AddItem
    Validate -->|No| RejectItem

    AddItem --> SuccessResponse
    RejectItem --> AwaitInput
    SuccessResponse --> AwaitInput
    ReadOrder --> AwaitInput
    Clarify --> AwaitInput
    RespondGreeting --> AwaitInput
    AnswerQuestion --> AwaitInput

    ConfirmFinal --> ThankCustomer
    ThankCustomer --> END([END])

    style START fill:#22c55e,color:#fff
    style END fill:#ef4444,color:#fff
    style IntentRouter fill:#f59e0b,color:#000
    style Validate fill:#f59e0b,color:#000
```

### v1: LLM Orchestrator (3 nodes)

```mermaid
flowchart TD
    START([START]) --> Orchestrator["Orchestrator<br/>(LLM + Tools)"]

    Orchestrator --> ShouldContinue{"Tool calls?"}

    ShouldContinue -->|"Yes (tool calls)"| Tools["Execute Tools"]
    ShouldContinue -->|"No (direct response)"| END([END])
    ShouldContinue -->|"finalize_order called"| END

    Tools --> Orchestrator

    style START fill:#22c55e,color:#fff
    style END fill:#ef4444,color:#fff
    style Orchestrator fill:#8b5cf6,color:#fff
    style ShouldContinue fill:#f59e0b,color:#000
    style Tools fill:#3b82f6,color:#fff
```

---

## v1 System Overview

High-level view of the orchestrator-based system.

```mermaid
flowchart TB
    subgraph External["External Systems"]
        Input["Text Input<br/>(Chatbot)"]
        Output["Text Output<br/>(Chatbot)"]
        MenuJSON["Menu JSON<br/>(Location-Specific)"]
    end

    subgraph LangGraph["LangGraph Application"]
        subgraph OrchestratorNode["Orchestrator Node"]
            LLM["LLM<br/>(gpt-4o-mini)"]
            SystemPrompt["System Prompt<br/>(menu + order context)"]
        end
        subgraph ToolNode["Tool Node"]
            T1["lookup_menu_item"]
            T2["add_item_to_order"]
            T3["get_current_order"]
            T4["finalize_order"]
        end
        State["DriveThruState<br/>(messages, menu, order)"]
    end

    subgraph Observability["Observability"]
        Langfuse["Langfuse"]
        Checkpointer["Checkpointer"]
    end

    Input -->|"Customer message"| State
    MenuJSON -->|"Load on start"| State
    State -->|"Full context"| LLM
    SystemPrompt -->|"Menu + order"| LLM
    LLM -->|"Tool calls"| ToolNode
    ToolNode -->|"Tool results"| LLM
    LLM -->|"Response"| Output
    State -->|"Checkpoint"| Checkpointer
    LLM -->|"Traces"| Langfuse

    style OrchestratorNode fill:#f3e8ff,stroke:#8b5cf6
    style ToolNode fill:#dbeafe,stroke:#3b82f6
```

---

## v1 Graph Architecture

The complete LangGraph graph with all edges.

```mermaid
flowchart TD
    START([START]) --> Orchestrator

    subgraph OrchestratorLoop["Orchestrator Tool-Calling Loop"]
        Orchestrator["orchestrator_node<br/><i>LLM reasons + calls tools</i>"]
        Tools["tool_node<br/><i>Executes tool calls</i>"]

        Orchestrator --> Check{"should_continue()"}
        Check -->|"has tool_calls<br/>(not finalize)"| Tools
        Tools --> Orchestrator
    end

    Check -->|"no tool_calls<br/>(direct response)"| END([END])
    Check -->|"finalize_order<br/>called"| END

    style START fill:#22c55e,color:#fff
    style END fill:#ef4444,color:#fff
    style Orchestrator fill:#8b5cf6,color:#fff
    style Tools fill:#3b82f6,color:#fff
    style Check fill:#f59e0b,color:#000
    style OrchestratorLoop fill:#faf5ff,stroke:#c4b5fd,stroke-dasharray: 5 5
```

---

## State Schema

Comparison of v0 and v1 state schemas.

```mermaid
classDiagram
    class DriveThruState_v0 {
        +list messages
        +Menu menu
        +Order current_order
        +ParsedIntent parsed_intent
        +ParsedItemRequest parsed_item_request
        +ValidationResult validation_result
        +CustomerResponse response
        +bool is_order_complete
        8 fields
    }

    class DriveThruState_v1 {
        +list messages
        +Menu menu
        +Order current_order
        3 fields
    }

    class Menu {
        +list~Item~ items
    }

    class Order {
        +list~Item~ items
    }

    DriveThruState_v1 --> Menu
    DriveThruState_v1 --> Order
    Menu --> Item
    Order --> Item
```

---

## Tool Interaction Flow

How the orchestrator uses tools to handle customer requests.

```mermaid
flowchart LR
    subgraph Orchestrator["Orchestrator (LLM)"]
        Reason["Reason about<br/>customer message"]
    end

    subgraph Tools["Available Tools"]
        Lookup["lookup_menu_item<br/><i>Verify item exists</i>"]
        Add["add_item_to_order<br/><i>Add validated item</i>"]
        GetOrder["get_current_order<br/><i>Read back order</i>"]
        Finalize["finalize_order<br/><i>Complete order</i>"]
    end

    subgraph Results["Tool Results"]
        Found["✅ found: true<br/>name, price, sizes"]
        NotFound["❌ found: false<br/>suggestions: [...]"]
        Added["✅ added: true<br/>item details"]
        OrderSummary["📋 items, total"]
        Done["🏁 finalized: true"]
    end

    Reason -->|"Customer orders item"| Lookup
    Reason -->|"Item verified"| Add
    Reason -->|"'What did I order?'"| GetOrder
    Reason -->|"'That's all'"| Finalize

    Lookup --> Found
    Lookup --> NotFound
    Add --> Added
    GetOrder --> OrderSummary
    Finalize --> Done

    Found -->|"Proceed to add"| Reason
    NotFound -->|"Suggest alternatives"| Reason
    Added -->|"Confirm to customer"| Reason
    OrderSummary -->|"Read back"| Reason
    Done -->|"Thank + end"| Reason

    style Orchestrator fill:#f3e8ff,stroke:#8b5cf6
    style Lookup fill:#dbeafe,stroke:#3b82f6
    style Add fill:#dbeafe,stroke:#3b82f6
    style GetOrder fill:#dbeafe,stroke:#3b82f6
    style Finalize fill:#dbeafe,stroke:#3b82f6
    style Found fill:#dcfce7,stroke:#22c55e
    style NotFound fill:#fee2e2,stroke:#ef4444
    style Added fill:#dcfce7,stroke:#22c55e
    style Done fill:#dcfce7,stroke:#22c55e
```

---

## Conversation Sequence: Simple Order

A typical single-item order flow.

```mermaid
sequenceDiagram
    participant C as Customer
    participant O as Orchestrator (LLM)
    participant T as Tools

    Note over O: Graph starts, menu loaded into state

    C->>O: "Hi, can I get an Egg McMuffin?"

    O->>O: Reason: greeting + order intent
    O->>T: lookup_menu_item("Egg McMuffin")
    T-->>O: {found: true, name: "Egg McMuffin", price: 4.49}

    O->>T: add_item_to_order("Egg McMuffin", qty=1)
    T-->>O: {added: true}

    O-->>C: "Hey there! Got one Egg McMuffin.<br/>Anything else?"

    C->>O: "No, that's all"

    O->>O: Reason: customer is done
    O->>T: get_current_order()
    T-->>O: {items: [{name: "Egg McMuffin", qty: 1}], total: 4.49}

    O-->>C: "Your order is one Egg McMuffin<br/>for $4.49. Sound good?"

    C->>O: "Yep!"

    O->>T: finalize_order()
    T-->>O: {finalized: true}

    O-->>C: "You're all set! Pull up to the<br/>next window. Have a great day!"

    Note over O: Graph ends (finalize_order called)
```

---

## Conversation Sequence: Multi-Intent

Handling multiple intents in a single customer utterance.

```mermaid
sequenceDiagram
    participant C as Customer
    participant O as Orchestrator (LLM)
    participant T as Tools

    C->>O: "Two hash browns, a large coffee,<br/>and what's your cheapest sandwich?"

    O->>O: Reason: 2 items + 1 question

    par Parallel tool calls
        O->>T: lookup_menu_item("hash brown")
        O->>T: lookup_menu_item("coffee")
    end

    T-->>O: hash brown: {found: true, price: 2.19}
    T-->>O: coffee: {found: true, price: 1.89}

    par Parallel adds
        O->>T: add_item_to_order("Hash Brown", qty=2)
        O->>T: add_item_to_order("Coffee", qty=1, size="large")
    end

    T-->>O: {added: true}
    T-->>O: {added: true}

    O->>O: Reason: answer menu question from context

    O-->>C: "Got it — two hash browns and a large coffee!<br/>Our cheapest sandwich is the Sausage McMuffin<br/>at $3.29. Want to add one?"

    Note over O: All 3 intents handled in ONE turn
```

---

## Conversation Sequence: Item Not Found

Handling an item that isn't on the menu.

```mermaid
sequenceDiagram
    participant C as Customer
    participant O as Orchestrator (LLM)
    participant T as Tools

    C->>O: "Can I get a Big Mac?"

    O->>T: lookup_menu_item("Big Mac")
    T-->>O: {found: false, suggestions: ["Big Breakfast", "McGriddle"]}

    O->>O: Reason: item not on breakfast menu,<br/>suggest alternatives from tool result

    O-->>C: "Sorry, we don't have the Big Mac<br/>on our breakfast menu! How about<br/>a Big Breakfast or a McGriddle?"

    Note over O: No reject node needed —<br/>orchestrator handles naturally
```

---

## Orchestrator Decision Flow

Internal logic of how the orchestrator decides what to do.

```mermaid
flowchart TD
    Input["Customer Message"] --> Orchestrator

    Orchestrator --> Analyze["LLM analyzes message<br/>in context of:<br/>• conversation history<br/>• current menu<br/>• current order"]

    Analyze --> WhatToDo{"What does the<br/>customer want?"}

    WhatToDo -->|"Order an item"| LookupFirst["Call lookup_menu_item"]
    WhatToDo -->|"Ask about menu"| AnswerFromContext["Answer from<br/>menu in system prompt"]
    WhatToDo -->|"Check their order"| CallGetOrder["Call get_current_order"]
    WhatToDo -->|"Done ordering"| ReadBack["Read back order,<br/>then call finalize_order"]
    WhatToDo -->|"Greeting/chitchat"| Respond["Respond directly<br/>(no tools needed)"]
    WhatToDo -->|"Multiple things"| HandleAll["Handle all via<br/>multiple tool calls"]

    LookupFirst --> Found{"Item found?"}
    Found -->|Yes| CallAdd["Call add_item_to_order"]
    Found -->|No| SuggestAlt["Suggest alternatives<br/>from tool result"]

    CallAdd --> ConfirmToCustomer["Confirm item added"]
    SuggestAlt --> RespondToCustomer["Respond with suggestions"]
    AnswerFromContext --> RespondToCustomer
    CallGetOrder --> RespondToCustomer
    ReadBack --> EndGraph["Graph ends"]
    Respond --> RespondToCustomer
    HandleAll --> RespondToCustomer

    ConfirmToCustomer --> AskAnythingElse["'Anything else?'"]
    RespondToCustomer --> WaitForNext["Wait for next message"]

    style Orchestrator fill:#8b5cf6,color:#fff
    style WhatToDo fill:#f59e0b,color:#000
    style Found fill:#f59e0b,color:#000
    style EndGraph fill:#ef4444,color:#fff

    style LookupFirst fill:#dbeafe,stroke:#3b82f6
    style CallAdd fill:#dbeafe,stroke:#3b82f6
    style CallGetOrder fill:#dbeafe,stroke:#3b82f6
```

---

## Langfuse Trace Structure

What traces look like in the orchestrator pattern vs v0.

```mermaid
flowchart TB
    subgraph v0_trace["v0 Trace (many spans)"]
        v0_root["Root Span"]
        v0_parse["parse_intent_node"]
        v0_item["parse_item_node"]
        v0_validate["validate_node"]
        v0_add["add_item_node"]
        v0_response["response_node"]

        v0_root --> v0_parse
        v0_root --> v0_item
        v0_root --> v0_validate
        v0_root --> v0_add
        v0_root --> v0_response
    end

    subgraph v1_trace["v1 Trace (cleaner)"]
        v1_root["Root Span"]
        v1_orch1["orchestrator (turn 1)"]
        v1_lookup["tool: lookup_menu_item"]
        v1_add_tool["tool: add_item_to_order"]
        v1_orch2["orchestrator (turn 2)"]

        v1_root --> v1_orch1
        v1_orch1 --> v1_lookup
        v1_orch1 --> v1_add_tool
        v1_root --> v1_orch2
    end

    style v0_trace fill:#fee2e2,stroke:#ef4444
    style v1_trace fill:#dcfce7,stroke:#22c55e
    style v1_orch1 fill:#8b5cf6,color:#fff
    style v1_orch2 fill:#8b5cf6,color:#fff
    style v1_lookup fill:#3b82f6,color:#fff
    style v1_add_tool fill:#3b82f6,color:#fff
```

---

## Complete State Machine

The v1 state machine is intentionally minimal.

```mermaid
stateDiagram-v2
    [*] --> Ready: Graph initialized with menu

    state Ready {
        [*] --> WaitingForInput
    }

    WaitingForInput --> Orchestrating: Customer message received

    state Orchestrating {
        [*] --> LLMReasoning
        LLMReasoning --> ToolCalling: Tool calls needed
        ToolCalling --> ToolExecuting: Execute tools
        ToolExecuting --> LLMReasoning: Results returned
        LLMReasoning --> Responding: No more tool calls
        LLMReasoning --> Finalizing: finalize_order called
    }

    Responding --> WaitingForInput: Response sent to customer
    Finalizing --> [*]: Order complete
```

---

## Legend

| Symbol | Meaning |
|--------|---------|
| Purple | Orchestrator (LLM reasoning) |
| Blue | Tools (deterministic functions) |
| Yellow/Orange | Decision points |
| Green | Success / v1 improvements |
| Red | End states / v0 complexity |
