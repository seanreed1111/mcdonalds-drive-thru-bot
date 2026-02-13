<!-- created: 2026-02-13 -->

# From Vibes to Metrics: Building an Evaluation Pipeline for an AI Drive-Thru Agent with Langfuse v3

You built an LLM-powered agent. It mostly works. You changed the prompt, chatted with it a few times, and it "seemed good." Ship it.

We've all been there. This post walks through how we moved past vibes-based testing for our McDonald's breakfast drive-thru chatbot and built a repeatable evaluation pipeline with Langfuse v3. By the end, we had one command, a quantitative score, and the confidence to actually ship prompt changes.

---

## The Agent Under Test

Our agent is a McDonald's breakfast drive-thru chatbot built with LangGraph and Mistral, traced with Langfuse v3. A customer says "I'll have two Egg McMuffins and a hash brown," and the agent looks up items on the menu, validates they exist, and builds a structured order.

The core is a 4-node LangGraph state machine:

```python
class DriveThruState(MessagesState):
    menu: Menu                                         # Loaded menu for this location
    current_order: Order                               # Customer's order in progress
    reasoning: Annotated[list[str], operator.add]      # LLM decision rationale log
```

An orchestrator LLM decides what to do, calls tools, updates the order, and loops back:

```python
_builder = StateGraph(DriveThruState)
_builder.add_node("orchestrator", orchestrator_node, retry_policy=LLM_RETRY_POLICY)
_builder.add_node("tools", _tool_node)
_builder.add_node("update_order", update_order)

_builder.add_edge(START, "orchestrator")
_builder.add_conditional_edges(
    "orchestrator", should_continue,
    {"tools": "tools", "respond": END},
)
_builder.add_edge("tools", "update_order")
_builder.add_conditional_edges(
    "update_order", should_end_after_update,
    {"end": END, "continue": "orchestrator"},
)
```

Before evaluations, our development workflow looked like this:

```
1. Change prompt
2. Chat with agent manually — try 3-4 orders
3. "Seems good" → ship
4. Users report broken orders a week later → panic
```

The problems with this are obvious once you list them:

- **No baseline.** You change the prompt or swap models and have no way to tell if things got better or worse.
- **Silent regressions.** The agent used to handle "gimme two hash browns" fine, but after a prompt rewrite it stopped working — and you don't notice for days.
- **No granularity.** Did it get the right item but wrong quantity? Or hallucinate an entirely different item? Binary "it worked / it didn't" hides the distinction.
- **Edge cases slip through.** Informal phrasing ("lemme get uhh..."), off-menu items ("Big Mac" during breakfast), ambiguous names ("a McMuffin") — you'd need to remember to test all of these manually, every time.

The goal: change a prompt, run `make eval`, get a score you can compare to the last run. One command. Quantitative. Repeatable.

To get there, we need three things: a dataset, evaluators, and a runner to connect them.

---

## Designing the Evaluation Dataset

### What to Evaluate First

We focused on **single-turn order correctness** — the highest-impact, most measurable capability. Given one customer utterance, does the agent produce the correct order?

We deliberately deferred multi-turn flows, tone, latency, and order modification. These matter, but they require more complex test harnesses and often more subjective scoring. Start with something deterministic.

> **Tip**: Pick the capability that (a) has a clear right answer and (b) matters most to your users. For us, that's order correctness — if the agent adds the wrong item, nothing else matters.

### Category-Based Coverage

Twenty-five well-chosen test cases beat 500 random ones. **Structured coverage across failure modes** catches more bugs than volume. We defined nine categories, each targeting a specific way the agent can fail:

| Category | Count | Example | What It Tests |
|----------|-------|---------|---------------|
| Simple order | 5 | "I'll have an Egg McMuffin" | Basic item identification |
| Quantity | 2 | "Two hash browns please" | Numeric extraction |
| Multi-item | 3 | "Egg McMuffin and a Hash Brown" | Parsing multiple items from one utterance |
| Modifiers | 3 | "Sausage McMuffin with egg" | Modifier extraction and attachment |
| Not on menu | 3 | "I'd like a Big Mac" | Hallucination resistance — should add nothing |
| Greeting/question | 3 | "Hi, good morning!" | Should add zero items |
| Informal phrasing | 2 | "Lemme get uhh two of those egg mcmuffins" | Robustness to casual speech |
| Ambiguous | 2 | "I'll have a McMuffin" (which one?) | Should clarify, not guess |
| Complex combo | 2 | "Two Sausage Biscuits with egg and a Sausage Burrito" | Quantity + modifier + multi-item |

Pay attention to the "absence" categories. `not_on_menu`, `greeting`, and `ambiguous` all expect an **empty order**. Many eval setups only test for the presence of correct items and never test for the absence of incorrect ones:

```python
# Not-on-menu: agent should NOT add anything
("I'd like a Big Mac", [], "not_on_menu", "medium")

# Ambiguous: agent should clarify, not guess
("I'll have a McMuffin", [], "ambiguous", "hard")
```

Without these, you'd never catch the hallucination bug where the agent confidently adds an item that doesn't exist on the breakfast menu.

### Dataset Item Structure

Each test case lands in Langfuse with a clear contract between input and expected output:

```python
langfuse.create_dataset_item(
    id="order-correctness-008",                     # Deterministic ID
    dataset_name="drive-thru/order-correctness-v1",
    input={"customer_utterance": "Can I get two Sausage McMuffins and a Sausage Burrito"},
    expected_output={
        "expected_items": [
            {"item_id": "sausage-mcmuffin", "name": "Sausage McMuffin", "quantity": 2, ...},
            {"item_id": "sausage-burrito", "name": "Sausage Burrito", "quantity": 1, ...},
        ]
    },
    metadata={"category": "multi_item", "difficulty": "medium"},
)
```

Three design decisions worth calling out:

1. **Deterministic IDs** (`order-correctness-000`, `order-correctness-001`, ...): Re-running the seed script upserts rather than duplicating. You can run `make eval-seed` as many times as you want.

2. **Metadata for slicing**: `category` and `difficulty` let you filter results in the Langfuse UI — "how do we score on hard cases vs easy?" — without changing the dataset.

3. **Input/output contract**: `input.customer_utterance` is what the agent receives; `expected_output.expected_items` is what evaluators compare against. This contract is the bridge between dataset and evaluators.

The seed script itself is straightforward — create the dataset, iterate through test cases, create each item with a deterministic ID:

```python
langfuse.create_dataset(
    name=DATASET_NAME,
    description=DATASET_DESCRIPTION,
    metadata={"version": "1.0", "scope": "single-turn", "focus": "order-correctness"},
)

for i, (utterance, expected_items, category, difficulty) in enumerate(TEST_CASES):
    langfuse.create_dataset_item(
        id=f"order-correctness-{i:03d}",
        dataset_name=DATASET_NAME,
        input={"customer_utterance": utterance},
        expected_output={"expected_items": expected_items},
        metadata={"category": category, "difficulty": difficulty, "index": i},
    )
```

One command seeds everything:

```bash
make eval-seed
```

---

## The Experiment Runner

This is the core of the pipeline. We need a task function that invokes the agent, three item-level evaluators that score the results, and one run-level aggregator.

### The Task Function

Langfuse's `dataset.run_experiment()` expects a callable that takes a dataset item and returns output for evaluators to score. Our task function is the adapter between the LangGraph agent and Langfuse's evaluation framework:

```python
def eval_task(*, item, **kwargs):
    customer_utterance = item.input["customer_utterance"]
    menu = _get_menu()

    # Fresh graph with its own checkpointer — state isolation
    graph = _builder.compile(checkpointer=MemorySaver())
    thread_id = f"eval-{uuid.uuid4()}"

    # Same tracing handler used in production
    langfuse_handler = CallbackHandler()
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [langfuse_handler],
    }

    result = graph.invoke(
        {
            "messages": [HumanMessage(content=customer_utterance)],
            "menu": menu,
            "current_order": Order(),
        },
        config=config,
    )
```

Three things matter here:

**State isolation.** Each dataset item gets a fresh graph with its own `MemorySaver` and unique thread ID. Without this, state from one test case leaks into the next — an order for "two hash browns" carries over into the greeting test, causing a false failure.

**Tracing for free.** The same `CallbackHandler` that traces production conversations also traces eval runs. Every evaluation item shows up as a full trace in Langfuse, so you can click into any failing test case and inspect the exact LLM calls, tool invocations, and state transitions. This is invaluable when debugging why a test case scored 0.4 instead of 1.0.

**Thin adapter.** After invocation, the function reshapes the result into a dict for evaluators — order items, tool calls, response text, item count. Business logic belongs in evaluators, not here:

```python
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

    tool_calls = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(tc["name"])

    return {
        "order_items": order_items,
        "tool_calls": tool_calls,
        "response": response,
        "item_count": sum(i["quantity"] for i in order_items),
    }
```

### The Evaluators

We built three item-level evaluators and one run-level aggregator. All are deterministic — no LLM calls in the eval loop.

#### Order Correctness (0.0–1.0, weighted partial credit)

The primary metric. Did the agent get the order right?

The evaluator handles edge cases first. When both sides are empty (greetings, questions, off-menu requests), the answer is correct — the agent correctly did nothing. When expected is empty but the agent added items, that's hallucination — the worst failure. When expected has items but the agent produced nothing, it missed the order entirely. Both score 0.0:

```python
expected_items = expected_output.get("expected_items", [])
actual_items = output.get("order_items", [])

# Both empty — correct (greeting, question, not-on-menu)
if not expected_items and not actual_items:
    return Evaluation(name="order_correctness", value=1.0,
                      comment="Correctly added no items")

# Expected empty but got items — hallucination
if not expected_items and actual_items:
    return Evaluation(name="order_correctness", value=0.0,
                      comment=f"Expected no items but got: {[i['name'] for i in actual_items]}")

# Expected items but got nothing
if expected_items and not actual_items:
    return Evaluation(name="order_correctness", value=0.0,
                      comment=f"Expected {[i['name'] for i in expected_items]} but order is empty")
```

When both sides have items, matching happens by `item_id` using dict lookups — order-independent, so "hash brown, then McMuffin" scores the same as "McMuffin, then hash brown":

```python
expected_by_id = {item["item_id"]: item for item in expected_items}
actual_by_id = {item["item_id"]: item for item in actual_items}
```

Each matched item gets a weighted score:

| Component | Weight | Rationale |
|-----------|--------|-----------|
| Name match | 40% | Did it identify the right item? |
| Quantity match | 30% | Partial credit via ratio (ordered 2, got 3 → 0.3 x 2/3) |
| Modifier match | 20% | Jaccard similarity of modifier sets |
| Size match | 10% | Least critical — sensible defaults exist |

Quantity scoring gives partial credit for being close rather than treating off-by-one the same as a total miss:

```python
ratio = min(act["quantity"], exp["quantity"]) / max(act["quantity"], exp["quantity"])
item_score += 0.3 * ratio
```

Modifiers are compared as sets using Jaccard similarity:

```python
intersection = exp_mod_ids & act_mod_ids
union = exp_mod_ids | act_mod_ids
item_score += 0.2 * (len(intersection) / len(union))
```

> **Why partial credit?** "Got the right item but wrong quantity" is fundamentally different from "hallucinated an item that doesn't exist." Binary scoring hides that distinction. With weighted scoring, a regression from correct quantity to off-by-one shows as a visible dip — not a silent pass-to-fail cliff.

#### Tool Call Accuracy (0.0–1.0, protocol compliance)

This evaluator checks whether the agent followed the correct tool-calling protocol, independent of whether the order ended up correct.

Our agent has an explicit rule: always call `lookup_menu_item` before `add_item_to_order`. The lookup validates that the item exists and returns the canonical `item_id`. Skipping it means the agent is guessing — and an agent that guesses correctly today will break silently when the menu changes.

The evaluator checks temporal ordering:

```python
first_lookup = tool_calls.index("lookup_menu_item")
first_add = tool_calls.index("add_item_to_order")

if first_lookup < first_add:
    return Evaluation(name="tool_call_accuracy", value=1.0,
                      comment="Correct: lookup before add")
```

Scoring:
- **1.0** — Correct protocol (lookup before add)
- **0.5** — Both called but wrong order
- **0.3** — Only one of the two called
- **0.0** — Neither called when items were expected

#### No Hallucinated Items (binary, 0 or 1)

The simplest evaluator, catching the worst failure mode: the agent inventing menu items that don't exist.

```python
menu = _get_menu()
valid_ids = {item.item_id for item in menu.items}
hallucinated = [item for item in actual_items if item["item_id"] not in valid_ids]
```

If the agent adds a "McChicken" to a breakfast order, partial credit doesn't apply. Hallucination is a hard failure.

#### Average Order Correctness (run-level aggregate)

A run-level evaluator that receives all item results and computes the single number you compare between runs:

```python
def avg_order_correctness_evaluator(*, item_results, **kwargs):
    scores = [
        ev.value
        for result in item_results
        for ev in result.evaluations
        if ev.name == "order_correctness" and ev.value is not None
    ]
    avg = sum(scores) / len(scores)
    return Evaluation(name="avg_order_correctness", value=round(avg, 3),
                      comment=f"Average order correctness: {avg:.1%} across {len(scores)} items")
```

"Prompt v1: 87%. Prompt v2: 92%. Ship it."

### Wiring It Together

Everything connects in a single `run_experiment()` call:

```python
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
```

A few things to note:

- **`evaluators` vs `run_evaluators`**: Item evaluators score each dataset item independently. Run evaluators aggregate across all items. You'll typically have several item-level evaluators and one or two run-level ones.
- **`max_concurrency=1`**: Sequential execution for deterministic ordering and to avoid rate limits during development. Increase once stable.
- **`metadata`**: Record anything you might want to slice by later — model name, temperature, prompt version. You'll thank yourself.

Two commands cover the full workflow:

```bash
make eval                                    # Auto-generated run name
make eval ARGS='--run-name prompt-v2-test'   # Custom name for comparison
```

---

## Prompt Management and the Eval Loop

We use Langfuse's prompt management for version control over the system prompt. Prompts are seeded with a `production` label:

```python
langfuse.create_prompt(
    name="drive-thru/orchestrator",
    type="chat",
    prompt=[{"role": "system", "content": DRIVE_THRU_SYSTEM_PROMPT}],
    config={"model": "mistral-small-latest", "temperature": 0.0},
    labels=["production"],
)
```

At runtime, the agent fetches by label with a hardcoded fallback:

```python
def _get_system_prompt_template() -> str:
    try:
        langfuse = Langfuse(...)
        prompt = langfuse.get_prompt(PROMPT_NAME, label="production")
        if isinstance(prompt.prompt, list):
            for msg in prompt.prompt:
                if msg.get("role") == "system":
                    return msg["content"]
        return prompt.prompt
    except Exception:
        logger.warning("Failed to fetch prompt from Langfuse — using fallback")
        return FALLBACK_SYSTEM_PROMPT
```

This closes the loop: change a prompt in Langfuse, run `make eval`, and the new version is what gets evaluated. The run metadata records which model and settings were used, so you can always trace back what was tested.

Here's what the workflow looks like in practice:

```
1. Establish baseline: make eval → 87% order correctness
2. Change prompt (or model, or temperature, or tool definitions)
3. Re-run: make eval ARGS='--run-name after-prompt-v2' → 92%
4. Compare in Langfuse UI: which categories improved? Any regressions?
5. Decide: promote or revert
```

The `category` and `difficulty` metadata on each dataset item let you slice results in the Langfuse UI. An aggregate score of "87%" is useful for comparison, but "we went from 60% to 90% on informal phrasing while staying flat on everything else" tells you exactly what your prompt change accomplished.

---

## Lessons Learned

**Deterministic evaluators first.** No LLM calls in the eval loop means fast runs (~2 minutes for 25 items), zero eval cost beyond the agent's own LLM calls, and perfectly reproducible scores. LLM-as-Judge adds variance and cost — save it for subjective metrics like tone.

**Partial credit over binary pass/fail.** "Right item, wrong quantity" (score: ~0.7) is actionable signal. Binary scoring treats it the same as "hallucinated a different item" (score: 0.0). Weighted scoring makes regressions visible at a finer granularity.

**Order-independent matching everywhere.** Items matched by `item_id` via dict lookups. Modifiers compared as sets. The agent saying items in a different order than expected doesn't affect scores. This eliminates an entire class of false negatives.

**Test for absence, not just presence.** Eight of our 25 test cases expect an empty order. Without these, we'd never catch hallucination bugs.

**Idempotent everything.** Re-running `make eval-seed` upserts via deterministic IDs. Re-running `make eval` creates a new experiment run, never overwriting old ones. You can't accidentally destroy your baseline.

**Start with evaluation earlier.** Designing the dataset forced us to articulate what "correct" means — which clarified the agent's requirements. "Should the agent guess when someone says 'a McMuffin' without specifying which one?" is a requirements question, not an evaluation question. This thinking should happen before you build the agent, not after.

---

## What's Next

1. **LLM-as-Judge evaluators** for tone, helpfulness, and response conciseness
2. **Multi-turn conversation evaluation** — full ordering flows with modifications and confirmations
3. **CI integration** — fail the build if order correctness drops below a threshold
4. **Production traffic sampling** — evaluate live conversations offline to catch drift

---

## Quick-Start Reference

### Reproduce This

```bash
# 1. Install Langfuse SDK
uv add langfuse

# 2. Set environment variables (.env)
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# 3. Seed your dataset (one-time, idempotent)
make eval-seed

# 4. Run your first experiment
make eval

# 5. View results
# Langfuse UI → Datasets → drive-thru/order-correctness-v1 → Runs tab
```

### File Map

| File | Role |
|------|------|
| `scripts/seed_eval_dataset.py` | Creates 25-item dataset in Langfuse |
| `scripts/run_eval.py` | Experiment runner with 4 evaluators |
| `scripts/seed_langfuse_prompts.py` | Seeds prompts with production labels |
| `src/orchestrator/orchestrator/graph.py` | Agent graph with prompt fallback |
| `src/orchestrator/orchestrator/tools.py` | 4 tools (lookup, add, get, finalize) |
| `src/orchestrator/orchestrator/models.py` | Pydantic models (Item, Order, Menu) |
| `src/orchestrator/orchestrator/config.py` | Settings with Langfuse credentials |
| `Makefile` | `eval-seed` and `eval` targets |

### Evaluator Function Signatures (Langfuse v3)

For readers implementing their own evaluators:

```python
# Item-level: receives output and expected_output from the dataset item
def my_evaluator(*, output, expected_output, **kwargs) -> Evaluation:
    return Evaluation(name="my_metric", value=0.85, comment="details...")

# Run-level: receives all item results after the full run completes
def my_run_evaluator(*, item_results, **kwargs) -> Evaluation:
    return Evaluation(name="aggregate_metric", value=0.9, comment="...")
```

The `**kwargs` matters — Langfuse may pass additional context. Accept it even if you don't use it.

---

That's the full pipeline. Twenty-five test cases, four evaluators, one command. The next time you change a prompt, you'll know whether it's better — not because it "seemed good," but because you measured it.
