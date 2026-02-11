# McDonald's Breakfast Menu Data Model

Pydantic v2 data models for a McDonald's breakfast menu drive-thru chatbot ordering system.

## Tech Stack

- Python 3.12+
- Pydantic v2 for data validation
- uv for package management

## Project Structure

This is a uv workspace project with multiple independent stages:

```
src/
├── orchestrator/               # Simple LangGraph chatbot
│   ├── pyproject.toml     # stage_1's own dependencies
│   └── orchestrator/           # Python package
│       ├── config.py
│       ├── graph.py
│       └── main.py
│       ├── enums.py       # Enums (Size, CategoryName)
│       └── models.py      # Pydantic models (Item, Modifier, Order, Menu)


menus/                     # Menu data (raw CSV, transformed JSON)
thoughts/                  # Design notes and requirements
```

## Commands

This is a uv workspace with multiple packages. Each stage has its own dependencies.

```bash
# Workspace commands
uv sync --all-packages              # Install all stages' dependencies


# Running stage-specific commands
uv run --package orchestrator python -m stage_1.main   # Run stage_1 chatbot
uv run --package stage-3 python                   # Python REPL with stage_3 available

# Adding dependencies to a specific stage
cd src/stage_1 && uv add <package>  # Add to stage_1
cd src/stage_3 && uv add <package>  # Add to stage_3

# Make targets (use SCOPE variable for stage selection)
make chat                # Run stage_1 chatbot CLI (default SCOPE=1)
make dev                 # Run LangGraph Studio for stage_1 (default SCOPE=1)
make setup               # Install all packages (default SCOPE=all)
make test                # Run smoke tests
make typecheck           # Run ty type checker
date -Iseconds           # Get current date
```

## Important: Package Management

- **Always use `uv add <package>`** to add new dependencies instead of manually editing pyproject.toml. This ensures you get the latest compatible versions.
- Run `date -Iseconds` to check the current date before suggesting Python packages or versions.
- Do not assume package versions do not exist based on training data—always verify against `uv.lock` and `pyproject.toml` in the repository, which reflect actually working versions.

## Models Overview

- `Size` - StrEnum: snack, small, medium, large
- `CategoryName` - Menu category (breakfast, beverages, coffee-tea, etc.)
- `Item` - Individual menu item with modifiers, default size is medium
- `Modifier` - Item variations (Extra Cheese, No Onions, etc.)
- `Order` - Collection of items for a customer order
- `Menu` - Full menu with items

## MCP Search Guidelines

- **`searchLangfuseDocs`**: Ask ONE focused natural-language question per call. Do not stuff multiple keywords/topics into a single query — this returns huge responses that fill up context.
  - Bad: `"LangGraph state checkpointer persistence tool calling"`
  - Good: `"How do I set up Langfuse tracing for a LangGraph agent?"`
- **`getLangfuseDocsPage`**: If you already know the specific docs page you need, fetch it directly instead of searching.
- Make multiple small, focused queries rather than one broad query.

## Markdown File Dates

When creating or editing any markdown file (except CLAUDE.md itself), add a date comment at the very top of the file:

- **New file**: Add `<!-- created: YYYY-MM-DD -->` as the first line.
- **Existing file**: If it already has a `<!-- created: ... -->` line, replace it with `<!-- modified: YYYY-MM-DD -->`. If it has a `<!-- modified: ... -->` line, update the date.
- Each file should have **exactly one** date line — either `created` or `modified`, never both.
- Use `date -Iseconds` to get the current date.

## Agent Behavior: Scope and Confirmation

**Do only what is explicitly requested.** Do not add extra features, refactors, or "improvements" beyond the specific ask.

After completing the requested work:
1. Provide a brief summary of what was done
2. If there are REQUIRED or CRITICAL follow-up items, list them briefly with why they're critical
3. Ask for confirmation before implementing anything else

### Examples

**Bad behavior:**
```
User: "Add a `total_price` property to the Order class"
Agent: *adds total_price, then also adds discount logic, tax calculation,
       currency formatting, and refactors the Item class*
```

**Good behavior:**
```
User: "Add a `total_price` property to the Order class"
Agent: *adds only total_price property*
"Done. Added `total_price` property that sums item prices.

Note: This doesn't account for modifiers that affect price. If modifier
pricing is needed, that would require changes to the Modifier model.

What would you like to do next?"
```

**Good behavior (question vs implementation):**
```
User: "How does the Menu class load items?"
Agent: *reads code and explains* — does NOT start implementing changes
```
