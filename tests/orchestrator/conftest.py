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
