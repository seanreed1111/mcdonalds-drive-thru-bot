# LangGraph Drive-Thru Bot: State Design

> **v0 Scope:** Customers can only **add items** to their order. Remove and modify functionality will be added in future versions.

> **v0 Interface:** Chatbot (text-only). No Speech-to-Text (STT) or Text-to-Speech (TTS) in v0. The design is structured to easily integrate STT/TTS in future versions.

> **Related Documents:**
> - [Langfuse Prompt Management](./langfuse-prompt-management-v0.md) – Prompt versioning, testing, and deployment strategies
> - [Langfuse Evaluation](./langfuse-evaluation-v0.md) – Systematic evaluation of application behavior
> - [Workflow Thoughts](./workflow-thoughts.md) – High-level ordering workflow requirements

---

## Table of Contents

- [Overview](#overview)
- [Workflow Requirements](#workflow-requirements)
  - [Core Responsibilities](#core-responsibilities)
  - [Validation Rules](#validation-rules)
  - [Edge Cases](#edge-cases)
- [LangGraph State Schema](#langgraph-state-schema)
- [Pydantic Models for Structured Outputs](#pydantic-models-for-structured-outputs)
  - [Intent Classification](#intent-classification)
  - [Parsed Item Request](#parsed-item-request)
  - [Validation Result](#validation-result)
  - [Customer Response](#customer-response)
  - [Combined Parse Result](#combined-parse-result)
- [Node Implementations](#node-implementations)
  - [Using Structured Outputs in Nodes](#using-structured-outputs-in-nodes)
- [Routing with Structured Outputs](#routing-with-structured-outputs)
- [Graph Architectures](#graph-architectures)
  - [Approach 1: Simple Linear with Conditional Loop (Deprecated)](#approach-1-simple-linear-with-conditional-loop-deprecated)
  - [Approach 2: Explicit State Machine (v0 Implementation)](#approach-2-explicit-state-machine-v0-implementation)
  - [Approach 3: Subgraph Pattern with Validation Subgraph (Future Consideration)](#approach-3-subgraph-pattern-with-validation-subgraph-future-consideration)
- [Tradeoff Summary](#tradeoff-summary)
- [v0 Implementation Decision](#v0-implementation-decision)
- [Implementation Best Practices](#implementation-best-practices)
  - [Structured Output Guidelines](#structured-output-guidelines)
  - [Persistence](#persistence)
  - [Streaming](#streaming)
  - [Error Recovery](#error-recovery)
  - [Interface Integration Points](#interface-integration-points)
- [Langfuse Integration for Observability](#langfuse-integration-for-observability)
  - [Why Langfuse?](#why-langfuse)
  - [Setup](#setup)
  - [Basic Integration](#basic-integration)
  - [Adding Context to Traces](#adding-context-to-traces)
  - [Adding Scores for Evaluation](#adding-scores-for-evaluation)
  - [Prompt Management](#prompt-management)
  - [Multi-Agent Tracing](#multi-agent-tracing)
  - [What You'll See in Langfuse](#what-youll-see-in-langfuse)
  - [Best Practices](#best-practices)
- [Next Steps](#next-steps)

---

## Overview

This document defines LangGraph state design patterns for a McDonald's breakfast drive-thru ordering system. In v0, customers interact via a **chatbot interface** (text-only). The architecture is designed to easily integrate Speech-to-Text (STT) and Text-to-Speech (TTS) in future versions without modifying the core graph logic.

The system uses Pydantic v2 models (`Item`, `Modifier`, `Order`, `Menu`) as structured inputs/outputs between workflow nodes and LLM calls.

---

## Workflow Requirements

### Core Responsibilities

1. **Menu Loading**: Load location-specific menu from JSON into memory. All nodes share access to the `Menu` object.

2. **Greeting**: Welcome customer with a friendly, brand-appropriate message.

3. **Order Loop**: Iteratively collect items until the customer signals completion:
   - Parse customer utterance into structured `Item` request
   - Validate against menu (strict matching on `Item.name`)
   - Handle success: add to `Order.items`, confirm item to customer
   - Handle failure: politely inform customer item not on the menu, prompt for alternatives
   - Ask if customer wants to order anything anything else, if so, continue loop. if not, exit loop as order is complete

4. **Order Confirmation**: Read back complete order (`Item.name`, `Item.quantity` for each item), thank customer.

### Validation Rules

| Check | Pass Condition | Fail Condition |
|-------|---------------|----------------|
| Item exists | `Item.name` matches  menu item | No match found |
| Quantity valid | `Item.quantity >= 1` | `quantity < 1` or invalid |
| Modifiers valid | All `Item.modifiers` exist in `Item.available_modifiers` | Unknown modifier requested |

### Edge Cases

- Customer orders item not on menu (polite decline, suggest alternatives)
- Customer requests invalid quantity
- Customer requests unavailable modifier
- Customer wants to hear order so far
- Customer says "that's all" / "done" / "nothing else"

---

## LangGraph State Schema

The workflow state extends `TypedDict` with structured Pydantic models:

```python
from typing import TypedDict
from langgraph.graph import MessagesState
from models import Order, Menu, Item


class DriveThruState(TypedDict):
    messages: list  # Conversation history
    menu: Menu  # Loaded menu for this location
    current_order: Order  # Customer's order in progress

    # Structured LLM outputs
    parsed_intent: ParsedIntent | None
    parsed_item_request: ParsedItemRequest | None
    validation_result: ValidationResult | None
    response: CustomerResponse | None

    # Flow control
    is_order_complete: bool
```

---

## Pydantic Models for Structured Outputs

Use `llm.with_structured_output(Model)` to ensure LLM responses conform to Pydantic schemas. This provides type safety, validation, and predictable outputs for routing decisions.

### Intent Classification

Parse customer intent to determine routing:

```python
from enum import StrEnum
from pydantic import BaseModel, Field


class CustomerIntent(StrEnum):
    ADD_ITEM = "add_item"
    READ_ORDER = "read_order"
    DONE = "done"
    UNCLEAR = "unclear"
    GREETING = "greeting"
    QUESTION = "question"


class ParsedIntent(BaseModel):
    """LLM output for classifying customer intent."""

    intent: CustomerIntent = Field(
        description="The customer's intent based on their utterance"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score for the classification"
    )
    reasoning: str = Field(
        description="Brief explanation of why this intent was chosen"
    )
```

### Parsed Item Request

Extract structured item details from natural language:

```python
from pydantic import BaseModel, Field
from enums import Size


class ParsedItemRequest(BaseModel):
    """LLM output for extracting item details from customer utterance."""

    item_name: str = Field(
        description="The menu item name as spoken by customer"
    )
    quantity: int = Field(
        default=1, ge=1,
        description="Number of this item requested"
    )
    size: Size | None = Field(
        default=None,
        description="Size if specified (snack, small, medium, large)"
    )
    modifiers: list[str] = Field(
        default_factory=list,
        description="Modifications requested (e.g., 'no pickles', 'extra cheese')"
    )
    raw_utterance: str = Field(
        description="The original customer utterance for debugging"
    )

```

### Validation Result

Structured output for menu validation:

```python
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Result of validating a parsed item against the menu."""

    is_valid: bool = Field(
        description="Whether the item passed validation"
    )
    matched_item_id: str | None = Field(
        default=None,
        description="The menu item_id if a match was found"
    )
    matched_item_name: str | None = Field(
        default=None,
        description="The canonical menu item name"
    )
    match_type: str | None = Field(
        default=None,
        description="'exact' or None if no match"
    )
    match_score: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Exact match confidence score"
    )
    failure_reason: str | None = Field(
        default=None,
        description="Why validation failed (if applicable)"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Alternative menu items to suggest on failure"
    )
```

### Customer Response

Structured output for customer-facing responses:

```python
from pydantic import BaseModel, Field


class CustomerResponse(BaseModel):
    """LLM output for generating customer-facing responses."""

    message: str = Field(
        description="The response to speak to the customer"
    )
    tone: str = Field(
        default="friendly",
        description="Tone of the response: friendly, apologetic, confirmatory"
    )
    should_prompt_next: bool = Field(
        default=True,
        description="Whether to ask 'anything else?' after this response"
    )
    internal_notes: str | None = Field(
        default=None,
        description="Internal notes for logging (not spoken)"
    )
```

### Combined Parse Result

For nodes that parse intent and item together:

```python
from pydantic import BaseModel, Field


class ParseResult(BaseModel):
    """Combined LLM output for intent + item parsing."""

    intent: ParsedIntent
    item_request: ParsedItemRequest | None = Field(
        default=None,
        description="Populated when intent is add_item"
    )
```

---

## Node Implementations

### Using Structured Outputs in Nodes

```python
from langchain_openai import ChatOpenAI

# Initialize LLM with structured output
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Create structured output chains
intent_parser = llm.with_structured_output(ParsedIntent)
item_parser = llm.with_structured_output(ParsedItemRequest)
response_generator = llm.with_structured_output(CustomerResponse)


def parse_intent_node(state: DriveThruState) -> dict:
    """Parse customer intent using structured LLM output."""
    last_message = state["messages"][-1].content

    system_prompt = """You are parsing customer intent at a McDonald's drive-thru.
    Classify the customer's utterance into one of the defined intents.
    Be conservative - use 'unclear' if the intent is ambiguous."""

    result: ParsedIntent = intent_parser.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message}
    ])

    return {"parsed_intent": result}


def parse_item_node(state: DriveThruState) -> dict:
    """Extract item details using structured LLM output."""
    last_message = state["messages"][-1].content
    menu_items = [item.name for item in state["menu"].items]

    system_prompt = f"""Extract the menu item details from the customer's order.
    Available menu items: {menu_items}
    Match the customer's words to the closest menu item name."""

    result: ParsedItemRequest = item_parser.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message}
    ])

    return {"parsed_item_request": result}


def generate_response_node(state: DriveThruState) -> dict:
    """Generate customer response using structured LLM output."""
    validation = state.get("validation_result")

    if validation and validation.is_valid:
        context = f"Item '{validation.matched_item_name}' was added to order."
    else:
        context = f"Item not found. Suggestions: {validation.suggestions}"

    system_prompt = """Generate a friendly, concise drive-thru response.
    Keep responses under 20 words. Be helpful and upbeat."""

    result: CustomerResponse = response_generator.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ])

    return {"response": result}
```

---

## Routing with Structured Outputs

Use the structured intent for deterministic routing:

```python
def route_by_intent(state: DriveThruState) -> str:
    """Route to next node based on parsed intent."""
    intent = state.get("parsed_intent")

    if intent is None or intent.confidence < 0.7:
        return "clarify"

    routing_map = {
        CustomerIntent.ADD_ITEM: "parse_item",
        CustomerIntent.READ_ORDER: "read_order",
        CustomerIntent.DONE: "confirm_order",
        CustomerIntent.UNCLEAR: "clarify",
        CustomerIntent.GREETING: "greet",
        CustomerIntent.QUESTION: "answer_question",
    }

    return routing_map.get(intent.intent, "clarify")


# In graph construction
builder.add_conditional_edges(
    "parse_intent",
    route_by_intent,
    {
        "parse_item": "parse_item",
        "read_order": "read_order",
        "confirm_order": "confirm_order",
        "clarify": "clarify",
        "greet": "greet",
        "answer_question": "answer_question",
    }
)
```

---

## Graph Architectures

### Approach 1: Simple Linear with Conditional Loop (Deprecated)

> **⚠️ DEPRECATED:** This approach will not be used. See [Approach 2](#approach-2-explicit-state-machine-v0-implementation) for the v0 implementation.

A minimal graph with a single order-handling node that loops until completion.

```
START --> Load Menu --> Greet Customer --> Take Order Node --> Order Complete?
                                                ^                    |
                                                |____ No ____________|
                                                                     |
                                                        Yes --> Confirm Order --> END
```

**Pros:**
- Simple to implement and debug
- Minimal state transitions
- Good for MVP/prototype

**Cons:**
- All logic bundled in one node (harder to test individually)
- Less flexibility for adding features
- **Not used—too limited for production requirements**

---

### Approach 2: Explicit State Machine (v0 Implementation)

> **✅ v0 IMPLEMENTATION:** This is the architecture used for v0.

Breaks the workflow into discrete, testable nodes with explicit transitions.

```
START --> Load Menu --> Greet --> Await Input --> Parse Intent
                                      ^                |
                                      |          [Intent Type]
                                      |                |
                    +-----------------+----------------+------------------+
                    |                                  |                  |
               add_item                           read_order            done
                    |                                  |                  |
                Validate                          Read Current     Confirm Final
                    |                                 Order             Order
               [Valid?]                               |                  |
                    |                                 |                  v
           +-------+--------+                         |                Thank
           |                |                         |                  |
          Yes              No                         |                  v
           |                |                         |                 END
        Add Item        Reject                        |
           |                |                         |
    Success Response   Await Input                    |
           |                                          |
           +------------------------------------------+
```

**Pros:**
- Each node has single responsibility (easy to test)
- Supports multiple intents (add, read back, done)
- Clear routing logic via conditional edges
- Extensible (can add remove/modify intents in future versions)
- Deterministic behavior (important for fast food ordering)

**Cons:**
- More nodes = more complexity
- Requires careful routing function design

---

### Approach 3: Subgraph Pattern with Validation Subgraph (Future Consideration)

> **📋 FUTURE:** This approach may be considered for future versions if validation complexity increases.

Main graph delegates complex validation to a dedicated subgraph.

```
Main Graph:
  START --> Load Menu --> Greet --> Order Loop --> Parse --> Validation Subgraph
                                        ^                           |
                                        |                    [Result]
                                        |                    /      \
                                        |              Success    Failure
                                        |                 |          |
                                        |           Add to Order   Suggest
                                        |                 |      Alternatives
                                        |            [Done?]         |
                                        |               |            |
                                        +------ No -----+------------+
                                                        |
                                                   Yes --> Confirm --> END

Validation Subgraph:
  Check Menu Match --> [Exact?] --> Yes --> Return Exact Item
                           |
                          No
                           |
                     Fuzzy Match --> [Found?] --> No --> Item Not Found
                                        |
                                       Yes
                                        |
                              Confirm with Customer --> [Confirms?]
                                                            |
                                               Yes --> Return Matched Item
                                               No  --> Item Not Found
```

**Pros:**
- Encapsulates complex validation logic
- Subgraph can be tested independently

**Cons:**
- Most complex to implement
- May be overkill for straightforward validation

---

## Tradeoff Summary

| Approach | Complexity | Testability | Flexibility | Determinism | Status |
|----------|------------|-------------|-------------|-------------|--------|
| **Simple Linear** | Low | Medium | Low | High | ⚠️ Deprecated |
| **Explicit State Machine** | Medium | High | Medium | High | ✅ **v0 Implementation** |
| **Subgraph Pattern** | High | High | High | Medium | 📋 Future consideration |

---

## v0 Implementation Decision

**Approach 2 (Explicit State Machine)** is the architecture for v0:

1. **Determinism matters**: Fast food ordering should be predictable
2. **Clear intents**: Add, read back, done are well-defined (v0 scope)
3. **Testability**: Each node can be unit tested
4. **Extensibility**: Can add remove, modify, combos, upselling later

**Why not Approach 1?** Too limited—bundling all logic in one node makes testing difficult and doesn't support the clear separation of concerns needed for production.

**Why not Approach 3 (yet)?** The subgraph pattern adds complexity that isn't justified for v0's straightforward validation requirements. May be reconsidered if validation logic grows more complex in future versions.

---

## Implementation Best Practices

### Structured Output Guidelines

1. **Always use Pydantic models for LLM outputs** - Never parse free-form text
2. **Set `temperature=0`** for deterministic parsing
3. **Include confidence scores** to handle low-confidence edge cases
4. **Validate at boundaries** - Pydantic validates LLM output, then validate against menu
5. **Keep models focused** - One model per task (intent, item, response)

```python
# Pattern: Chain structured outputs for multi-step parsing
async def parse_and_validate(state: DriveThruState) -> dict:
    # Step 1: Parse intent (structured)
    intent: ParsedIntent = await intent_parser.ainvoke(...)

    # Step 2: If add_item, parse item details (structured)
    if intent.intent == CustomerIntent.ADD_ITEM:
        item: ParsedItemRequest = await item_parser.ainvoke(...)

        # Step 3: Validate against menu (deterministic, no LLM)
        validation: ValidationResult = validate_against_menu(item, state["menu"])

        return {
            "parsed_intent": intent,
            "parsed_item_request": item,
            "validation_result": validation
        }

    return {"parsed_intent": intent}
```

### Persistence

Use LangGraph's `InMemorySaver` or `SqliteSaver` for checkpointing:
- Enables resuming interrupted orders
- Supports multi-turn conversations
- Required for human-in-the-loop if adding manager approval

### Streaming

Enable streaming for real-time responses (v0: chatbot, future: voice synthesis):
```python
async for event in graph.astream(input, config):
    # Stream response chunks (text for v0, TTS for future)
```

### Error Recovery

- Wrap validation in try/except
- Use `Command(goto="await_input")` for graceful recovery
- Log failures for menu improvement insights

### Interface Integration Points

**v0 (Chatbot - Text Only):**
- **Input**: User text message --> `await_input` node
- **Output**: Node responses --> Chat display

**Future (Voice with STT/TTS):**
- **Input**: ASR (Speech-to-Text) output --> `await_input` node
- **Output**: Node responses --> TTS (Text-to-Speech) system
- Consider latency requirements (sub-second response for voice)

> **Design Note:** The graph architecture is interface-agnostic. The same nodes and state machine work for both text and voice—only the input/output adapters change. This allows easy migration from chatbot to voice interface without modifying core logic.

---

## Langfuse Integration for Observability

Langfuse provides open-source observability for LangGraph applications. It enables tracing, debugging, and analyzing workflows without adding latency (fully async).

### Why Langfuse?

- **Trace visualization**: See complete workflow execution including all nodes, LLM calls, and tool usage
- **Agent graphs**: Visual representation of LangGraph state machine execution
- **Cost tracking**: Monitor token usage and costs per trace, user, or session
- **Debugging**: Identify failures, slow nodes, and unexpected routing
- **Evaluation**: Add scores (user feedback, automated evals) to traces
- **Prompt management**: Version and manage prompts with hot-swapping

---

### Setup

#### 1. Install Dependencies

```bash
uv add langfuse langchain-openai
```

#### 2. Configure Environment Variables

```python
import os

os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-..."
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..."
os.environ["LANGFUSE_BASE_URL"] = "https://cloud.langfuse.com"  # EU region
# os.environ["LANGFUSE_BASE_URL"] = "https://us.cloud.langfuse.com"  # US region
```

#### 3. Initialize Callback Handler

```python
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()

# Verify connection
from langfuse import get_client
langfuse = get_client()
if langfuse.auth_check():
    print("Langfuse connected!")
```

---

### Basic Integration

Pass the callback handler when invoking the graph:

```python
# Single invocation
result = graph.invoke(
    {"messages": [HumanMessage(content="I'd like a McMuffin")]},
    config={"callbacks": [langfuse_handler]}
)

# Streaming
for event in graph.stream(
    {"messages": [HumanMessage(content="I'd like a McMuffin")]},
    config={"callbacks": [langfuse_handler]}
):
    print(event)
```

### Persistent Config (LangGraph Server)

For LangGraph Server deployments, attach the handler at compile time:

```python
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()

# Handler attached to all invocations automatically
graph = graph_builder.compile().with_config({"callbacks": [langfuse_handler]})
```

---

### Adding Context to Traces

#### Session and User Tracking

Track conversations and users for debugging and analytics:

```python
from langfuse.langchain import CallbackHandler

# Pass session and user IDs for grouping
langfuse_handler = CallbackHandler()

result = graph.invoke(
    {"messages": [HumanMessage(content="Add a hash brown")]},
    config={
        "callbacks": [langfuse_handler],
        "metadata": {
            "langfuse_session_id": "drive-thru-session-123",
            "langfuse_user_id": "customer-456"
        }
    }
)
```

#### Custom Trace Attributes

Add metadata using context managers:

```python
from langfuse import get_client

langfuse = get_client()

with langfuse.start_as_current_observation(
    name="drive-thru-order",
    trace_context={"trace_id": "custom-trace-id"}
) as span:
    span.update_trace(
        input="Customer wants breakfast items",
        metadata={"location_id": "store-789"}
    )

    result = graph.invoke(
        {"messages": [HumanMessage(content="I want an Egg McMuffin")]},
        config={"callbacks": [langfuse_handler]}
    )

    span.update_trace(output=result)
```

---

### Adding Scores for Evaluation

Scores enable tracking quality metrics, user feedback, and automated evaluations:

```python
from langfuse import get_client

langfuse = get_client()

# After order completion, score the interaction
langfuse.create_score(
    trace_id="trace-id-from-order",
    name="order-accuracy",
    value=1.0,  # 0-1 scale
    data_type="NUMERIC",
    comment="All items correctly captured"
)

# User feedback (thumbs up/down)
langfuse.create_score(
    trace_id="trace-id-from-order",
    name="user-feedback",
    value="positive",
    data_type="CATEGORICAL"
)
```

---

### Prompt Management

> **See also:** [Langfuse Prompt Management](./langfuse-prompt-management-v0.md) for detailed coverage of prompt versioning, testing workflows, deployment strategies, and best practices.

Manage and version prompts in Langfuse, then use in LangGraph nodes:

```python
from langfuse import get_client

langfuse = get_client()

# Create/update prompt in Langfuse (or via UI)
langfuse.create_prompt(
    name="drive-thru-system-prompt",
    prompt="""You are a friendly McDonald's drive-thru assistant.
    Available menu items: {{menu_items}}
    Current order: {{current_order}}
    Help the customer complete their breakfast order.""",
    labels=["production"]
)

# Fetch prompt in node
def get_system_prompt(menu_items: list[str], current_order: str) -> str:
    prompt = langfuse.get_prompt("drive-thru-system-prompt")
    return prompt.compile(
        menu_items=", ".join(menu_items),
        current_order=current_order
    )
```

---

### Multi-Agent Tracing

For workflows with multiple LangGraph agents (e.g., order agent + payment agent), group traces:

```python
from langfuse import get_client, Langfuse
from langfuse.langchain import CallbackHandler

langfuse = get_client()

# Generate shared trace ID
shared_trace_id = Langfuse.create_trace_id()

# Main agent
with langfuse.start_as_current_observation(
    name="main-drive-thru-agent",
    trace_context={"trace_id": shared_trace_id}
) as span:
    span.update_trace(input="Customer interaction started")

    # Sub-agent for order validation
    with langfuse.start_as_current_observation(
        name="order-validation-agent",
        trace_context={"trace_id": shared_trace_id}
    ) as sub_span:
        validation_result = validation_graph.invoke(
            state,
            config={"callbacks": [langfuse_handler]}
        )
```

---

### What You'll See in Langfuse

1. **Trace Timeline**: Chronological view of all nodes executed
2. **Agent Graph View**: Visual state machine diagram showing node transitions
3. **LLM Details**: Prompts, completions, token usage, latency per call
4. **Tool Calls**: Inputs/outputs for structured output parsing
5. **Cost Breakdown**: Per-trace and aggregated cost tracking
6. **Session View**: All traces grouped by drive-thru session

---

### Best Practices

1. **Always pass callbacks**: Never invoke graph without `config={"callbacks": [langfuse_handler]}`
2. **Use session IDs**: Group related traces (e.g., entire drive-thru conversation)
3. **Add user IDs**: Track per-customer behavior and issues
4. **Score completed orders**: Enable quality monitoring and evaluation
5. **Use prompt management**: Version prompts separately from code
6. **Flush on shutdown**: Call `langfuse.flush()` before process exit

```python
# Graceful shutdown
import atexit
from langfuse import get_client

langfuse = get_client()
atexit.register(langfuse.flush)
```

---

## Next Steps

### v0 (Chatbot Interface)
1. Define exact node signatures and state schema
2. Implement exact menu matching
3. Build and test individual nodes
4. Wire up graph with conditional edges
5. Add persistence and streaming
6. Build chatbot interface (text input/output)
7. **Set up Langfuse project and integrate observability**

### Future Versions
8. Integrate with voice pipeline (ASR/TTS)
9. Add remove/modify item functionality
