"""Smoke tests for the orchestrator graph.

These tests verify that the graph compiles, tools work with mock data,
and state management is correct. No LLM API calls are made.
"""

import json

from langchain_core.messages import AIMessage, ToolMessage

from orchestrator.graph import DriveThruState, _extract_reasoning, graph, update_order
from orchestrator.models import Menu, Order
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
            content=json.dumps({"added": False, "error": "Item not found"}),
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
            content=json.dumps({"order_id": "abc", "items": [], "item_count": 0}),
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


class TestReasoning:
    """Test reasoning extraction and formatting."""

    def test_extract_reasoning_with_tags(self):
        """_extract_reasoning should extract text from <reasoning> tags."""
        content = "<reasoning>Looking up the item first.</reasoning>Sure, let me check that for you."
        reasoning, cleaned = _extract_reasoning(content)
        assert reasoning == "Looking up the item first."
        assert cleaned == "Sure, let me check that for you."

    def test_extract_reasoning_without_tags(self):
        """_extract_reasoning should return empty string when no tags present."""
        content = "Sure, let me check that for you."
        reasoning, cleaned = _extract_reasoning(content)
        assert reasoning == ""
        assert cleaned == "Sure, let me check that for you."

    def test_extract_reasoning_multiline(self):
        """_extract_reasoning should handle multiline reasoning."""
        content = (
            "<reasoning>Customer wants two items.\nNeed to look up both.</reasoning>OK!"
        )
        reasoning, cleaned = _extract_reasoning(content)
        assert "Customer wants two items." in reasoning
        assert "Need to look up both." in reasoning
        assert cleaned == "OK!"

    def test_extract_reasoning_empty_content(self):
        """_extract_reasoning should handle empty string."""
        reasoning, cleaned = _extract_reasoning("")
        assert reasoning == ""
        assert cleaned == ""

    def test_state_reasoning_field_defaults_empty(self, menu, empty_order):
        """DriveThruState reasoning field should accept empty list."""
        state = DriveThruState(
            messages=[],
            menu=menu,
            current_order=empty_order,
            reasoning=[],
        )
        assert state["reasoning"] == []

    def test_state_reasoning_field_accumulates(self, menu, empty_order):
        """DriveThruState reasoning field should be a list of strings."""
        state = DriveThruState(
            messages=[],
            menu=menu,
            current_order=empty_order,
            reasoning=["[DIRECT] Greeting the customer."],
        )
        assert len(state["reasoning"]) == 1
        assert state["reasoning"][0].startswith("[DIRECT]")
