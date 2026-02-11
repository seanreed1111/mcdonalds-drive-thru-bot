# Phase 4: CLI + Langfuse

<- [Back to Main Plan](./README.md)

## Table of Contents

- [Overview](#overview)
- [Context](#context)
- [Dependencies](#dependencies)
- [Changes Required](#changes-required)
- [Success Criteria](#success-criteria)

## Overview

Create `main.py` as the CLI entry point for the drive-thru chatbot. Update `scripts/seed_langfuse_prompts.py` to seed the orchestrator system prompt into Langfuse. The CLI runs a simple `input()` loop that invokes the graph per turn, with Langfuse callback handler for observability.

## Context

Before starting, read these files:
- `src/orchestrator/orchestrator/graph.py` — The compiled graph, `DriveThruState` (created in Phase 3)
- `src/orchestrator/orchestrator/config.py` — Settings class with Langfuse credentials
- `src/orchestrator/orchestrator/models.py` — `Menu.from_json_file()`, `Order` model
- `scripts/seed_langfuse_prompts.py` — Existing Langfuse prompt seeding script (to be updated)
- `docs/thoughts/target-implementation/v1/langgraph-state-design-v1.md` — Human-in-the-loop section (lines 555-641), Langfuse integration (lines 797-821)

## Dependencies

**Depends on:** Phase 3 (Graph)
**Required by:** Phase 5 (Smoke Test)

## Changes Required

### 4.1: Create `main.py`
**File:** `src/orchestrator/orchestrator/main.py`
**Action:** CREATE

**What this does:** CLI entry point for the chatbot. Loads the menu, creates an empty order, and runs a request-response loop. Each user message triggers `graph.invoke()` with the same `thread_id` so the checkpointer maintains conversation state. Langfuse callback handler is attached if credentials are configured.

```python
"""CLI entry point for the McDonald's drive-thru chatbot.

Usage:
    uv run --package orchestrator python -m orchestrator.main
"""

import uuid

from langchain_core.messages import HumanMessage, ToolMessage
from loguru import logger

from .config import get_settings
from .graph import graph
from .logging import setup_logging
from .models import Menu, Order


def _create_langfuse_handler():
    """Create a Langfuse callback handler if credentials are configured.

    Returns None if Langfuse is not configured.
    """
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    from langfuse.callback import CallbackHandler

    return CallbackHandler(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def main() -> None:
    """Run the drive-thru chatbot CLI."""
    settings = get_settings()

    # Initialize logging first (stderr + rotating file)
    setup_logging(level=settings.log_level)
    logger.info("Starting drive-thru chatbot CLI")

    # Load menu from JSON
    menu = Menu.from_json_file(settings.menu_json_path)
    logger.info("Menu loaded: {} ({} items)", menu.menu_name, len(menu.items))
    print(f"Menu loaded: {menu.menu_name} ({len(menu.items)} items)")
    print(f"Location: {menu.location.name}")
    print()

    # Create empty order
    order = Order()

    # Session config for checkpointer
    thread_id = f"cli-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    # Attach Langfuse callback handler if available
    langfuse_handler = _create_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
        logger.info("Langfuse tracing enabled")
        print("Langfuse tracing: enabled")
    else:
        logger.info("Langfuse tracing disabled (no credentials)")
        print("Langfuse tracing: disabled (no credentials)")

    print("-" * 50)
    print("Drive-thru chatbot ready! Type 'quit' to exit.")
    print("-" * 50)
    print()

    # Initial invocation — triggers greeting (empty message list, LLM sees
    # system prompt and generates a greeting)
    result = graph.invoke(
        {
            "messages": [HumanMessage(content="Hi")],
            "menu": menu,
            "current_order": order,
        },
        config=config,
    )

    # Print the assistant's greeting
    last_msg = result["messages"][-1]
    print(f"Bot: {last_msg.content}")
    print()

    # Conversation loop
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Invoke graph with user message
        logger.debug("User input: {}", user_input)
        result = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )

        # Print the assistant's response
        last_msg = result["messages"][-1]
        logger.debug("Bot response: {}", last_msg.content[:100])
        print(f"Bot: {last_msg.content}")
        print()

        # Check if order was finalized (graph ended after finalize_order
        # went through tools -> update_order -> END). We detect this by
        # checking for a finalize_order ToolMessage in the recent messages.
        for msg in reversed(result["messages"]):
            if isinstance(msg, ToolMessage) and msg.name == "finalize_order":
                print("-" * 50)
                print("Order finalized! Thank you for visiting.")
                print("-" * 50)

                # Flush Langfuse if enabled
                if langfuse_handler:
                    langfuse_handler.flush()

                return
            # Stop scanning once we hit an AIMessage (only check recent batch)
            if hasattr(msg, "tool_calls"):
                break

    # Flush Langfuse on exit
    if langfuse_handler:
        langfuse_handler.flush()

    logger.info("Chatbot session ended (thread_id={})", thread_id)


if __name__ == "__main__":
    main()
```

### 4.2: Create `__main__.py`
**File:** `src/orchestrator/orchestrator/__main__.py`
**Action:** CREATE

**What this does:** Enables running the package with `python -m orchestrator`.

```python
"""Allow running as: python -m orchestrator"""

from .main import main

main()
```

### 4.3: Update `seed_langfuse_prompts.py`
**File:** `scripts/seed_langfuse_prompts.py`
**Action:** REPLACE_ENTIRE

**What this does:** Updates the prompt seeding script to include the drive-thru orchestrator system prompt alongside the existing interview prompts. The orchestrator prompt uses `{{variable}}` template syntax for runtime compilation.

**Before:**
```python
"""One-time script to create interview prompts in Langfuse.

Run from project root:
    uv run --package stage-2 python scripts/seed_langfuse_prompts.py

This creates two chat prompts with the 'production' label.
If prompts already exist, Langfuse will create a new version.
"""

from langfuse import Langfuse
from stage_2.config import get_settings

PROMPT_TEMPLATE = (
    "You are {{persona_name}}, {{persona_description}}. "
    "{{persona_behavior}} "
    "Keep responses to 2-3 sentences. Do not break character. "
    "Address {{other_persona}} directly."
)

PROMPT_CONFIG = {"model": "mistral-small-latest", "temperature": 0.9}

PROMPTS = [
    "interview/initiator",
    "interview/responder",
]


def main() -> None:
    settings = get_settings()
    langfuse = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_base_url,
    )

    for name in PROMPTS:
        langfuse.create_prompt(
            name=name,
            type="chat",
            prompt=[{"role": "system", "content": PROMPT_TEMPLATE}],
            config=PROMPT_CONFIG,
            labels=["production"],
        )
        print(f"Created prompt: {name}")

    langfuse.flush()
    print("Done. Prompts created with 'production' label.")


if __name__ == "__main__":
    main()
```

**After:**
```python
"""One-time script to create prompts in Langfuse.

Run from project root:
    uv run --package orchestrator python scripts/seed_langfuse_prompts.py

This creates prompts with the 'production' label.
If prompts already exist, Langfuse will create a new version.
"""

from langfuse import Langfuse
from orchestrator.config import get_settings

# ---------------------------------------------------------------------------
# Drive-Thru Orchestrator Prompt (v1)
# ---------------------------------------------------------------------------

DRIVE_THRU_SYSTEM_PROMPT = """\
You are a friendly McDonald's drive-thru assistant taking breakfast orders.

LOCATION: {{location_name}} — {{location_address}}

CURRENT MENU:
{{menu_items}}

CURRENT ORDER:
{{current_order}}

RULES:
1. Greet the customer warmly when the conversation starts.
2. When a customer orders an item, ALWAYS call lookup_menu_item first to verify it exists.
3. Only call add_item_to_order for items confirmed to exist via lookup_menu_item.
   Pass the exact item_id, item_name, and category_name from the lookup result.
4. If an item isn't found, suggest the alternatives from lookup_menu_item results.
   Do NOT invent alternatives.
5. When the customer says they're done, call get_current_order, read back the
   full order, and ask them to confirm.
6. Only call finalize_order AFTER the customer confirms their order.
7. Handle multiple items in a single request — call lookup_menu_item for each,
   then add_item_to_order for each confirmed item.
8. Keep responses concise and friendly — this is a drive-thru, not a sit-down restaurant.
9. Answer menu questions from the CURRENT MENU above. Do NOT make up items.
10. You do NOT have access to prices. Do not quote prices or totals.
    Say "your total will be at the window" if asked.
11. If the customer asks to remove or change an item, explain you can only
    add items right now.
12. When adding modifiers, only use modifiers from the item's available_modifiers
    list returned by lookup_menu_item. Do not accept modifiers that aren't
    available for that item.
13. Sizes are: snack, small, medium, large, regular. If the customer doesn't
    specify a size, do not ask — the item's default size will be used automatically.\
"""

DRIVE_THRU_PROMPT_CONFIG = {"model": "mistral-small-latest", "temperature": 0.0}

# ---------------------------------------------------------------------------
# Interview Prompts (legacy — from stage-2)
# ---------------------------------------------------------------------------

INTERVIEW_PROMPT_TEMPLATE = (
    "You are {{persona_name}}, {{persona_description}}. "
    "{{persona_behavior}} "
    "Keep responses to 2-3 sentences. Do not break character. "
    "Address {{other_persona}} directly."
)

INTERVIEW_PROMPT_CONFIG = {"model": "mistral-small-latest", "temperature": 0.9}

# ---------------------------------------------------------------------------
# All prompts to seed
# ---------------------------------------------------------------------------

PROMPTS = [
    # Drive-thru orchestrator
    {
        "name": "drive-thru/orchestrator",
        "type": "chat",
        "prompt": [{"role": "system", "content": DRIVE_THRU_SYSTEM_PROMPT}],
        "config": DRIVE_THRU_PROMPT_CONFIG,
    },
    # Interview prompts (legacy)
    {
        "name": "interview/initiator",
        "type": "chat",
        "prompt": [{"role": "system", "content": INTERVIEW_PROMPT_TEMPLATE}],
        "config": INTERVIEW_PROMPT_CONFIG,
    },
    {
        "name": "interview/responder",
        "type": "chat",
        "prompt": [{"role": "system", "content": INTERVIEW_PROMPT_TEMPLATE}],
        "config": INTERVIEW_PROMPT_CONFIG,
    },
]


def main() -> None:
    settings = get_settings()
    langfuse = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )

    for prompt_def in PROMPTS:
        langfuse.create_prompt(
            name=prompt_def["name"],
            type=prompt_def["type"],
            prompt=prompt_def["prompt"],
            config=prompt_def["config"],
            labels=["production"],
        )
        print(f"Created prompt: {prompt_def['name']}")

    langfuse.flush()
    print(f"\nDone. {len(PROMPTS)} prompts created with 'production' label.")


if __name__ == "__main__":
    main()
```

**Key changes from the original script:**
1. **Imports `orchestrator.config`** instead of `stage_2.config` (matches current package)
2. **Uses `settings.langfuse_host`** instead of `settings.langfuse_base_url` (matches `config.py` field name from Phase 1)
3. **Adds the `drive-thru/orchestrator` prompt** with the full system prompt template using `{{variable}}` syntax
4. **Restructured as a list of prompt dicts** for cleaner iteration
5. **Preserves legacy interview prompts** (backward compatible)

**Note:** We intentionally do NOT export `graph` or `DriveThruState` from `__init__.py`. The graph module uses lazy LLM initialization, but importing it at the package level would still couple basic model imports (e.g., `from orchestrator import Item`) to having all graph dependencies available. Users who need the graph import it directly via `from orchestrator.graph import graph`. The `__init__.py` remains as Phase 2 left it (exporting models, enums, and tools only).

## Success Criteria

### Automated Verification:
- [ ] File exists: `src/orchestrator/orchestrator/main.py`
- [ ] File exists: `src/orchestrator/orchestrator/__main__.py`
- [ ] File updated: `scripts/seed_langfuse_prompts.py` includes `drive-thru/orchestrator` prompt
- [ ] Python can import the module (no API key needed — graph uses lazy LLM init): `uv run --package orchestrator python -c "from orchestrator.main import main; print('OK')"`
- [ ] Ruff passes: `uv run ruff check src/orchestrator/orchestrator/main.py src/orchestrator/orchestrator/__main__.py scripts/seed_langfuse_prompts.py`
- [ ] Seed script can be run (requires Langfuse credentials): `uv run --package orchestrator python scripts/seed_langfuse_prompts.py`

### Manual Verification:
- [ ] Run `uv run --package orchestrator python -m orchestrator.main` and have a multi-turn conversation
- [ ] Verify greeting, ordering, read-back, and finalization work
- [ ] Check Langfuse dashboard for traces after a conversation
- [ ] Run seed script and verify `drive-thru/orchestrator` prompt appears in Langfuse

---

<- [Back to Main Plan](./README.md)
