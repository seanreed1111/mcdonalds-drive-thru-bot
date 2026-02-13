<!-- created: 2026-02-13 -->

# From Vibes to Metrics: Building an Evaluation Pipeline for an AI Drive-Thru Agent with Langfuse v3

You built an LLM-powered agent. It mostly works. You changed the prompt, chatted with it a few times, and it "seemed good." Ship it.

We've all been there. This post walks through how we moved past vibes-based testing for our McDonald's breakfast drive-thru chatbot and built a repeatable, quantitative evaluation pipeline using Langfuse v3. One command, a score we can compare, and the confidence to actually ship prompt changes.

---

## Part 1: The Problem — Why You Can't Just Chat With Your Agent and Call It Tested

Our agent is a McDonald's breakfast drive-thru chatbot built with LangGraph and Mistral, traced with Langfuse v3. A customer says something like "I'll have two Egg McMuffins and a hash brown," and the agent looks up items on the menu, validates they exist, and builds a structured order. The core architecture is a 4-node LangGraph state machine:

```python
# graph.py — DriveThruState (the state schema)
class DriveThruState(MessagesState):
    menu: Menu                                         # Loaded menu for this location
    current_order: Order                               # Customer's order in progress
    reasoning: Annotated[list[str], operator.add]      # LLM decision rationale log
```

The graph itself is straightforward: an orchestrator LLM decides what to do, calls tools, updates the order, and loops back.

```python
# graph.py — Graph construction
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

Before we had evaluations, our development workflow looked like this:

```
1. Change prompt
2. Chat with agent manually — try 3-4 orders
3. "Seems good" → ship
4. Users report broken orders a week later → panic
```

This workflow has specific, painful failure modes:

- **No baseline to compare against.** You change the prompt or swap models and have no way to tell if things got better or worse.
- **Can't detect regressions.** The agent used to handle "gimme two hash browns" fine, but after a prompt rewrite it stopped working — and you don't notice for days.
- **No visibility into *how wrong* a failure is.** Did it get the right item but wrong quantity? Or hallucinate an entirely different item? Binary "it worked / it didn't" hides this distinction completely.
- **Impossible to systematically cover edge cases.** Informal phrasing ("lemme get uhh..."), off-menu items ("Big Mac" during breakfast), ambiguous partial names ("a McMuffin") — you'd need to remember to test all of these manually, every time.

The goal: a pipeline where you change a prompt, run `make eval`, and get a score you can compare to the last run. One command. Quantitative. Repeatable.

To build this, we need three things: a dataset, evaluators, and a runner to connect them.

---

## Part 2: Designing the Evaluation Dataset

### Scoping: What to Evaluate First

We focused on **single-turn order correctness** — the highest-impact, most measurable capability. Given one customer utterance, does the agent produce the correct order?

We deliberately deferred multi-turn conversation flows, tone and politeness, response latency, and order modification. These are all worth evaluating eventually, but they require more complex test harnesses and often more subjective scoring. Start with something deterministic and objective.

> **Tip**: When choosing what to evaluate first, pick the capability that (a) has a clear right answer and (b) matters most to your users. For us, that's order correctness — if the agent adds the wrong item, nothing else matters.

### Category-Based Coverage Strategy

Twenty-five well-chosen test cases beat 500 random ones. The key insight: **structured coverage across failure modes** catches more bugs than volume. We defined nine categories, each targeting a specific failure mode:

| Category | Count | Example Utterance | What It Tests | Difficulty |
|----------|-------|-------------------|---------------|------------|
| Simple order | 5 | "I'll have an Egg McMuffin" | Basic item identification | Easy |
| Quantity | 2 | "Two hash browns please" | Numeric extraction | Easy-Medium |
| Multi-item | 3 | "Egg McMuffin and a Hash Brown" | Item separation in a single utterance | Medium |
| Modifiers | 3 | "Sausage McMuffin with egg" | Modifier extraction and attachment | Medium |
| Not on menu | 3 | "I'd like a Big Mac" | Hallucination resistance (should add nothing) | Medium |
| Greeting/question | 3 | "Hi, good morning!" | Should add zero items to order | Easy |
| Informal phrasing | 2 | "Lemme get uhh two of those egg mcmuffins" | Robustness to casual speech | Medium-Hard |
| Ambiguous | 2 | "I'll have a McMuffin" (which one?) | Should clarify, not guess | Hard |
| Complex combo | 2 | "Two Sausage Biscuits with egg and a Sausage Burrito" | Quantity + modifier + multi-item combined | Hard |

Pay special attention to the "absence" test cases. Categories like `not_on_menu`, `greeting`, and `ambiguous` expect an **empty order**. This is critical — many eval setups only test for the presence of correct items, never for the absence of incorrect ones.

```python
# seed_eval_dataset.py — Not-on-menu cases expect empty orders
(
    "I'd like a Big Mac",
    [],           # Empty — agent should NOT add anything
    "not_on_menu",
    "medium",
),
```

```python
# seed_eval_dataset.py — Ambiguous case: agent should clarify, not guess
(
    "I'll have a McMuffin",
    [],           # Could be Egg McMuffin, Sausage McMuffin, etc.
    "ambiguous",
    "hard",
),
```

Without these cases, we would never catch the hallucination bug where the agent confidently adds an item that doesn't exist on the breakfast menu.

### Dataset Item Structure

Each test case lands in Langfuse as a dataset item with a clear contract between input and expected output:

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

Three design decisions here are worth calling out:

1. **Deterministic IDs** (`order-correctness-000`, `order-correctness-001`, ...): Re-running the seed script upserts rather than duplicating. You can safely run `make eval-seed` as many times as you want.

2. **Metadata for slicing**: `category` and `difficulty` let you filter results in the Langfuse UI — "how do we score on `hard` cases vs `easy`?" — without changing the dataset itself.

3. **Input/output contract**: `input.customer_utterance` is what the agent receives; `expected_output.expected_items` is what evaluators compare against. This contract is the bridge between dataset and evaluators. Get it right and everything downstream is cleaner.

### The Seed Script

The seed script (`scripts/seed_eval_dataset.py`) is intentionally simple. It creates the dataset, then iterates through `TEST_CASES` and creates each item with a deterministic ID:

```python
# seed_eval_dataset.py — main()
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
# or: uv run --package orchestrator python scripts/seed_eval_dataset.py
```

---

## Part 3: The Experiment Runner — Connecting Agent to Evaluators

This is the core technical section. We need a task function that invokes the agent, three item-level evaluators that score the results, and a run-level aggregator.

### The Task Function

Langfuse's `dataset.run_experiment()` expects a callable that takes a dataset item and returns output for evaluators to score. Our task function (`eval_task`) is the adapter between our LangGraph agent and Langfuse's evaluation framework.

```python
# run_eval.py — eval_task (abbreviated)
def eval_task(*, item, **kwargs):
    customer_utterance = item.input["customer_utterance"]
    menu = _get_menu()

    # Compile a fresh graph with its own checkpointer for state isolation
    graph = _builder.compile(checkpointer=MemorySaver())
    thread_id = f"eval-{uuid.uuid4()}"

    # Trace every eval item as a full Langfuse trace
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

Three critical decisions here:

**State isolation.** Each dataset item gets a fresh graph with its own `MemorySaver` and a unique thread ID. Without this, state from one test case leaks into the next — an order for "two hash browns" would carry over into the greeting test, causing it to fail.

**CallbackHandler for tracing.** The same handler that traces production conversations also traces eval runs. Every evaluation item execution shows up as a full trace in Langfuse, so you can click into any failing test case and inspect the exact LLM calls, tool invocations, and responses.

**Output extraction.** After invoking the graph, the task function reshapes the result into a dict that evaluators can score:

```python
    # Extract structured output for evaluators
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

    return {
        "order_items": order_items,
        "tool_calls": tool_calls,
        "response": response,
        "item_count": sum(i["quantity"] for i in order_items),
    }
```

> **Tip**: Keep the task function thin. Its job is to invoke your agent and reshape the output into a dict that evaluators can score. Business logic belongs in evaluators, not here.

### Designing the Evaluators

We built three item-level evaluators, each catching a different class of failure, plus one run-level aggregator. All are deterministic — no LLM calls in the eval loop.

#### Evaluator 1: Order Correctness (0.0-1.0, weighted partial credit)

This is the primary metric. Did the agent get the order right?

The evaluator starts with edge cases:

```python
# run_eval.py — order_correctness_evaluator
expected_items = expected_output.get("expected_items", [])
actual_items = output.get("order_items", [])

# Both empty — correct behavior (greeting, question, not-on-menu)
if not expected_items and not actual_items:
    return Evaluation(name="order_correctness", value=1.0,
                      comment="Correctly added no items")

# Expected empty but got items — hallucination (the worst failure)
if not expected_items and actual_items:
    return Evaluation(name="order_correctness", value=0.0,
                      comment=f"Expected no items but got: {[i['name'] for i in actual_items]}")

# Expected items but got nothing — missed the order entirely
if expected_items and not actual_items:
    return Evaluation(name="order_correctness", value=0.0,
                      comment=f"Expected {[i['name'] for i in expected_items]} but order is empty")
```

When both sides have items, we match by `item_id` using dict lookups (order-independent — the agent saying "hash brown, then McMuffin" vs "McMuffin, then hash brown" doesn't affect the score):

```python
expected_by_id = {item["item_id"]: item for item in expected_items}
actual_by_id = {item["item_id"]: item for item in actual_items}
```

Each matched item is scored with weighted components:

| Component | Weight | Rationale |
|-----------|--------|-----------|
| Name match | 40% | Most important — did it identify the right item? |
| Quantity match | 30% | Partial credit via ratio (ordered 2, got 3 = 0.3 x 2/3) |
| Size match | 10% | Least critical — sensible defaults exist |
| Modifier match | 20% | Jaccard similarity of modifier sets (order-independent) |

The quantity scoring gives partial credit for being close:

```python
# Partial credit for close quantities
ratio = min(act["quantity"], exp["quantity"]) / max(act["quantity"], exp["quantity"])
item_score += 0.3 * ratio
```

Modifiers are compared as sets using Jaccard similarity:

```python
intersection = exp_mod_ids & act_mod_ids
union = exp_mod_ids | act_mod_ids
item_score += 0.2 * (len(intersection) / len(union))
```

> **Design decision**: We chose partial credit over binary pass/fail because "got the right item but wrong quantity" is fundamentally different from "hallucinated an item that doesn't exist." Binary scoring loses that signal. With weighted scoring, a regression from "correct quantity" to "off-by-one quantity" shows as a visible dip, not a silent pass-to-fail cliff.

#### Evaluator 2: Tool Call Accuracy (0.0-1.0, protocol compliance)

This evaluator checks that the agent followed the correct tool-calling protocol, independent of whether the order ended up correct.

Our agent has explicit rules in its system prompt: always call `lookup_menu_item` before `add_item_to_order`. This isn't just a guideline — it's a safety mechanism. The lookup tool validates that the item exists on the menu and returns the canonical `item_id`. Skipping it means the agent is guessing.

```python
# graph.py — system prompt rules
# 2. When a customer orders an item, ALWAYS call lookup_menu_item first to verify it exists.
# 3. Only call add_item_to_order for items confirmed to exist via lookup_menu_item.
```

Why does this matter independently of order correctness? An agent could get the right answer by skipping the lookup and calling `add_item_to_order` directly with a guessed `item_id`. The order would be correct, but the process is fragile — one menu change and it breaks silently.

The evaluator checks temporal ordering:

```python
# run_eval.py — tool_call_accuracy_evaluator
first_lookup = tool_calls.index("lookup_menu_item")
first_add = tool_calls.index("add_item_to_order")

if first_lookup < first_add:
    return Evaluation(name="tool_call_accuracy", value=1.0,
                      comment="Correct: lookup before add")
```

Scoring breakdown:
- **1.0**: Correct protocol (lookup before add)
- **0.5**: Both called but in wrong order
- **0.3**: Only one of the two called
- **0.0**: Neither called when items were expected

#### Evaluator 3: No Hallucinated Items (binary 0 or 1)

The simplest evaluator, but it catches the worst failure mode: the agent making up menu items that don't exist.

```python
# run_eval.py — no_hallucinated_items_evaluator
menu = _get_menu()
valid_ids = {item.item_id for item in menu.items}
hallucinated = [item for item in actual_items if item["item_id"] not in valid_ids]
```

If the agent adds a "McChicken" to a breakfast order, partial credit makes no sense. Hallucination is a hard failure — binary scoring is the right choice here.

#### Evaluator 4: Average Order Correctness (run-level aggregate)

This is a **run-level** evaluator, not item-level. It receives all item results and computes a single aggregate score — the number you compare between runs.

```python
# run_eval.py — avg_order_correctness_evaluator
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

This is the number you compare between runs: "Prompt v1: 87%. Prompt v2: 92%. Ship it."

### Running the Experiment

Everything comes together in a single `run_experiment()` call:

```python
# run_eval.py — run_experiment invocation
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

Key parameters:

- **`evaluators` vs `run_evaluators`**: Item evaluators score each dataset item independently. Run evaluators aggregate across all items. You'll typically have many item-level evaluators and one or two run-level ones.
- **`max_concurrency=1`**: Sequential execution for deterministic ordering and to avoid rate limits during development. Increase this once your pipeline is stable.
- **`metadata`**: Attached to the run so you can filter and compare in the Langfuse UI. Record anything you might want to slice by later — model name, temperature, prompt version.

Two commands cover the workflow:

```bash
make eval                                    # Auto-generated run name
make eval ARGS='--run-name prompt-v2-test'   # Custom run name for comparison
```

---

## Part 4: The Langfuse v3 Integration Layer

This section covers the Langfuse-specific patterns that tie everything together. Useful whether you're setting up Langfuse for the first time or looking at how to structure evaluation alongside production tracing.

### Client Initialization

The Langfuse client is initialized with credentials from environment variables managed by pydantic-settings:

```python
# config.py — Settings
class Settings(BaseSettings):
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"
```

```python
# run_eval.py — client initialization
langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_base_url,
)
```

### Prompt Management

We use Langfuse's prompt management for version control over our system prompt. The workflow:

1. **Seed prompts** with a `production` label via `seed_langfuse_prompts.py`:

```python
# seed_langfuse_prompts.py — creating a versioned prompt
langfuse.create_prompt(
    name="drive-thru/orchestrator",
    type="chat",
    prompt=[{"role": "system", "content": DRIVE_THRU_SYSTEM_PROMPT}],
    config={"model": "mistral-small-latest", "temperature": 0.0},
    labels=["production"],
)
```

2. **Runtime fetches by label**, with a fallback if Langfuse is unavailable:

```python
# graph.py — prompt fetch with fallback
def _get_system_prompt_template() -> str:
    try:
        langfuse = Langfuse(...)
        prompt = langfuse.get_prompt(PROMPT_NAME, label="production")
        # Extract system message from chat prompt
        if isinstance(prompt.prompt, list):
            for msg in prompt.prompt:
                if msg.get("role") == "system":
                    return msg["content"]
        return prompt.prompt
    except Exception:
        logger.warning("Failed to fetch prompt from Langfuse — using fallback")
        return FALLBACK_SYSTEM_PROMPT
```

This matters for evaluation because when you change a prompt in Langfuse and re-run `make eval`, you're evaluating the new prompt version. The eval run metadata records which model and settings were used, so you can trace back exactly what was tested.

### CallbackHandler: Tracing as the Foundation for Evaluation

The same `CallbackHandler` from `langfuse.langchain` traces both production conversations and evaluation runs:

```python
# Production (main.py)
langfuse_handler = CallbackHandler()
config["callbacks"] = [langfuse_handler]

# Evaluation (run_eval.py)
langfuse_handler = CallbackHandler()
config = {
    "configurable": {"thread_id": thread_id},
    "callbacks": [langfuse_handler],
}
```

You don't need separate instrumentation for production and evaluation. The same tracing setup captures both. Every evaluation item execution shows up as a full trace in Langfuse — you can click into any failing test case and see the exact LLM calls, tool invocations, and responses. This is enormously valuable when debugging why a particular test case scored 0.4 instead of 1.0.

### Langfuse v3 SDK Methods Reference

A quick-reference table of the SDK methods used across the project:

| Method | Where Used | Purpose |
|--------|-----------|---------|
| `Langfuse(public_key, secret_key, host)` | `run_eval.py` | Initialize client |
| `langfuse.create_dataset(name, description, metadata)` | `seed_eval_dataset.py` | Create/upsert dataset |
| `langfuse.create_dataset_item(id, dataset_name, input, expected_output, metadata)` | `seed_eval_dataset.py` | Add test case (idempotent via deterministic id) |
| `langfuse.get_dataset(name)` | `run_eval.py` | Fetch dataset for experiment |
| `dataset.run_experiment(name, task, evaluators, run_evaluators, ...)` | `run_eval.py` | Execute full experiment |
| `langfuse.create_prompt(name, type, prompt, config, labels)` | `seed_langfuse_prompts.py` | Seed versioned prompt |
| `langfuse.get_prompt(name, label)` | `graph.py` | Fetch prompt at runtime |
| `CallbackHandler()` | `run_eval.py`, `main.py` | LangChain/LangGraph tracing |
| `langfuse.flush()` | `run_eval.py` | Ensure all events are sent |
| `Evaluation(name, value, comment)` | `run_eval.py` | Return type for evaluator functions |

---

## Part 5: The Iteration Loop — How This Changes Your Development Workflow

### The Workflow in Practice

Here's the before and after:

**Before (vibes-based)**:
```
1. Change prompt
2. Chat with agent manually — try 3-4 orders
3. "Seems good" → ship
4. Users report broken orders a week later → panic
```

**After (evaluation-driven)**:
```
1. Establish baseline: make eval → 87% order correctness
2. Change prompt (or model, or temperature, or tool definitions)
3. Re-run: make eval ARGS='--run-name after-prompt-v2' → 92%
4. Compare in Langfuse UI: which categories improved? Any regressions?
5. Decide: promote the new prompt to production or revert
```

The key shift is from subjective confidence to quantitative comparison. You don't need to feel good about the change — you can see whether it's better.

### What You Can Compare Across Runs

Concrete examples of what developers actually test with this pipeline:

- **Model swaps**: Mistral Small vs. Mistral Large — is the accuracy gain worth the latency and cost?
- **Prompt rewrites**: Reworded Rule #7 about multi-item handling — did multi-item scores improve without breaking anything else?
- **Temperature changes**: 0.0 vs. 0.3 — does creativity help or hurt order accuracy?
- **Tool definition changes**: Improved the `lookup_menu_item` docstring — did tool call accuracy go up?
- **Architecture changes**: Added a `reasoning` step to the graph — did complex cases improve?

Each of these is a single `make eval` run with a descriptive name. Langfuse stores every run, so you can always go back and compare.

### Using Metadata to Slice Results

Remember the `category` and `difficulty` metadata on each dataset item? In the Langfuse UI, these let you answer questions like:

- "How do we score on `hard` cases vs `easy`?"
- "Did the prompt change help `informal` phrasing but hurt `modifier` cases?"
- "Which specific test cases regressed between runs?"

This granularity is what makes evaluation actionable. An aggregate score of "87%" is useful for comparison, but "we went from 60% to 90% on informal phrasing while staying flat on everything else" tells you exactly what your prompt change accomplished.

---

## Part 6: Lessons Learned and Practical Tips

### Design Decisions That Paid Off

**1. Deterministic evaluators first, no LLM-as-Judge yet.** No LLM calls in the eval loop means fast runs (~2 minutes for 25 items), zero eval cost beyond the agent's own LLM calls, and perfectly reproducible scores. LLM-as-Judge adds variance and cost — save it for subjective metrics like tone and helpfulness.

**2. Partial credit over binary pass/fail.** "Got the right item but wrong quantity" (score: ~0.7) gives you actionable signal. Binary pass/fail would score this the same as "hallucinated a completely different item" (score: 0.0). The weighted scoring makes regressions visible at a much finer granularity.

**3. Order-independent matching everywhere.** Items are matched by `item_id` using dict lookups. Modifiers are compared as sets. The agent saying items in a different order than expected doesn't affect scores. This required deliberate design in both the evaluators and the dataset structure — but it eliminates an entire class of false negatives.

**4. Idempotent everything.** Re-running `make eval-seed` is safe because dataset items are upserted via deterministic IDs. Re-running `make eval` creates a new experiment run and never overwrites old ones. You can never accidentally destroy your baseline.

**5. Testing for absence, not just presence.** Eight of our 25 test cases expect an empty order (greetings, questions, not-on-menu items, ambiguous names). Without these, we would never catch hallucination bugs where the agent invents items that don't exist on the breakfast menu.

### What We'd Do Differently

**Start with evaluation earlier.** Designing the dataset forced us to articulate what "correct" means — which clarified the agent's requirements. Questions like "should the agent guess when someone says 'a McMuffin' without specifying which one?" are requirements questions, not evaluation questions. This thinking should happen before building the agent, not after.

**More edge cases in v1.** Twenty-five items is a minimum viable dataset. Production failures — once we have them — should feed back into the dataset as regression tests. Every bug report is a free test case.

### What's Next (Not Yet Built)

1. **LLM-as-Judge evaluators** for tone, helpfulness, and response conciseness
2. **Multi-turn conversation evaluation** — full ordering flows: greeting, order, modify, confirm, finalize
3. **CI integration** — run evaluations on every PR, fail the build if order correctness drops below a threshold
4. **Production traffic sampling** — evaluate a percentage of live conversations offline to catch drift

---

## Part 7: Quick-Start Reference

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

| File | Role | Key Lines |
|------|------|-----------|
| `scripts/seed_eval_dataset.py` | Creates 25-item dataset in Langfuse | `TEST_CASES` L36-389, `main()` L392-441 |
| `scripts/run_eval.py` | Experiment runner with 4 evaluators | `eval_task` L66-150, evaluators L161-405, `run_experiment` L433-449 |
| `scripts/seed_langfuse_prompts.py` | Seeds prompts with production labels | `PROMPTS` L72-93, `create_prompt` L105-111 |
| `src/orchestrator/orchestrator/graph.py` | Agent graph with prompt fallback | `DriveThruState` L39-48, graph L399-421, prompt fallback L101-134 |
| `src/orchestrator/orchestrator/tools.py` | 4 tools (lookup, add, get, finalize) | `lookup_menu_item` L17-67, `add_item_to_order` L71-135 |
| `src/orchestrator/orchestrator/models.py` | Pydantic models (Item, Order, Menu) | `Order.__add__` for quantity merging |
| `src/orchestrator/orchestrator/config.py` | Settings with Langfuse credentials | `Settings` L16-46 |
| `Makefile` | `eval-seed` and `eval` targets | L119-127 |

### Evaluator Function Signatures (Langfuse v3 SDK)

For readers implementing their own evaluators, here are the exact function signatures expected by `run_experiment()`:

```python
# Item-level evaluator: receives output and expected_output from the dataset item
def my_evaluator(*, output, expected_output, **kwargs) -> Evaluation:
    return Evaluation(name="my_metric", value=0.85, comment="details...")

# Run-level evaluator: receives all item results after the full run completes
def my_run_evaluator(*, item_results, **kwargs) -> Evaluation:
    return Evaluation(name="aggregate_metric", value=0.9, comment="...")
```

The `**kwargs` is important — Langfuse may pass additional context. Accept it even if you don't use it.

---

That's the full pipeline. Twenty-five test cases, four evaluators, one command. The next time you change a prompt, you'll know whether it's better — not because it "seems good," but because you measured it.
