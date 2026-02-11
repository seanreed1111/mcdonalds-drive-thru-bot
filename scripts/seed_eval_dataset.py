"""Seed the Langfuse evaluation dataset for drive-thru order correctness.

Usage:
    uv run --package orchestrator python scripts/seed_eval_dataset.py

Creates a dataset in Langfuse with test cases for single-turn ordering evaluation.
Each item has:
  - input: {"customer_utterance": "..."} — what the customer says
  - expected_output: {"expected_items": [...]} — what should end up in the order
  - metadata: {"category": "...", "difficulty": "..."} — for filtering/analysis

Idempotent: each item has a deterministic id, so running twice upserts (no duplicates).
"""

from orchestrator.config import get_settings

DATASET_NAME = "drive-thru/order-correctness-v1"
DATASET_DESCRIPTION = (
    "Single-turn order correctness evaluation dataset. "
    "Tests whether the chatbot correctly adds items to the order "
    "based on a single customer utterance."
)

# ── Test Cases ──────────────────────────────────────────────────────────────
# Each test case: (customer_utterance, expected_items, category, difficulty)
#
# expected_items format:
#   [{"item_id": "...", "name": "...", "quantity": N, "size": "...", "modifiers": [...]}]
#
# An empty list [] means no items should be added (e.g., greeting, question).
#
# NOTE: The order of items in expected_items does NOT matter — the evaluator
# matches by item_id using dicts, not by list position.
# ────────────────────────────────────────────────────────────────────────────

TEST_CASES: list[tuple[str, list[dict], str, str]] = [
    # ── Simple single-item orders (easy) ──
    (
        "I'll have an Egg McMuffin",
        [
            {
                "item_id": "egg-mcmuffin",
                "name": "Egg McMuffin",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            }
        ],
        "simple_order",
        "easy",
    ),
    (
        "Can I get a Hash Brown please?",
        [
            {
                "item_id": "hash-brown",
                "name": "Hash Brown",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            }
        ],
        "simple_order",
        "easy",
    ),
    (
        "I'd like the Hotcakes",
        [
            {
                "item_id": "hotcakes",
                "name": "Hotcakes",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            }
        ],
        "simple_order",
        "easy",
    ),
    (
        "Give me a Sausage Burrito",
        [
            {
                "item_id": "sausage-burrito",
                "name": "Sausage Burrito",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            }
        ],
        "simple_order",
        "easy",
    ),
    (
        "I want the Fruit & Maple Oatmeal",
        [
            {
                "item_id": "fruit-maple-oatmeal",
                "name": "Fruit & Maple Oatmeal",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            }
        ],
        "simple_order",
        "easy",
    ),
    # ── Quantities (easy-medium) ──
    (
        "Two hash browns please",
        [
            {
                "item_id": "hash-brown",
                "name": "Hash Brown",
                "quantity": 2,
                "size": "regular",
                "modifiers": [],
            }
        ],
        "quantity",
        "easy",
    ),
    (
        "I'll take three Sausage Biscuits",
        [
            {
                "item_id": "sausage-biscuit",
                "name": "Sausage Biscuit",
                "quantity": 3,
                "size": "regular",
                "modifiers": [],
            }
        ],
        "quantity",
        "medium",
    ),
    # ── Multi-item in single utterance (medium) ──
    (
        "I'll have an Egg McMuffin and a Hash Brown",
        [
            {
                "item_id": "egg-mcmuffin",
                "name": "Egg McMuffin",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            },
            {
                "item_id": "hash-brown",
                "name": "Hash Brown",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            },
        ],
        "multi_item",
        "medium",
    ),
    (
        "Can I get two Sausage McMuffins and a Sausage Burrito",
        [
            {
                "item_id": "sausage-mcmuffin",
                "name": "Sausage McMuffin",
                "quantity": 2,
                "size": "regular",
                "modifiers": [],
            },
            {
                "item_id": "sausage-burrito",
                "name": "Sausage Burrito",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            },
        ],
        "multi_item",
        "medium",
    ),
    (
        "I'd like a Steak & Egg McMuffin, two Hash Browns, and Hotcakes",
        [
            {
                "item_id": "steak-egg-mcmuffin",
                "name": "Steak & Egg McMuffin",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            },
            {
                "item_id": "hash-brown",
                "name": "Hash Brown",
                "quantity": 2,
                "size": "regular",
                "modifiers": [],
            },
            {
                "item_id": "hotcakes",
                "name": "Hotcakes",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            },
        ],
        "multi_item",
        "medium",
    ),
    # ── Modifiers (medium) ──
    (
        "Sausage McMuffin with egg please",
        [
            {
                "item_id": "sausage-mcmuffin",
                "name": "Sausage McMuffin",
                "quantity": 1,
                "size": "regular",
                "modifiers": [{"modifier_id": "egg", "name": "Egg"}],
            }
        ],
        "modifier",
        "medium",
    ),
    (
        "I'll have a Sausage Biscuit with egg whites",
        [
            {
                "item_id": "sausage-biscuit",
                "name": "Sausage Biscuit",
                "quantity": 1,
                "size": "regular",
                "modifiers": [{"modifier_id": "egg-whites", "name": "Egg Whites"}],
            }
        ],
        "modifier",
        "medium",
    ),
    (
        "Hotcakes with sausage",
        [
            {
                "item_id": "hotcakes",
                "name": "Hotcakes",
                "quantity": 1,
                "size": "regular",
                "modifiers": [{"modifier_id": "sausage", "name": "Sausage"}],
            }
        ],
        "modifier",
        "medium",
    ),
    # ── Not on menu / should add nothing (medium-hard) ──
    (
        "I'd like a Big Mac",
        [],
        "not_on_menu",
        "medium",
    ),
    (
        "Can I get a Quarter Pounder?",
        [],
        "not_on_menu",
        "medium",
    ),
    (
        "I want chicken nuggets",
        [],
        "not_on_menu",
        "medium",
    ),
    # ── Greetings / questions — no items should be added (easy) ──
    (
        "Hi, good morning!",
        [],
        "greeting",
        "easy",
    ),
    (
        "What do you have on the menu?",
        [],
        "question",
        "easy",
    ),
    (
        "What comes with the Big Breakfast?",
        [],
        "question",
        "easy",
    ),
    # ── Informal / colloquial phrasing (medium-hard) ──
    (
        "Lemme get uhh two of those egg mcmuffins",
        [
            {
                "item_id": "egg-mcmuffin",
                "name": "Egg McMuffin",
                "quantity": 2,
                "size": "regular",
                "modifiers": [],
            }
        ],
        "informal",
        "medium",
    ),
    (
        "yeah gimme a sausage mcmuffin with egg and a hash brown",
        [
            {
                "item_id": "sausage-mcmuffin",
                "name": "Sausage McMuffin",
                "quantity": 1,
                "size": "regular",
                "modifiers": [{"modifier_id": "egg", "name": "Egg"}],
            },
            {
                "item_id": "hash-brown",
                "name": "Hash Brown",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            },
        ],
        "informal",
        "hard",
    ),
    # ── Ambiguous / partial names (hard) ──
    (
        "I'll have a McMuffin",
        [],  # Ambiguous — could be Egg McMuffin, Sausage McMuffin, etc. Agent should clarify, not guess.
        "ambiguous",
        "hard",
    ),
    (
        "Give me some bacon",
        [
            {
                "item_id": "bacon",
                "name": "Bacon",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            }
        ],
        "ambiguous",
        "hard",
    ),
    # ── Quantity + modifier combo (hard) ──
    (
        "Two Sausage Biscuits with egg and a Sausage Burrito",
        [
            {
                "item_id": "sausage-biscuit",
                "name": "Sausage Biscuit",
                "quantity": 2,
                "size": "regular",
                "modifiers": [{"modifier_id": "egg", "name": "Egg"}],
            },
            {
                "item_id": "sausage-burrito",
                "name": "Sausage Burrito",
                "quantity": 1,
                "size": "regular",
                "modifiers": [],
            },
        ],
        "complex",
        "hard",
    ),
    (
        "I'd like three hash browns and two Egg McMuffins",
        [
            {
                "item_id": "hash-brown",
                "name": "Hash Brown",
                "quantity": 3,
                "size": "regular",
                "modifiers": [],
            },
            {
                "item_id": "egg-mcmuffin",
                "name": "Egg McMuffin",
                "quantity": 2,
                "size": "regular",
                "modifiers": [],
            },
        ],
        "complex",
        "hard",
    ),
]


def main() -> None:
    """Seed the evaluation dataset in Langfuse."""
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        print("ERROR: Langfuse credentials not configured in .env")
        print("Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY")
        return

    from langfuse import Langfuse

    langfuse = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_base_url,
    )

    # Create the dataset (idempotent — Langfuse upserts by name)
    print(f"Creating dataset: {DATASET_NAME}")
    langfuse.create_dataset(
        name=DATASET_NAME,
        description=DATASET_DESCRIPTION,
        metadata={
            "version": "1.0",
            "scope": "single-turn",
            "focus": "order-correctness",
            "item_count": len(TEST_CASES),
        },
    )

    # Add test cases as dataset items
    # Each item has a deterministic id so re-running upserts instead of duplicating
    for i, (utterance, expected_items, category, difficulty) in enumerate(TEST_CASES):
        print(
            f"  [{i + 1}/{len(TEST_CASES)}] {category}/{difficulty}: {utterance[:50]}..."
        )
        langfuse.create_dataset_item(
            id=f"order-correctness-{i:03d}",
            dataset_name=DATASET_NAME,
            input={"customer_utterance": utterance},
            expected_output={"expected_items": expected_items},
            metadata={
                "category": category,
                "difficulty": difficulty,
                "index": i,
            },
        )

    langfuse.flush()
    print(f"\nDone! {len(TEST_CASES)} items seeded to '{DATASET_NAME}'")
    print("View in Langfuse UI: Datasets > drive-thru/order-correctness-v1")


if __name__ == "__main__":
    main()
