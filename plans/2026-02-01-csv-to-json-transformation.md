# CSV to JSON Transformation Plan

> **Status:** DRAFT

## Table of Contents

- [Overview](#overview)
- [Current State Analysis](#current-state-analysis)
- [Desired End State](#desired-end-state)
- [What We're NOT Doing](#what-were-not-doing)
- [JSON Schema Design](#json-schema-design)
- [Implementation Approach](#implementation-approach)
- [Phase 1: Create Transformation Script](#phase-1-create-transformation-script)
- [Testing Strategy](#testing-strategy)
- [References](#references)

## Overview

Transform the CSV file `menus/transformed-data/mcdonalds-menu-items-revised-full.csv` into a JSON format that can be loaded and validated using the Pydantic models defined in `src/models.py`.

The CSV contains 269 menu items across 10 categories. The JSON output must conform to the `Menu` model structure, which consists of `Category` objects containing `Item` objects.

## Current State Analysis

### CSV Structure (`mcdonalds-menu-items-revised-full.csv`)
- Two columns: `Category`, `Item`
- 269 rows of menu items (including some duplicates like "Bacon")
- Categories: Breakfast, Beef & Pork, Chicken & Fish, Salads, Snacks & Sides, Desserts, Beverages, Coffee & Tea, Smoothies & Shakes
- Some items include size in name (e.g., "Coca-Cola Classic, Small")
- Some items include piece count (e.g., "Chicken McNuggets, 4 pc")

### Pydantic Models (`src/models.py`)
```python
class Size(StrEnum):
    SNACK = "snack"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class Category(BaseModel):
    category_id: str
    name: str

class Modifier(BaseModel):
    modifier_id: str
    name: str
    restrictions: list["Category"] = Field(default_factory=list)

class Item(BaseModel):
    item_id: str
    name: str
    category_name: str
    size: Size = Field(default=Size.MEDIUM)
    quantity: int = Field(default=1, ge=1)
    modifiers: list[Modifier] = Field(default_factory=list)

class Combo(BaseModel):
    combo_id: str
    items: list[Item]
    quantity: int = Field(default=1, ge=1)

class Menu(BaseModel):
    name: str
    allowed_categories: list[Category]
```

### Key Discoveries
- The `Item` model has `size` as a direct field, not `available_sizes`
- Items are tied to categories via `category_name` (string), not nested under categories
- The existing JSON (`menu-structure-2026-01-30.json`) uses a different structure with `options` and `defaults` - this is NOT compatible with the current Pydantic models
- The `Size` enum only has 4 values: snack, small, medium, large - CSV has "Kids" size which maps to "small"
- Modifiers are not present in the CSV but are part of the model

## Desired End State

A JSON file that can be loaded and validated with this code:
```python
import json
from models import Menu

with open("menu.json") as f:
    data = json.load(f)
    menu = Menu.model_validate(data)
```

**Success Criteria:**
- [ ] JSON validates against the `Menu` Pydantic model without errors
- [ ] All 10 categories from CSV are represented
- [ ] All unique items from CSV are included
- [ ] Size information is correctly extracted and mapped to `Size` enum
- [ ] Items with size in name are properly consolidated (e.g., "Coca-Cola Classic" appears once with default size)

**How to Verify:**
```bash
uv run python -c "import json; from src.models import Menu; Menu.model_validate(json.load(open('menus/transformed-data/menu.json')))"
```

## What We're NOT Doing

- NOT creating modifier definitions (the CSV doesn't contain modifier data)
- NOT creating combo definitions (the CSV doesn't contain combo data)
- NOT adding pricing information (not in source data)
- NOT handling the `options`/`defaults` structure from the existing JSON (doesn't match current models)
- NOT modifying the Pydantic models to accommodate more complex structures

## JSON Schema Design

### Option A: Flat Menu Structure (Recommended)

This matches the current Pydantic models exactly.

```json
{
  "name": "McDonald's Menu",
  "allowed_categories": [
    {
      "category_id": "breakfast",
      "name": "Breakfast"
    },
    {
      "category_id": "beef-pork",
      "name": "Beef & Pork"
    }
  ]
}
```

**Note:** The current `Menu` model only stores categories, not items. Items would need to be stored separately or the model would need modification.

### Option B: Extended Structure (Requires Model Changes)

If we want the menu to contain items, we'd need to add an `items` field to the `Menu` model:

```json
{
  "name": "McDonald's Menu",
  "allowed_categories": [
    {
      "category_id": "breakfast",
      "name": "Breakfast"
    }
  ],
  "items": [
    {
      "item_id": "egg-mcmuffin",
      "name": "Egg McMuffin",
      "category_name": "Breakfast",
      "size": "medium",
      "quantity": 1,
      "modifiers": []
    }
  ]
}
```

### Recommended Decision

**Option A is recommended** for initial implementation since it matches the existing models. The `Item` model appears designed for order items (with `quantity`), not menu item definitions.

However, if you need a catalog of available items, we should create a separate structure or model.

## Questions for Clarification

Before implementing, please clarify:

1. **What is the JSON file's purpose?**
   - Is it a menu catalog (what items are available)?
   - Is it validation rules (which categories exist)?
   - Is it for order processing (items with quantities)?

2. **How should size variations be handled?**
   - Option A: One item per size (Coca-Cola Small, Coca-Cola Medium, etc.)
   - Option B: One item with default size, variations handled elsewhere

3. **Should we modify the Pydantic models?**
   - The current models don't have a clean way to store a "catalog" of available items
   - `Item` has `quantity` which suggests it's for orders, not menu definitions

## Implementation Approach

Pending answers to the questions above, the implementation will:

1. Parse the CSV file
2. Extract unique categories and generate category_ids (kebab-case)
3. Process items:
   - Extract size from item name if present
   - Generate item_id (kebab-case from name)
   - Deduplicate items with same base name
4. Build JSON structure matching the chosen schema
5. Validate against Pydantic model
6. Write to output file

## Phase 1: Create Transformation Script

### Overview
Create a Python script to transform the CSV to JSON.

### Context
Before starting, read these files:
- `src/models.py` - Pydantic model definitions
- `menus/transformed-data/mcdonalds-menu-items-revised-full.csv` - Source data

### Dependencies
**Depends on:** Clarification on questions above
**Required by:** None

### Changes Required

#### 1.1: Create Transformation Script
**File:** `scripts/csv_to_json.py`

```python
import csv
import json
import re
from pathlib import Path

def slugify(text: str) -> str:
    """Convert text to kebab-case slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def parse_size_from_name(name: str) -> tuple[str, str | None]:
    """Extract size from item name if present."""
    size_patterns = [
        (r',\s*(Small|Medium|Large|Kids|Snack)$', lambda m: m.group(1).lower()),
        (r',\s*(\d+)\s*pc$', None),  # piece count, not size
    ]
    for pattern, extractor in size_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match and extractor:
            base_name = name[:match.start()]
            size = extractor(match)
            # Map "kids" to "small" per Size enum
            if size == "kids":
                size = "small"
            return base_name, size
    return name, None

def main():
    csv_path = Path("menus/transformed-data/mcdonalds-menu-items-revised-full.csv")
    output_path = Path("menus/transformed-data/menu.json")

    categories = {}

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat_name = row['Category'].strip()
            if cat_name and cat_name not in categories:
                categories[cat_name] = {
                    "category_id": slugify(cat_name),
                    "name": cat_name
                }

    menu = {
        "name": "McDonald's Menu",
        "allowed_categories": list(categories.values())
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(menu, f, indent=2)

    print(f"Generated {output_path}")

if __name__ == "__main__":
    main()
```

### Success Criteria

#### Automated Verification:
- [ ] Script runs without errors: `uv run python scripts/csv_to_json.py`
- [ ] Output JSON is valid: `uv run python -c "import json; json.load(open('menus/transformed-data/menu.json'))"`
- [ ] JSON validates against Menu model: `uv run python -c "from src.models import Menu; import json; Menu.model_validate(json.load(open('menus/transformed-data/menu.json')))"`

#### Manual Verification:
- [ ] All 10 categories are present in output
- [ ] Category IDs are valid kebab-case strings
- [ ] JSON is human-readable with proper formatting

## Testing Strategy

### Unit Tests:
- Test `slugify()` function with various inputs
- Test `parse_size_from_name()` with items containing sizes
- Test category extraction from CSV

### Integration Tests:
- Validate full transformation produces valid JSON
- Validate JSON loads into Pydantic model

### Manual Testing Steps:
1. Run transformation script
2. Open output JSON and verify structure
3. Load JSON in Python and validate against models
4. Verify all expected categories are present

## References

- Source CSV: `menus/transformed-data/mcdonalds-menu-items-revised-full.csv`
- Pydantic Models: `src/models.py`
- Design Notes: `thoughts/README.md`
- Existing JSON (different structure): `menus/raw-data/menu-structure-2026-01-30.json`
