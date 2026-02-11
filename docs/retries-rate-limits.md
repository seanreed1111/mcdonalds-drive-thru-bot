<!-- created: 2026-02-11 -->

# Retries & Rate Limits for the Drive-Thru Orchestrator

How to add sensible retry and rate-limit handling to the orchestrator package, based on [langgraph-retries-rate-limits-tutorial.md](../../docs/langgraph-retries-rate-limits-tutorial.md).

---

## Current State (no retries anywhere)

The orchestrator has **zero** retry or rate-limit logic today:

| Call site | What happens on failure |
|-----------|------------------------|
| `orchestrator_node` → Mistral LLM (`graph.py:235`) | Exception propagates, graph crashes |
| `_get_system_prompt_template` → Langfuse prompt fetch (`graph.py:119`) | Caught by bare `except`, falls back to hardcoded prompt |
| `ToolNode` → pure functions (no network) | N/A — deterministic, can't rate-limit |
| `update_order` / `should_end_after_update` — pure state logic | N/A |

The only external API call that can rate-limit or flake is the **Mistral LLM call** in `orchestrator_node`. That's the primary target.

---

## What to Add

### 1. RetryPolicy on the `orchestrator` node (high priority)

This is the single highest-value change. LangGraph's `RetryPolicy` handles transient errors (rate limits, network blips) with exponential backoff at the node level — no code changes inside the node function.

```python
from langgraph.types import RetryPolicy

LLM_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=30.0,
    jitter=True,
)

_builder.add_node("orchestrator", orchestrator_node, retry_policy=LLM_RETRY_POLICY)
```

**Why these values:**

- `max_attempts=5` — Mistral rate limits are short-lived; 5 attempts with backoff covers ~30s of retrying, enough for most 429 bursts.
- `initial_interval=1.0` — Start with 1s delay. Mistral's rate-limit windows are per-minute, so sub-second retries waste quota.
- `backoff_factor=2.0` — Delays: 1s → 2s → 4s → 8s → 16s (capped at 30s). Standard exponential backoff.
- `max_interval=30.0` — Cap so a user isn't waiting >30s between retries at a drive-thru.
- `jitter=True` — Adds ±25% randomness. Prevents thundering herd if multiple sessions hit the limit simultaneously (e.g., load testing, LangGraph Studio).

**What it retries by default:** LangGraph's `default_retry_on()` retries all exceptions *except* programming errors (`ValueError`, `TypeError`, `RuntimeError`, etc.) and retries HTTP 5xx automatically. This covers:

- `mistralai` SDK rate-limit errors (HTTP 429)
- Mistral server errors (HTTP 500/502/503)
- Network timeouts / connection resets

**What it does NOT retry** (correctly): `ValueError` from bad tool args, `ValidationError` from Pydantic — these are bugs, not transient failures.

### 2. RetryPolicy on the `tools` node (low priority, still recommended)

The `ToolNode` runs pure functions today, but adding a lightweight retry policy is defensive — if tools ever make network calls (e.g., price lookup API, inventory check), retries are already in place.

```python
TOOL_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    initial_interval=0.5,
    backoff_factor=2.0,
    max_interval=5.0,
    jitter=True,
)

_builder.add_node("tools", _tool_node, retry_policy=TOOL_RETRY_POLICY)
```

### 3. No RetryPolicy on `update_order` (not needed)

`update_order` is pure state manipulation — JSON parsing and Order arithmetic. No network calls, no reason to retry. If it throws, it's a bug.

---

## Optional: Custom retry_on for Mistral-specific errors

The default `retry_on` is already good for HTTP-based SDKs, but if you want to be explicit:

```python
from mistralai import SDKError
import httpx

def is_retriable_mistral_error(exc: Exception) -> bool:
    """Retry on rate limits, server errors, and network issues."""
    # httpx transport errors (used by mistralai SDK)
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 529)
    # Check status_code attribute (some SDK wrappers)
    if hasattr(exc, "status_code"):
        return exc.status_code in (429, 500, 502, 503, 529)
    # Fallback: check error message
    msg = str(exc).lower()
    return any(s in msg for s in ("rate limit", "too many requests", "overloaded"))

LLM_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=30.0,
    jitter=True,
    retry_on=is_retriable_mistral_error,
)
```

This is optional — the default works well. Only add this if you're seeing unexpected retries on programming errors cluttering logs.

---

## Implementation: What Changes

### graph.py — minimal diff

The only file that needs to change is `graph.py`. Three lines change in the graph construction section:

```python
# ---------------------------------------------------------------------------
# Retry Policies
# ---------------------------------------------------------------------------

LLM_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=30.0,
    jitter=True,
)

# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

_tool_node = ToolNode(_tools)

_builder = StateGraph(DriveThruState)
_builder.add_node("orchestrator", orchestrator_node, retry_policy=LLM_RETRY_POLICY)  # <-- changed
_builder.add_node("tools", _tool_node)
_builder.add_node("update_order", update_order)
```

**Import to add:** `from langgraph.types import RetryPolicy`

That's it. No changes to node functions, no changes to state schema, no changes to config.py.

---

## What NOT to Do

| Temptation | Why not |
|-----------|---------|
| Add `try/except` with manual `time.sleep` inside `orchestrator_node` | RetryPolicy already does this at the framework level with proper backoff. Manual retries duplicate logic and don't integrate with LangGraph's checkpointing. |
| Add retry logic around `_get_system_prompt_template` Langfuse call | The existing fallback-to-hardcoded-prompt is the right pattern. Retrying a prompt fetch adds latency to every conversation start for marginal benefit. |
| Add a rate-limit semaphore or token bucket | Unnecessary for a single-user drive-thru bot. Only relevant at scale with shared API keys across many concurrent sessions. |
| Add `max_retries` on the `ChatMistralAI` constructor | LangChain's built-in retries and LangGraph's RetryPolicy can conflict. Pick one layer — RetryPolicy is better because it retries the whole node (including prompt compilation), not just the HTTP call. |
| Retry on Pydantic `ValidationError` | Validation errors are deterministic — retrying produces the same error. Fix the schema or the LLM prompt instead. |

---

## Observability: How to Know It's Working

Retries are invisible by default. To see them:

1. **Loguru logs** — LangGraph logs retry attempts at DEBUG level. The existing `logger.debug` calls in `orchestrator_node` will show re-entry.

2. **Langfuse traces** — Each retry creates a new LLM span under the same trace. Look for traces where the `orchestrator` node has multiple LLM calls. The Langfuse callback handler (already configured in `main.py`) captures this automatically.

3. **Add a retry counter to state** (optional, only if you need it for analytics):

```python
class DriveThruState(MessagesState):
    menu: Menu
    current_order: Order
    reasoning: Annotated[list[str], operator.add]
    retry_count: int  # new — but only useful for metrics
```

This is probably overkill for now. The Langfuse traces already show retry behavior.

---

## Summary

| Priority | Change | Effort | Impact |
|----------|--------|--------|--------|
| **High** | Add `RetryPolicy` to `orchestrator` node | 1 import + 1 constant + 1 line change | Prevents drive-thru crashes from Mistral rate limits |
| Low | Add `RetryPolicy` to `tools` node | 1 constant + 1 line change | Future-proofs for network-calling tools |
| None | `update_order` / `should_end_after_update` | No change needed | Pure functions, no failure modes |
