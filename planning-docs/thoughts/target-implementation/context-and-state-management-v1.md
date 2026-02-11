# Context & State Management: Menu and Order Persistence (v1)

> **Question:** Does the orchestrator need the full menu and full order in LLM context at all times? What are the options for storing each efficiently?

> **Reference Documents:**
> - [v1 State Design](./langgraph-state-design-v1.md) — Orchestrator pattern and tool definitions
> - [v1 State Diagrams](./langgraph-state-diagrams-v1.md) — Visual diagrams

---

## Table of Contents

- [The Problem](#the-problem)
- [Two Distinct Concerns](#two-distinct-concerns)
- [LangGraph Persistence Primitives](#langgraph-persistence-primitives)
  - [Checkpointer](#checkpointer)
  - [Store](#store)
  - [InjectedState and InjectedStore](#injectedstate-and-injectedstore)
  - [Command (Tool State Writes)](#command-tool-state-writes)
  - [Runtime Context](#runtime-context)
- [Options for Menu Storage](#options-for-menu-storage)
  - [Option A: Full Menu in System Prompt (Current Design)](#option-a-full-menu-in-system-prompt-current-design)
  - [Option B: Tool-Based Menu Retrieval](#option-b-tool-based-menu-retrieval)
  - [Option C: Runtime Context Schema](#option-c-runtime-context-schema)
  - [Option D: Hybrid — Summary in Prompt, Detail via Tool](#option-d-hybrid--summary-in-prompt-detail-via-tool)
  - [Menu Options Comparison](#menu-options-comparison)
- [Options for Order Persistence](#options-for-order-persistence)
  - [Option 1: State + Checkpointer (Current Design)](#option-1-state--checkpointer-current-design)
  - [Option 2: Tool-Managed via Command](#option-2-tool-managed-via-command)
  - [Option 3: State + Custom Reducer](#option-3-state--custom-reducer)
  - [Order Options Comparison](#order-options-comparison)
- [Recommended Approach for v1](#recommended-approach-for-v1)
- [Token Budget Analysis](#token-budget-analysis)
- [Implementation Sketch](#implementation-sketch)
- [Future Scaling Considerations](#future-scaling-considerations)

---

## The Problem

In the current v1 design, the orchestrator system prompt contains:

```
LOCATION: {location_name} — {location_address}

CURRENT MENU:
- Egg McMuffin [breakfast] (default size: regular)
- Sausage McMuffin [breakfast] (default size: regular)
- Hash Brown [snacks-sides] (default size: regular)
- Coffee [beverages] (default size: medium)
... (50+ items)

CURRENT ORDER:
- 2x Hash Brown (regular)
- 1x Coffee (large) [Extra Sugar]
```

This means **every single LLM call** — every turn of the conversation — sends the full menu and order in the system prompt. For a 50-item menu, that's potentially 1,000+ tokens of static context repeated across every turn.

**Questions this raises:**
1. Is this token cost acceptable, or is there a more efficient approach?
2. Does the menu need to be in the prompt at all, or can tools handle it?
3. How should the order be persisted and updated across turns?
4. What LangGraph primitives exist to help with this?

---

## Two Distinct Concerns

The menu and the order have fundamentally different characteristics:

| Aspect | Menu | Order |
|--------|------|-------|
| **Mutability** | Static for the entire conversation | Changes every turn |
| **Size** | Large (50+ items with modifiers) | Small (typically 1-10 items) |
| **Access pattern** | Read-only, queried selectively | Read-write, need full view |
| **Who needs it** | Tools (for validation) + LLM (for questions) | LLM (for read-back) + Tools (for add/finalize) |
| **Lifecycle** | Loaded once at graph init | Created at graph init, updated per turn |

This means they should be stored and accessed differently.

---

## LangGraph Persistence Primitives

LangGraph provides several mechanisms for persisting and accessing data. Here's what each does and when to use it.

### Checkpointer

**What it does:** Automatically saves the complete graph state after every step (node execution). On the next `graph.invoke()` with the same `thread_id`, state is fully restored.

**Options:**
- `MemorySaver` — in-memory, development only (lost on restart)
- `SqliteSaver` — file-based, good for local dev
- `PostgresSaver` — production-grade, recommended for deployment

**How it works:**
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# Turn 1
result = graph.invoke(
    {"messages": [HumanMessage(content="Hi")]},
    config={"configurable": {"thread_id": "session-123"}},
)

# Turn 2 — checkpointer restores messages, menu, current_order
result = graph.invoke(
    {"messages": [HumanMessage(content="Add a McMuffin")]},
    config={"configurable": {"thread_id": "session-123"}},
)
```

**Key characteristics:**
- Saves ALL state fields (messages, menu, current_order)
- Scoped to a single conversation thread
- Automatic — no code needed beyond `compile(checkpointer=...)`
- Menu gets serialized/deserialized every turn even though it never changes

**Best for:** Order persistence across turns. This is exactly what checkpointers are designed for.

**Not ideal for:** Static reference data like the menu (wasteful to serialize every step).

### Store

**What it does:** Key-value storage that persists across threads (conversations). Organized by namespaces.

**Options:**
- `InMemoryStore` — development only
- `PostgresStore` / `RedisStore` — production

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
graph = builder.compile(checkpointer=checkpointer, store=store)
```

**Key characteristics:**
- Cross-session — survives across different `thread_id`s
- Namespace-scoped (e.g., by user ID, location ID)
- Supports semantic search (vector similarity)
- Accessible from tools via `InjectedStore`

**Best for:** User preferences, learned facts across conversations, long-term memory.

**Not ideal for:** Static reference data like a menu. The menu is the same for every customer at a location — it's not per-user long-term memory.

### InjectedState and InjectedStore

Tools can access graph state and store without the LLM knowing about it:

```python
from langchain_core.tools import tool, InjectedState, InjectedStore
from typing import Annotated

# Read full state
@tool
def my_tool(item_name: str, state: Annotated[dict, InjectedState]) -> dict:
    menu = state["menu"]  # Access menu from state
    # ...

# Read specific field
@tool
def my_tool(item_name: str, menu: Annotated[Menu, InjectedState("menu")]) -> dict:
    # menu is injected directly
    # ...

# Access persistent store
@tool
def my_tool(key: str, store: Annotated[Any, InjectedStore()]) -> str:
    result = store.get(("namespace",), key)
    # ...
```

**Key characteristics:**
- Injected parameters are **invisible to the LLM** — they don't appear in the tool's schema
- `InjectedState` is **read-only** — tools cannot modify state through it
- This is how `lookup_menu_item` should access the menu

### Command (Tool State Writes)

Tools can write back to state using `Command`:

```python
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage

@tool
def add_item_to_order(
    item_name: str,
    quantity: int,
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[dict, InjectedState],
) -> Command:
    """Add item to order — writes directly to state."""
    current_order = state["current_order"]
    # ... construct new_item, add to order ...

    return Command(update={
        "messages": [ToolMessage(f"Added {quantity}x {item_name}", tool_call_id=tool_call_id)],
        "current_order": updated_order,
    })
```

**Critical requirements:**
- `Command.update` **must** include a `messages` key with a `ToolMessage`
- The `ToolMessage` needs a `tool_call_id` (obtained via `InjectedToolCallId`)
- Without the `ToolMessage`, the LLM's conversation history becomes invalid (AI message with tool call but no result)

**Key characteristics:**
- This is the **only way** for tools to modify state
- `ToolNode` automatically handles `Command` objects
- If a tool returns a plain string/dict (not `Command`), `ToolNode` wraps it as a `ToolMessage` and only updates `messages`

### Runtime Context

A newer LangGraph pattern (2025) for passing immutable data to nodes:

```python
from dataclasses import dataclass

@dataclass
class Context:
    menu: Menu  # Full menu — passed once, not serialized in checkpoints

graph = StateGraph(state_schema=DriveThruState, context_schema=Context)

def orchestrator_node(state: DriveThruState, runtime: Runtime[Context]) -> dict:
    menu = runtime.context.menu  # Access menu without it being in state
    # ...
```

**Key characteristics:**
- Menu is NOT serialized in checkpoints
- Available to all nodes
- Cleaner separation between mutable state (order) and immutable reference data (menu)
- Relatively new API — may be less documented

---

## Options for Menu Storage

### Option A: Full Menu in System Prompt (Current Design)

The v1 design puts the entire menu in the system prompt every turn.

```python
SYSTEM_PROMPT = """...
CURRENT MENU:
{menu_items}
...
"""

def orchestrator_node(state: DriveThruState) -> dict:
    menu_items = "\n".join(
        f"- {item.name} [{item.category_name.value}] (default size: {item.default_size.value})"
        for item in state["menu"].items
    )
    # ... format and send
```

**Pros:**
- Simplest implementation
- LLM can answer menu questions directly without tool calls ("What sandwiches do you have?")
- No extra round-trips

**Cons:**
- ~1,000+ tokens of static menu repeated every turn
- Scales poorly — 200 items = 4,000+ tokens per turn
- Menu gets serialized into every checkpoint
- LLM may get distracted by irrelevant menu items

### Option B: Tool-Based Menu Retrieval

Remove the menu from the system prompt entirely. The LLM uses tools for ALL menu access.

```python
SYSTEM_PROMPT = """...
You have access to a breakfast menu. Use lookup_menu_item to find items and
search_menu_by_category to browse available items. Do not guess what's on
the menu — always use the tools.
...
"""

@tool
def lookup_menu_item(
    item_name: str,
    menu: Annotated[Menu, InjectedState("menu")],
) -> dict:
    """Look up a specific item by name."""
    # ... (as in current design)

@tool
def search_menu_by_category(
    category: str,
    menu: Annotated[Menu, InjectedState("menu")],
) -> dict:
    """Browse items in a menu category (e.g., 'breakfast', 'beverages')."""
    matching = [
        {"name": item.name, "default_size": item.default_size.value}
        for item in menu.items
        if item.category_name.value == category
    ]
    return {"category": category, "items": matching[:10]}
```

**Pros:**
- Dramatically fewer tokens per turn — LLM only sees items it asks about
- Scales to very large menus (100s of items)
- Menu stays in state (for tool access via `InjectedState`) but not in the prompt

**Cons:**
- Extra round-trips: "What sandwiches do you have?" now requires a tool call
- LLM might forget to use tools for simple questions
- Adds latency (one more orchestrator loop iteration per menu question)
- Requires a new tool (`search_menu_by_category`) — current design only has `lookup_menu_item`

### Option C: Runtime Context Schema

Use LangGraph's context schema to pass the menu outside of state:

```python
from dataclasses import dataclass

@dataclass
class DriveThruContext:
    menu: Menu

class DriveThruState(MessagesState):
    current_order: Order  # Only mutable state

graph = StateGraph(
    state_schema=DriveThruState,
    context_schema=DriveThruContext,
)
```

**Pros:**
- Menu is NOT serialized in checkpoints — saves storage and serialization cost
- Clean separation: state = mutable, context = immutable
- Tools can still access menu via the runtime

**Cons:**
- Newer API — less community documentation and examples
- Still need to decide whether to put menu in the prompt or use tools
- The menu still needs to be loaded and passed on every `graph.invoke()`

### Option D: Hybrid — Summary in Prompt, Detail via Tool

Put a **condensed menu summary** (categories and counts) in the system prompt, and use tools for item-level detail.

```python
SYSTEM_PROMPT = """...
MENU CATEGORIES (use search_menu_by_category or lookup_menu_item for details):
- breakfast: 12 items (McMuffins, McGriddles, Big Breakfast, etc.)
- beverages: 8 items (Coffee, Orange Juice, Milk, etc.)
- snacks-sides: 5 items (Hash Brown, Apple Slices, etc.)
- coffee-tea: 6 items (Latte, Cappuccino, Hot Tea, etc.)

CURRENT ORDER:
{current_order}
...
"""
```

**Pros:**
- Very few tokens in the prompt (~100-200 for the summary)
- LLM knows what categories exist and can mention them conversationally
- Detail comes from tools — only relevant items loaded into context
- Scales to any menu size

**Cons:**
- Two-step for menu questions: LLM reads summary, then calls tool for details
- Requires maintaining the summary format separately from the menu data
- Slightly more complex implementation

### Menu Options Comparison

| Aspect | A: Full in Prompt | B: Tool-Only | C: Runtime Context | D: Hybrid |
|--------|------------------|-------------|-------------------|-----------|
| **Tokens per turn** | ~1,000+ (50 items) | ~0 (menu not in prompt) | ~1,000+ if in prompt, ~0 if tool-only | ~150 (summary only) |
| **Menu questions** | Direct answer (no tool) | Tool call required | Depends on prompt strategy | Tool call for detail |
| **Implementation** | Simplest | +1 new tool | New API pattern | +1 tool + summary logic |
| **Scales to 200+ items** | Poorly (4,000+ tokens) | Well | Well | Well |
| **Checkpoint size** | Menu serialized | Menu serialized | Menu NOT serialized | Menu serialized (if in state) |
| **Extra latency** | None | 1 extra loop per question | None (if in prompt) | 1 extra loop per detail |

---

## Options for Order Persistence

### Option 1: State + Checkpointer (Current Design)

The order lives in `DriveThruState.current_order` and the checkpointer saves it between turns.

```python
class DriveThruState(MessagesState):
    menu: Menu
    current_order: Order  # Checkpointer saves this automatically

# Tools return dicts, orchestrator node handles state updates
@tool
def add_item_to_order(item_name: str, quantity: int = 1, ...) -> dict:
    return {"added": True, "item_name": item_name, "quantity": quantity}
```

The orchestrator node (or a separate update node) reads the tool result from messages and updates `current_order`.

**Pros:**
- Simplest mental model — order is just a state field
- Checkpointer handles persistence automatically
- Order available to all nodes
- Tools remain pure functions (return dicts) — easy to unit test

**Filling the gap — who updates `current_order`?**

In the raw version of this option, tools return dicts (e.g., `{added: true, item_name: "Egg McMuffin"}`) but nothing actually modifies `current_order`. This gap is closed by adding an **`update_order` node** between the tool node and the orchestrator:

```
START -> orchestrator -> should_continue?
              ^                |
              |          [tool_calls?]
              |                |
              |     Yes: execute tools
              |          |
              |     update_order  ← NEW: processes tool results, updates current_order
              |          |
              +----------+
                         |
                    No: respond
                         |
                        END
```

The `update_order` node:
1. Scans the latest `ToolMessage`s in `state["messages"]`
2. For any `add_item_to_order` results, constructs an `Item` from the tool's returned data
3. Merges the item into `current_order` using `Order.__add__`
4. Returns `{"current_order": updated_order}` — the checkpointer persists this

```python
from langchain_core.messages import ToolMessage

def update_order(state: DriveThruState) -> dict:
    """Process tool results and update current_order.

    Runs after every tool execution. Scans ToolMessages for
    add_item_to_order results and applies them to the order.
    """
    current_order = state["current_order"]
    menu = state["menu"]

    for msg in state["messages"]:
        if not isinstance(msg, ToolMessage):
            continue
        # ToolMessage.name contains the tool name
        if msg.name != "add_item_to_order":
            continue

        # Parse the tool result (tool returns a dict)
        result = msg.content  # or json.loads(msg.content) depending on format
        if not result.get("added"):
            continue

        # Find the menu item for defaults
        menu_item = next(
            (i for i in menu.items if i.item_id == result["item_id"]), None
        )
        if not menu_item:
            continue

        # Construct Item and merge into order
        new_item = Item(
            item_id=result["item_id"],
            name=result["item_name"],
            category_name=CategoryName(result["category_name"]),
            default_size=menu_item.default_size,
            size=Size(result["size"]) if result.get("size") and result["size"] != "default" else None,
            quantity=result["quantity"],
            modifiers=[Modifier(**m) for m in result.get("modifiers", [])],
        )
        current_order = current_order + new_item  # Order.__add__

    return {"current_order": current_order}
```

This keeps tools as **pure functions** (they validate and return data, but don't mutate state) while ensuring the order is always consistent with what the tools reported.

**Cons:**
- Adds a 4th node to the graph (still much simpler than v0's 12+)
- Tool result parsing in `update_order` must stay in sync with tool return schemas

### Option 2: Tool-Managed via Command

Tools directly modify the order using `Command`:

```python
from langgraph.types import Command
from langchain_core.messages import ToolMessage

@tool
def add_item_to_order(
    item_id: str,
    item_name: str,
    category_name: str,
    quantity: int = 1,
    size: str | None = None,
    modifiers: list[dict] | None = None,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Add item to the customer's order."""
    menu = state["menu"]
    current_order = state["current_order"]

    # Find the menu item to get defaults
    menu_item = next(
        (i for i in menu.items if i.item_id == item_id), None
    )
    if not menu_item:
        return Command(update={
            "messages": [ToolMessage(
                f"Error: item_id '{item_id}' not found on menu.",
                tool_call_id=tool_call_id,
            )]
        })

    # Construct the order Item
    new_item = Item(
        item_id=item_id,
        name=item_name,
        category_name=CategoryName(category_name),
        default_size=menu_item.default_size,
        size=Size(size) if size else None,
        quantity=quantity,
        modifiers=[Modifier(**m) for m in (modifiers or [])],
    )

    # Use Order.__add__ to merge item into order
    # (combines quantities for duplicates, appends if new)
    updated_order = current_order + new_item

    return Command(update={
        "messages": [ToolMessage(
            f"Added {quantity}x {item_name} ({new_item.size.value})",
            tool_call_id=tool_call_id,
        )],
        "current_order": updated_order,
    })
```

**Pros:**
- Tools directly update state — no gap between "tool says added" and "order actually updated"
- Leverages `Order.__add__` to merge items into the order (quantity merging for duplicates via `Item.__add__` internally)
- Validates against actual menu item (size defaults, modifier validation)
- Pydantic validation happens at construction time
- The `ToolMessage` gives the LLM a clear confirmation

**Cons:**
- More complex tool implementation
- Tools now have side effects (state mutation) — harder to unit test in isolation
- Must remember to always include `ToolMessage` in `Command.update`

### Option 3: State + Custom Reducer

Define a custom reducer that knows how to merge order updates:

```python
def merge_order(current: Order, update: Order) -> Order:
    """Reducer that merges items from update into current using Order.__add__."""
    result = current
    for new_item in update.items:
        result = result + new_item  # Order.__add__ handles merge/append
    return result

class DriveThruState(MessagesState):
    menu: Menu
    current_order: Annotated[Order, merge_order]
```

Tools return partial `Order` objects (just the new item), and the reducer handles merging:

```python
@tool
def add_item_to_order(...) -> Command:
    new_item = Item(...)
    partial_order = Order(items=[new_item])
    return Command(update={
        "messages": [ToolMessage(...)],
        "current_order": partial_order,
    })
```

**Pros:**
- Merge logic is centralized in the reducer, not in each tool
- Tools are simpler — they just say "add this item"
- Handles parallel tool calls naturally (LLM adds 2 items at once)
- Clean separation of concerns

**Cons:**
- Need to handle `order_id` preservation in the reducer
- Reducer must handle edge cases (empty orders, first item, etc.)
- Slightly more abstract pattern

### Order Options Comparison

| Aspect | 1: State + Checkpointer | 2: Command in Tools | 3: Custom Reducer |
|--------|------------------------|--------------------|--------------------|
| **State update** | Gap — tool says "added" but doesn't update | Direct — tool updates via Command | Reducer merges partial updates |
| **Merge logic** | N/A (not implemented) | In each tool | Centralized in reducer |
| **Parallel adds** | N/A | Must handle manually | Reducer handles naturally |
| **Tool complexity** | Minimal (returns dict) | High (constructs Item, merges, returns Command) | Medium (constructs Item, returns Command) |
| **Testability** | Tools are pure functions | Tools have side effects | Tools are simpler, reducer testable separately |
| **Correctness** | Risk of drift (tool says X, state shows Y) | Guaranteed consistent | Guaranteed consistent |

---

## Chosen Approach for v1

### Menu: Option A — Full Menu in System Prompt

**For v1 with ~50 items:** Use **Option A (full menu in prompt)**. It's the simplest approach and ~50 items is manageable (~1,000 tokens per turn). The token cost is acceptable for short drive-thru conversations (3-8 turns). The LLM can answer menu questions directly without tool calls, reducing latency.

**v2 plan:** Switch to **Option B (tool-based menu retrieval)** when the menu grows beyond breakfast or token cost becomes a concern. Structure the v1 code so the menu formatting in the system prompt can be swapped out without restructuring.

### Order: Option 1 — State + Checkpointer with `update_order` Node

**Order lives in `DriveThruState.current_order`** as a plain state field. The checkpointer persists it automatically across turns.

**Tools remain pure functions** — `add_item_to_order` validates the item against the menu, constructs the response data, and returns a plain dict. It does NOT use `Command` or modify state directly. This keeps tools easy to unit test.

**Who updates `current_order`?** A dedicated **`update_order` node** sits between the tool node and the orchestrator in the graph loop. After tools execute, `update_order` scans the `ToolMessage`s for `add_item_to_order` results, constructs `Item` instances, and merges them into `current_order` using `Order.__add__`. This cleanly separates concerns:

| Component | Responsibility |
|-----------|---------------|
| **Tools** | Validate input, return structured data (pure functions) |
| **`update_order` node** | Parse tool results, construct `Item` models, update `current_order` via `Order.__add__` |
| **Checkpointer** | Persist `current_order` (and all state) between turns |
| **Orchestrator** | Read `current_order` for the system prompt, generate responses |

The graph becomes:

```
START -> orchestrator -> should_continue?
              ^                |
              |          [tool_calls?]
              |                |
              |     Yes: execute tools
              |          |
              |     update_order (process results, update current_order)
              |          |
              +----------+
                         |
                    No: respond
                         |
                        END
```

### Menu Access: InjectedState

**Use `InjectedState("menu")` in tools** so the menu is accessible for validation without the LLM needing to pass it.

### Persistence: Checkpointer

**Use `MemorySaver` for development**, plan for `PostgresSaver` in production. The checkpointer handles both menu and order persistence across turns automatically.

---

## Token Budget Analysis

Estimating token costs for a typical 5-turn conversation:

### Option A (Full Menu in Prompt)

```
Per turn:
  System prompt base:     ~200 tokens
  Menu (50 items):        ~1,000 tokens
  Current order (avg):    ~50 tokens
  Conversation history:   ~100-500 tokens (grows)
  Total per turn:         ~1,350-1,750 tokens (input)

5-turn conversation:
  Total input tokens:     ~7,500-9,000
  Total output tokens:    ~500-1,000
  Grand total:            ~8,000-10,000 tokens
```

### Option D (Hybrid Summary + Tool)

```
Per turn:
  System prompt base:     ~200 tokens
  Menu summary:           ~150 tokens
  Current order (avg):    ~50 tokens
  Conversation history:   ~100-500 tokens (grows)
  Tool results (avg):     ~100 tokens (when tool called)
  Total per turn:         ~600-1,000 tokens (input)

5-turn conversation:
  Total input tokens:     ~4,000-5,500
  + Extra loop iterations: ~1,000 (tool calls for menu questions)
  Grand total:            ~5,000-7,000 tokens
```

**Savings with Option D:** ~30-40% fewer input tokens. For gpt-4o-mini at current pricing, this is a modest cost difference per conversation but adds up at scale.

**Verdict for v1:** The difference is ~3,000-4,000 tokens per conversation. With gpt-4o-mini pricing, this is negligible for development. **v1 uses Option A.** Switch to Option B (tool-based) in v2 if cost matters at scale or the menu grows beyond breakfast.

---

## Implementation Sketch

Here's how the chosen approach (Option A menu + Option 1 order with `update_order` node) looks in code:

```python
import json
from typing import Annotated
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool, InjectedState
from langchain_core.messages import ToolMessage
from orchestrator.models import Order, Item, Modifier, Menu
from orchestrator.enums import Size, CategoryName


# --- State (no custom reducer needed) ---

class DriveThruState(MessagesState):
    menu: Menu
    current_order: Order  # Plain state field — checkpointer persists it


# --- Tools (pure functions — return dicts, no Command/state mutation) ---

@tool
def lookup_menu_item(
    item_name: str,
    menu: Annotated[Menu, InjectedState("menu")],
) -> dict:
    """Look up a menu item by name. Use this BEFORE adding any item."""
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
    # ... fuzzy matching / suggestions ...
    return {"found": False, "requested": item_name, "suggestions": []}


@tool
def add_item_to_order(
    item_id: str,
    item_name: str,
    category_name: str,
    quantity: int = 1,
    size: str | None = None,
    modifiers: list[dict] | None = None,
    menu: Annotated[Menu, InjectedState("menu")],
) -> dict:
    """Add an item to the customer's order. Returns item data for state update."""
    # Validate against menu
    menu_item = next((i for i in menu.items if i.item_id == item_id), None)
    if not menu_item:
        return {"added": False, "error": f"Item '{item_id}' not found on menu."}

    # Validate modifiers against available_modifiers
    valid_modifier_ids = {m.modifier_id for m in menu_item.available_modifiers}
    for mod in (modifiers or []):
        if mod.get("modifier_id") not in valid_modifier_ids:
            return {"added": False, "error": f"Modifier '{mod.get('name')}' not available for {item_name}."}

    resolved_size = size or menu_item.default_size.value

    return {
        "added": True,
        "item_id": item_id,
        "item_name": item_name,
        "category_name": category_name,
        "quantity": quantity,
        "size": resolved_size,
        "modifiers": modifiers or [],
    }


@tool
def get_current_order(
    state: Annotated[dict, InjectedState],
) -> dict:
    """Get the current order summary."""
    order = state["current_order"]
    return {
        "order_id": order.order_id,
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "size": item.size.value if item.size else "default",
                "modifiers": [m.name for m in item.modifiers],
            }
            for item in order.items
        ],
        "item_count": sum(item.quantity for item in order.items),
    }


@tool
def finalize_order(
    state: Annotated[dict, InjectedState],
) -> dict:
    """Finalize and submit the order."""
    order = state["current_order"]
    return {
        "finalized": True,
        "order_id": order.order_id,
        "message": "Order has been submitted.",
    }


# --- update_order Node (bridges tool results → state) ---

def update_order(state: DriveThruState) -> dict:
    """Process tool results and update current_order.

    Scans the latest ToolMessages for add_item_to_order results.
    Constructs Item instances and merges into current_order via Order.__add__.
    """
    current_order = state["current_order"]
    menu = state["menu"]

    for msg in state["messages"]:
        if not isinstance(msg, ToolMessage):
            continue
        if msg.name != "add_item_to_order":
            continue

        # Parse tool result
        result = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        if not result.get("added"):
            continue

        # Find menu item for defaults
        menu_item = next(
            (i for i in menu.items if i.item_id == result["item_id"]), None
        )
        if not menu_item:
            continue

        # Construct Item and merge into order via Order.__add__
        new_item = Item(
            item_id=result["item_id"],
            name=result["item_name"],
            category_name=CategoryName(result["category_name"]),
            default_size=menu_item.default_size,
            size=Size(result["size"]) if result.get("size") else None,
            quantity=result["quantity"],
            modifiers=[Modifier(**m) for m in result.get("modifiers", [])],
        )
        current_order = current_order + new_item

    return {"current_order": current_order}


# --- Graph Construction ---

tools = [lookup_menu_item, add_item_to_order, get_current_order, finalize_order]
tool_node = ToolNode(tools)

builder = StateGraph(DriveThruState)
builder.add_node("orchestrator", orchestrator_node)  # LLM reasoning
builder.add_node("tools", tool_node)                  # Execute tool calls
builder.add_node("update_order", update_order)         # Process results → state

builder.add_edge(START, "orchestrator")
builder.add_conditional_edges(
    "orchestrator",
    should_continue,
    {"tools": "tools", "respond": END, "end": END},
)
builder.add_edge("tools", "update_order")              # tools → update_order
builder.add_edge("update_order", "orchestrator")       # update_order → orchestrator

from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

### Why `update_order` instead of `Command`?

| Aspect | Option 1 (`update_order` node) | Option 2 (`Command` in tools) |
|--------|-------------------------------|------------------------------|
| **Tools** | Pure functions — return dicts | Side effects — return `Command` with state updates |
| **Unit testing** | Easy — tools have no state dependencies beyond `InjectedState` reads | Harder — must mock `InjectedToolCallId`, assert `Command` structure |
| **State update logic** | Centralized in `update_order` | Spread across each tool |
| **Debugging** | Tool results visible in messages before state changes | State changes happen atomically with tool execution |
| **Graph complexity** | 4 nodes (still simple) | 3 nodes |

For v1, the simplicity of pure-function tools and centralized state updates outweighs the extra node.

---

## Future Scaling Considerations

| Concern | When it matters | Solution |
|---------|----------------|----------|
| **Menu > 75 items** | Multi-category menu (breakfast + lunch) | Switch to Option D (summary + tool) |
| **Menu > 500 items** | Full McDonald's menu or multi-restaurant | Option B (tool-only) + semantic search |
| **Conversation > 20 turns** | Complex orders, frequent changes | Message summarization / trimming |
| **Multi-location menus** | Different items per restaurant | Menu loaded per-location at init, keyed by `Menu.location.id` |
| **Menu changes mid-day** | Lunch menu replaces breakfast | Reload menu in state; consider Runtime Context to avoid re-checkpointing |
| **High throughput** | Many concurrent conversations | `PostgresSaver` + connection pooling |
| **Order modifications** | Remove/modify items (v2) | `remove_item_from_order` tool + new reducer logic |

---

## Summary

| Decision | v1 Choice | v2 Direction | Rationale |
|----------|-----------|-------------|-----------|
| **Menu storage** | Option A — full menu in system prompt | Option B — tool-based retrieval | ~50 items is manageable (~1,000 tokens); simplest implementation |
| **Menu accessible to tools?** | Via `InjectedState("menu")` | Same | Tools validate against menu without LLM passing it |
| **Order persistence** | Option 1 — `DriveThruState.current_order` + Checkpointer | Same | Automatic multi-turn persistence; simplest mental model |
| **Who updates `current_order`?** | `update_order` node (between tools and orchestrator) | Consider `Command` if tools need direct state writes | Tools stay pure functions; state updates are centralized and testable |
| **Graph nodes** | 4 — orchestrator, tools, update_order, should_continue | Same or +1 for remove/modify | Still much simpler than v0's 12+ nodes |
| **Checkpointer** | `MemorySaver` (dev) / `PostgresSaver` (prod) | Same | Standard LangGraph pattern |
| **Store** | Not used in v1 | Evaluate for user preferences | Menu is static reference data, not per-user memory |
