# McDonald's Breakfast Menu - Voice Ordering System

A drive-thru voice ordering system for McDonald's breakfast menu, built with LangGraph and Pydantic v2.

## Tech Stack

- Python 3.12+
- [LangGraph](https://langchain-ai.github.io/langgraph/) for agent orchestration
- [LangChain](https://python.langchain.com/) + Mistral AI for LLM integration
- [Langfuse](https://langfuse.com/) for observability and tracing
- [Pydantic v2](https://docs.pydantic.dev/) for data validation
- [uv](https://docs.astral.sh/uv/) for package management

## Project Structure

```
src/
  enums.py           # Enums (Size, CategoryName)
  models.py          # Pydantic models (Item, Modifier, Order, Menu, Location)
  stage_1/           # Stage 1: Simple chatbot
    config.py        #   Settings from environment variables
    graph.py         #   LangGraph chatbot graph with Langfuse tracing
    main.py          #   CLI chat interface with streaming
menus/               # Menu data (CSV, JSON, XML with schemas)
thoughts/            # Design notes and requirements
plan/                # Implementation plans and handoff docs
langgraph.json       # LangGraph Platform configuration
```

## Getting Started

```bash
uv sync            # Install dependencies
```

### Environment Variables

Create a `.env` file with:

```
MISTRAL_API_KEY=your-key
LANGFUSE_SECRET_KEY=your-key
LANGFUSE_PUBLIC_KEY=your-key
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
```

### Run the Chatbot

```bash
uv run python -m stage_1.main
```

## Stages

### Stage 1 - Simple Chatbot (implemented)

A basic conversational chatbot using LangGraph with a single node, Mistral AI as the LLM, streaming responses, and Langfuse observability. Serves as the foundation for adding menu-aware ordering in later stages.

### Stage 2+ - Menu-Aware Ordering (planned)

Will add menu knowledge, order management, and drive-thru specific conversation flows.

## Data Models

- `Size` - StrEnum: snack, small, medium, large, regular
- `CategoryName` - Menu category (breakfast, beverages, coffee-tea, etc.)
- `Modifier` - Item variations (Extra Cheese, No Onions, etc.)
- `Item` - Menu item with modifiers, size, quantity; supports equality, ordering, and addition
- `Order` - Collection of items for a customer order
- `Location` - Restaurant location details
- `Menu` - Full menu with items, loadable from JSON files
