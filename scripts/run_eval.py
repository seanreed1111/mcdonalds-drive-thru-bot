"""Run evaluation experiment on the drive-thru chatbot.

Usage:
    uv run --package orchestrator python scripts/run_eval.py
    uv run --package orchestrator python scripts/run_eval.py --run-name "mistral-small-v2"

Runs the LangGraph agent against every item in the Langfuse evaluation dataset,
scores each result with deterministic evaluators, and prints a summary.
"""

import argparse
import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from orchestrator.config import get_settings
from orchestrator.graph import _builder
from orchestrator.models import Menu, Order


# ── Langfuse Setup ──────────────────────────────────────────────────────────


def _init_langfuse():
    """Initialize and return the Langfuse client."""
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        raise RuntimeError("Langfuse credentials not configured in .env")

    from langfuse import Langfuse

    langfuse = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_base_url,
    )
    return langfuse


# ── Task Function ───────────────────────────────────────────────────────────

DATASET_NAME = "drive-thru/order-correctness-v1"


def _load_menu() -> Menu:
    """Load the breakfast menu."""
    settings = get_settings()
    return Menu.from_json_file(settings.menu_json_path)


# Cache the menu so it's loaded once across all task invocations.
# This is populated on the first task invocation before run_experiment()
# starts concurrent execution, so subsequent reads are safe.
_menu: Menu | None = None


def _get_menu() -> Menu:
    global _menu
    if _menu is None:
        _menu = _load_menu()
    return _menu


def eval_task(*, item, **kwargs):
    """Task function for the experiment runner.

    Invokes the LangGraph agent with the customer utterance from the dataset
    item. Returns a dict with the resulting order and tool call trace for
    evaluators to score.

    Args:
        item: A DatasetItemClient from Langfuse. Has .input and .expected_output.

    Returns:
        dict with keys:
            - "order_items": list of dicts with item details from the final order
            - "tool_calls": list of tool call names in execution order
            - "response": the final assistant message text
            - "item_count": total number of items in the order
    """
    from langfuse.langchain import CallbackHandler

    customer_utterance = item.input["customer_utterance"]
    menu = _get_menu()

    # Compile a fresh graph with its own checkpointer for state isolation
    graph = _builder.compile(checkpointer=MemorySaver())

    # Unique thread for this evaluation item
    thread_id = f"eval-{uuid.uuid4()}"

    # The CallbackHandler captures LangChain-specific observations (LLM calls,
    # tool calls, chain runs) and links them under the experiment trace created
    # by run_experiment(). run_experiment() manages the top-level trace/span;
    # the CallbackHandler adds the LangChain detail underneath it.
    langfuse_handler = CallbackHandler()

    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [langfuse_handler],
    }

    # Invoke the graph with the customer utterance
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=customer_utterance)],
            "menu": menu,
            "current_order": Order(),
        },
        config=config,
    )

    # Extract the final order state
    current_order = result["current_order"]
    order_items = [
        {
            "item_id": item_obj.item_id,
            "name": item_obj.name,
            "quantity": item_obj.quantity,
            "size": item_obj.size.value if item_obj.size else "regular",
            "modifiers": [
                {"modifier_id": m.modifier_id, "name": m.name}
                for m in item_obj.modifiers
            ],
        }
        for item_obj in current_order.items
    ]

    # Extract tool call sequence from messages
    tool_calls = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(tc["name"])

    # Get the final assistant response
    response = ""
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and not isinstance(msg, (HumanMessage, ToolMessage)):
            response = msg.content or ""
            break

    return {
        "order_items": order_items,
        "tool_calls": tool_calls,
        "response": response,
        "item_count": sum(i["quantity"] for i in order_items),
    }


# ── Evaluators ──────────────────────────────────────────────────────────────
#
# IMPORTANT: All evaluators are ORDER-INDEPENDENT. They match items by item_id
# using dict lookups, and compare modifiers using sets. The order that items
# appear in order_items or expected_items lists does NOT affect scores.
# ────────────────────────────────────────────────────────────────────────────


def order_correctness_evaluator(*, output, expected_output, **kwargs):
    """Score how well the actual order matches the expected order.

    ORDER-INDEPENDENT: Items are matched by item_id using dict lookups,
    not by list position. Modifiers are compared as sets of modifier_id.

    Scoring:
    - If expected is empty and actual is empty: 1.0 (correct: no items should be added)
    - If expected is empty but actual has items: 0.0 (hallucinated items)
    - If expected has items but actual is empty: 0.0 (missed everything)
    - Otherwise: Jaccard-like score based on item matching by item_id
    """
    from langfuse import Evaluation

    if output is None:
        return Evaluation(
            name="order_correctness", value=0.0, comment="Task returned None"
        )

    expected_items = expected_output.get("expected_items", [])
    actual_items = output.get("order_items", [])

    # Both empty — correct behavior (greeting, question, not-on-menu)
    if not expected_items and not actual_items:
        return Evaluation(
            name="order_correctness", value=1.0, comment="Correctly added no items"
        )

    # Expected empty but got items — hallucination
    if not expected_items and actual_items:
        item_names = [i["name"] for i in actual_items]
        return Evaluation(
            name="order_correctness",
            value=0.0,
            comment=f"Expected no items but got: {item_names}",
        )

    # Expected items but got nothing
    if expected_items and not actual_items:
        item_names = [i["name"] for i in expected_items]
        return Evaluation(
            name="order_correctness",
            value=0.0,
            comment=f"Expected {item_names} but order is empty",
        )

    # Both have items — compute match score
    # Build lookup by item_id — order of items in lists does NOT matter
    expected_by_id = {item["item_id"]: item for item in expected_items}
    actual_by_id = {item["item_id"]: item for item in actual_items}

    all_ids = set(expected_by_id.keys()) | set(actual_by_id.keys())
    total_score = 0.0
    max_score = len(all_ids)
    details = []

    for item_id in sorted(all_ids):  # sorted for deterministic comment output
        exp = expected_by_id.get(item_id)
        act = actual_by_id.get(item_id)

        if exp and act:
            # Item present in both — score match quality
            item_score = 0.0

            # Name match (0.4 weight)
            if act["name"].lower() == exp["name"].lower():
                item_score += 0.4

            # Quantity match (0.3 weight)
            if act["quantity"] == exp["quantity"]:
                item_score += 0.3
            else:
                # Partial credit for close quantities
                ratio = min(act["quantity"], exp["quantity"]) / max(
                    act["quantity"], exp["quantity"]
                )
                item_score += 0.3 * ratio

            # Size match (0.1 weight)
            if act.get("size") == exp.get("size"):
                item_score += 0.1

            # Modifier match (0.2 weight) — uses SETS, order-independent
            exp_mod_ids = {m["modifier_id"] for m in exp.get("modifiers", [])}
            act_mod_ids = {m["modifier_id"] for m in act.get("modifiers", [])}
            if not exp_mod_ids and not act_mod_ids:
                item_score += 0.2  # Both have no modifiers — match
            elif exp_mod_ids or act_mod_ids:
                intersection = exp_mod_ids & act_mod_ids
                union = exp_mod_ids | act_mod_ids
                item_score += 0.2 * (len(intersection) / len(union))

            total_score += item_score
            details.append(f"{exp['name']}: {item_score:.2f}/1.0")

        elif exp and not act:
            details.append(f"{exp['name']}: MISSING from order")
        elif act and not exp:
            details.append(f"{act['name']}: UNEXPECTED in order")

    final_score = total_score / max_score if max_score > 0 else 0.0
    comment = "; ".join(details)

    return Evaluation(
        name="order_correctness", value=round(final_score, 3), comment=comment
    )


def tool_call_accuracy_evaluator(*, output, expected_output, **kwargs):
    """Check that the agent followed the correct tool-calling protocol.

    NOTE: This evaluator intentionally checks temporal ordering of tool calls
    (lookup must come before add). This is a protocol sequence check, not a
    list-equality check — the order of tool calls in time IS meaningful here.

    Rules:
    - If items were expected: lookup_menu_item must appear before add_item_to_order
    - If no items were expected: add_item_to_order should NOT appear
    - lookup_menu_item before add_item_to_order (protocol compliance)
    """
    from langfuse import Evaluation

    if output is None:
        return Evaluation(
            name="tool_call_accuracy", value=0.0, comment="Task returned None"
        )

    expected_items = expected_output.get("expected_items", [])
    tool_calls = output.get("tool_calls", [])

    # No items expected — check that add_item_to_order was NOT called
    if not expected_items:
        if "add_item_to_order" not in tool_calls:
            return Evaluation(
                name="tool_call_accuracy",
                value=1.0,
                comment="Correctly did not add items",
            )
        return Evaluation(
            name="tool_call_accuracy",
            value=0.0,
            comment=f"Should not have called add_item_to_order. Tool calls: {tool_calls}",
        )

    # Items expected — check protocol
    has_lookup = "lookup_menu_item" in tool_calls
    has_add = "add_item_to_order" in tool_calls

    if not has_lookup and not has_add:
        return Evaluation(
            name="tool_call_accuracy",
            value=0.0,
            comment="No tool calls made — expected ordering tools",
        )

    if not has_lookup:
        return Evaluation(
            name="tool_call_accuracy",
            value=0.3,
            comment="add_item_to_order called without lookup_menu_item first",
        )

    if not has_add:
        return Evaluation(
            name="tool_call_accuracy",
            value=0.3,
            comment="lookup_menu_item called but add_item_to_order never called",
        )

    # Check ordering: first lookup should come before first add
    first_lookup = tool_calls.index("lookup_menu_item")
    first_add = tool_calls.index("add_item_to_order")

    if first_lookup < first_add:
        return Evaluation(
            name="tool_call_accuracy", value=1.0, comment="Correct: lookup before add"
        )

    return Evaluation(
        name="tool_call_accuracy",
        value=0.5,
        comment=f"Protocol violation: add_item_to_order at index {first_add} before lookup_menu_item at {first_lookup}",
    )


def no_hallucinated_items_evaluator(*, output, **kwargs):
    """Check that no items outside the breakfast menu were added.

    ORDER-INDEPENDENT: Uses set membership check on item_ids.
    Loads the menu and checks all item_ids in the order exist on the menu.
    """
    from langfuse import Evaluation

    if output is None:
        return Evaluation(
            name="no_hallucinated_items", value=0.0, comment="Task returned None"
        )

    actual_items = output.get("order_items", [])
    if not actual_items:
        return Evaluation(
            name="no_hallucinated_items", value=1.0, comment="No items in order"
        )

    menu = _get_menu()
    valid_ids = {item.item_id for item in menu.items}

    hallucinated = [item for item in actual_items if item["item_id"] not in valid_ids]

    if not hallucinated:
        return Evaluation(
            name="no_hallucinated_items", value=1.0, comment="All items are on the menu"
        )

    names = [i["name"] for i in hallucinated]
    return Evaluation(
        name="no_hallucinated_items",
        value=0.0,
        comment=f"Hallucinated items not on menu: {names}",
    )


# ── Run-level Evaluator ────────────────────────────────────────────────────


def avg_order_correctness_evaluator(*, item_results, **kwargs):
    """Compute average order_correctness across all items in the run."""
    from langfuse import Evaluation

    scores = [
        ev.value
        for result in item_results
        for ev in result.evaluations
        if ev.name == "order_correctness" and ev.value is not None
    ]

    if not scores:
        return Evaluation(name="avg_order_correctness", value=None, comment="No scores")

    avg = sum(scores) / len(scores)
    return Evaluation(
        name="avg_order_correctness",
        value=round(avg, 3),
        comment=f"Average order correctness: {avg:.1%} across {len(scores)} items",
    )


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Run drive-thru evaluation experiment")
    parser.add_argument(
        "--run-name",
        default=None,
        help="Name for this experiment run (default: auto-generated with timestamp)",
    )
    args = parser.parse_args()

    run_name = args.run_name or f"eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    langfuse = _init_langfuse()

    print(f"Loading dataset: {DATASET_NAME}")
    dataset = langfuse.get_dataset(DATASET_NAME)
    print(f"Dataset has {len(dataset.items)} items")

    print(f"Running experiment: {run_name}")
    print("This will invoke the LangGraph agent for each dataset item...")
    print()

    settings = get_settings()
    result = dataset.run_experiment(
        name=run_name,
        description=f"Single-turn order correctness evaluation using {settings.mistral_model}",
        task=eval_task,
        evaluators=[
            order_correctness_evaluator,
            tool_call_accuracy_evaluator,
            no_hallucinated_items_evaluator,
        ],
        run_evaluators=[avg_order_correctness_evaluator],
        max_concurrency=1,
        metadata={
            "model": settings.mistral_model,
            "temperature": settings.mistral_temperature,
            "dataset": DATASET_NAME,
        },
    )

    print()
    # Handle Windows encoding issues with emoji in format() output
    formatted = result.format()
    try:
        print(formatted)
    except UnicodeEncodeError:
        print(formatted.encode("utf-8", errors="replace").decode("utf-8"))

    langfuse.flush()
    print(f"\nDone! View results in Langfuse: Datasets > {DATASET_NAME}")


if __name__ == "__main__":
    main()
