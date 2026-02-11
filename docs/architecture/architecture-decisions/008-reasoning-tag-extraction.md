# ADR-008: Structured Reasoning Extraction via XML Tags

**Status:** Accepted

[Back to ADR Index](./adr.md)

---

## Context

With the LLM orchestrator pattern ([ADR-001](./001-llm-orchestrator-pattern.md)), all routing decisions are made by the LLM rather than explicit graph edges. This makes it harder to understand *why* the LLM chose a particular action. For debugging, evaluation, and observability, the system needs a way to capture the LLM's decision rationale without exposing it to the customer.

**Options considered:**
1. **No reasoning capture** — Just log tool calls and responses
2. **Separate reasoning LLM call** — Ask the LLM to explain its decision after acting
3. **Inline XML tags** — Instruct the LLM to wrap reasoning in `<reasoning>` tags in every response, then strip them before showing to the customer

## Decision

Require the LLM to start every response with a `<reasoning>` tag. Extract the reasoning content, strip the tag from user-facing output, and log it to the `reasoning` state field with a structured prefix.

### System prompt instruction

```
14. ALWAYS start your response with a <reasoning> tag explaining your decision.
    If you are calling tools, explain which tools you chose and why.
    If you are responding directly, explain why no tool call is needed.
    Example: <reasoning>Customer asked for an Egg McMuffin. I need to call
    lookup_menu_item to verify it exists before adding it.</reasoning>
    The reasoning tag MUST appear before any other content in your response.
```

### Extraction logic

```python
# graph.py:170-186

_REASONING_PATTERN = re.compile(r"<reasoning>(.*?)</reasoning>", re.DOTALL)

def _extract_reasoning(content: str) -> tuple[str, str]:
    match = _REASONING_PATTERN.search(content)
    if not match:
        return "", content
    reasoning_text = match.group(1).strip()
    cleaned = _REASONING_PATTERN.sub("", content).strip()
    return reasoning_text, cleaned
```

### Structured logging to state

```python
# graph.py:244-268

raw_reasoning, cleaned_content = _extract_reasoning(response.content or "")

if response.tool_calls:
    tool_names = ", ".join(tc["name"] for tc in response.tool_calls)
    reasoning_entry = f"[TOOL_CALL] {tool_names}: {raw_reasoning}"
else:
    reasoning_entry = f"[DIRECT] {raw_reasoning}"

# Fallback if LLM omits reasoning tag
if not raw_reasoning and response.tool_calls:
    args_summary = "; ".join(
        f"{tc['name']}({', '.join(f'{k}={v!r}' for k, v in tc['args'].items())})"
        for tc in response.tool_calls
    )
    reasoning_entry = f"[TOOL_CALL] {tool_names}: {args_summary}"

return {"messages": [response], "reasoning": [reasoning_entry]}
```

### Example reasoning log

```
[TOOL_CALL] lookup_menu_item: Customer asked for an Egg McMuffin, verifying existence
[TOOL_CALL] add_item_to_order: Item confirmed on menu, adding 2x Egg McMuffin
[DIRECT] Customer greeted, welcoming them and asking what they'd like
[TOOL_CALL] get_current_order: Customer said they're done, reading back order
[DIRECT] Reading order back to customer for confirmation
[TOOL_CALL] finalize_order: Customer confirmed, submitting order
```

**Why "no reasoning" was rejected:**
- Tool call names alone don't explain *why* the LLM chose them
- Critical for debugging when the LLM makes unexpected decisions

**Why a separate reasoning call was rejected:**
- Doubles LLM invocations and latency
- The reasoning is most accurate when generated alongside the decision, not after

## Consequences

**Benefits:**
- Every LLM decision is logged with rationale — invaluable for debugging and evaluation
- Reasoning is stripped from customer-facing output — the customer sees clean responses
- The `[TOOL_CALL]`/`[DIRECT]` prefix enables structured filtering and analysis
- Accumulated in state via `operator.add` reducer — full decision history available at any point
- Fallback logic handles cases where the LLM omits the tag (logs tool args instead)

**Tradeoffs:**
- Consumes output tokens for reasoning text the customer never sees
- The LLM may not always comply with the `<reasoning>` tag instruction (handled by fallback)
- Regex-based extraction is fragile if the LLM produces malformed tags (e.g., nested tags, unclosed tags)
- The reasoning quality depends on the LLM's ability to articulate its own decision process

---

[Back to ADR Index](./adr.md)
