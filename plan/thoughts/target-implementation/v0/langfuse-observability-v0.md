# Langfuse Observability for Drive-Thru Voice AI

> **Related Documents:**
> - [LangGraph State Design](./langgraph-state-design-v0.md) – Workflow architecture and basic integration setup
> - [Langfuse Prompt Management](./langfuse-prompt-management-v0.md) – Prompt versioning, testing, and deployment strategies
> - [Langfuse Evaluation](./langfuse-evaluation-v0.md) – Datasets, scoring, and systematic evaluation

---

## Table of Contents

- [Overview](#overview)
- [Why Observability Matters](#why-observability-matters)
- [Core Concepts](#core-concepts)
  - [Traces](#traces)
  - [Observations](#observations)
  - [Sessions](#sessions)
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Verifying Connection](#verifying-connection)
- [Instrumentation Approaches](#instrumentation-approaches)
  - [LangChain/LangGraph Callback Handler](#langchainlanggraph-callback-handler)
  - [Observe Decorator](#observe-decorator)
  - [Context Manager](#context-manager)
  - [Choosing the Right Approach](#choosing-the-right-approach)
- [Instrumenting LangGraph Workflows](#instrumenting-langgraph-workflows)
  - [Basic Integration](#basic-integration)
  - [Persistent Config for LangGraph Server](#persistent-config-for-langgraph-server)
  - [Complete Node Instrumentation Example](#complete-node-instrumentation-example)
- [Adding Trace Attributes](#adding-trace-attributes)
  - [User IDs](#user-ids)
  - [Session IDs](#session-ids)
  - [Tags](#tags)
  - [Metadata](#metadata)
  - [Environments](#environments)
- [Updating Traces](#updating-traces)
  - [Trace Input/Output](#trace-inputoutput)
  - [Observation Updates](#observation-updates)
- [Background Processing and Flushing](#background-processing-and-flushing)
  - [How Langfuse Sends Data](#how-langfuse-sends-data)
  - [Long-Running Applications](#long-running-applications)
  - [Short-Lived Applications](#short-lived-applications)
- [Trace IDs and Distributed Tracing](#trace-ids-and-distributed-tracing)
  - [Deterministic Trace IDs](#deterministic-trace-ids)
  - [Linking to External Systems](#linking-to-external-systems)
- [Drive-Thru Specific Patterns](#drive-thru-specific-patterns)
  - [Tracing a Complete Order](#tracing-a-complete-order)
  - [Tracking Multi-Turn Conversations](#tracking-multi-turn-conversations)
  - [Error and Recovery Tracing](#error-and-recovery-tracing)
- [What You See in Langfuse UI](#what-you-see-in-langfuse-ui)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Overview

This document covers Langfuse observability (tracing) for the McDonald's drive-thru voice AI system. Observability answers the question: **"What happened during this interaction?"**

While related documents cover evaluation (how well did it work?) and prompt management (what prompts are we using?), this document focuses on:

1. **Capturing traces** – Recording every step of an interaction
2. **Structured logging** – Inputs, outputs, latencies, token usage, costs
3. **Debugging** – Finding why a specific order failed
4. **Monitoring** – Tracking system health over time

---

## Why Observability Matters

LLM applications are inherently non-deterministic. The same input can produce different outputs, and debugging without observability is guesswork.

| Without Observability | With Observability |
|-----------------------|--------------------|
| "The order was wrong" | "Intent parsed as `done` instead of `add_item` at 2:34pm" |
| "It's slow sometimes" | "Item validation took 3.2s due to fuzzy matching" |
| "Costs are high" | "Average 1,200 tokens per order, p95 is 2,800 tokens" |
| "Something broke" | "gpt-4o timeout at node `validate_item` for session xyz" |

For a drive-thru system, observability helps with:

- **Debugging failed orders** – See exactly what the customer said and how it was interpreted
- **Latency optimization** – Identify slow nodes that hurt the voice experience
- **Cost management** – Track token usage per order, identify expensive patterns
- **Quality monitoring** – Detect degradation before customers complain

---

## Core Concepts

### Traces

A **trace** represents a single request or interaction. In the drive-thru context, this could be:

- A single customer utterance and response
- An entire order from greeting to confirmation
- A background evaluation run

Every trace has:
- A unique `trace_id`
- Input and output
- Start and end times
- Nested observations

```
TRACE: "order-session-123"
├── Input: "I'd like a sausage McMuffin"
├── Output: "Got it! One Sausage McMuffin. Anything else?"
├── Duration: 1.2s
├── Total Cost: $0.002
└── Observations: [intent_parse, validate_item, generate_response]
```

### Observations

**Observations** are the individual steps within a trace. Langfuse supports several observation types:

| Type | Use Case | Example |
|------|----------|---------|
| **Span** | Generic step or function | `validate_item`, `load_menu` |
| **Generation** | LLM call | `gpt-4o-mini` intent classification |
| **Tool** | Tool/function call | Menu lookup, order update |
| **Event** | Point-in-time occurrence | Error logged, item added |

Observations can be nested to show hierarchy:

```
TRACE
├── SPAN: parse_intent
│   └── GENERATION: gpt-4o-mini (intent classification)
├── SPAN: validate_item
│   ├── SPAN: menu_lookup
│   └── SPAN: fuzzy_match
└── GENERATION: gpt-4o-mini (response generation)
```

### Sessions

**Sessions** group related traces. For drive-thru:

- A session = one customer's complete interaction (multiple turns)
- Multiple traces (one per turn) share the same `session_id`
- Enables analyzing full conversations, not just isolated turns

```
SESSION: "drive-thru-session-456"
├── TRACE 1: "Hi" → "Welcome to McDonald's!"
├── TRACE 2: "I want a McMuffin" → "Got it! Anything else?"
├── TRACE 3: "Add a coffee" → "One coffee. Anything else?"
└── TRACE 4: "That's all" → "Your total is $6.50..."
```

---

## Getting Started

### Installation

```bash
uv add langfuse
```

For LangChain/LangGraph integration:

```bash
uv add langfuse langchain langchain-openai langgraph
```

### Environment Configuration

Set environment variables for Langfuse authentication:

```bash
# .env file
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_BASE_URL="https://cloud.langfuse.com"  # EU region (default)
# LANGFUSE_BASE_URL="https://us.cloud.langfuse.com"  # US region

# Optional: Enable debug logging
LANGFUSE_DEBUG="true"
```

Or configure programmatically:

```python
from langfuse import Langfuse

# Initialize with explicit configuration
Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com",
)
```

### Verifying Connection

```python
from langfuse import get_client

langfuse = get_client()

if langfuse.auth_check():
    print("Connected to Langfuse!")
else:
    print("Connection failed - check credentials")
```

---

## Instrumentation Approaches

Langfuse Python SDK v3 provides multiple ways to instrument your code. All approaches are interoperable—you can mix and match.

### LangChain/LangGraph Callback Handler

**Best for:** LangChain chains, LangGraph workflows, any code using LangChain's callback system.

```python
from langfuse.langchain import CallbackHandler
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

langfuse_handler = CallbackHandler()

llm = ChatOpenAI(model_name="gpt-4o-mini")
prompt = ChatPromptTemplate.from_template("Parse this order: {input}")
chain = prompt | llm

# Pass handler in config
result = chain.invoke(
    {"input": "I want a hash brown"},
    config={"callbacks": [langfuse_handler]}
)
```

For LangGraph:

```python
from langgraph.graph import StateGraph

graph = graph_builder.compile()

# Every node execution is traced automatically
result = graph.invoke(
    {"messages": [HumanMessage(content="I want a McMuffin")]},
    config={"callbacks": [langfuse_handler]}
)
```

### Observe Decorator

**Best for:** Tracing Python functions without modifying internal logic.

```python
from langfuse import observe

@observe()
def validate_item(item_name: str, menu: Menu) -> bool:
    """Validates item against menu. Automatically traced."""
    return item_name.lower() in [i.name.lower() for i in menu.items]

@observe(name="intent-classification", as_type="generation")
async def classify_intent(utterance: str) -> ParsedIntent:
    """LLM call traced as a generation."""
    # ... LLM call logic ...
    return intent

@observe()
def process_order(utterance: str):
    """Nested decorators create hierarchical traces."""
    intent = classify_intent(utterance)  # Child observation
    if intent.intent == "add_item":
        valid = validate_item(intent.item, menu)  # Child observation
    return result
```

**Key features:**

- Automatically captures function inputs, outputs, timings, exceptions
- Nesting is automatic—calling a decorated function from another creates parent-child relationship
- Use `as_type="generation"` for LLM calls to get token tracking
- Set `capture_input=False` or `capture_output=False` to skip large payloads

### Context Manager

**Best for:** Fine-grained control, wrapping code blocks, setting trace attributes.

```python
from langfuse import get_client, propagate_attributes

langfuse = get_client()

# Create a trace with context manager
with langfuse.start_as_current_observation(
    as_type="span",
    name="order-processing",
    input={"customer_utterance": "I want a McMuffin"},
) as span:

    # Propagate attributes to all child observations
    with propagate_attributes(
        user_id="customer-123",
        session_id="drive-thru-session-456",
        tags=["breakfast", "voice-order"],
    ):
        # Nested observation
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="intent-parse",
            model="gpt-4o-mini",
        ) as gen:
            result = llm.invoke(...)
            gen.update(output=result, usage_details={"input": 50, "output": 20})

        span.update(output={"status": "success"})
```

### Choosing the Right Approach

| Approach | Use When |
|----------|----------|
| **Callback Handler** | Using LangChain/LangGraph; want automatic tracing of all components |
| **Decorator** | Tracing custom functions; simple setup; want automatic nesting |
| **Context Manager** | Need explicit control; setting trace attributes; wrapping code blocks |

**Recommendation for this project:** Use the **Callback Handler** for LangGraph integration, supplemented with **decorators** for custom validation functions and **context managers** for setting trace-level attributes.

---

## Instrumenting LangGraph Workflows

### Basic Integration

```python
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

# Initialize handler
langfuse_handler = CallbackHandler()

# Build graph
graph_builder = StateGraph(DriveThruState)
graph_builder.add_node("greet", greet_customer)
graph_builder.add_node("parse", parse_intent)
graph_builder.add_node("validate", validate_item)
# ... add more nodes and edges ...
graph = graph_builder.compile()

# Invoke with tracing
result = graph.invoke(
    {"messages": [HumanMessage(content="I'd like a sausage McMuffin")]},
    config={"callbacks": [langfuse_handler]}
)
```

### Persistent Config for LangGraph Server

When deploying with LangGraph Server, attach the handler at compile time:

```python
langfuse_handler = CallbackHandler()

graph = graph_builder.compile().with_config({
    "callbacks": [langfuse_handler]
})
```

### Complete Node Instrumentation Example

```python
from langfuse import observe, get_client
from langfuse.langchain import CallbackHandler
from langchain_openai import ChatOpenAI

langfuse = get_client()
langfuse_handler = CallbackHandler()

@observe()
def parse_intent_node(state: DriveThruState) -> dict:
    """Parse customer intent from latest message."""

    # Get the latest message
    latest_message = state["messages"][-1].content

    # LLM call (traced via callback handler)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    result = llm.with_structured_output(ParsedIntent).invoke(
        [SystemMessage(content="Classify the customer's intent..."),
         HumanMessage(content=latest_message)],
        config={"callbacks": [langfuse_handler]}
    )

    return {"parsed_intent": result}


@observe()
def validate_item_node(state: DriveThruState) -> dict:
    """Validate requested item against menu."""

    item_request = state["parsed_item_request"]
    menu = state["menu"]

    # Deterministic validation (no LLM)
    match = find_menu_item(item_request.item_name, menu)

    if match:
        validation = ValidationResult(
            is_valid=True,
            matched_item=match,
            confidence=1.0
        )
    else:
        validation = ValidationResult(
            is_valid=False,
            error_message=f"'{item_request.item_name}' not found on menu"
        )

    return {"validation_result": validation}
```

---

## Adding Trace Attributes

Attributes help filter, group, and analyze traces in Langfuse.

### User IDs

Track which customer made the request:

```python
# Via metadata in LangGraph config
result = graph.invoke(
    input,
    config={
        "callbacks": [langfuse_handler],
        "metadata": {"langfuse_user_id": "customer-123"}
    }
)

# Or via propagate_attributes
with propagate_attributes(user_id="customer-123"):
    result = graph.invoke(input, config={"callbacks": [langfuse_handler]})
```

### Session IDs

Group traces from the same conversation:

```python
# Via metadata
config = {
    "callbacks": [langfuse_handler],
    "metadata": {
        "langfuse_session_id": "drive-thru-session-456",
        "langfuse_user_id": "customer-123"
    }
}

# All turns in this conversation use the same session_id
result = graph.invoke({"messages": [msg1]}, config=config)
result = graph.invoke({"messages": [msg2]}, config=config)
result = graph.invoke({"messages": [msg3]}, config=config)
```

### Tags

Categorize traces for filtering:

```python
config = {
    "callbacks": [langfuse_handler],
    "metadata": {
        "langfuse_tags": ["breakfast", "voice-order", "store-789"]
    }
}
```

### Metadata

Store arbitrary key-value data:

```python
with langfuse.start_as_current_observation(as_type="span", name="order") as span:
    span.update_trace(
        metadata={
            "store_id": "store-789",
            "lane_number": 2,
            "time_of_day": "morning",
            "order_count": 3,
        }
    )
```

### Environments

Separate traces by deployment stage:

```bash
# Via environment variable
LANGFUSE_TRACING_ENVIRONMENT="staging"
```

```python
# Or programmatically
Langfuse(environment="staging")
```

---

## Updating Traces

### Trace Input/Output

The trace-level input/output defaults to the root observation, but can be overridden:

```python
with langfuse.start_as_current_observation(as_type="span", name="order") as span:
    # Root observation has its own input/output
    span.update(
        input="Internal processing data",
        output="Internal result"
    )

    # Override trace-level input/output (for UI and evaluation)
    span.update_trace(
        input={"customer_utterance": "I want a McMuffin"},
        output={"response": "Got it! One Sausage McMuffin. Anything else?"}
    )
```

Or from within a decorated function:

```python
@observe()
def process_order(utterance: str):
    langfuse = get_client()

    # ... processing logic ...

    langfuse.update_current_trace(
        input={"utterance": utterance},
        output={"order": order.model_dump()}
    )
```

### Observation Updates

Update observations with additional data:

```python
with langfuse.start_as_current_observation(
    as_type="generation",
    name="llm-call",
    model="gpt-4o-mini"
) as gen:
    response = llm.invoke(messages)

    gen.update(
        output=response.content,
        usage_details={
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
        },
        metadata={"temperature": 0, "max_tokens": 500}
    )
```

---

## Background Processing and Flushing

### How Langfuse Sends Data

Langfuse batches traces locally and sends them asynchronously to avoid blocking your application:

```
Your App        Langfuse SDK        Langfuse Backend
   │                 │                    │
   ├──create trace───►│                    │
   │                 ├──queue locally─────►│
   ├──continue work──►│                    │
   │                 │    (background)     │
   │                 ├────batch send──────►│
   │                 │                    ◄┤
```

### Long-Running Applications

For web servers and long-running services, the background exporter runs continuously. No special handling needed.

### Short-Lived Applications

For scripts, serverless functions, or short-lived processes, **you must flush before exit** to avoid data loss:

```python
from langfuse import get_client

langfuse = get_client()

# Your application logic
result = graph.invoke(...)

# CRITICAL: Flush before process exits
langfuse.flush()
```

For graceful shutdown:

```python
import atexit

langfuse = get_client()
atexit.register(langfuse.shutdown)
```

For serverless (AWS Lambda, etc.):

```python
def handler(event, context):
    langfuse = get_client()

    # ... process request ...

    # Flush before returning
    langfuse.flush()
    return response
```

---

## Trace IDs and Distributed Tracing

### Deterministic Trace IDs

Generate predictable trace IDs from external identifiers:

```python
from langfuse import Langfuse

# Generate deterministic trace ID from external system
external_order_id = "order-2024-001234"
trace_id = Langfuse.create_trace_id(seed=external_order_id)

# Use this trace ID for correlation
with langfuse.start_as_current_observation(
    as_type="span",
    name="order-processing",
    trace_context={"trace_id": trace_id}
) as span:
    # ... processing ...
    pass
```

### Linking to External Systems

For distributed systems, propagate trace context:

```python
# Service A: Start trace and propagate
trace_id = langfuse.get_current_trace_id()
observation_id = langfuse.get_current_observation_id()

# Pass to Service B via headers, message queue, etc.
headers = {
    "x-langfuse-trace-id": trace_id,
    "x-langfuse-parent-observation-id": observation_id
}

# Service B: Continue trace
with langfuse.start_as_current_observation(
    as_type="span",
    name="service-b-processing",
    trace_context={
        "trace_id": headers["x-langfuse-trace-id"],
        "parent_span_id": headers["x-langfuse-parent-observation-id"]
    }
) as span:
    # ... processing ...
    pass
```

---

## Drive-Thru Specific Patterns

### Tracing a Complete Order

```python
from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

langfuse = get_client()
langfuse_handler = CallbackHandler()

def handle_customer_turn(
    utterance: str,
    session_id: str,
    user_id: str,
    store_id: str,
) -> str:
    """Handle a single customer turn with full tracing."""

    with langfuse.start_as_current_observation(
        as_type="span",
        name="customer-turn",
    ) as span:
        # Set trace attributes
        with propagate_attributes(
            session_id=session_id,
            user_id=user_id,
            tags=["drive-thru", f"store-{store_id}"],
            metadata={"store_id": store_id}
        ):
            # Update trace input
            span.update_trace(input={"utterance": utterance})

            # Run LangGraph (automatically traced via callback)
            result = graph.invoke(
                {"messages": [HumanMessage(content=utterance)]},
                config={"callbacks": [langfuse_handler]}
            )

            response = result["response"].text

            # Update trace output
            span.update_trace(
                output={
                    "response": response,
                    "order_items": [i.name for i in result["current_order"].items]
                }
            )

            return response
```

### Tracking Multi-Turn Conversations

```python
class DriveThruSession:
    """Manages a drive-thru session with observability."""

    def __init__(self, store_id: str):
        self.session_id = f"session-{uuid.uuid4()}"
        self.user_id = f"customer-{uuid.uuid4()}"
        self.store_id = store_id
        self.turn_count = 0

    def process_turn(self, utterance: str) -> str:
        self.turn_count += 1

        return handle_customer_turn(
            utterance=utterance,
            session_id=self.session_id,
            user_id=self.user_id,
            store_id=self.store_id,
        )

    def complete_session(self, order: Order):
        """Record session completion metrics."""
        langfuse = get_client()

        # Score the completed session
        langfuse.create_score(
            trace_id=langfuse.get_current_trace_id(),
            name="order-completed",
            value=1.0,
            data_type="NUMERIC",
        )

        langfuse.create_score(
            trace_id=langfuse.get_current_trace_id(),
            name="turn-count",
            value=self.turn_count,
            data_type="NUMERIC",
        )
```

### Error and Recovery Tracing

```python
@observe()
def validate_item_with_recovery(
    item_name: str,
    menu: Menu,
) -> ValidationResult:
    """Validate item with traced error recovery."""

    langfuse = get_client()

    try:
        # Attempt exact match
        match = exact_match(item_name, menu)
        if match:
            return ValidationResult(is_valid=True, matched_item=match)

        # Try fuzzy match
        langfuse.update_current_span(
            metadata={"recovery_attempted": "fuzzy_match"}
        )

        fuzzy_match = fuzzy_match(item_name, menu)
        if fuzzy_match and fuzzy_match.score > 0.8:
            return ValidationResult(
                is_valid=True,
                matched_item=fuzzy_match.item,
                confidence=fuzzy_match.score
            )

        # No match found
        return ValidationResult(
            is_valid=False,
            error_message=f"'{item_name}' not found on menu",
            suggestions=get_suggestions(item_name, menu)
        )

    except Exception as e:
        # Log error to trace
        langfuse.update_current_span(
            level="ERROR",
            metadata={"error": str(e), "error_type": type(e).__name__}
        )
        raise
```

---

## What You See in Langfuse UI

After instrumenting your application, the Langfuse dashboard provides:

### Trace View

- **Timeline**: Chronological view of all observations
- **Hierarchy**: Nested parent-child relationship between spans
- **Details**: Input/output, latency, token usage for each observation

### Session View

- **Conversation flow**: All traces grouped by session
- **Turn-by-turn**: See how the conversation progressed
- **Session metrics**: Total duration, turns, cost

### Dashboard

- **Volume**: Traces per hour/day
- **Latency**: p50, p95, p99 response times
- **Cost**: Token usage and estimated costs
- **Errors**: Failure rate by node, model, or error type

### Filtering

Filter traces by:
- User ID
- Session ID
- Tags
- Time range
- Score values
- Metadata fields

---

## Best Practices

### 1. Always Pass Callbacks

Never invoke LangGraph without the callback handler:

```python
# GOOD
result = graph.invoke(input, config={"callbacks": [langfuse_handler]})

# BAD - No tracing!
result = graph.invoke(input)
```

### 2. Use Consistent Session IDs

Group all turns in a conversation:

```python
session_id = f"drive-thru-{store_id}-{uuid.uuid4()}"

# Use same session_id for entire conversation
for turn in conversation:
    result = graph.invoke(turn, config={
        "callbacks": [langfuse_handler],
        "metadata": {"langfuse_session_id": session_id}
    })
```

### 3. Set Trace Input/Output for Evaluation

Make sure trace-level input/output matches what evaluators need:

```python
# Set meaningful trace input/output (not internal state)
span.update_trace(
    input={"customer_said": utterance},
    output={"ai_responded": response, "items_added": items}
)
```

### 4. Tag for Filtering

Use consistent tags for analysis:

```python
tags = [
    "drive-thru",
    f"store-{store_id}",
    "breakfast" if is_breakfast_hours() else "lunch",
    "voice" if is_voice else "text",
]
```

### 5. Flush on Shutdown

Always flush before process exit:

```python
import atexit
from langfuse import get_client

langfuse = get_client()
atexit.register(langfuse.shutdown)
```

### 6. Use Environments

Separate development, staging, and production:

```bash
# Development
LANGFUSE_TRACING_ENVIRONMENT="development"

# Staging
LANGFUSE_TRACING_ENVIRONMENT="staging"

# Production
LANGFUSE_TRACING_ENVIRONMENT="production"
```

### 7. Sample in High-Volume Production

For high traffic, consider sampling:

```python
import random

SAMPLE_RATE = 0.1  # 10% of traffic

if random.random() < SAMPLE_RATE:
    config = {"callbacks": [langfuse_handler]}
else:
    config = {}

result = graph.invoke(input, config=config)
```

---

## Troubleshooting

### Traces Not Appearing

1. **Check credentials**: Verify `auth_check()` returns `True`
2. **Check flush**: Call `langfuse.flush()` before process exit
3. **Check environment**: Ensure `LANGFUSE_BASE_URL` matches your region
4. **Enable debug**: Set `LANGFUSE_DEBUG=true` for detailed logs

### Missing Observations

1. **Verify callbacks**: Ensure handler is in `config={"callbacks": [handler]}`
2. **Check nesting**: Decorated functions only trace when called within a trace context

### High Latency

1. **Async by default**: Langfuse doesn't block your application
2. **Check batch size**: If you see latency, it's likely in your LLM calls, not Langfuse

### Cost Tracking Issues

1. **Use generation type**: Set `as_type="generation"` for LLM calls
2. **Pass usage**: Include `usage_details` with token counts

---

## Next Steps

1. **Set up Langfuse project** – Create account at [cloud.langfuse.com](https://cloud.langfuse.com)
2. **Add environment variables** – Configure credentials in `.env`
3. **Instrument graph** – Add callback handler to all graph invocations
4. **Add session tracking** – Group multi-turn conversations
5. **Set up dashboards** – Configure key metrics to monitor
6. **Integrate with evaluation** – See [Langfuse Evaluation](./langfuse-evaluation-v0.md)
7. **Connect prompt management** – See [Langfuse Prompt Management](./langfuse-prompt-management-v0.md)
