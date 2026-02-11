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

    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    # Initialize the Langfuse singleton client with credentials
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_base_url,
    )

    return CallbackHandler()


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
    session_id = f"cli-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": session_id}}
    logger.info("Session started (session_id={})", session_id)

    # Attach Langfuse callback handler if available
    langfuse_handler = _create_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
        config["metadata"] = {"langfuse_session_id": session_id}
        logger.info("Langfuse tracing enabled (session_id={})", session_id)
        print(f"Langfuse tracing: enabled (session_id={session_id})")
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
                    from langfuse import get_client

                    get_client().flush()

                return
            # Stop scanning once we hit an AIMessage (only check recent batch)
            if hasattr(msg, "tool_calls"):
                break

    # Flush Langfuse on exit
    if langfuse_handler:
        from langfuse import get_client

        get_client().flush()

    logger.info("Chatbot session ended (session_id={})", session_id)


if __name__ == "__main__":
    main()
