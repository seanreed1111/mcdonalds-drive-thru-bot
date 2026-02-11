# LangGraph Drive-Thru Bot: State Design (v1 — LLM Orchestrator Pattern)

> **v1 Change from v0:** Replaces the explicit state machine (12+ nodes, intent routing, conditional edges) with an **LLM orchestrator pattern** — a single reasoning node with tool-calling that dramatically simplifies the graph.

> **v1 Scope:** Same as v0 — customers can only **add items** to their order. Remove and modify functionality will be added in future versions.

> **v1 Interface:** Chatbot (text-only). Same as v0.

> **Related Documents:**
> - [v0 State Design](../langgraph-state-design-v0.md) — Previous explicit state machine approach
> - [v1 State Diagrams](./langgraph-state-diagrams-v1.md) — Visual diagrams for this design
> - [v1 Context & State Management](./context-and-state-management-v1.md) — Design decisions for menu storage and order persistence

---

## Table of Contents

- [The LLM Orchestrator Pattern](#the-llm-orchestrator-pattern)
  - [What Is It?](#what-is-it)
  - [Why Use It for a Drive-Thru Bot?](#why-use-it-for-a-drive-thru-bot)
- [v0 vs v1 Comparison](#v0-vs-v1-comparison)
- [v1 Graph Architecture](#v1-graph-architecture)
- [LangGraph State Schema](#langgraph-state-schema)
- [Tool Definitions](#tool-definitions)
  - [lookup_menu_item](#lookup_menu_item)
  - [add_item_to_order](#add_item_to_order)
  - [get_current_order](#get_current_order)
  - [finalize_order](#finalize_order)
- [Orchestrator Node Implementation](#orchestrator-node-implementation)
- [Graph Construction](#graph-construction)
- [Human-in-the-Loop: How User Input Works](#human-in-the-loop-how-user-input-works)
- [How Conversations Flow](#how-conversations-flow)
  - [Simple Order](#simple-order)
  - [Multi-Intent Utterance](#multi-intent-utterance)
  - [Item Not on Menu](#item-not-on-menu)
- [Tradeoff Analysis](#tradeoff-analysis)
- [Implementation Best Practices](#implementation-best-practices)
- [Langfuse Integration](#langfuse-integration)
- [Next Steps](#next-steps)

---

## The LLM Orchestrator Pattern

### What Is It?

In the orchestrator pattern, a single LLM node acts as the **central brain** of the application. Instead of encoding conversation flow as a graph of specialized nodes connected by conditional edges, the LLM:

1. **Reads the full state** — conversation history, current order, menu
2. **Reasons about what to do** — no separate intent classification step
3. **Calls tools** to take actions — validate items, add to order, etc.
4. **Generates the response** — no separate response generation node

The graph structure becomes a simple loop:

```
START -> orchestrator -> should_continue? -> tools -> orchestrator -> ... -> END
```

This is sometimes called the **ReAct pattern** (Reason + Act) or **agentic tool-calling loop**. The LLM reasons about what needs to happen, takes action via tools, observes the result, and continues until the task is complete.

### Why Use It for a Drive-Thru Bot?

The v0 explicit state machine encodes conversational logic as graph structure:

- **6 intent types** = 6 routing branches
- **Separate nodes** for parsing, validation, response generation
- **Conditional edges** for every routing decision
- **12+ nodes** total

This works, but it fights against the natural fluidity of conversation. Consider what happens when a customer says:

> "Can I get two Egg McMuffins, a large coffee, and — actually, what hash brown sizes do you have?"

That single utterance contains:
- An order for Egg McMuffins (quantity 2)
- An order for coffee (large)
- A question about the menu

The v0 state machine classifies **one intent per turn**. It would need special handling for multi-intent utterances, adding more conditional logic to an already complex graph.

With the orchestrator pattern, the LLM handles this naturally:
1. It calls `lookup_menu_item("Egg McMuffin")` and `lookup_menu_item("coffee")`
2. It calls `add_item_to_order(...)` for each valid item
3. It looks up hash brown sizes from the menu context
4. It generates a single response covering all three parts

**The key insight:** In a drive-thru conversation, the *complexity is in understanding natural language*, not in *state transitions*. The LLM is already doing the hard work — let it drive.

---

## v0 vs v1 Comparison

| Aspect | v0 (Explicit State Machine) | v1 (LLM Orchestrator) |
|--------|----------------------------|----------------------|
| **Graph nodes** | 12+ (load_menu, greet, await_input, parse_intent, parse_item, validate, add_item, reject_item, success_response, read_order, clarify, confirm_order, thank) | 4 (orchestrator, tools, update_order, end check) |
| **Routing logic** | Explicit conditional edges + intent enum + confidence gating | LLM decides via tool selection |
| **Intent handling** | One intent per turn, classified via structured output | Multi-intent natural, LLM reasons freely |
| **Structured outputs** | ParsedIntent, ParsedItemRequest, ValidationResult, CustomerResponse | Tool input schemas only (simpler) |
| **State fields** | 8 fields (messages, menu, order, parsed_intent, parsed_item_request, validation_result, response, is_order_complete) | 3 fields (messages, menu, current_order) |
| **Testability** | Unit test each node | Unit test each tool + integration test orchestrator |
| **Determinism** | High (explicit routing) | Medium (LLM-driven routing, deterministic tools) |
| **Multi-intent** | Not supported without additional complexity | Natural |
| **Adding new capabilities** | Add node + routing branch + conditional edge | Add a tool |

---

## v1 Graph Architecture

The graph is a four-node loop: orchestrator, tools, update_order, and conditional routing:

```
START --> orchestrator --> should_continue?
              ^                |
              |          [tool_calls?]
              |                |
              |     Yes: execute tools
              |          |
              |     update_order (process tool results → update current_order)
              |          |
              +----------+
                         |
                    No: respond
                         |
                        END
```

The `orchestrator` node is an LLM with tools bound. LangGraph's prebuilt `ToolNode` handles tool execution. The `update_order` node processes tool results and updates `current_order` in state (see [Context & State Management](./context-and-state-management-v1.md) for the full rationale). The `should_continue` conditional edge checks whether the LLM wants to call more tools or is done responding.

---

## LangGraph State Schema

The state is dramatically simpler than v0:

```python
from typing import Annotated
from langgraph.graph import MessagesState
from orchestrator.models import Order, Menu


class DriveThruState(MessagesState):
    """State for the drive-thru orchestrator graph.

    Inherits `messages` from MessagesState (with add-message reducer).
    Only adds the domain objects the orchestrator needs.
    """
    menu: Menu                  # Loaded menu for this location
    current_order: Order        # Customer's order in progress
```

**What changed from v0:**
- Removed `parsed_intent`, `parsed_item_request`, `validation_result`, `response` — these intermediate structured outputs are no longer needed as separate state fields. The LLM handles parsing and the tools handle validation internally.
- Removed `is_order_complete` — the orchestrator calls `finalize_order` when done, which is the signal to end.
- Uses `MessagesState` base class — provides the `messages` field with the proper add-message reducer built in.

### Pydantic Model Reference

The state references models from the `orchestrator` package. Key details:

**`Menu`** — Rich model with location metadata:
- `menu_id`, `menu_name`, `menu_version` — menu identity and versioning
- `location: Location` — the physical location (id, name, address, city, state, zip, country)
- `items: list[Item]` — all available menu items
- `from_json_file(path)` / `from_dict(data)` — factory methods for loading menu data

**`Order`** — Customer's in-progress order:
- `order_id: str` — auto-generated UUID
- `items: list[Item]` — ordered items with quantities
- Supports `__add__` with an `Item` operand: `updated_order = order + new_item`. If the item (same id/name/category/modifiers) already exists, quantities merge via `Item.__add__`. Otherwise, the item is appended. Returns a new `Order` preserving the original `order_id`.

**`Item`** — Dual-purpose model (menu definition *and* order line item):
- `item_id`, `name`, `category_name: CategoryName` — identity fields
- `default_size: Size` — the item's default size (defaults to `Size.REGULAR`)
- `size: Size | None` — customer-selected size (auto-populated from `default_size` via model validator if not set)
- `quantity: int` — number ordered (minimum 1, enforced by Pydantic `ge=1`)
- `modifiers: list[Modifier]` — customer-selected modifications (for orders)
- `available_modifiers: list[Modifier]` — what modifications are possible (for menu definitions)
- `Item` supports `__add__` — two identical items (same id/name/category/modifiers) can be added to merge quantities
- `Order` supports `__add__` with an `Item` operand — `order + item` merges the item into the order (combining quantities for duplicates, appending if new)
- Supports comparison operators (`>=`, `>`, `<=`, `<`) on quantity for same-item comparisons
- **No price field** — prices are intentionally not modeled. The system does not quote prices.

**`Modifier`** — Item modification:
- `modifier_id: str` — unique identifier
- `name: str` — display name (e.g., "No Canadian Bacon", "Extra Cheese")
- Hashable and equality-comparable by `(modifier_id, name)`

**`Size`** — StrEnum with five values: `snack`, `small`, `medium`, `large`, `regular`

**`CategoryName`** — StrEnum: `breakfast`, `beef-pork`, `chicken-fish`, `salads`, `snacks-sides`, `desserts`, `beverages`, `coffee-tea`, `smoothies-shakes`

---

## Tool Definitions

Tools are where the **determinism lives**. The LLM decides *when* to call them, but the tools themselves are pure functions with predictable behavior.

### lookup_menu_item

Searches the menu for an item. Returns match information without modifying state.

```python
from langchain_core.tools import tool
from orchestrator.models import Menu


@tool
def lookup_menu_item(item_name: str, menu: Menu) -> dict:
    """Look up a menu item by name. Use this BEFORE adding any item to the
    order to verify it exists on the menu. Returns the matched item details
    including category, default size, and available modifiers. If no exact
    match is found, returns up to 3 suggestions for similar items.

    You MUST call this tool before calling add_item_to_order. Never skip
    this step.

    Args:
        item_name: The item name as spoken by the customer.
        menu: The current location's menu (injected via InjectedState).
    """
    # Exact match (case-insensitive)
    for item in menu.items:
        if item.name.lower() == item_name.lower():
            return {
                "found": True,
                "item_id": item.item_id,
                "name": item.name,
                "category_name": item.category_name.value,
                "default_size": item.default_size.value,
                "available_modifiers": [
                    {"modifier_id": m.modifier_id, "name": m.name}
                    for m in item.available_modifiers
                ],
            }

    # No match — suggest similar items
    suggestions = [
        item.name for item in menu.items
        if item_name.lower() in item.name.lower()
        or item.name.lower() in item_name.lower()
    ]

    return {
        "found": False,
        "requested": item_name,
        "suggestions": suggestions[:3] if suggestions else ["Check our menu for available items"],
    }
```

> **Model alignment notes:**
> - Returns `category_name` and `default_size` instead of the former `price` and `available_sizes` — these fields match the actual `Item` model.
> - Returns `available_modifiers` as full `{modifier_id, name}` objects, not bare strings. The LLM needs both fields to construct valid `Modifier` instances when calling `add_item_to_order`.
> - The `menu` parameter should be injected via LangGraph's `InjectedState`, not passed by the LLM.

### add_item_to_order

Adds a validated item to the current order. Uses `Order.__add__` to merge the item into the order (combining quantities for duplicates via `Item.__add__` internally).

```python
from langchain_core.tools import tool
from orchestrator.models import Order, Item, Modifier, Size
from orchestrator.enums import CategoryName


@tool
def add_item_to_order(
    item_id: str,
    item_name: str,
    category_name: str,
    quantity: int = 1,
    size: str | None = None,
    modifiers: list[dict] | None = None,
) -> dict:
    """Add an item to the customer's order. Only call this AFTER you have
    confirmed the item exists using lookup_menu_item. Pass the exact item_id,
    item_name, and category_name returned by lookup_menu_item.

    If the same item (same id, name, category, and modifiers) is already in
    the order, the quantities are merged rather than creating a duplicate.

    Args:
        item_id: The item_id from lookup_menu_item result.
        item_name: Exact menu item name from lookup_menu_item result.
        category_name: Category from lookup_menu_item result.
        quantity: Number of this item (default 1, minimum 1).
        size: Size if applicable (snack, small, medium, large, regular).
              If not specified, uses the item's default_size.
        modifiers: List of modifier objects from lookup_menu_item's
                   available_modifiers. Each must have "modifier_id" and
                   "name" keys. Only use modifiers that appeared in the
                   item's available_modifiers list.
    """
    # Implementation constructs an Item and uses Order.__add__ to merge
    # it into the current order (duplicates get quantities combined).
    return {
        "added": True,
        "item_id": item_id,
        "item_name": item_name,
        "category_name": category_name,
        "quantity": quantity,
        "size": size or "default",
        "modifiers": modifiers or [],
    }
```

> **Model alignment notes:**
> - Requires `item_id` and `category_name` in addition to `item_name` — all three are required to construct a valid `Item` instance.
> - `modifiers` are `{modifier_id, name}` dicts (matching the `Modifier` model), not bare strings. The LLM must use modifier objects from `lookup_menu_item`'s `available_modifiers` response.
> - `size` accepts all five `Size` enum values: `snack`, `small`, `medium`, `large`, `regular`. If omitted, the `Item` model validator auto-populates `size` from `default_size`.
> - `quantity` has a Pydantic `ge=1` constraint — invalid quantities are rejected at the model layer.
> - When the same item configuration is added again, `Order.__add__` merges it into the order, using `Item.__add__` internally for quantity combination (e.g., `order + Item(McMuffin, qty=2)` when order already has 1 McMuffin → single entry with quantity 3).

### get_current_order

Reads back the current order state.

```python
@tool
def get_current_order() -> dict:
    """Get the current order summary. Use this when:
    - The customer asks "what did I order?" or "can you read that back?"
    - You are about to finalize the order and want to confirm with the customer.

    Returns the order ID, list of items with quantities and sizes, and total
    item count. Note: prices are not available — do not quote a total."""
    # Implementation reads from state's current_order (Order model)
    return {
        "order_id": "",       # from Order.order_id (UUID)
        "items": [],          # populated from Order.items
        "item_count": 0,      # sum of all item quantities
    }
```

> **Model alignment notes:**
> - Returns `order_id` from the `Order` model (auto-generated UUID) — useful for finalization and tracing.
> - No `total_price` — the `Item` model has no price field. The system prompt must instruct the LLM not to fabricate totals.
> - Each item in the response includes `item_id`, `name`, `category_name`, `quantity`, `size`, and `modifiers` — the full `Item` model serialized.

### finalize_order

Marks the order as complete and triggers the end of the conversation.

```python
@tool
def finalize_order() -> dict:
    """Finalize and submit the order. Call this ONLY when:
    1. The customer has explicitly said they are done ordering.
    2. You have read back the complete order to the customer using
       get_current_order.
    3. The customer has confirmed the order is correct.

    Do NOT call this if the customer is still adding items or hasn't
    confirmed. After calling this, thank the customer and end the
    conversation."""
    # Implementation reads order_id from state's current_order
    return {
        "finalized": True,
        "order_id": "",       # from Order.order_id (UUID)
        "message": "Order has been submitted.",
    }
```

> **Model alignment note:** Returns the `order_id` from the `Order` model so the orchestrator can reference it in the farewell message (e.g., "Your order #abc123 is confirmed!").

---

## Orchestrator Node Implementation

The orchestrator is a single LLM node with tools bound and a system prompt that defines its role:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

tools = [lookup_menu_item, add_item_to_order, get_current_order, finalize_order]

orchestrator_llm = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are a friendly McDonald's drive-thru assistant taking breakfast orders.

LOCATION: {location_name} — {location_address}

CURRENT MENU:
{menu_items}

CURRENT ORDER:
{current_order}

RULES:
1. Greet the customer warmly when the conversation starts.
2. When a customer orders an item, ALWAYS call lookup_menu_item first to verify it exists.
3. Only call add_item_to_order for items confirmed to exist via lookup_menu_item.
   Pass the exact item_id, item_name, and category_name from the lookup result.
4. If an item isn't found, suggest the alternatives from lookup_menu_item results.
   Do NOT invent alternatives.
5. When the customer says they're done, call get_current_order, read back the
   full order, and ask them to confirm.
6. Only call finalize_order AFTER the customer confirms their order.
7. Handle multiple items in a single request — call lookup_menu_item for each,
   then add_item_to_order for each confirmed item.
8. Keep responses concise and friendly — this is a drive-thru, not a sit-down restaurant.
9. Answer menu questions from the CURRENT MENU above. Do NOT make up items.
10. You do NOT have access to prices. Do not quote prices or totals.
    Say "your total will be at the window" if asked.
11. If the customer asks to remove or change an item, explain you can only
    add items right now.
12. When adding modifiers, only use modifiers from the item's available_modifiers
    list returned by lookup_menu_item. Do not accept modifiers that aren't
    available for that item.
13. Sizes are: snack, small, medium, large, regular. If the customer doesn't
    specify a size, do not ask — the item's default size will be used automatically.
"""


def orchestrator_node(state: DriveThruState) -> dict:
    """The central orchestrator node. Reasons about the conversation
    and decides what tools to call."""
    location = state["menu"].location
    menu_items = "\n".join(
        f"- {item.name} [{item.category_name.value}] (default size: {item.default_size.value})"
        for item in state["menu"].items
    )
    current_items = "\n".join(
        f"- {item.quantity}x {item.name} ({item.size.value})"
        + (f" [{', '.join(m.name for m in item.modifiers)}]" if item.modifiers else "")
        for item in state["current_order"].items
    ) or "Empty"

    system_message = SYSTEM_PROMPT.format(
        location_name=location.name,
        location_address=f"{location.address}, {location.city}, {location.state} {location.zip}",
        menu_items=menu_items,
        current_order=current_items,
    )

    messages = [{"role": "system", "content": system_message}] + state["messages"]
    response = orchestrator_llm.invoke(messages)

    return {"messages": [response]}
```

> **Model alignment notes:**
> - Menu items now show `[category_name]` and `(default size: ...)` instead of prices — matching the actual `Item` fields.
> - Location info from `Menu.location` (the `Location` model) is injected into the prompt header.
> - Current order displays size and modifiers per item, since those are tracked on `Item`.
> - Rule 10 explicitly prevents the LLM from hallucinating prices from training data.
> - Rule 12 constrains the LLM to use only `Modifier` objects from `available_modifiers`, since the `Modifier` model requires both `modifier_id` and `name`.
> - Rule 13 lists all five `Size` enum values including `regular` and tells the LLM not to ask about size when the customer doesn't specify one (the model validator handles defaults).

---

## Graph Construction

The full graph in LangGraph:

```python
import json
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import ToolMessage
from orchestrator.models import Order, Item, Modifier
from orchestrator.enums import Size, CategoryName


def should_continue(state: DriveThruState) -> str:
    """Check if the orchestrator wants to call tools or is done."""
    last_message = state["messages"][-1]

    # If the LLM made tool calls, execute them
    if last_message.tool_calls:
        # Check if finalize_order was called
        for tc in last_message.tool_calls:
            if tc["name"] == "finalize_order":
                return "end"
        return "tools"

    # No tool calls — LLM is responding directly to the customer
    return "respond"


def update_order(state: DriveThruState) -> dict:
    """Process tool results and update current_order.

    Runs after every tool execution. Scans ToolMessages for
    add_item_to_order results and applies them to the order
    using Order.__add__ (merges duplicates, appends new items).
    """
    current_order = state["current_order"]
    menu = state["menu"]

    for msg in state["messages"]:
        if not isinstance(msg, ToolMessage):
            continue
        if msg.name != "add_item_to_order":
            continue

        result = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        if not result.get("added"):
            continue

        menu_item = next(
            (i for i in menu.items if i.item_id == result["item_id"]), None
        )
        if not menu_item:
            continue

        new_item = Item(
            item_id=result["item_id"],
            name=result["item_name"],
            category_name=CategoryName(result["category_name"]),
            default_size=menu_item.default_size,
            size=Size(result["size"]) if result.get("size") else None,
            quantity=result["quantity"],
            modifiers=[Modifier(**m) for m in result.get("modifiers", [])],
        )
        current_order = current_order + new_item  # Order.__add__

    return {"current_order": current_order}


# Build the graph
tool_node = ToolNode(tools)

builder = StateGraph(DriveThruState)
builder.add_node("orchestrator", orchestrator_node)
builder.add_node("tools", tool_node)
builder.add_node("update_order", update_order)

builder.add_edge(START, "orchestrator")
builder.add_conditional_edges(
    "orchestrator",
    should_continue,
    {
        "tools": "tools",
        "respond": END,
        "end": END,
    },
)
builder.add_edge("tools", "update_order")          # tools → update_order
builder.add_edge("update_order", "orchestrator")   # update_order → orchestrator

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

That's the entire graph — 4 nodes. The `update_order` node bridges the gap between tool results (plain dicts) and actual state updates. Compare this to v0's 12+ nodes and multiple conditional edges.

> **Why `update_order` instead of `Command`?** Tools stay as pure functions that return dicts — easy to unit test without mocking `InjectedToolCallId` or asserting `Command` structure. State update logic is centralized in one place. See [Context & State Management](./context-and-state-management-v1.md#chosen-approach-for-v1) for the full comparison.

---

## Human-in-the-Loop: How User Input Works

### The Request-Response Model

The graph does **not** stay running while waiting for user input. Each user message triggers a **separate graph invocation**, and the checkpointer ties them together:

```
Turn 1:
  User sends "Hi, can I get a McMuffin?"
  → graph.invoke() runs the orchestrator loop to completion
  → orchestrator calls tools, generates response
  → graph hits END, returns response
  → "Got it! One Egg McMuffin. Anything else?"

Turn 2:
  User sends "That's all"
  → graph.invoke() runs again (checkpointer restores state from turn 1)
  → orchestrator sees full history, calls finalize_order
  → graph hits END, returns response
  → "Your order is one Egg McMuffin. Your total will be at the window. Have a great day!"
```

The `thread_id` in the config is what connects these separate invocations into a single conversation:

```python
config = {"configurable": {"thread_id": "session-123"}}

# Turn 1
result = graph.invoke(
    {"messages": [HumanMessage(content="Hi, can I get a McMuffin?")]},
    config=config,
)

# Turn 2 — same thread_id, checkpointer restores messages + order state
result = graph.invoke(
    {"messages": [HumanMessage(content="That's all")]},
    config=config,
)
```

### Where "Await Input" Lives

In v0, there was an explicit `await_input` node in the graph. In v1, **there is no await node** — the waiting happens **outside the graph**, in whatever application layer serves the chatbot:

```
┌─────────────────────────────────────┐
│  Application Layer (FastAPI, CLI)   │
│                                     │
│  while True:                        │
│    user_input = get_user_input()  ◄── user types here (blocking)
│    result = graph.invoke(...)     ◄── graph runs to completion
│    display(result)                ◄── show response
│                                     │
└─────────────────────────────────────┘
```

The graph itself is stateless between invocations — it runs, produces a response, and exits. The checkpointer persists `messages`, `menu`, and `current_order` so the next invocation picks up where things left off.

### Can the User Interact During Processing?

**No.** While the graph is running (orchestrator reasoning, tool calls, etc.):

- The user is blocked — they cannot send another message until the response comes back
- The orchestrator may loop internally (call tools, reason, call more tools) but this all happens within a single invocation
- With **streaming**, the user can see partial output as it's generated, but still cannot send new input until the turn completes

```python
# Streaming — user sees output incrementally but can't interrupt
async for event in graph.astream(
    {"messages": [HumanMessage(content="Two McMuffins and a coffee")]},
    config=config,
):
    # Partial responses appear as the orchestrator works
    print(event)
# Only AFTER this loop completes can the user send the next message
```

### Summary

| Question | Answer |
|----------|--------|
| Where does the system wait for input? | **Outside the graph**, in your application layer |
| Can the user interact during processing? | **No** — it's request-response per turn |
| How does state persist between turns? | **Checkpointer** (MemorySaver/SqliteSaver) keyed by `thread_id` |
| Is there an `await_input` node? | **No** — that concept moves to the application layer |
| Can the user see partial output? | **Yes, with streaming** — but can't send new input until the turn finishes |

---

## How Conversations Flow

### Simple Order

Customer: *"Hi, can I get an Egg McMuffin?"*

```
orchestrator (reasoning):
  - Customer is greeting and ordering
  - Need to verify "Egg McMuffin" exists
  - Call lookup_menu_item("Egg McMuffin")

tools: lookup_menu_item returns {found: True, item_id: "mcmuffin-egg-001",
       name: "Egg McMuffin", category_name: "breakfast",
       default_size: "regular", available_modifiers: [...]}

orchestrator (reasoning):
  - Item exists, customer wants 1 (default quantity)
  - Call add_item_to_order(item_id="mcmuffin-egg-001",
      item_name="Egg McMuffin", category_name="breakfast", quantity=1)

tools: add_item_to_order returns {added: True, ...}

orchestrator (response):
  "Hi there! I've got one Egg McMuffin for you. Anything else?"
```

### Multi-Intent Utterance

Customer: *"Two hash browns and a large coffee. What sandwiches do you have?"*

```
orchestrator (reasoning):
  - Customer wants 2 hash browns, 1 large coffee, and has a question
  - Call lookup_menu_item("hash brown")
  - Call lookup_menu_item("coffee")

tools: both return {found: True, ...} with item_id, category_name, etc.

orchestrator (reasoning):
  - Both items exist
  - Call add_item_to_order(item_id="hashbrown-001", item_name="Hash Brown",
      category_name="snacks-sides", quantity=2)
  - Call add_item_to_order(item_id="coffee-001", item_name="Coffee",
      category_name="beverages", quantity=1, size="large")

tools: both return {added: True, ...}

orchestrator (reasoning):
  - Answer menu question from system prompt context (no tool needed)

orchestrator (response):
  "Got it — two hash browns and a large coffee! For sandwiches, we've
   got the Egg McMuffin, Sausage McMuffin, and McGriddle. Want to add one?"
```

Notice how the orchestrator handled three different "intents" in a single turn without any routing logic. The menu question is answered from the system prompt context — no price is quoted since the model has no price data.

### Item Not on Menu

Customer: *"Can I get a Big Mac?"*

```
orchestrator (reasoning):
  - Customer wants a Big Mac, need to check menu
  - Call lookup_menu_item("Big Mac")

tools: lookup_menu_item returns {found: False, suggestions: [...]}

orchestrator (response):
  "Sorry, we don't have the Big Mac on our breakfast menu right now!
   How about an Egg McMuffin or a Sausage McGriddle instead?"
```

No separate reject/suggest node needed — the orchestrator generates the appropriate response based on the tool result.

---

## Tradeoff Analysis

| Aspect | Orchestrator Advantage | Orchestrator Risk |
|--------|----------------------|-------------------|
| **Simplicity** | 3 nodes vs 12+. Easy to understand the whole system at a glance. | — |
| **Multi-intent** | Handles naturally via multiple tool calls in one turn. | — |
| **Extensibility** | Adding capability = adding a tool. No graph restructuring. | — |
| **Conversation quality** | LLM generates contextually appropriate responses. | May occasionally be too creative or off-brand. |
| **Determinism** | Tools are deterministic. Menu validation is exact. | LLM *routing* is probabilistic — it might not always call the right tool. |
| **Testability** | Tools are pure functions, easy to unit test. | Orchestrator behavior requires integration testing with LLM. |
| **Cost** | — | Each turn may use more tokens (full menu + order in system prompt). |
| **Latency** | Often fewer LLM round-trips (one call can handle multiple intents). | Tool-calling loop may add latency if LLM makes sequential tool calls. |
| **Observability** | Cleaner traces — each tool call is a span. | Less structured intermediate state to inspect. |

### When to Fall Back to Explicit Nodes

The orchestrator pattern isn't always the right choice. Consider reverting to explicit state machine (v0 style) if:

- **Strict regulatory requirements** demand fully deterministic, auditable conversation flow
- **The LLM consistently misroutes** and prompt engineering can't fix it
- **Cost per conversation** becomes prohibitive (though `gpt-4o-mini` is quite cheap)
- **You need guaranteed sub-100ms responses** (the tool-calling loop adds latency)

---

## Implementation Best Practices

### Tool Design

1. **Tools should be deterministic** — All business logic (menu matching, validation, size defaults) lives in tools, not in the LLM's reasoning.
2. **Tools should be idempotent where possible** — Calling `lookup_menu_item` twice for the same item should return the same result.
3. **Tool descriptions matter** — The LLM decides which tool to call based on the description. Be precise about when each tool should be used.
4. **Return structured data from tools** — Give the LLM clear data to reason about in subsequent turns. Return full `Modifier` objects (`modifier_id` + `name`), not bare strings.
5. **Leverage Pydantic validation** — `Item.quantity` has `ge=1`, `Size` and `CategoryName` are `StrEnum`s. Let the model layer reject bad data rather than writing manual validation in tools.
6. **Use `Order.__add__` for item addition** — Add items to orders via `updated_order = order + new_item`. This handles both appending new items and merging quantities for duplicates (via `Item.__add__` internally).

### System Prompt

1. **Include the full menu with categories and sizes** — The orchestrator needs menu context to answer questions and guide the customer. Show `[category_name]` and `(default size: ...)` per item — no prices.
2. **Include the current order with sizes and modifiers** — So the orchestrator knows what's already been ordered, including customizations.
3. **Include location context** — From `Menu.location`, inject the restaurant name and address into the prompt.
4. **Be explicit about the workflow** — "ALWAYS use lookup_menu_item before add_item_to_order" prevents the LLM from skipping validation.
5. **Set the tone** — "concise and friendly" keeps responses appropriate for a drive-thru.
6. **Explicitly forbid price quoting** — The `Item` model has no price field. Without this rule, the LLM will hallucinate prices from training data.
7. **Constrain modifier usage** — The LLM must only use modifiers from `available_modifiers` returned by `lookup_menu_item`, since `Modifier` requires both `modifier_id` and `name`.

### Persistence

The checkpointer automatically saves all state fields (`messages`, `menu`, `current_order`) after every node execution. When `graph.invoke()` is called with the same `thread_id`, state is fully restored — this is how the order persists across conversation turns.

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()  # Dev only — use PostgresSaver for production
graph = builder.compile(checkpointer=checkpointer)

# Each conversation gets a thread_id
config = {"configurable": {"thread_id": "drive-thru-session-123"}}
```

The `update_order` node's state updates are persisted by the checkpointer just like any other node's updates. After `update_order` writes `{"current_order": updated_order}`, the checkpointer saves it, and the next `orchestrator` invocation sees the updated order in its system prompt.

### Streaming

```python
async for event in graph.astream(
    {"messages": [HumanMessage(content="I'd like a McMuffin")]},
    config=config,
):
    # Stream orchestrator reasoning + tool calls + final response
    print(event)
```

---

## Langfuse Integration

Integration is the same as v0 but simpler — fewer nodes means cleaner traces:

```python
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()

result = graph.invoke(
    {"messages": [HumanMessage(content="I'd like an Egg McMuffin")]},
    config={
        "callbacks": [langfuse_handler],
        "configurable": {"thread_id": "session-123"},
    },
)
```

What you'll see in Langfuse:
- **One trace per customer turn** with clear spans for each tool call
- **Tool call inputs/outputs** — exactly what the orchestrator asked for and got back (including `item_id`, `category_name`, modifier objects)
- **LLM reasoning** visible in the orchestrator span
- **Token usage and cost** per turn
- **Order ID** from `Order.order_id` for correlating traces to specific orders

---

## Next Steps

### v1 Implementation
1. Implement the four tools with proper state access via LangGraph's `InjectedState`
2. Write and iterate on the orchestrator system prompt
3. Build the 3-node graph
4. Test with realistic multi-turn conversations
5. Compare conversation quality and cost against v0

### Future Considerations
- Add `remove_item_from_order` and `modify_item` tools (much easier than adding new graph branches)
- Add `get_menu_by_category` tool for browsing — can filter `Menu.items` by `CategoryName`
- Consider structured output for the final response if brand consistency requires it
- Evaluate whether a hybrid approach (orchestrator + one guard-rail node) is needed
- Consider adding `price: float` to the `Item` model if price quoting becomes a requirement
- Consider adding `available_sizes: list[Size]` to `Item` if items need to advertise which sizes they come in (currently only `default_size` is modeled)
