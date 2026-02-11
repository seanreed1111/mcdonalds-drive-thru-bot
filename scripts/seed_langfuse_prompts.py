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
        host=settings.langfuse_base_url,
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
