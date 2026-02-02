# McDonald's Data Model

Pydantic v2 data models for a McDonald's voice ordering system.

## Tech Stack

- Python 3.12+
- Pydantic v2 for data validation
- uv for package management

## Project Structure

```
src/models.py      # Pydantic models (Size, Category, Item, Modifier, Combo, Menu)
menus/             # Menu data (raw CSV, transformed JSON)
thoughts/          # Design notes and requirements
```

## Commands

```bash
uv sync            # Install dependencies
uv run python      # Run Python with project dependencies
```

## Models Overview

- `Size` - StrEnum: snack, small, medium, large
- `Category` - Menu category (Breakfast, Beef & Pork, etc.)
- `Item` - Individual menu item with modifiers, default size is medium
- `Modifier` - Item variations (Extra Cheese, No Onions, etc.)
- `Combo` - Collection of items
- `Menu` - Full menu with allowed categories
