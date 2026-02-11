# McDonald's Breakfast Menu - Chatbot Ordering System

A drive-thru chatbot ordering system for McDonald's breakfast menu, built with LangGraph and Pydantic v2.

## Tech Stack

- Python 3.12+
- [LangGraph](https://langchain-ai.github.io/langgraph/) for agent orchestration
- [LangChain](https://python.langchain.com/) + Mistral AI for LLM integration
- [Langfuse v3](https://langfuse.com/) for observability, tracing, and prompt management
- [Pydantic v2](https://docs.pydantic.dev/) for data validation
- [uv](https://docs.astral.sh/uv/) for package management (workspace mode)

## Project Structure

```
src/orchestrator/orchestrator/   # Main chatbot package
  config.py        # Settings from environment variables (.env)
  graph.py         # LangGraph chatbot graph with tool routing
  main.py          # CLI chat interface
  tools.py         # LangGraph tools (add/remove items, finalize order)
  models.py        # Pydantic models (Item, Modifier, Order, Menu, Location)
  enums.py         # Enums (Size, CategoryName)
  logging.py       # Loguru logging setup
menus/             # Menu data (CSV, JSON, XML with schemas)
scripts/           # Utility scripts (e.g. seed_langfuse_prompts.py)
plan/              # Implementation plans and handoff docs
tests/             # Tests
```

## Getting Started

```bash
uv sync --all-packages   # Install all workspace dependencies
```

### Environment Variables

Create a `.env` file at the project root:

```
MISTRAL_API_KEY=your-key
LANGFUSE_PUBLIC_KEY=your-key
LANGFUSE_SECRET_KEY=your-key
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
```

### Seed Langfuse Prompts

The chatbot fetches its system prompt from Langfuse. Seed the prompts before first run:

```bash
uv run --package orchestrator python scripts/seed_langfuse_prompts.py
```

### Run the Chatbot

```bash
uv run --package orchestrator python -m orchestrator.main
```

## Langfuse Integration (v3)

This project uses **Langfuse SDK v3** (3.x). Key differences from v2:

- **CallbackHandler import**: `from langfuse.langchain import CallbackHandler` (not `langfuse.callback`)
- **Client initialization**: Credentials are set on the `Langfuse()` singleton client, not on the handler
- **No constructor args on handler**: `CallbackHandler()` takes no `session_id`, `user_id`, etc. — these are passed via config metadata or `propagate_attributes()`
- **Session/user tracking**: Pass `langfuse_session_id` and `langfuse_user_id` in `config["metadata"]`
- **Flushing**: Use `get_client().flush()` instead of `handler.flush()`
- **Environment variables**: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`

```python
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler

# Initialize client (reads from env vars, or pass explicitly)
Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://us.cloud.langfuse.com",
)

# Create handler (no constructor args in v3)
handler = CallbackHandler()

# Pass session_id/user_id via metadata (v3 pattern)
config = {
    "callbacks": [handler],
    "metadata": {
        "langfuse_session_id": "my-session-id",
        "langfuse_user_id": "my-user-id",
        "langfuse_tags": ["tag1", "tag2"],
    },
}
result = graph.invoke(state, config=config)

# Flush on exit
get_client().flush()
```

> **v2 → v3 breaking change**: `CallbackHandler(session_id=...)` no longer works. Use `config["metadata"]["langfuse_session_id"]` instead. See [Langfuse upgrade guide](https://langfuse.com/docs/observability/sdk/upgrade-path).

Langfuse is also used for **prompt management** — the system prompt is fetched at runtime via `langfuse.get_prompt()` with a fallback if Langfuse is unavailable.

## Architecture

### System Overview

```mermaid
graph TB
    subgraph User
        CLI[CLI Chat Interface]
    end

    subgraph Orchestrator["orchestrator package"]
        Main[main.py<br/>Chat Loop]
        Graph[graph.py<br/>LangGraph Graph]
        Tools[tools.py<br/>4 Tools]
        Config[config.py<br/>Settings]
        Models[models.py<br/>Pydantic Models]
    end

    subgraph External
        Mistral[Mistral AI<br/>LLM]
        LF[Langfuse v3<br/>Tracing + Prompts]
    end

    subgraph Data
        MenuJSON[breakfast-v2.json<br/>21 Items]
    end

    CLI <--> Main
    Main --> Graph
    Graph --> Tools
    Graph <--> Mistral
    Graph <-.-> LF
    Main --> Config
    Config -.-> |.env| Main
    Tools --> Models
    MenuJSON --> Main
```

### LangGraph Flow

```mermaid
graph LR
    START((START)) --> O

    O[orchestrator<br/>─────────────<br/>Invoke LLM with<br/>menu + order context]

    O -->|tool_calls| T[tools<br/>─────────────<br/>Execute tool calls<br/>lookup, add, get, finalize]
    O -->|no tool_calls| END((END))

    T --> U[update_order<br/>─────────────<br/>Apply add_item results<br/>to current_order]

    U -->|finalize called| END
    U -->|continue| O
```

### Data Models

```mermaid
classDiagram
    class Size {
        <<StrEnum>>
        SNACK
        SMALL
        MEDIUM
        LARGE
        REGULAR
    }

    class CategoryName {
        <<StrEnum>>
        BREAKFAST
        BEEF_PORK
        CHICKEN_FISH
        ...
    }

    class Modifier {
        str modifier_id
        str name
    }

    class Item {
        str item_id
        str name
        CategoryName category_name
        Size default_size
        Size size
        int quantity
        list~Modifier~ modifiers
        list~Modifier~ available_modifiers
        __add__(Item) Item
        __eq__() bool
    }

    class Order {
        str order_id
        list~Item~ items
        __add__(Item) Order
    }

    class Location {
        str id
        str name
        str address
        str city
        str state
        str zip
        str country
    }

    class Menu {
        str menu_id
        str menu_name
        str menu_version
        Location location
        list~Item~ items
        from_json_file()$ Menu
    }

    class DriveThruState {
        <<LangGraph State>>
        list messages
        Menu menu
        Order current_order
    }

    Menu "1" --> "1" Location
    Menu "1" --> "*" Item
    Item "*" --> "*" Modifier
    Item --> Size
    Item --> CategoryName
    Order "1" --> "*" Item
    DriveThruState --> Menu
    DriveThruState --> Order
```

### Tools

```mermaid
graph LR
    subgraph Tools
        L[lookup_menu_item<br/>──────────<br/>Search menu by name<br/>fuzzy matching]
        A[add_item_to_order<br/>──────────<br/>Validate & prepare<br/>item for order]
        G[get_current_order<br/>──────────<br/>Return order summary]
        F[finalize_order<br/>──────────<br/>Submit order<br/>ends conversation]
    end

    L -->|"must call first"| A
    G -->|"confirm before"| F

    style L fill:#e1f5fe
    style A fill:#e8f5e9
    style G fill:#fff3e0
    style F fill:#fce4ec
```

## Data Models

- `Size` - StrEnum: snack, small, medium, large, regular
- `CategoryName` - Menu category (breakfast, beverages, coffee-tea, etc.)
- `Modifier` - Item variations (Extra Cheese, No Onions, etc.)
- `Item` - Menu item with modifiers, size, quantity; supports equality, ordering, and addition
- `Order` - Collection of items for a customer order
- `Location` - Restaurant location details
- `Menu` - Full menu with items, loadable from JSON files
