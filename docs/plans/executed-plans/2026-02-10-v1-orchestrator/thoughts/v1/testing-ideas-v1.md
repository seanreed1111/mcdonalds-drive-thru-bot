# Testing Ideas for v1 Orchestrator

> **Status:** Ideas for future implementation. The current v1 has a smoke test only.
> **See also:** [v1 State Design](./langgraph-state-design-v1.md)

## Current Tests (v1)

- `tests/orchestrator/test_smoke.py` — Graph compiles, tools work with mock data, update_order processes results correctly. No LLM API calls.

## Future Test Ideas

### Unit Tests for Tools (no LLM needed)

These test each tool function directly with mock `InjectedState`:

1. **`lookup_menu_item`**
   - Exact match (case-insensitive): "Egg McMuffin" → found=True
   - No match: "Big Mac" → found=False with suggestions
   - Partial match suggestions: "McMuffin" → suggestions include Egg McMuffin, Sausage McMuffin
   - Empty menu → found=False
   - Returns correct `available_modifiers` structure

2. **`add_item_to_order`**
   - Valid item → added=True with correct fields
   - Invalid item_id → added=False with error
   - Invalid modifier → added=False with error
   - Size resolution: explicit size used, None falls back to default
   - Quantity validation: quantity=0 should fail (Pydantic ge=1)

3. **`get_current_order`**
   - Empty order → item_count=0
   - Order with items → correct serialization (name, qty, size, modifiers)
   - Order preserves order_id

4. **`finalize_order`**
   - Returns finalized=True with order_id
   - Order_id matches the state's current_order

### Unit Tests for `update_order` Node

5. **State mutation**
   - Single add → order has 1 item
   - Multiple adds in one turn → order has N items
   - Duplicate add → quantities merge (2+1=3)
   - Add with modifiers → modifiers preserved on item
   - Failed add (added=False) → order unchanged
   - Non-add tool messages → order unchanged

6. **Message scanning**
   - Only processes messages after the last AIMessage
   - Does not re-process old add results from previous turns

### Integration Tests (requires LLM API)

7. **Single-turn ordering**
   - "I'd like an Egg McMuffin" → calls lookup then add, responds with confirmation
   - "What do you have?" → responds with menu items, no tool calls

8. **Multi-intent**
   - "Two hash browns and a large coffee" → two lookups, two adds

9. **Item not found**
   - "Big Mac" → lookup returns not found, suggests alternatives

10. **Order flow**
    - Full conversation: greet → order → read back → confirm → finalize
    - Verify finalize_order is only called after confirmation

11. **Edge cases**
    - Customer asks about prices → "total will be at the window"
    - Customer asks to remove item → "can only add items right now"
    - Customer orders with invalid modifier → polite rejection

### End-to-End Conversation Tests

12. **Happy path**: Greet → order 2 items → "that's all" → read back → "yes" → finalize
13. **Menu browsing**: Ask about categories → order from suggestion
14. **Multi-turn with corrections**: Order item → "actually make that two" → finalize

### Langfuse Trace Verification

15. **Trace structure**: Each turn produces a trace with orchestrator + tool spans
16. **Tool inputs/outputs**: Tool call args and results are visible in traces
17. **Token usage**: Token counts are tracked per turn
