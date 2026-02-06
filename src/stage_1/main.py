"""CLI chat interface for stage-1 chatbot with streaming responses."""

import uuid

from langchain_core.messages import AIMessage, HumanMessage, AIMessageChunk

from stage_1.graph import graph, get_langfuse_handler, get_langfuse_client


def run_chat() -> None:
    """Run interactive chat loop with streaming responses."""
    # Generate session and user IDs for tracing
    session_id = f"cli-session-{uuid.uuid4().hex[:8]}"
    user_id = f"cli-user-{uuid.uuid4().hex[:8]}"

    print("Stage-1 Chatbot (type 'quit' to exit)")
    print(f"Session: {session_id}")
    print("-" * 40)

    # Get Langfuse callback handler (v3: no constructor args)
    langfuse_handler = get_langfuse_handler()

    messages = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Add user message
        messages.append(HumanMessage(content=user_input))

        # Stream response with Langfuse tracing
        # Pass session_id/user_id via metadata (v3 pattern)
        print("\nAssistant: ", end="", flush=True)

        full_response = ""
        try:
            for chunk, metadata in graph.stream(
                {"messages": messages},
                config={
                    "callbacks": [langfuse_handler],
                    "metadata": {
                        "langfuse_session_id": session_id,
                        "langfuse_user_id": user_id,
                    },
                },
                stream_mode="messages",
            ):
                # Only process AI message chunks
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    print(chunk.content, end="", flush=True)
                    full_response += chunk.content
        except Exception as e:
            print(f"\nError: {e}")
            # Remove the orphaned user message from history since stream failed
            messages.pop()
            continue

        print()  # Newline after streaming completes

        # Add complete response to message history
        messages.append(AIMessage(content=full_response))

    # Flush traces before exit
    get_langfuse_client().flush()


if __name__ == "__main__":
    run_chat()
