# McDonald's Breakfast Menu Data Model

Pydantic v2 data models for a McDonald's breakfast menu drive-thru voice ordering system.

## Tech Stack

- Python 3.12+
- Pydantic v2 for data validation
- uv for package management

## Project Structure

```
src/models.py      # Pydantic models (Item, Modifier, Order, Menu)
src/enums.py       # Enums (Size, CategoryName)
menus/             # Menu data (raw CSV, transformed JSON)
thoughts/          # Design notes and requirements
```

## Getting Started

```bash
uv sync            # Install dependencies
uv run python      # Run Python with project dependencies
```

## Models Overview

- `Size` - StrEnum: snack, small, medium, large
- `CategoryName` - Menu category (breakfast, beverages, coffee-tea, etc.)
- `Item` - Individual menu item with modifiers
- `Modifier` - Item variations (Extra Cheese, No Onions, etc.)
- `Order` - Collection of items for a customer order
- `Menu` - Full menu with items
