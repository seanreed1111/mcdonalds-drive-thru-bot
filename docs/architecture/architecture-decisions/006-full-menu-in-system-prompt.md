# ADR-006: Embed Full Menu in the System Prompt

**Status:** Accepted

[Back to ADR Index](./adr.md)

---

## Context

The LLM needs access to the menu to answer questions like "what breakfast items do you have?" and to validate customer requests. The question is how much menu data to include in the system prompt vs. requiring the LLM to use tools for all menu access.

The current breakfast menu has **21 items**, each represented as a single line in the prompt (name, category, default size). This is a small, fixed dataset.

**Approaches considered:**

| Approach | Description |
|----------|-------------|
| **A: Full menu in prompt** | List all 21 items in the system prompt |
| **B: Tool-only** | No menu in prompt; LLM must call `lookup_menu_item` for everything |
| **C: Embeddings/RAG** | Vector search over menu items |
| **D: Hybrid** | Category summary in prompt + tool for details |

## Decision

**Approach A: Full menu in the system prompt.**

Each item is formatted as a single line:

```
- Egg McMuffin [breakfast] (default size: regular)
- Hash Browns [breakfast] (default size: regular)
- Hotcakes [breakfast] (default size: regular)
- Premium Roast Coffee [coffee-tea] (default size: medium)
...
```

This appears in the `CURRENT MENU` section of the compiled system prompt on every LLM invocation.

**Why B (tool-only) was rejected:**
- Customers frequently ask "what do you have?" or "what's on the menu?" — the LLM cannot answer these without multiple tool calls
- Adds unnecessary latency for simple menu browsing questions
- The LLM may hallucinate items it "remembers" from training data if it cannot see the actual menu

**Why C (RAG) was rejected:**
- 21 items is far too small to justify a vector database
- Adds infrastructure complexity (embedding model, vector store) with no benefit at this scale

**Why D (hybrid) was rejected:**
- More complexity than needed for v1
- Would be the right choice if the menu grows to hundreds of items

## Consequences

**Benefits:**
- The LLM can answer menu questions instantly without tool calls
- No hallucination risk — the LLM sees exactly what is available
- Simplest possible implementation: string formatting in the orchestrator node
- `lookup_menu_item` still provides detailed info (modifiers, exact IDs) that the prompt summary omits

**Tradeoffs:**
- Does not scale to large menus (hundreds of items would consume too much context)
- Menu data is duplicated: once in the JSON file, once formatted into the prompt
- Every conversation turn re-sends the full menu in the system message, using tokens even when the customer isn't asking about the menu

**When to revisit:**
- If the menu grows beyond ~50 items, migrate to Approach D (hybrid)
- If the menu becomes dynamic (items change mid-conversation), the prompt compilation already supports this since it reads from `state["menu"]` on every turn

---

[Back to ADR Index](./adr.md)
