# LangGraph Drive-Thru Bot: State Design (v1 — LLM Orchestrator Pattern)

> **v1 Change from v0:** Replaces the explicit state machine (12+ nodes, intent routing, conditional edges) with an **LLM orchestrator pattern** — a single reasoning node with tool-calling that dramatically simplifies the graph.

> **v1 Scope:** Same as v0 — customers can only **add items** to their order. Remove and modify functionality will be added in future versions.

> **v1 Interface:** Chatbot (text-only). Same as v0.

> **Related Documents:**
> - [v0 State Design](../langgraph-state-design-v0.md) — Previous explicit state machine approach
> - [v1 State Diagrams](./langgraph-state-diagrams-v1.md) — Visual diagrams for this design

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
| **Graph nodes** | 12+ (load_menu, greet, await_input, parse_intent, parse_item, validate, add_item, reject_item, success_response, read_order, clarify, confirm_order, thank) | 3 (orchestrator, tools, end check) |
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

The entire graph is three conceptual steps in a loop:

```
START --> orchestrator --> should_continue?
              ^                |
              |          [tool_calls?]
              |                |
              |     Yes: execute tools
              |          |
              +----------+
                         |
                    No: respond
                         |
                        END
```

The `orchestrator` node is an LLM with tools bound. LangGraph's prebuilt `ToolNode` handles tool execution. The `should_continue` conditional edge checks whether the LLM wants to call more tools or is done responding.

---

## LangGraph State Schema

The state is dramatically simpler than v0:

```python
from typing import Annotated
from langgraph.graph import MessagesState
from models import Order, Menu


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

---

## Tool Definitions

Tools are where the **determinism lives**. The LLM decides *when* to call them, but the tools themselves are pure functions with predictable behavior.

### lookup_menu_item

Searches the menu for an item. Returns match information without modifying state.

```python
from langchain_core.tools import tool
from models import Menu


@tool
def lookup_menu_item(item_name: str, menu: Menu) -> dict:
    """Look up a menu item by name. Use this before adding items to verify
    they exist on the menu. Returns the matched item details or suggestions
    if no exact match is found.

    Args:
        item_name: The item name as spoken by the customer.
        menu: The current location's menu.
    """
    # Exact match (case-insensitive)
    for item in menu.items:
        if item.name.lower() == item_name.lower():
            return {
                "found": True,
                "item_id": item.item_id,
                "name": item.name,
                "price": item.price,
                "available_sizes": [s.value for s in item.available_sizes],
                "available_modifiers": [m.name for m in item.available_modifiers],
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

### add_item_to_order

Adds a validated item to the current order.

```python
from langchain_core.tools import tool
from models import Order, Item, Size


@tool
def add_item_to_order(
    item_name: str,
    quantity: int = 1,
    size: str | None = None,
    modifiers: list[str] | None = None,
) -> dict:
    """Add an item to the customer's order. Only call this after confirming
    the item exists via lookup_menu_item.

    Args:
        item_name: Exact menu item name (use the name from lookup_menu_item).
        quantity: Number of this item (default 1).
        size: Size if applicable (snack, small, medium, large).
        modifiers: List of modifications (e.g., "no onions", "extra cheese").
    """
    # Implementation adds to state's current_order
    return {
        "added": True,
        "item_name": item_name,
        "quantity": quantity,
        "size": size or "medium",
        "modifiers": modifiers or [],
    }
```

### get_current_order

Reads back the current order state.

```python
@tool
def get_current_order() -> dict:
    """Get the current order summary. Use this when the customer asks
    what they've ordered so far, or before finalizing."""
    # Implementation reads from state's current_order
    return {
        "items": [],  # populated from state
        "item_count": 0,
        "total_price": 0.0,
    }
```

### finalize_order

Marks the order as complete and triggers the end of the conversation.

```python
@tool
def finalize_order() -> dict:
    """Finalize the order. Call this when the customer says they're done
    ordering and you've confirmed their complete order with them."""
    return {
        "finalized": True,
        "message": "Order has been submitted.",
    }
```

---

## Orchestrator Node Implementation

The orchestrator is a single LLM node with tools bound and a system prompt that defines its role:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

tools = [lookup_menu_item, add_item_to_order, get_current_order, finalize_order]

orchestrator_llm = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are a friendly McDonald's drive-thru assistant taking breakfast orders.

CURRENT MENU:
{menu_items}

CURRENT ORDER:
{current_order}

INSTRUCTIONS:
- Greet the customer warmly when the conversation starts.
- When a customer orders an item, ALWAYS use lookup_menu_item first to verify it exists.
- Only use add_item_to_order for items confirmed to exist on the menu.
- If an item isn't found, politely let the customer know and suggest alternatives from the lookup results.
- When the customer says they're done, read back their complete order for confirmation, then call finalize_order.
- Keep responses concise and friendly — this is a drive-thru, not a sit-down restaurant.
- If the customer asks a question about the menu, answer from the menu context provided.
- Handle multiple items in a single request naturally.
"""


def orchestrator_node(state: DriveThruState) -> dict:
    """The central orchestrator node. Reasons about the conversation
    and decides what tools to call."""
    menu_items = "\n".join(
        f"- {item.name} (${item.price:.2f})" for item in state["menu"].items
    )
    current_items = "\n".join(
        f"- {item.quantity}x {item.name}" for item in state["current_order"].items
    ) or "Empty"

    system_message = SYSTEM_PROMPT.format(
        menu_items=menu_items,
        current_order=current_items,
    )

    messages = [{"role": "system", "content": system_message}] + state["messages"]
    response = orchestrator_llm.invoke(messages)

    return {"messages": [response]}
```

---

## Graph Construction

The full graph in LangGraph:

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode


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


# Build the graph
tool_node = ToolNode(tools)

builder = StateGraph(DriveThruState)
builder.add_node("orchestrator", orchestrator_node)
builder.add_node("tools", tool_node)

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
builder.add_edge("tools", "orchestrator")

graph = builder.compile()
```

That's the entire graph. Compare this to v0's 12+ nodes and multiple conditional edges.

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
  → "Your order is one Egg McMuffin for $4.49. Have a great day!"
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

tools: lookup_menu_item returns {found: True, name: "Egg McMuffin", ...}

orchestrator (reasoning):
  - Item exists, customer wants 1 (default quantity)
  - Call add_item_to_order(item_name="Egg McMuffin", quantity=1)

tools: add_item_to_order returns {added: True, ...}

orchestrator (response):
  "Hi there! I've got one Egg McMuffin for you. Anything else?"
```

### Multi-Intent Utterance

Customer: *"Two hash browns and a large coffee. What's the cheapest sandwich you have?"*

```
orchestrator (reasoning):
  - Customer wants 2 hash browns, 1 large coffee, and has a question
  - Call lookup_menu_item("hash brown")
  - Call lookup_menu_item("coffee")

tools: both return {found: True, ...}

orchestrator (reasoning):
  - Both items exist
  - Call add_item_to_order("Hash Brown", quantity=2)
  - Call add_item_to_order("Coffee", quantity=1, size="large")

tools: both return {added: True, ...}

orchestrator (response):
  "Got it — two hash browns and a large coffee! As for our cheapest
   sandwich, that'd be the Sausage McMuffin at $3.29. Want to add one?"
```

Notice how the orchestrator handled three different "intents" in a single turn without any routing logic.

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

1. **Tools should be deterministic** — All business logic (menu matching, validation, price calculation) lives in tools, not in the LLM's reasoning.
2. **Tools should be idempotent where possible** — Calling `lookup_menu_item` twice for the same item should return the same result.
3. **Tool descriptions matter** — The LLM decides which tool to call based on the description. Be precise about when each tool should be used.
4. **Return structured data from tools** — Give the LLM clear data to reason about in subsequent turns.

### System Prompt

1. **Include the full menu** — The orchestrator needs menu context to answer questions and guide the customer.
2. **Include the current order** — So the orchestrator knows what's already been ordered.
3. **Be explicit about the workflow** — "ALWAYS use lookup_menu_item before add_item_to_order" prevents the LLM from skipping validation.
4. **Set the tone** — "concise and friendly" keeps responses appropriate for a drive-thru.

### Persistence

Same as v0 — use LangGraph's checkpointer for multi-turn conversations:

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# Each conversation gets a thread_id
config = {"configurable": {"thread_id": "drive-thru-session-123"}}
```

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
- **Tool call inputs/outputs** — exactly what the orchestrator asked for and got back
- **LLM reasoning** visible in the orchestrator span
- **Token usage and cost** per turn

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
- Add `get_menu_by_category` tool for browsing
- Consider structured output for the final response if brand consistency requires it
- Evaluate whether a hybrid approach (orchestrator + one guard-rail node) is needed
