# LangGraph Drive-Thru Bot: State Diagrams

> **Reference Document:** [LangGraph State Design v0](./langgraph-state-design-v0.md)

> **v0 Scope:** Customers can only **add items** to their order. Remove and modify functionality will be added in future versions.

> **v0 Interface:** Chatbot (text-only). No Speech-to-Text (STT) or Text-to-Speech (TTS) in v0. The design is structured to easily integrate STT/TTS in future versions.

This document provides detailed Mermaid diagrams visualizing the state design for the McDonald's breakfast drive-thru ordering system.

---

## Table of Contents

- [System Overview](#system-overview)
- [State Schema](#state-schema)
- [Pydantic Model Relationships](#pydantic-model-relationships)
- [Graph Architectures](#graph-architectures)
  - [Approach 1: Simple Linear with Conditional Loop (Deprecated)](#approach-1-simple-linear-with-conditional-loop-deprecated)
  - [Approach 2: Explicit State Machine (v0 Implementation)](#approach-2-explicit-state-machine-v0-implementation)
  - [Approach 3: Subgraph Pattern (Future Consideration)](#approach-3-subgraph-pattern-future-consideration)
- [Intent Routing Flow](#intent-routing-flow)
- [Validation Flow](#validation-flow)
- [Node Execution Sequence](#node-execution-sequence)
- [Error Recovery Flow](#error-recovery-flow)
- [Langfuse Integration](#langfuse-integration)

---

## System Overview

High-level view of the drive-thru ordering system components and their interactions. In v0, input/output is via chatbot (text). STT/TTS integration is shown as future capability.

```mermaid
flowchart TB
    subgraph External["External Systems (v0: Chatbot)"]
        Input["Text Input<br/>(Chatbot Interface)"]
        Output["Text Output<br/>(Chatbot Response)"]
        Menu["Menu JSON<br/>(Location-Specific)"]
    end

    subgraph Future["Future: Voice Integration"]
        ASR["ASR<br/>(Speech-to-Text)"]
        TTS["TTS<br/>(Text-to-Speech)"]
    end

    subgraph LangGraph["LangGraph Application"]
        State["DriveThruState"]
        Nodes["Graph Nodes"]
        Router["Intent Router"]
        LLM["LLM<br/>(gpt-4o-mini)"]
    end

    subgraph Observability["Observability"]
        Langfuse["Langfuse<br/>(Tracing)"]
        Checkpointer["State Checkpointer<br/>(SQLite/Memory)"]
    end

    subgraph DataModels["Pydantic Models"]
        Order["Order"]
        Item["Item"]
        Modifier["Modifier"]
    end

    Input -->|"Customer Message"| Nodes
    ASR -.->|"Future: Voice Input"| Nodes
    Menu -->|"Load on Start"| State
    Nodes -->|"Update"| State
    State -->|"Route"| Router
    Router -->|"Next Node"| Nodes
    Nodes -->|"Structured Output"| LLM
    LLM -->|"Parsed Response"| Nodes
    Nodes -->|"Build Order"| DataModels
    Nodes -->|"Response Message"| Output
    Nodes -.->|"Future: Voice Output"| TTS
    Nodes -->|"Trace Events"| Langfuse
    State -->|"Checkpoint"| Checkpointer

    style Future fill:#f5f5f5,stroke:#999,stroke-dasharray: 5 5
    style ASR fill:#e0e0e0,color:#666
    style TTS fill:#e0e0e0,color:#666
```

---

## State Schema

The `DriveThruState` TypedDict structure and its components.

```mermaid
classDiagram
    class DriveThruState {
        +list messages
        +Menu menu
        +Order current_order
        +ParsedIntent parsed_intent
        +ParsedItemRequest parsed_item_request
        +ValidationResult validation_result
        +CustomerResponse response
        +bool is_order_complete
    }

    class Menu {
        +str location_id
        +list~Item~ items
        +get_item_by_name()
        +get_items_by_category()
    }

    class Order {
        +str order_id
        +list~Item~ items
        +datetime created_at
        +add_item()
        +total_price()
    }

    class Item {
        +str item_id
        +str name
        +Size size
        +int quantity
        +float price
        +list~Modifier~ modifiers
        +list~Modifier~ available_modifiers
    }

    class Modifier {
        +str modifier_id
        +str name
        +float price_adjustment
    }

    DriveThruState --> Menu : contains
    DriveThruState --> Order : contains
    Order --> Item : contains many
    Item --> Modifier : has many
    Menu --> Item : contains many
```

---

## Pydantic Model Relationships

Structured output models used for LLM parsing and validation.

```mermaid
classDiagram
    class ParsedIntent {
        +CustomerIntent intent
        +float confidence
        +str reasoning
    }

    class CustomerIntent {
        <<enumeration>>
        ADD_ITEM
        READ_ORDER
        DONE
        UNCLEAR
        GREETING
        QUESTION
    }

    class ParsedItemRequest {
        +str item_name
        +int quantity
        +Size size
        +list~str~ modifiers
        +str raw_utterance
    }

    class Size {
        <<enumeration>>
        SNACK
        SMALL
        MEDIUM
        LARGE
    }

    class ValidationResult {
        +bool is_valid
        +str matched_item_id
        +str matched_item_name
        +str match_type
        +float match_score
        +str failure_reason
        +list~str~ suggestions
    }

    class CustomerResponse {
        +str message
        +str tone
        +bool should_prompt_next
        +str internal_notes
    }

    class ParseResult {
        +ParsedIntent intent
        +ParsedItemRequest item_request
    }

    ParsedIntent --> CustomerIntent : uses
    ParsedItemRequest --> Size : uses
    ParseResult --> ParsedIntent : contains
    ParseResult --> ParsedItemRequest : contains
```

---

## Graph Architectures

### Approach 1: Simple Linear with Conditional Loop (Deprecated)

> **⚠️ DEPRECATED:** This approach will not be used. See [Approach 2](#approach-2-explicit-state-machine-v0-implementation) for the v0 implementation.

Minimal graph with single order-handling node.

```mermaid
flowchart TD
    START([START]) --> LoadMenu["Load Menu"]
    LoadMenu --> Greet["Greet Customer"]
    Greet --> TakeOrder["Take Order Node"]

    TakeOrder --> CheckComplete{"Order<br/>Complete?"}

    CheckComplete -->|No| TakeOrder
    CheckComplete -->|Yes| Confirm["Confirm Order"]

    Confirm --> END([END])

    style START fill:#22c55e,color:#fff
    style END fill:#ef4444,color:#fff
    style TakeOrder fill:#3b82f6,color:#fff
    style CheckComplete fill:#f59e0b,color:#000
```

**Characteristics:**
- All logic bundled in `Take Order Node`
- Simple state transitions
- ~~Best for MVP/prototyping~~ **Not used—too limited for production requirements**

---

### Approach 2: Explicit State Machine (v0 Implementation)

> **✅ v0 IMPLEMENTATION:** This is the architecture used for v0.

Discrete, testable nodes with explicit transitions.

```mermaid
flowchart TD
    START([START]) --> LoadMenu["Load Menu"]
    LoadMenu --> Greet["Greet Customer"]
    Greet --> AwaitInput["Await Input"]

    AwaitInput --> ParseIntent["Parse Intent"]

    ParseIntent --> IntentRouter{"Intent Type"}

    IntentRouter -->|add_item| ParseItem["Parse Item"]
    IntentRouter -->|read_order| ReadOrder["Read Current Order"]
    IntentRouter -->|done| ConfirmFinal["Confirm Final Order"]
    IntentRouter -->|unclear| Clarify["Clarify Request"]
    IntentRouter -->|greeting| RespondGreeting["Respond to Greeting"]
    IntentRouter -->|question| AnswerQuestion["Answer Question"]

    ParseItem --> Validate{"Valid<br/>Item?"}

    Validate -->|Yes| AddItem["Add Item to Order"]
    Validate -->|No| RejectItem["Reject Item<br/>Suggest Alternatives"]

    AddItem --> SuccessResponse["Success Response"]
    RejectItem --> AwaitInput

    SuccessResponse --> AwaitInput
    ReadOrder --> AwaitInput
    Clarify --> AwaitInput
    RespondGreeting --> AwaitInput
    AnswerQuestion --> AwaitInput

    ConfirmFinal --> ThankCustomer["Thank Customer"]
    ThankCustomer --> END([END])

    style START fill:#22c55e,color:#fff
    style END fill:#ef4444,color:#fff
    style IntentRouter fill:#f59e0b,color:#000
    style Validate fill:#f59e0b,color:#000
    style ParseIntent fill:#8b5cf6,color:#fff
    style AddItem fill:#3b82f6,color:#fff
    style AwaitInput fill:#06b6d4,color:#fff
```

---

### Approach 3: Subgraph Pattern (Future Consideration)

> **📋 FUTURE:** This approach may be considered for future versions if validation complexity increases.

Main graph delegates validation to a dedicated subgraph.

#### Main Graph

```mermaid
flowchart TD
    START([START]) --> LoadMenu["Load Menu"]
    LoadMenu --> Greet["Greet Customer"]
    Greet --> OrderLoop["Order Loop"]

    OrderLoop --> Parse["Parse Utterance"]
    Parse --> ValidationSub[["Validation<br/>Subgraph"]]

    ValidationSub --> Result{"Result"}

    Result -->|Success| AddToOrder["Add to Order"]
    Result -->|Failure| SuggestAlt["Suggest<br/>Alternatives"]

    AddToOrder --> CheckDone{"Done?"}
    SuggestAlt --> OrderLoop

    CheckDone -->|No| OrderLoop
    CheckDone -->|Yes| Confirm["Confirm Order"]

    Confirm --> END([END])

    style START fill:#22c55e,color:#fff
    style END fill:#ef4444,color:#fff
    style ValidationSub fill:#a855f7,color:#fff
    style Result fill:#f59e0b,color:#000
    style CheckDone fill:#f59e0b,color:#000
```

#### Validation Subgraph

```mermaid
flowchart TD
    SubStart([Subgraph Entry]) --> CheckExact["Check Menu<br/>Exact Match"]

    CheckExact --> ExactMatch{"Exact<br/>Match?"}

    ExactMatch -->|Yes| ReturnExact["Return Exact Item"]
    ExactMatch -->|No| FuzzyMatch["Fuzzy Match"]

    FuzzyMatch --> FuzzyFound{"Match<br/>Found?"}

    FuzzyFound -->|No| NotFound["Item Not Found"]
    FuzzyFound -->|Yes| ConfirmMatch["Confirm with<br/>Customer"]

    ConfirmMatch --> CustomerConfirms{"Customer<br/>Confirms?"}

    CustomerConfirms -->|Yes| ReturnMatched["Return Matched Item"]
    CustomerConfirms -->|No| NotFound

    ReturnExact --> SubEnd([Subgraph Exit])
    ReturnMatched --> SubEnd
    NotFound --> SubEnd

    style SubStart fill:#a855f7,color:#fff
    style SubEnd fill:#a855f7,color:#fff
    style ExactMatch fill:#f59e0b,color:#000
    style FuzzyFound fill:#f59e0b,color:#000
    style CustomerConfirms fill:#f59e0b,color:#000
```

---

## Intent Routing Flow

Detailed view of how customer intents are classified and routed.

```mermaid
flowchart LR
    subgraph Input
        Utterance["Customer<br/>Utterance"]
    end

    subgraph Classification["Intent Classification (LLM)"]
        IntentParser["intent_parser<br/>.with_structured_output()"]
    end

    subgraph ParsedIntent["ParsedIntent Model"]
        Intent["intent: CustomerIntent"]
        Confidence["confidence: 0.0-1.0"]
        Reasoning["reasoning: str"]
    end

    subgraph ConfidenceCheck["Confidence Gate"]
        ConfCheck{"confidence<br/>≥ 0.7?"}
    end

    subgraph Routing["Route by Intent"]
        AddRoute["add_item → parse_item"]
        ReadRoute["read_order → read_order"]
        DoneRoute["done → confirm_order"]
        UnclearRoute["unclear → clarify"]
        GreetRoute["greeting → greet"]
        QuestionRoute["question → answer_question"]
    end

    Utterance --> IntentParser
    IntentParser --> Intent
    IntentParser --> Confidence
    IntentParser --> Reasoning

    Confidence --> ConfCheck

    ConfCheck -->|No| UnclearRoute
    ConfCheck -->|Yes| Intent

    Intent -->|ADD_ITEM| AddRoute
    Intent -->|READ_ORDER| ReadRoute
    Intent -->|DONE| DoneRoute
    Intent -->|UNCLEAR| UnclearRoute
    Intent -->|GREETING| GreetRoute
    Intent -->|QUESTION| QuestionRoute

    style IntentParser fill:#8b5cf6,color:#fff
    style ConfCheck fill:#f59e0b,color:#000
```

---

## Validation Flow

How parsed items are validated against the menu.

```mermaid
flowchart TD
    subgraph Input["Parsed Input"]
        ParsedItem["ParsedItemRequest"]
        ItemName["item_name"]
        Quantity["quantity"]
        Modifiers["modifiers[]"]
    end

    subgraph MenuValidation["Menu Validation"]
        CheckItem{"Item exists<br/>in Menu?"}
        CheckQty{"quantity ≥ 1?"}
        CheckMods{"All modifiers<br/>in available_modifiers?"}
    end

    subgraph Results["ValidationResult"]
        Valid["is_valid: true<br/>matched_item_id: '...'<br/>matched_item_name: '...'<br/>match_score: 1.0"]
        Invalid["is_valid: false<br/>failure_reason: '...'<br/>suggestions: [...]"]
    end

    ParsedItem --> ItemName
    ParsedItem --> Quantity
    ParsedItem --> Modifiers

    ItemName --> CheckItem

    CheckItem -->|No| Invalid
    CheckItem -->|Yes| CheckQty

    CheckQty -->|No| Invalid
    CheckQty -->|Yes| CheckMods

    CheckMods -->|No| Invalid
    CheckMods -->|Yes| Valid

    style CheckItem fill:#f59e0b,color:#000
    style CheckQty fill:#f59e0b,color:#000
    style CheckMods fill:#f59e0b,color:#000
    style Valid fill:#22c55e,color:#fff
    style Invalid fill:#ef4444,color:#fff
```

---

## Node Execution Sequence

Sequence diagram showing typical order flow (v0: text-based chatbot).

```mermaid
sequenceDiagram
    participant C as Customer
    participant Chat as Chatbot Interface
    participant G as Graph
    participant PI as parse_intent_node
    participant PItem as parse_item_node
    participant V as validate_node
    participant R as response_node

    Note over G: Graph initialized with Menu

    C->>Chat: "I'd like an Egg McMuffin"
    Chat->>G: HumanMessage(content="...")

    G->>PI: invoke(state)
    PI->>PI: LLM: ParsedIntent
    PI-->>G: {parsed_intent: ADD_ITEM}

    G->>PItem: invoke(state)
    PItem->>PItem: LLM: ParsedItemRequest
    PItem-->>G: {parsed_item_request: ...}

    G->>V: invoke(state)
    V->>V: Menu.get_item_by_name()
    V-->>G: {validation_result: is_valid=True}

    G->>G: Add Item to Order

    G->>R: invoke(state)
    R->>R: LLM: CustomerResponse
    R-->>G: {response: "Got it! ..."}

    G->>Chat: "Got it! One Egg McMuffin. Anything else?"
    Chat->>C: Display Text Response
```

> **Future (STT/TTS):** Replace `Chatbot Interface` with ASR (Speech-to-Text) for input and TTS (Text-to-Speech) for output. The graph nodes remain unchanged—only the input/output interfaces change.

---

## Error Recovery Flow

How the system handles errors and edge cases.

```mermaid
flowchart TD
    subgraph Errors["Error Types"]
        ItemNotFound["Item Not Found"]
        InvalidQty["Invalid Quantity"]
        BadModifier["Unknown Modifier"]
        LowConfidence["Low Confidence<br/>(< 0.7)"]
        LLMError["LLM API Error"]
    end

    subgraph Recovery["Recovery Actions"]
        Suggest["Suggest Alternatives"]
        AskAgain["Ask for Clarification"]
        DefaultQty["Default to qty=1"]
        IgnoreMod["Ignore & Inform"]
        Retry["Retry with Backoff"]
    end

    subgraph NextState["Next State"]
        AwaitInput["await_input"]
    end

    ItemNotFound --> Suggest
    InvalidQty --> DefaultQty
    BadModifier --> IgnoreMod
    LowConfidence --> AskAgain
    LLMError --> Retry

    Suggest --> AwaitInput
    AskAgain --> AwaitInput
    DefaultQty --> AwaitInput
    IgnoreMod --> AwaitInput
    Retry -->|"Max retries exceeded"| AskAgain
    Retry -->|"Success"| AwaitInput

    style ItemNotFound fill:#ef4444,color:#fff
    style InvalidQty fill:#ef4444,color:#fff
    style BadModifier fill:#ef4444,color:#fff
    style LowConfidence fill:#f59e0b,color:#000
    style LLMError fill:#ef4444,color:#fff
    style AwaitInput fill:#06b6d4,color:#fff
```

---

## Langfuse Integration

How Langfuse observability integrates with the graph.

```mermaid
flowchart TB
    subgraph Application["LangGraph Application"]
        Graph["Graph Invoke"]
        Node1["parse_intent_node"]
        Node2["parse_item_node"]
        Node3["validate_node"]
        Node4["response_node"]
    end

    subgraph Langfuse["Langfuse Observability"]
        Handler["CallbackHandler"]
        Trace["Trace"]
        Spans["Spans"]
        LLMCalls["LLM Calls"]
        Scores["Scores"]
        Prompts["Prompt Management"]
    end

    subgraph Dashboard["Langfuse Dashboard"]
        Timeline["Trace Timeline"]
        AgentGraph["Agent Graph View"]
        Costs["Cost Tracking"]
        Sessions["Session Grouping"]
    end

    Graph -->|"config={callbacks: [handler]}"| Handler
    Node1 -->|"Trace Event"| Handler
    Node2 -->|"Trace Event"| Handler
    Node3 -->|"Trace Event"| Handler
    Node4 -->|"Trace Event"| Handler

    Handler --> Trace
    Trace --> Spans
    Trace --> LLMCalls
    Trace --> Scores

    Prompts -->|"get_prompt()"| Node1
    Prompts -->|"get_prompt()"| Node2
    Prompts -->|"get_prompt()"| Node4

    Spans --> Timeline
    Spans --> AgentGraph
    LLMCalls --> Costs
    Trace --> Sessions

    style Handler fill:#06b6d4,color:#fff
    style Trace fill:#8b5cf6,color:#fff
```

---

## Tracing Data Flow

Detailed view of what data flows through Langfuse traces.

```mermaid
flowchart LR
    subgraph TraceContext["Trace Context"]
        TraceID["trace_id"]
        SessionID["session_id<br/>(drive-thru-session-123)"]
        UserID["user_id<br/>(customer-456)"]
    end

    subgraph Spans["Span Hierarchy"]
        RootSpan["Root: drive-thru-order"]
        IntentSpan["Span: parse_intent"]
        ItemSpan["Span: parse_item"]
        ValidateSpan["Span: validate"]
        ResponseSpan["Span: generate_response"]
    end

    subgraph Metadata["Span Metadata"]
        Input["input: customer utterance"]
        Output["output: structured result"]
        Duration["duration_ms"]
        Tokens["token_usage"]
        Cost["cost_usd"]
    end

    subgraph Evaluation["Scores"]
        Accuracy["order-accuracy: 1.0"]
        Feedback["user-feedback: positive"]
    end

    TraceID --> RootSpan
    SessionID --> RootSpan
    UserID --> RootSpan

    RootSpan --> IntentSpan
    RootSpan --> ItemSpan
    RootSpan --> ValidateSpan
    RootSpan --> ResponseSpan

    IntentSpan --> Input
    IntentSpan --> Output
    IntentSpan --> Duration
    IntentSpan --> Tokens
    IntentSpan --> Cost

    RootSpan --> Accuracy
    RootSpan --> Feedback

    style RootSpan fill:#8b5cf6,color:#fff
    style TraceID fill:#06b6d4,color:#fff
```

---

## Complete System State Machine

Comprehensive view of all states and transitions.

```mermaid
stateDiagram-v2
    [*] --> Initializing: Start

    state Initializing {
        [*] --> LoadMenu
        LoadMenu --> MenuLoaded
    }

    MenuLoaded --> Greeting: Menu Ready

    state Greeting {
        [*] --> GenerateGreeting
        GenerateGreeting --> GreetingDelivered
    }

    GreetingDelivered --> AwaitingInput: Greeting Complete

    state AwaitingInput {
        [*] --> Listening
        Listening --> ReceivedUtterance: Text Input
    }

    ReceivedUtterance --> ParsingIntent: Process Utterance

    state ParsingIntent {
        [*] --> ClassifyIntent
        ClassifyIntent --> IntentParsed
    }

    IntentParsed --> RoutingDecision: Intent Ready

    state RoutingDecision {
        [*] --> CheckConfidence
        CheckConfidence --> HighConfidence: >= 0.7
        CheckConfidence --> LowConfidence: < 0.7
    }

    HighConfidence --> AddingItem: ADD_ITEM
    HighConfidence --> ReadingOrder: READ_ORDER
    HighConfidence --> CompletingOrder: DONE
    HighConfidence --> AnsweringQuestion: QUESTION
    LowConfidence --> Clarifying: Need clarification

    state AddingItem {
        [*] --> ParseItem
        ParseItem --> ValidateItem
        ValidateItem --> ItemValid: Passes validation
        ValidateItem --> ItemInvalid: Fails validation
        ItemValid --> AddToOrder
        ItemInvalid --> SuggestAlternatives
    }

    AddToOrder --> AwaitingInput: Success response
    SuggestAlternatives --> AwaitingInput: Rejection response
    ReadingOrder --> AwaitingInput: Order summary
    Clarifying --> AwaitingInput: Clarification request
    AnsweringQuestion --> AwaitingInput: Answer provided

    CompletingOrder --> Confirming: All items captured

    state Confirming {
        [*] --> ReadBackOrder
        ReadBackOrder --> ThankCustomer
    }

    ThankCustomer --> [*]: Order Complete
```

---

## Legend

| Symbol | Meaning |
|--------|---------|
| 🟢 Green | Start/Success states |
| 🔴 Red | End/Failure states |
| 🟡 Yellow/Orange | Decision points |
| 🔵 Blue | Processing nodes |
| 🟣 Purple | LLM/Subgraph operations |
| 🔵 Cyan | Waiting/Input states |
