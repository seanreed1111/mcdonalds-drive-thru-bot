# LangGraph Retries and Rate Limits with Pydantic Structured Output

This document covers strategies for handling retries and rate limits when using LangGraph with Pydantic models for structured output.

## Error Categories and Handling Strategies

LangGraph distinguishes four error types, each requiring a different approach:

| Error Type | Who Fixes It | Strategy | When to Use |
|------------|--------------|----------|-------------|
| **Transient errors** (network issues, rate limits) | System (automatic) | RetryPolicy | Temporary failures that usually resolve on retry |
| **LLM-recoverable errors** (tool failures, parsing issues) | LLM | Store error in state, loop back | LLM can see error and adjust approach |
| **User-fixable errors** (missing info, unclear instructions) | Human | `interrupt()` | Need user input to proceed |
| **Unexpected errors** | Developer | Let them bubble up | Unknown issues needing debugging |

---

## 1. LangGraph Node RetryPolicy (for Transient Errors)

The `RetryPolicy` is applied at the node level and handles transient failures like rate limits and network issues automatically.

### Basic Usage

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy

builder = StateGraph(MyState)

# Add node with retry policy
builder.add_node(
    "call_llm",
    call_llm_function,
    retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0)
)
```

### RetryPolicy Parameters

```python
from langgraph.types import RetryPolicy

retry_policy = RetryPolicy(
    max_attempts=3,           # Maximum retry attempts (default: 3)
    initial_interval=1.0,     # Initial delay in seconds before first retry
    backoff_factor=2.0,       # Multiplier for exponential backoff
    max_interval=60.0,        # Maximum delay between retries (caps growth)
    jitter=True,              # Add ±25% random jitter to avoid thundering herd
    retry_on=None,            # Exception types to retry on (see below)
)
```

### Default Retry Behavior

By default, `retry_on` uses `default_retry_on()` which retries on **all exceptions EXCEPT**:
- `ValueError`
- `TypeError`
- `ArithmeticError`
- `ImportError`
- `LookupError`
- `NameError`
- `SyntaxError`
- `RuntimeError`
- `ReferenceError`
- `StopIteration`
- `StopAsyncIteration`
- `OSError`

For HTTP libraries (`requests`, `httpx`), it only retries on **5xx status codes**.

### Custom Retry Conditions

```python
import sqlite3
from openai import RateLimitError, APIConnectionError

# Retry on specific exception type
retry_policy = RetryPolicy(retry_on=sqlite3.OperationalError)

# Retry on multiple exception types
retry_policy = RetryPolicy(retry_on=(RateLimitError, APIConnectionError))

# Custom retry function
def should_retry(exc: Exception) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if hasattr(exc, 'status_code') and exc.status_code >= 500:
        return True
    return False

retry_policy = RetryPolicy(retry_on=should_retry)
```

### Complete Example with Multiple Nodes

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import RetryPolicy
from langchain.chat_models import init_chat_model

model = init_chat_model("claude-haiku-4-5-20251001")

def call_model(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def call_external_api(state: MessagesState):
    # External API call that might rate limit
    result = external_api.call(state["query"])
    return {"api_result": result}

builder = StateGraph(MessagesState)

# LLM calls: more retries, longer backoff
builder.add_node(
    "model",
    call_model,
    retry_policy=RetryPolicy(max_attempts=5, initial_interval=2.0, backoff_factor=2.0)
)

# External API: fewer retries, shorter initial delay
builder.add_node(
    "external_api",
    call_external_api,
    retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.5)
)

builder.add_edge(START, "model")
builder.add_edge("model", "external_api")
builder.add_edge("external_api", END)

graph = builder.compile()
```

---

## 2. LangChain Middleware (for create_agent)

If using LangChain's `create_agent`, use middleware for retries.

### Model Retry Middleware

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware

agent = create_agent(
    model="gpt-4.1-mini",
    tools=[my_tool],
    middleware=[
        ModelRetryMiddleware(
            max_retries=3,              # Retries after initial call
            initial_delay=1.0,          # Seconds before first retry
            backoff_factor=2.0,         # Exponential multiplier
            max_delay=60.0,             # Maximum delay cap
            jitter=True,                # Random delay variation
            retry_on=(Exception,),      # Exception types to retry
            on_failure='continue',      # 'continue', 'error', or callable
        )
    ]
)
```

### Tool Retry Middleware

```python
from langchain.agents.middleware import ToolRetryMiddleware

agent = create_agent(
    model="gpt-4.1-mini",
    tools=[weather_tool, search_tool],
    middleware=[
        ToolRetryMiddleware(
            max_retries=3,
            tools=["weather_tool"],     # Apply only to specific tools
            on_failure='return_message' # Let LLM handle failure gracefully
        )
    ]
)
```

### on_failure Options

| Value | Behavior |
|-------|----------|
| `'continue'` | Return message with error details, let agent handle |
| `'error'` / `'raise'` | Re-raise exception, stop execution |
| `callable` | Custom function returning error message string |

---

## 3. Structured Output with Pydantic Models

### Basic Structured Output

```python
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model

class OrderItem(BaseModel):
    """A menu item in a customer order."""
    name: str = Field(description="Name of the item")
    quantity: int = Field(description="Number of items", ge=1)
    size: str = Field(description="Size: small, medium, or large")

model = init_chat_model("gpt-4.1-mini")
structured_model = model.with_structured_output(OrderItem)

result = structured_model.invoke("I want 2 large coffees")
# Returns: OrderItem(name="coffee", quantity=2, size="large")
```

### Structured Output with create_agent

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from pydantic import BaseModel, Field

class ExtractedOrder(BaseModel):
    items: list[OrderItem]
    special_requests: str | None = None

agent = create_agent(
    model="gpt-4.1-mini",
    tools=[menu_lookup_tool],
    response_format=ToolStrategy(ExtractedOrder),  # handle_errors=True by default
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "I want a Big Mac and large fries"}]
})

# Access the structured response
order = result["structured_response"]  # ExtractedOrder instance
```

### Error Handling for Structured Output

LangChain's `ToolStrategy` has built-in error handling (enabled by default):

**Schema validation errors**: When output doesn't match schema, agent provides error feedback and retries.

**Multiple tool calls errors**: When model incorrectly calls multiple structured output tools.

```python
# Disable automatic error handling if needed
response_format=ToolStrategy(MyModel, handle_errors=False)
```

---

## 4. Combining Retries with Structured Output in LangGraph

For full control, combine LangGraph's RetryPolicy with structured output handling.

### Pattern: Structured Output Node with Retries

```python
from typing import TypedDict
from pydantic import BaseModel, Field, ValidationError
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy
from langchain.chat_models import init_chat_model

class OrderExtraction(BaseModel):
    items: list[str]
    total_items: int = Field(ge=1)

class GraphState(TypedDict):
    user_input: str
    extracted_order: OrderExtraction | None
    error: str | None
    retry_count: int

model = init_chat_model("gpt-4.1-mini")
structured_model = model.with_structured_output(OrderExtraction, include_raw=True)

def extract_order(state: GraphState) -> dict:
    """Extract order with structured output."""
    result = structured_model.invoke(state["user_input"])

    if result["parsed"]:
        return {"extracted_order": result["parsed"], "error": None}
    else:
        # Parsing failed, store error for potential LLM recovery
        return {"error": str(result["raw"]), "retry_count": state.get("retry_count", 0) + 1}

def should_retry(state: GraphState) -> str:
    """Route based on success/failure."""
    if state.get("extracted_order"):
        return "success"
    if state.get("retry_count", 0) < 3:
        return "retry"
    return "fail"

builder = StateGraph(GraphState)

# Add extraction node with RetryPolicy for transient errors (rate limits)
builder.add_node(
    "extract",
    extract_order,
    retry_policy=RetryPolicy(
        max_attempts=3,
        initial_interval=1.0,
        backoff_factor=2.0,
    )
)
builder.add_node("success", lambda s: s)
builder.add_node("fail", lambda s: {"error": "Max retries exceeded"})

builder.add_edge(START, "extract")
builder.add_conditional_edges("extract", should_retry, {
    "success": "success",
    "retry": "extract",  # Loop back for LLM-recoverable errors
    "fail": "fail"
})
builder.add_edge("success", END)
builder.add_edge("fail", END)

graph = builder.compile()
```

### Pattern: Store Error in State for LLM Recovery

```python
def call_tool_with_recovery(state: GraphState) -> dict:
    """Call tool and store errors for LLM to see."""
    try:
        result = external_tool.invoke(state["query"])
        return {"tool_result": result, "tool_error": None}
    except ToolExecutionError as e:
        # Store error in state - LLM can see it and adjust
        return {"tool_error": str(e), "tool_result": None}

def llm_decide_next(state: GraphState) -> dict:
    """LLM sees any errors and decides how to proceed."""
    messages = state["messages"]

    if state.get("tool_error"):
        # Add error to conversation so LLM can react
        messages.append(SystemMessage(
            content=f"Previous tool call failed: {state['tool_error']}. Please try a different approach."
        ))

    response = model.invoke(messages)
    return {"messages": messages + [response]}
```

---

## 5. Pydantic State Schema Considerations

When using Pydantic for LangGraph state:

### Known Limitations

1. **Output is NOT a Pydantic instance**: Graph output is dict, not BaseModel
2. **Validation only on input**: First node input only, not subsequent nodes
3. **Error traces unclear**: Validation errors don't show which node failed
4. **Performance**: Recursive validation can be slow; consider dataclass for performance

### Using Pydantic State

```python
from pydantic import BaseModel
from langgraph.graph import StateGraph

class MyState(BaseModel):
    user_input: str
    processed: bool = False
    result: str | None = None

builder = StateGraph(MyState)
# Validation happens on graph.invoke() input
```

### Best Practice: TypedDict for State, Pydantic for Structured Output

```python
from typing import TypedDict
from pydantic import BaseModel

# Graph state: TypedDict (faster, no validation overhead)
class GraphState(TypedDict):
    messages: list
    structured_result: dict | None

# Structured output: Pydantic (validation + descriptions for LLM)
class OrderOutput(BaseModel):
    """Customer order details."""
    items: list[str] = Field(description="List of ordered items")
    notes: str | None = Field(description="Special instructions")
```

---

## 6. Rate Limit Best Practices

### Exponential Backoff Formula

```
delay = initial_interval * (backoff_factor ** retry_number)
```

With jitter (±25%):
```
delay = base_delay * (0.75 + random() * 0.5)
```

### Recommended Settings by Provider

| Provider | max_attempts | initial_interval | backoff_factor | Notes |
|----------|--------------|------------------|----------------|-------|
| OpenAI | 5 | 1.0s | 2.0 | Retry on 429, 500, 502, 503 |
| Anthropic | 5 | 1.0s | 2.0 | Similar to OpenAI |
| External APIs | 3 | 0.5s | 2.0 | Depends on SLA |

### Detecting Rate Limits

```python
from openai import RateLimitError
from anthropic import RateLimitError as AnthropicRateLimitError
import httpx

def is_rate_limit_error(exc: Exception) -> bool:
    """Check if exception is a rate limit error."""
    # OpenAI/Anthropic SDK errors
    if isinstance(exc, (RateLimitError, AnthropicRateLimitError)):
        return True

    # HTTP library errors
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429

    # Generic check
    if hasattr(exc, 'status_code'):
        return exc.status_code == 429

    return False

retry_policy = RetryPolicy(
    max_attempts=5,
    retry_on=is_rate_limit_error
)
```

---

## 7. Drive-Thru Bot Examples (Using Project Models)

These examples use the `Item`, `Modifier`, `Order`, and `Menu` models from `src/models.py` and the structured output models from `langgraph-state-design-v0.md`.

### Example 1: Parse Intent Node with RetryPolicy

```python
"""Intent parsing with retry for rate limits."""

from typing import TypedDict
from enum import StrEnum

from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy

from models import Menu, Order, Item


# --- Structured Output Models (from langgraph-state-design-v0.md) ---

class CustomerIntent(StrEnum):
    ADD_ITEM = "add_item"
    REMOVE_ITEM = "remove_item"
    MODIFY_ITEM = "modify_item"
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


# --- Graph State ---

class DriveThruState(TypedDict):
    messages: list
    menu: Menu
    current_order: Order
    parsed_intent: ParsedIntent | None
    is_order_complete: bool


# --- Node Implementation ---

llm = init_chat_model("gpt-4o-mini", temperature=0)
intent_parser = llm.with_structured_output(ParsedIntent)


def parse_intent_node(state: DriveThruState) -> dict:
    """Parse customer intent with structured output."""
    last_message = state["messages"][-1]["content"]

    system_prompt = """You are parsing customer intent at a McDonald's drive-thru.
    Classify the customer's utterance into one of the defined intents.
    Be conservative - use 'unclear' if the intent is ambiguous."""

    result: ParsedIntent = intent_parser.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message}
    ])

    return {"parsed_intent": result}


# --- Graph Construction with RetryPolicy ---

builder = StateGraph(DriveThruState)

# Intent parsing gets retry policy for rate limits
builder.add_node(
    "parse_intent",
    parse_intent_node,
    retry_policy=RetryPolicy(
        max_attempts=5,
        initial_interval=1.0,
        backoff_factor=2.0,
        jitter=True,
    )
)

builder.add_edge(START, "parse_intent")
builder.add_edge("parse_intent", END)

graph = builder.compile()
```

---

### Example 2: Item Parsing with Validation and Error Recovery

```python
"""Parse item request, validate against menu, handle errors."""

from typing import TypedDict
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy

from models import Menu, Order, Item, Modifier
from enums import Size


# --- Structured Output Models ---

class ParsedItemRequest(BaseModel):
    """LLM output for extracting item details from customer utterance."""
    item_name: str = Field(description="The menu item name as spoken by customer")
    quantity: int = Field(default=1, ge=1, description="Number of items requested")
    size: Size | None = Field(default=None, description="Size if specified")
    modifiers: list[str] = Field(
        default_factory=list,
        description="Modifications requested (e.g., 'no pickles', 'extra cheese')"
    )
    raw_utterance: str = Field(description="Original customer utterance for debugging")


class ValidationResult(BaseModel):
    """Result of validating a parsed item against the menu."""
    is_valid: bool = Field(description="Whether the item passed validation")
    matched_item_id: str | None = Field(default=None, description="Menu item_id if matched")
    matched_item_name: str | None = Field(default=None, description="Canonical menu item name")
    match_type: str | None = Field(default=None, description="'exact', 'fuzzy', or None")
    failure_reason: str | None = Field(default=None, description="Why validation failed")
    suggestions: list[str] = Field(default_factory=list, description="Alternative items")


# --- Graph State ---

class ItemParsingState(TypedDict):
    messages: list
    menu: Menu
    current_order: Order
    parsed_item_request: ParsedItemRequest | None
    validation_result: ValidationResult | None
    error: str | None
    retry_count: int


# --- Node Implementations ---

llm = init_chat_model("gpt-4o-mini", temperature=0)
item_parser = llm.with_structured_output(ParsedItemRequest, include_raw=True)


def parse_item_node(state: ItemParsingState) -> dict:
    """Extract item details using structured LLM output."""
    last_message = state["messages"][-1]["content"]
    menu_items = [item.name for item in state["menu"].items]

    system_prompt = f"""Extract the menu item details from the customer's order.
    Available menu items: {menu_items}
    Match the customer's words to the closest menu item name."""

    result = item_parser.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message}
    ])

    if result["parsed"]:
        return {"parsed_item_request": result["parsed"], "error": None}
    else:
        # Structured output parsing failed - store for recovery
        return {
            "error": f"Failed to parse item: {result['raw']}",
            "retry_count": state.get("retry_count", 0) + 1
        }


def validate_item_node(state: ItemParsingState) -> dict:
    """Validate parsed item against menu (deterministic, no LLM)."""
    request = state["parsed_item_request"]
    menu = state["menu"]

    if request is None:
        return {"validation_result": ValidationResult(
            is_valid=False,
            failure_reason="No item request to validate"
        )}

    # Exact match
    for menu_item in menu.items:
        if menu_item.name.lower() == request.item_name.lower():
            return {"validation_result": ValidationResult(
                is_valid=True,
                matched_item_id=menu_item.item_id,
                matched_item_name=menu_item.name,
                match_type="exact"
            )}

    # Fuzzy match (simplified - use rapidfuzz in production)
    suggestions = [
        item.name for item in menu.items
        if request.item_name.lower() in item.name.lower()
        or item.name.lower() in request.item_name.lower()
    ][:3]

    return {"validation_result": ValidationResult(
        is_valid=False,
        failure_reason=f"'{request.item_name}' not found on menu",
        suggestions=suggestions
    )}


def add_to_order_node(state: ItemParsingState) -> dict:
    """Add validated item to order using project Item model."""
    validation = state["validation_result"]
    request = state["parsed_item_request"]
    menu = state["menu"]
    order = state["current_order"]

    if not validation or not validation.is_valid:
        return {}  # Nothing to add

    # Find the menu item
    menu_item = next(
        (item for item in menu.items if item.item_id == validation.matched_item_id),
        None
    )

    if menu_item is None:
        return {"error": "Validated item not found in menu"}

    # Create order item with customer specifications
    order_item = Item(
        item_id=menu_item.item_id,
        name=menu_item.name,
        category_name=menu_item.category_name,
        default_size=menu_item.default_size,
        size=request.size or menu_item.default_size,
        quantity=request.quantity,
        modifiers=[],  # Would match modifiers here
        available_modifiers=menu_item.available_modifiers,
    )

    # Check if same item already in order (use Item.__add__)
    updated_items = list(order.items)
    found_existing = False

    for i, existing in enumerate(updated_items):
        if existing._is_same_item(order_item):
            updated_items[i] = existing + order_item  # Uses Item.__add__
            found_existing = True
            break

    if not found_existing:
        updated_items.append(order_item)

    new_order = Order(order_id=order.order_id, items=updated_items)
    return {"current_order": new_order}


# --- Routing ---

def route_after_parse(state: ItemParsingState) -> str:
    if state.get("error"):
        return "handle_error" if state.get("retry_count", 0) < 3 else "max_retries"
    return "validate"


def route_after_validation(state: ItemParsingState) -> str:
    validation = state.get("validation_result")
    if validation and validation.is_valid:
        return "add_to_order"
    return "suggest_alternatives"


# --- Graph Construction ---

builder = StateGraph(ItemParsingState)

# Parsing node: retry on rate limits (transient errors)
builder.add_node(
    "parse_item",
    parse_item_node,
    retry_policy=RetryPolicy(
        max_attempts=5,
        initial_interval=1.0,
        backoff_factor=2.0,
    )
)

# Validation: no retry needed (deterministic)
builder.add_node("validate", validate_item_node)
builder.add_node("add_to_order", add_to_order_node)
builder.add_node("suggest_alternatives", lambda s: s)
builder.add_node("handle_error", lambda s: s)
builder.add_node("max_retries", lambda s: {"error": "Max parsing retries exceeded"})

builder.add_edge(START, "parse_item")
builder.add_conditional_edges("parse_item", route_after_parse, {
    "validate": "validate",
    "handle_error": "parse_item",  # Loop back for LLM-recoverable errors
    "max_retries": "max_retries",
})
builder.add_conditional_edges("validate", route_after_validation, {
    "add_to_order": "add_to_order",
    "suggest_alternatives": "suggest_alternatives",
})
builder.add_edge("add_to_order", END)
builder.add_edge("suggest_alternatives", END)
builder.add_edge("max_retries", END)

graph = builder.compile()
```

---

### Example 3: Full Drive-Thru Graph with Comprehensive Retry Strategy

```python
"""Complete drive-thru graph showing retry strategies for different node types."""

from typing import TypedDict
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy
from langgraph.checkpoint.memory import InMemorySaver

from models import Menu, Order, Item


# --- State and Models (abbreviated) ---

class CustomerResponse(BaseModel):
    message: str = Field(description="Response to speak to customer")
    should_prompt_next: bool = Field(default=True, description="Ask 'anything else?'")


class DriveThruState(TypedDict):
    messages: list
    menu: Menu
    current_order: Order
    is_order_complete: bool
    last_response: CustomerResponse | None
    error: str | None


# --- Retry Policies for Different Node Types ---

# LLM calls: aggressive retry with backoff (rate limits common)
LLM_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=30.0,
    jitter=True,
)

# External API calls: moderate retry
API_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    initial_interval=0.5,
    backoff_factor=2.0,
    max_interval=10.0,
    jitter=True,
)

# Database operations: quick retry for transient locks
DB_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    initial_interval=0.1,
    backoff_factor=1.5,
    max_interval=2.0,
)


# --- Node Implementations ---

llm = init_chat_model("gpt-4o-mini", temperature=0)
response_generator = llm.with_structured_output(CustomerResponse)


def load_menu_node(state: DriveThruState) -> dict:
    """Load menu from database/file."""
    menu = Menu.from_json_file("menus/breakfast-menu.json")
    return {"menu": menu}


def greet_node(state: DriveThruState) -> dict:
    """Generate greeting with structured output."""
    result: CustomerResponse = response_generator.invoke([
        {"role": "system", "content": "Generate a friendly McDonald's drive-thru greeting."},
        {"role": "user", "content": "Customer just arrived at drive-thru."}
    ])
    return {
        "messages": [AIMessage(content=result.message)],
        "last_response": result
    }


def process_order_node(state: DriveThruState) -> dict:
    """Process customer order request."""
    last_message = state["messages"][-1]
    menu_items = [f"{item.name} ({item.category_name})" for item in state["menu"].items]

    system_prompt = f"""You are a McDonald's drive-thru assistant.
    Menu items: {menu_items}
    Current order: {[item.name for item in state['current_order'].items]}

    Respond helpfully to the customer. If they ordered something, confirm it.
    If item not on menu, politely suggest alternatives."""

    result: CustomerResponse = response_generator.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_message.content if hasattr(last_message, 'content') else str(last_message)}
    ])

    return {
        "messages": state["messages"] + [AIMessage(content=result.message)],
        "last_response": result
    }


def confirm_order_node(state: DriveThruState) -> dict:
    """Confirm final order."""
    order_summary = ", ".join([
        f"{item.quantity}x {item.name}" for item in state["current_order"].items
    ])

    result: CustomerResponse = response_generator.invoke([
        {"role": "system", "content": "Confirm the customer's order and thank them."},
        {"role": "user", "content": f"Order to confirm: {order_summary}"}
    ])

    return {
        "messages": state["messages"] + [AIMessage(content=result.message)],
        "is_order_complete": True
    }


# --- Graph Construction ---

builder = StateGraph(DriveThruState)

# Menu loading: DB retry policy (file/database access)
builder.add_node("load_menu", load_menu_node, retry_policy=DB_RETRY_POLICY)

# Greeting: LLM retry policy
builder.add_node("greet", greet_node, retry_policy=LLM_RETRY_POLICY)

# Order processing: LLM retry policy
builder.add_node("process_order", process_order_node, retry_policy=LLM_RETRY_POLICY)

# Confirmation: LLM retry policy
builder.add_node("confirm_order", confirm_order_node, retry_policy=LLM_RETRY_POLICY)


def route_after_process(state: DriveThruState) -> str:
    """Route based on whether customer is done ordering."""
    if state.get("is_order_complete"):
        return "confirm_order"
    # In production, check parsed intent for "done" signal
    return "await_input"


builder.add_edge(START, "load_menu")
builder.add_edge("load_menu", "greet")
builder.add_edge("greet", "process_order")
builder.add_conditional_edges("process_order", route_after_process, {
    "confirm_order": "confirm_order",
    "await_input": END,  # Return to user for next input
})
builder.add_edge("confirm_order", END)

# Compile with checkpointer for multi-turn conversations
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)


# --- Usage ---

async def handle_customer_message(thread_id: str, user_message: str):
    """Handle a customer message with automatic retry on rate limits."""
    config = {"configurable": {"thread_id": thread_id}}

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=user_message)],
            "current_order": Order(),
            "is_order_complete": False,
        },
        config=config
    )

    return result["last_response"].message
```

---

### Example 4: Custom Rate Limit Detection for Multiple Providers

```python
"""Custom retry logic that handles rate limits from multiple LLM providers."""

from openai import RateLimitError as OpenAIRateLimitError
from anthropic import RateLimitError as AnthropicRateLimitError
import httpx

from langgraph.types import RetryPolicy


def is_retriable_error(exc: Exception) -> bool:
    """Determine if an exception should trigger a retry.

    Handles:
    - OpenAI rate limits (429)
    - Anthropic rate limits (429)
    - OpenAI overloaded errors (503)
    - Generic HTTP 5xx errors
    - Connection errors
    """
    # OpenAI SDK errors
    if isinstance(exc, OpenAIRateLimitError):
        return True

    # Anthropic SDK errors
    if isinstance(exc, AnthropicRateLimitError):
        return True

    # httpx HTTP errors
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500

    # Connection errors (network issues)
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True

    # Generic status code check
    if hasattr(exc, 'status_code'):
        status = exc.status_code
        return status == 429 or status >= 500

    # Check error message for rate limit indicators
    error_msg = str(exc).lower()
    rate_limit_indicators = ['rate limit', 'too many requests', 'overloaded', '429']
    if any(indicator in error_msg for indicator in rate_limit_indicators):
        return True

    return False


# Use with any LLM provider
MULTI_PROVIDER_RETRY = RetryPolicy(
    max_attempts=5,
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=60.0,
    jitter=True,
    retry_on=is_retriable_error,
)


# Apply to nodes
builder.add_node(
    "call_llm",
    call_llm_function,
    retry_policy=MULTI_PROVIDER_RETRY
)
```

---

## Summary

1. **Use LangGraph RetryPolicy** for transient errors (rate limits, network issues) at the node level
2. **Use LangChain Middleware** when using `create_agent` for model/tool retries
3. **Store errors in state** for LLM-recoverable errors (parsing, validation)
4. **Use `interrupt()`** for user-fixable errors
5. **Let unexpected errors bubble up** for debugging
6. **Prefer TypedDict for state, Pydantic for structured output** for best performance
7. **Enable jitter** to avoid thundering herd problems
8. **Set reasonable max_attempts** (3-5) to avoid excessive delays
9. **Use different retry policies** for different node types (LLM vs DB vs API)
10. **Combine RetryPolicy with conditional edges** for LLM-recoverable errors (loop back)
