"""LangGraph drive-thru orchestrator graph (v1).

4-node graph: orchestrator -> tools -> update_order -> orchestrator (loop).
The orchestrator is a Mistral LLM with tools bound. The system prompt is
fetched from Langfuse prompt management and compiled with runtime variables.

Exported as `graph` for langgraph.json.
"""

import json
import operator
import re
from functools import lru_cache
from typing import Annotated

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_mistralai import ChatMistralAI
from langfuse import Langfuse
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from loguru import logger

from .config import get_settings
from .enums import CategoryName, Size
from .models import Item, Menu, Modifier, Order
from .tools import (
    add_item_to_order,
    finalize_order,
    get_current_order,
    lookup_menu_item,
)

# ---------------------------------------------------------------------------
# State Schema
# ---------------------------------------------------------------------------


class DriveThruState(MessagesState):
    """State for the drive-thru orchestrator graph.

    Inherits `messages` from MessagesState (with add-message reducer).
    Only adds the domain objects the orchestrator needs.
    """

    menu: Menu  # Loaded menu for this location
    current_order: Order  # Customer's order in progress
    reasoning: Annotated[list[str], operator.add]  # LLM decision rationale log


# ---------------------------------------------------------------------------
# System Prompt (Langfuse)
# ---------------------------------------------------------------------------

PROMPT_NAME = "drive-thru/orchestrator"

# Fallback prompt used if Langfuse is unavailable (e.g., no API keys configured)
FALLBACK_SYSTEM_PROMPT = """\
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
    specify a size, do not ask — the item's default size will be used automatically.
14. ALWAYS start your response with a <reasoning> tag explaining your decision.
    If you are calling tools, explain which tools you chose and why.
    If you are responding directly, explain why no tool call is needed.
    Example: <reasoning>Customer asked for an Egg McMuffin. I need to call
    lookup_menu_item to verify it exists before adding it.</reasoning>
    The reasoning tag MUST appear before any other content in your response.\
"""


def _get_system_prompt_template() -> str:
    """Fetch the system prompt template from Langfuse.

    Falls back to FALLBACK_SYSTEM_PROMPT if Langfuse is unavailable
    (no API keys, network error, prompt not seeded yet).

    Returns the raw template string with {{variable}} placeholders.
    """
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("Langfuse keys not configured — using fallback system prompt")
        return FALLBACK_SYSTEM_PROMPT

    try:
        langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_base_url,
        )
        prompt = langfuse.get_prompt(PROMPT_NAME, label="production")
        logger.info("Fetched system prompt from Langfuse: {}", PROMPT_NAME)
        # For chat prompts, extract the system message content
        if isinstance(prompt.prompt, list):
            for msg in prompt.prompt:
                if msg.get("role") == "system":
                    return msg["content"]
        # For text prompts, return directly
        return prompt.prompt
    except Exception:
        logger.warning(
            "Failed to fetch prompt from Langfuse — using fallback",
            exc_info=True,
        )
        return FALLBACK_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# LLM + Tools (lazy initialization)
# ---------------------------------------------------------------------------

_tools = [lookup_menu_item, add_item_to_order, get_current_order, finalize_order]


@lru_cache(maxsize=1)
def _get_orchestrator_llm():
    """Create and return the LLM with tools bound.

    Lazy-initialized via @lru_cache so the LLM is only created when
    the graph is first invoked, NOT at import time. This allows
    graph.py to be imported without MISTRAL_API_KEY being set
    (important for tests and __init__.py imports).
    """
    settings = get_settings()
    logger.info(
        "Initializing LLM: model={}, temperature={}",
        settings.mistral_model,
        settings.mistral_temperature,
    )
    llm = ChatMistralAI(
        model=settings.mistral_model,
        temperature=settings.mistral_temperature,
        api_key=settings.mistral_api_key,
    )
    return llm.bind_tools(_tools)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

_REASONING_PATTERN = re.compile(r"<reasoning>(.*?)</reasoning>", re.DOTALL)


def _extract_reasoning(content: str) -> tuple[str, str]:
    """Extract and strip <reasoning> tags from LLM response content.

    Returns:
        (reasoning_text, cleaned_content) — reasoning_text is the extracted
        reasoning (empty string if no tag found), cleaned_content is the
        original content with the <reasoning> tag removed.
    """
    match = _REASONING_PATTERN.search(content)
    if not match:
        return "", content
    reasoning_text = match.group(1).strip()
    cleaned = _REASONING_PATTERN.sub("", content).strip()
    return reasoning_text, cleaned


def orchestrator_node(state: DriveThruState) -> dict:
    """Central orchestrator node. Reasons about the conversation and decides
    what tools to call.

    Formats the system prompt with current location, menu, and order context,
    then invokes the LLM.
    """
    prompt_template = _get_system_prompt_template()

    # Format location info
    location = state["menu"].location
    location_address = (
        f"{location.address}, {location.city}, {location.state} {location.zip}"
    )

    # Format menu items for the prompt
    menu_items = "\n".join(
        f"- {item.name} [{item.category_name.value}] "
        f"(default size: {item.default_size.value})"
        for item in state["menu"].items
    )

    # Format current order for the prompt
    current_items = (
        "\n".join(
            f"- {item.quantity}x {item.name} ({item.size.value})"
            + (
                f" [{', '.join(m.name for m in item.modifiers)}]"
                if item.modifiers
                else ""
            )
            for item in state["current_order"].items
        )
        or "Empty"
    )

    # Compile the prompt template (replace {{var}} with values)
    system_content = (
        prompt_template.replace("{{location_name}}", location.name)
        .replace("{{location_address}}", location_address)
        .replace("{{menu_items}}", menu_items)
        .replace("{{current_order}}", current_items)
    )

    messages = [SystemMessage(content=system_content)] + state["messages"]
    logger.debug("Invoking orchestrator LLM with {} messages", len(messages))
    response = _get_orchestrator_llm().invoke(messages)

    # Extract reasoning from <reasoning> tags in content
    raw_reasoning, cleaned_content = _extract_reasoning(response.content or "")

    # Strip reasoning tags from the message content before storing
    if cleaned_content != (response.content or ""):
        response.content = cleaned_content

    # Format reasoning entry with structured prefix
    if response.tool_calls:
        tool_names = ", ".join(tc["name"] for tc in response.tool_calls)
        logger.info("Orchestrator requesting tools: {}", tool_names)
        if raw_reasoning:
            reasoning_entry = f"[TOOL_CALL] {tool_names}: {raw_reasoning}"
        else:
            # Fallback: generate from tool call metadata
            args_summary = "; ".join(
                f"{tc['name']}({', '.join(f'{k}={v!r}' for k, v in tc['args'].items())})"
                for tc in response.tool_calls
            )
            reasoning_entry = f"[TOOL_CALL] {tool_names}: {args_summary}"
    else:
        logger.info("Orchestrator responding directly (no tool calls)")
        if raw_reasoning:
            reasoning_entry = f"[DIRECT] {raw_reasoning}"
        else:
            # Fallback: note that no reasoning was provided
            snippet = (response.content or "")[:80]
            reasoning_entry = f"[DIRECT] {snippet}"

    logger.debug("Reasoning: {}", reasoning_entry)

    return {"messages": [response], "reasoning": [reasoning_entry]}


def should_continue(state: DriveThruState) -> str:
    """Check if the orchestrator wants to call tools or is done.

    Returns:
        "tools" — LLM wants to call tools (route to ToolNode).
                   This includes finalize_order — all tools go through the
                   normal tools -> update_order path.
        "respond" — No tool calls, LLM is responding directly (route to END)
    """
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        logger.debug(
            "should_continue -> tools ({} calls)", len(last_message.tool_calls)
        )
        return "tools"

    # No tool calls — LLM is responding directly
    logger.debug("should_continue -> respond")
    return "respond"


def update_order(state: DriveThruState) -> dict:
    """Process tool results and update current_order.

    Runs after every tool execution. Scans ONLY the latest batch of
    ToolMessages (after the last AIMessage) for add_item_to_order results
    and applies them to the order using Order.__add__.
    """
    current_order = state["current_order"]
    menu = state["menu"]

    # Find the last AIMessage index to only process new tool results
    last_ai_idx = -1
    for i, msg in enumerate(state["messages"]):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            last_ai_idx = i

    # Only process ToolMessages after the last AIMessage
    recent_messages = state["messages"][last_ai_idx + 1 :] if last_ai_idx >= 0 else []

    for msg in recent_messages:
        if not isinstance(msg, ToolMessage):
            continue
        if msg.name != "add_item_to_order":
            continue

        result = (
            json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        )
        if not result.get("added"):
            continue

        menu_item = next(
            (i for i in menu.items if i.item_id == result["item_id"]), None
        )
        if not menu_item:
            continue

        new_item = Item(
            item_id=result["item_id"],
            name=result["item_name"],
            category_name=CategoryName(result["category_name"]),
            default_size=menu_item.default_size,
            size=Size(result["size"]) if result.get("size") else None,
            quantity=result["quantity"],
            modifiers=[Modifier(**m) for m in result.get("modifiers", [])],
        )
        current_order = current_order + new_item
        logger.info(
            "update_order: added {}x {} to order",
            result["quantity"],
            result["item_name"],
        )

    logger.debug(
        "update_order complete: order now has {} items", len(current_order.items)
    )
    return {"current_order": current_order}


def should_end_after_update(state: DriveThruState) -> str:
    """Check if finalize_order was called in the latest tool batch.

    Called after update_order. Checks the recent ToolMessages for a
    finalize_order result. If found, routes to END. Otherwise, loops
    back to the orchestrator for more conversation.

    Returns:
        "end" — finalize_order was called, conversation is done
        "continue" — normal flow, loop back to orchestrator
    """
    # Find the last AIMessage index
    last_ai_idx = -1
    for i, msg in enumerate(state["messages"]):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            last_ai_idx = i

    # Check recent ToolMessages for finalize_order
    recent_messages = state["messages"][last_ai_idx + 1 :] if last_ai_idx >= 0 else []
    for msg in recent_messages:
        if isinstance(msg, ToolMessage) and msg.name == "finalize_order":
            logger.info("should_end_after_update -> end (finalize_order detected)")
            return "end"

    logger.debug("should_end_after_update -> continue")
    return "continue"


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

_tool_node = ToolNode(_tools)

_builder = StateGraph(DriveThruState)
_builder.add_node("orchestrator", orchestrator_node)
_builder.add_node("tools", _tool_node)
_builder.add_node("update_order", update_order)

_builder.add_edge(START, "orchestrator")
_builder.add_conditional_edges(
    "orchestrator",
    should_continue,
    {
        "tools": "tools",
        "respond": END,
    },
)
_builder.add_edge("tools", "update_order")
_builder.add_conditional_edges(
    "update_order",
    should_end_after_update,
    {
        "end": END,
        "continue": "orchestrator",
    },
)

# Compile without checkpointer — LangGraph Studio provides its own.
# For CLI usage, main.py compiles from _builder with a MemorySaver.
graph = _builder.compile()
