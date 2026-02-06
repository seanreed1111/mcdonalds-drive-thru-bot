"""LangGraph chatbot graph using Mistral AI with Langfuse observability."""

import atexit

from langchain_core.messages import SystemMessage
from langchain_mistralai import ChatMistralAI
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler
from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.graph.state import CompiledStateGraph

from stage_1.config import get_settings

SYSTEM_PROMPT = """You are a helpful, friendly assistant. Be concise and helpful.
If you don't know something, say so. Keep responses brief unless asked for detail."""

# Initialize the Langfuse singleton (v3 pattern)
_settings = get_settings()
Langfuse(
    public_key=_settings.langfuse_public_key,
    secret_key=_settings.langfuse_secret_key,
    host=_settings.langfuse_base_url,
)


def get_langfuse_client() -> Langfuse:
    """Get Langfuse singleton client instance."""
    return get_client()


def get_langfuse_handler() -> CallbackHandler:
    """Get Langfuse callback handler for tracing.

    In v3, CallbackHandler takes no constructor args — it inherits
    from the Langfuse singleton. Pass session_id/user_id via metadata
    in the config dict when invoking the graph.
    """
    return CallbackHandler()


def create_chat_model() -> ChatMistralAI:
    """Create Mistral chat model."""
    settings = get_settings()
    return ChatMistralAI(
        model="mistral-small-latest",
        api_key=settings.mistral_api_key,  # type: ignore[unknown-argument]  # valid at runtime
        temperature=0.7,
    )


def chatbot(state: MessagesState) -> dict:
    """Process messages and generate response.

    Returns partial state update (dict), not full MessagesState.
    """
    llm = create_chat_model()

    # Prepend system message if not present
    messages = state["messages"]
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = llm.invoke(messages)
    return {"messages": [response]}


def create_graph() -> CompiledStateGraph:
    """Create the chatbot graph."""
    graph_builder = StateGraph(MessagesState)  # type: ignore[invalid-argument-type]  # valid at runtime
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    return graph_builder.compile()


# Export compiled graph for LangGraph Platform
graph = create_graph()

# Register flush on shutdown
atexit.register(get_client().flush)
