# Phase 5: Smoke Test + Test Ideas

<- [Back to Main Plan](./README.md)

## Table of Contents

- [Overview](#overview)
- [Context](#context)
- [Dependencies](#dependencies)
- [Changes Required](#changes-required)
- [Success Criteria](#success-criteria)

## Overview

Create a minimal smoke test that verifies the graph compiles and the tools work correctly with mock data (no LLM API calls required). Also create a testing ideas document outlining what comprehensive tests would look like for v2.

## Context

Before starting, read these files:
- `src/orchestrator/orchestrator/graph.py` — The compiled graph and `DriveThruState`
- `src/orchestrator/orchestrator/tools.py` — All 4 tool functions
- `src/orchestrator/orchestrator/models.py` — Menu, Order, Item models and `from_json_file()`
- `src/orchestrator/pyproject.toml` — Verify `pytest` is in dev dependencies
- `menus/mcdonalds/breakfast-menu/json/breakfast-v2.json` — Menu data for fixtures

## Dependencies

**Depends on:** Phase 4 (CLI + Langfuse)
**Required by:** None (final phase)

## Changes Required

### 5.1a: Create parent test package init
**File:** `tests/__init__.py`
**Action:** CREATE

**What this does:** Creates the parent test package directory so pytest can discover nested test packages.

```python
```

(Empty file — just needs to exist for pytest discovery.)

### 5.1b: Create test sub-package init
**File:** `tests/orchestrator/__init__.py`
**Action:** CREATE

**What this does:** Creates the orchestrator test sub-package directory so pytest discovers tests.

```python
```

(Empty file — just needs to exist for pytest discovery.)

### 5.2: Create `conftest.py` with fixtures
**File:** `tests/orchestrator/conftest.py`
**Action:** CREATE

**What this does:** Provides pytest fixtures for a loaded `Menu` and an empty `Order`, reusable across all tests.

```python
"""Shared pytest fixtures for orchestrator tests."""

from pathlib import Path

import pytest

from orchestrator.models import Menu, Order

# Path to the breakfast menu JSON relative to project root
MENU_JSON_PATH = (
    Path(__file__).resolve().parents[2]
    / "menus"
    / "mcdonalds"
    / "breakfast-menu"
    / "json"
    / "breakfast-v2.json"
)


@pytest.fixture
def menu() -> Menu:
    """Load the breakfast menu from JSON."""
    return Menu.from_json_file(MENU_JSON_PATH)


@pytest.fixture
def empty_order() -> Order:
    """Create a fresh empty order."""
    return Order()
```

### 5.3: Create `test_smoke.py`
**File:** `tests/orchestrator/test_smoke.py`
**Action:** CREATE

**What this does:** Smoke tests that verify:
1. The graph compiles and has expected nodes
2. The `DriveThruState` schema is correct
3. Tools can be called directly with mock state (no LLM)
4. The `update_order` node processes tool results correctly
5. Menu loads correctly from JSON

These tests do NOT call the LLM API — they test the deterministic parts only.

```python
"""Smoke tests for the orchestrator graph.

These tests verify that the graph compiles, tools work with mock data,
and state management is correct. No LLM API calls are made.
"""

import json

from langchain_core.messages import AIMessage, ToolMessage

from orchestrator.graph import DriveThruState, graph, update_order, should_end_after_update
from orchestrator.models import Item, Menu, Order
from orchestrator.enums import CategoryName, Size


class TestGraphCompiles:
    """Verify the graph compiles and has the expected structure."""

    def test_graph_is_compiled(self):
        """Graph should be a compiled StateGraph."""
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Graph should have orchestrator, tools, and update_order nodes."""
        node_names = set(graph.get_graph().nodes)
        # LangGraph adds __start__ and __end__ nodes automatically
        assert "orchestrator" in node_names
        assert "tools" in node_names
        assert "update_order" in node_names


class TestMenuLoads:
    """Verify menu data loads correctly."""

    def test_menu_loads_from_json(self, menu: Menu):
        """Menu should load from the breakfast JSON file."""
        assert menu.menu_id == "mcd-breakfast-menu"
        assert menu.menu_name == "McDonald's Breakfast Menu"
        assert len(menu.items) > 0

    def test_menu_has_location(self, menu: Menu):
        """Menu should have location data."""
        assert menu.location.name is not None
        assert menu.location.address is not None

    def test_menu_items_have_required_fields(self, menu: Menu):
        """Each menu item should have id, name, category, and default_size."""
        for item in menu.items:
            assert item.item_id
            assert item.name
            assert isinstance(item.category_name, CategoryName)
            assert isinstance(item.default_size, Size)


class TestUpdateOrderNode:
    """Test the update_order node processes tool results correctly."""

    def test_update_order_with_add_result(self, menu: Menu, empty_order: Order):
        """update_order should construct Item and merge into order."""
        # Find a real item from the menu
        menu_item = menu.items[0]

        # Simulate the state after tools execute: an AIMessage with tool_calls
        # followed by a ToolMessage with the add_item_to_order result
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_123",
                    "name": "add_item_to_order",
                    "args": {
                        "item_id": menu_item.item_id,
                        "item_name": menu_item.name,
                        "category_name": menu_item.category_name.value,
                        "quantity": 2,
                    },
                }
            ],
        )
        tool_msg = ToolMessage(
            content=json.dumps(
                {
                    "added": True,
                    "item_id": menu_item.item_id,
                    "item_name": menu_item.name,
                    "category_name": menu_item.category_name.value,
                    "quantity": 2,
                    "size": menu_item.default_size.value,
                    "modifiers": [],
                }
            ),
            name="add_item_to_order",
            tool_call_id="call_123",
        )

        state = DriveThruState(
            messages=[ai_msg, tool_msg],
            menu=menu,
            current_order=empty_order,
        )

        result = update_order(state)
        updated_order = result["current_order"]

        assert len(updated_order.items) == 1
        assert updated_order.items[0].name == menu_item.name
        assert updated_order.items[0].quantity == 2

    def test_update_order_ignores_failed_adds(self, menu: Menu, empty_order: Order):
        """update_order should skip tool results where added=False."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_456",
                    "name": "add_item_to_order",
                    "args": {"item_id": "nonexistent"},
                }
            ],
        )
        tool_msg = ToolMessage(
            content=json.dumps(
                {"added": False, "error": "Item not found"}
            ),
            name="add_item_to_order",
            tool_call_id="call_456",
        )

        state = DriveThruState(
            messages=[ai_msg, tool_msg],
            menu=menu,
            current_order=empty_order,
        )

        result = update_order(state)
        assert len(result["current_order"].items) == 0

    def test_update_order_ignores_non_add_tools(self, menu: Menu, empty_order: Order):
        """update_order should ignore ToolMessages from other tools."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_789",
                    "name": "get_current_order",
                    "args": {},
                }
            ],
        )
        tool_msg = ToolMessage(
            content=json.dumps(
                {"order_id": "abc", "items": [], "item_count": 0}
            ),
            name="get_current_order",
            tool_call_id="call_789",
        )

        state = DriveThruState(
            messages=[ai_msg, tool_msg],
            menu=menu,
            current_order=empty_order,
        )

        result = update_order(state)
        assert len(result["current_order"].items) == 0
```

### 5.4: Create testing ideas document
**File:** `docs/thoughts/target-implementation/v1/testing-ideas-v1.md`
**Action:** CREATE

**What this does:** Documents comprehensive testing ideas for v2 — unit tests for each tool, integration tests with LLM, and end-to-end conversation tests.

```markdown
# Testing Ideas for v1 Orchestrator

> **Status:** Ideas for future implementation. The current v1 has a smoke test only.
> **See also:** [v1 State Design](./langgraph-state-design-v1.md)

## Current Tests (v1)

- `tests/orchestrator/test_smoke.py` — Graph compiles, tools work with mock data, update_order processes results correctly. No LLM API calls.

## Future Test Ideas

### Unit Tests for Tools (no LLM needed)

These test each tool function directly with mock `InjectedState`:

1. **`lookup_menu_item`**
   - Exact match (case-insensitive): "Egg McMuffin" → found=True
   - No match: "Big Mac" → found=False with suggestions
   - Partial match suggestions: "McMuffin" → suggestions include Egg McMuffin, Sausage McMuffin
   - Empty menu → found=False
   - Returns correct `available_modifiers` structure

2. **`add_item_to_order`**
   - Valid item → added=True with correct fields
   - Invalid item_id → added=False with error
   - Invalid modifier → added=False with error
   - Size resolution: explicit size used, None falls back to default
   - Quantity validation: quantity=0 should fail (Pydantic ge=1)

3. **`get_current_order`**
   - Empty order → item_count=0
   - Order with items → correct serialization (name, qty, size, modifiers)
   - Order preserves order_id

4. **`finalize_order`**
   - Returns finalized=True with order_id
   - Order_id matches the state's current_order

### Unit Tests for `update_order` Node

5. **State mutation**
   - Single add → order has 1 item
   - Multiple adds in one turn → order has N items
   - Duplicate add → quantities merge (2+1=3)
   - Add with modifiers → modifiers preserved on item
   - Failed add (added=False) → order unchanged
   - Non-add tool messages → order unchanged

6. **Message scanning**
   - Only processes messages after the last AIMessage
   - Does not re-process old add results from previous turns

### Integration Tests (requires LLM API)

7. **Single-turn ordering**
   - "I'd like an Egg McMuffin" → calls lookup then add, responds with confirmation
   - "What do you have?" → responds with menu items, no tool calls

8. **Multi-intent**
   - "Two hash browns and a large coffee" → two lookups, two adds

9. **Item not found**
   - "Big Mac" → lookup returns not found, suggests alternatives

10. **Order flow**
    - Full conversation: greet → order → read back → confirm → finalize
    - Verify finalize_order is only called after confirmation

11. **Edge cases**
    - Customer asks about prices → "total will be at the window"
    - Customer asks to remove item → "can only add items right now"
    - Customer orders with invalid modifier → polite rejection

### End-to-End Conversation Tests

12. **Happy path**: Greet → order 2 items → "that's all" → read back → "yes" → finalize
13. **Menu browsing**: Ask about categories → order from suggestion
14. **Multi-turn with corrections**: Order item → "actually make that two" → finalize

### Langfuse Trace Verification

15. **Trace structure**: Each turn produces a trace with orchestrator + tool spans
16. **Tool inputs/outputs**: Tool call args and results are visible in traces
17. **Token usage**: Token counts are tracked per turn
```

## Success Criteria

### Automated Verification:
- [ ] File exists: `tests/__init__.py`
- [ ] Test directory exists: `tests/orchestrator/`
- [ ] All smoke tests pass: `uv run --package orchestrator pytest tests/orchestrator/test_smoke.py -v`
- [ ] Ruff passes: `uv run ruff check tests/orchestrator/`
- [ ] Testing ideas doc exists: `docs/thoughts/target-implementation/v1/testing-ideas-v1.md`

---

<- [Back to Main Plan](./README.md)
