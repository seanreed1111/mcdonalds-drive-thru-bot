# Phase 2: Tools

<- [Back to Main Plan](./README.md)

## Table of Contents

- [Overview](#overview)
- [Context](#context)
- [Dependencies](#dependencies)
- [Changes Required](#changes-required)
- [Success Criteria](#success-criteria)

## Overview

Create `tools.py` with 4 tool functions: `lookup_menu_item`, `add_item_to_order`, `get_current_order`, and `finalize_order`. All tools are **pure functions** that return dicts. They access state via `InjectedState` for reading menu and order data but do NOT modify state (no `Command` pattern).

## Context

Before starting, read these files:
- `src/orchestrator/orchestrator/models.py` — Item, Modifier, Order, Menu models and their fields
- `src/orchestrator/orchestrator/enums.py` — Size, CategoryName StrEnums
- `src/orchestrator/orchestrator/__init__.py` — Verify exports (created in Phase 1)
- `docs/thoughts/target-implementation/v1/langgraph-state-design-v1.md` — Tool definitions section (lines 195-365)
- `docs/thoughts/target-implementation/v1/context-and-state-management-v1.md` — Implementation sketch section (lines 719-899)

## Dependencies

**Depends on:** Phase 1 (Foundation)
**Required by:** Phase 3 (Graph)

## Changes Required

### 2.1: Create `tools.py`
**File:** `src/orchestrator/orchestrator/tools.py`
**Action:** CREATE

**What this does:** Implements 4 LangChain tools that the orchestrator LLM can call. Each tool uses `InjectedState` to read menu/order data from graph state without the LLM passing it. Tools return plain dicts — state mutation happens in the `update_order` node (Phase 3).

```python
"""Drive-thru orchestrator tools.

All tools are pure functions that return dicts. They read state via
InjectedState but do NOT modify state — the update_order node handles that.
"""

from typing import Annotated

from langchain_core.tools import InjectedState, tool
from loguru import logger

from .models import Menu


@tool
def lookup_menu_item(
    item_name: str,
    menu: Annotated[Menu, InjectedState("menu")],
) -> dict:
    """Look up a menu item by name. Use this BEFORE adding any item to the
    order to verify it exists on the menu. Returns the matched item details
    including category, default size, and available modifiers. If no exact
    match is found, returns up to 3 suggestions for similar items.

    You MUST call this tool before calling add_item_to_order. Never skip
    this step.

    Args:
        item_name: The item name as spoken by the customer.
    """
    logger.info("Looking up menu item: {}", item_name)

    # Exact match (case-insensitive)
    for item in menu.items:
        if item.name.lower() == item_name.lower():
            logger.info("Found exact match: {} ({})", item.name, item.item_id)
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

    # No exact match — suggest similar items (substring match)
    suggestions = [
        item.name
        for item in menu.items
        if item_name.lower() in item.name.lower()
        or item.name.lower() in item_name.lower()
    ]

    logger.warning("No exact match for '{}', suggestions: {}", item_name, suggestions[:3])
    return {
        "found": False,
        "requested": item_name,
        "suggestions": suggestions[:3]
        if suggestions
        else ["Check our menu for available items"],
    }


@tool
def add_item_to_order(
    item_id: str,
    item_name: str,
    category_name: str,
    quantity: int = 1,
    size: str | None = None,
    modifiers: list[dict] | None = None,
    menu: Annotated[Menu, InjectedState("menu")] = None,
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
    logger.info("Adding item to order: {} (id={}, qty={})", item_name, item_id, quantity)

    # Validate item exists on menu
    menu_item = next((i for i in menu.items if i.item_id == item_id), None)
    if not menu_item:
        logger.warning("Item not found on menu: {}", item_id)
        return {"added": False, "error": f"Item '{item_id}' not found on menu."}

    # Validate modifiers against available_modifiers
    valid_modifier_ids = {m.modifier_id for m in menu_item.available_modifiers}
    for mod in modifiers or []:
        if mod.get("modifier_id") not in valid_modifier_ids:
            logger.warning("Invalid modifier '{}' for item {}", mod.get("name"), item_name)
            return {
                "added": False,
                "error": f"Modifier '{mod.get('name')}' not available for {item_name}.",
            }

    # Resolve size: use provided size or fall back to item's default
    resolved_size = size or menu_item.default_size.value

    logger.info("Item added successfully: {}x {} (size={})", quantity, item_name, resolved_size)
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
    """Get the current order summary. Use this when:
    - The customer asks "what did I order?" or "can you read that back?"
    - You are about to finalize the order and want to confirm with the customer.

    Returns the order ID, list of items with quantities and sizes, and total
    item count. Note: prices are not available — do not quote a total.
    """
    order = state["current_order"]
    item_count = sum(item.quantity for item in order.items)
    logger.info("Getting current order: {} ({} items)", order.order_id, item_count)
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
        "item_count": item_count,
    }


@tool
def finalize_order(
    state: Annotated[dict, InjectedState],
) -> dict:
    """Finalize and submit the order. Call this ONLY when:
    1. The customer has explicitly said they are done ordering.
    2. You have read back the complete order to the customer using
       get_current_order.
    3. The customer has confirmed the order is correct.

    Do NOT call this if the customer is still adding items or hasn't
    confirmed. After calling this, thank the customer and end the
    conversation.
    """
    order = state["current_order"]
    logger.info("Finalizing order: {} ({} items)", order.order_id, len(order.items))
    return {
        "finalized": True,
        "order_id": order.order_id,
        "message": "Order has been submitted.",
    }
```

**Key design decisions:**
- `menu` parameter on `lookup_menu_item` and `add_item_to_order` uses `Annotated[Menu, InjectedState("menu")]` — this injects the menu from graph state without the LLM needing to pass it.
- `get_current_order` and `finalize_order` use `Annotated[dict, InjectedState]` to access the full state dict (they need `current_order` which isn't a top-level injectable field in the same way).
- Tool docstrings are critical — they instruct the LLM on when/how to call each tool.
- `add_item_to_order` validates against the menu (checks item exists, validates modifiers) before returning success.

### 2.2: Update `__init__.py` to export tools
**File:** `src/orchestrator/orchestrator/__init__.py`
**Action:** MODIFY

**What this does:** Adds tool exports so they're accessible via `from orchestrator.tools import ...`.

**Before:**
```python
"""McDonald's Drive-Thru Orchestrator — LLM Orchestrator Pattern (v1)."""

from .enums import CategoryName, Size
from .models import Item, Location, Menu, Modifier, Order

__all__ = [
    "CategoryName",
    "Item",
    "Location",
    "Menu",
    "Modifier",
    "Order",
    "Size",
]
```

**After:**
```python
"""McDonald's Drive-Thru Orchestrator — LLM Orchestrator Pattern (v1)."""

from .enums import CategoryName, Size
from .models import Item, Location, Menu, Modifier, Order
from .tools import (
    add_item_to_order,
    finalize_order,
    get_current_order,
    lookup_menu_item,
)

__all__ = [
    "CategoryName",
    "Item",
    "Location",
    "Menu",
    "Modifier",
    "Order",
    "Size",
    "add_item_to_order",
    "finalize_order",
    "get_current_order",
    "lookup_menu_item",
]
```

## Success Criteria

### Automated Verification:
- [ ] File exists: `src/orchestrator/orchestrator/tools.py`
- [ ] Python can import tools: `uv run --package orchestrator python -c "from orchestrator.tools import lookup_menu_item, add_item_to_order, get_current_order, finalize_order; print('OK')"`
- [ ] Ruff passes: `uv run ruff check src/orchestrator/orchestrator/tools.py`

---

<- [Back to Main Plan](./README.md)
