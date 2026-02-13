<!-- created: 2026-02-13 -->

# Blog Outline v2: Building an Evaluation Pipeline for a Drive-Thru Ordering Agent with Langfuse v3

## Writing Instructions for Agent

This outline is detailed enough to write a complete blog post. Follow these conventions:

- **Tone**: Technical but approachable. Write for a software engineer who has built an LLM app but hasn't set up evaluations yet. Assume familiarity with Python, LLMs, and basic tool-calling concepts.
- **Code snippets**: Embed actual code from the referenced files with line numbers. Use the `file_path:line_range` references below to pull exact code. Trim irrelevant lines (imports, logging) when showing snippets — focus on the logic.
- **Length**: Aim for ~3,000–4,000 words. Each Part should be 400–700 words.
- **Format**: Use headers, code blocks, tables, and callout boxes (> blockquotes for tips/warnings). No emojis.
- **Voice**: First person plural ("we built", "our agent") — this is a practitioner sharing their experience.

---

## Proposed Title

"From Vibes to Metrics: Building an Evaluation Pipeline for an AI Drive-Thru Agent with Langfuse v3"

---

## Part 1: The Problem — Why You Can't Just Chat With Your Agent and Call It Tested

**Goal**: Establish the motivation. Make the reader feel the pain of "vibes-based" testing so they want the solution.

**Structure**:

1. **Introduce the agent in 2–3 sentences.** A McDonald's breakfast drive-thru chatbot built with LangGraph + Mistral, traced with Langfuse v3. It takes natural language orders, looks up items on the menu, and builds a structured order. Link to the graph definition for context.
   - Reference: `src/orchestrator/orchestrator/graph.py:39-48` — `DriveThruState` showing the state schema (menu, current_order, reasoning)
   - Reference: `src/orchestrator/orchestrator/graph.py:399-421` — the 4-node graph construction (orchestrator → tools → update_order → loop)

2. **Describe the "vibes-based" workflow** that most teams start with:
   ```
   1. Change prompt
   2. Chat with agent manually
   3. "Seems good" → ship
   4. Users report broken orders → panic
   ```

3. **Articulate the specific failures this causes** (use concrete examples from our agent):
   - No baseline to compare against when you change prompts or swap models
   - Can't detect regressions ("it used to handle 'gimme two hash browns' fine, but after the prompt rewrite it stopped working")
   - No visibility into _how wrong_ a failure is — did it get the right item but wrong quantity? Or hallucinate an entirely different item? Binary pass/fail hides this.
   - Impossible to systematically cover edge cases: informal phrasing ("lemme get uhh..."), not-on-menu items ("Big Mac" during breakfast), ambiguous partial names ("a McMuffin")

4. **State the goal clearly**: A pipeline where you change a prompt, run `make eval`, and get a score you can compare to the last run. One command. Quantitative. Repeatable.

**Transition**: "To build this, we need three things: a dataset, evaluators, and a runner to connect them."

---

## Part 2: Designing the Evaluation Dataset

**Goal**: Teach dataset design thinking. This is the section where most blog posts are too thin — go deep on the _why_ behind the test case categories.

### 2.1 — Scoping: What to Evaluate First

- **Decision**: Focus on **single-turn order correctness** — the highest-impact, most measurable capability
- **Deliberately deferred**: Multi-turn conversation flows, tone/politeness, response latency, order modification
- **Rationale**: Start with deterministic, objective metrics. Subjective quality (tone, helpfulness) can come later with LLM-as-Judge. Getting the order right is table stakes.

> **Tip for the reader**: "When choosing what to evaluate first, pick the capability that (a) has a clear right answer and (b) matters most to your users. For us, that's order correctness — if the agent adds the wrong item, nothing else matters."

### 2.2 — Category-Based Coverage Strategy

Explain why 25 well-chosen test cases beat 500 random ones. The key insight: **structured coverage across failure modes** catches more bugs than volume.

Walk through each category with 1–2 example utterances and explain what failure mode it tests. Pull examples directly from the seed script:

| Category | Count | Example Utterance | What It Tests | Difficulty |
|----------|-------|-------------------|---------------|------------|
| Simple order | 5 | "I'll have an Egg McMuffin" | Basic item identification | Easy |
| Quantity | 2 | "Two hash browns please" | Numeric extraction | Easy–Medium |
| Multi-item | 3 | "Egg McMuffin and a Hash Brown" | Item separation in a single utterance | Medium |
| Modifiers | 3 | "Sausage McMuffin with egg" | Modifier extraction and attachment | Medium |
| Not on menu | 3 | "I'd like a Big Mac" | Hallucination resistance (should add nothing) | Medium |
| Greeting/question | 3 | "Hi, good morning!" / "What comes with the Big Breakfast?" | Should add zero items to order | Easy |
| Informal phrasing | 2 | "Lemme get uhh two of those egg mcmuffins" | Robustness to casual/colloquial speech | Medium–Hard |
| Ambiguous | 2 | "I'll have a McMuffin" (which one?) | Should clarify, not guess | Hard |
| Complex combo | 2 | "Two Sausage Biscuits with egg and a Sausage Burrito" | Quantity + modifier + multi-item combined | Hard |

- Reference: `scripts/seed_eval_dataset.py:36-389` — the full `TEST_CASES` list

**Call out the "absence" test cases**: Categories like `not_on_menu`, `greeting`, and `ambiguous` expect an **empty order**. This is critical — many eval setups only test for presence of correct items, not absence of incorrect ones.

- Reference: `scripts/seed_eval_dataset.py:251-267` — not-on-menu cases with empty expected output `[]`
- Reference: `scripts/seed_eval_dataset.py:326-331` — ambiguous case "I'll have a McMuffin" with empty expected (agent should clarify, not guess)

### 2.3 — Dataset Item Structure

Show the shape of a single dataset item as it lands in Langfuse:

```python
langfuse.create_dataset_item(
    id="order-correctness-008",           # Deterministic ID
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

- Reference: `scripts/seed_eval_dataset.py:427-437` — the `create_dataset_item` call with deterministic IDs

**Key design decisions to explain**:
1. **Deterministic IDs** (`order-correctness-000`, `001`, ...): Re-running the seed script upserts rather than duplicating. Reference: `scripts/seed_eval_dataset.py:428`
2. **Metadata for slicing**: `category` and `difficulty` let you filter results in the Langfuse UI ("how do we score on `hard` cases vs `easy`?") without changing the dataset. Reference: `scripts/seed_eval_dataset.py:432-435`
3. **Input/output contract**: `input.customer_utterance` is what the agent receives; `expected_output.expected_items` is what evaluators compare against. This contract is the bridge between dataset and evaluators.

### 2.4 — The Seed Script

Brief walkthrough of `seed_eval_dataset.py`. Emphasize idempotency and the one-command workflow.

- Reference: `scripts/seed_eval_dataset.py:392-441` — the `main()` function
- Reference: `Makefile:119-122` — the `make eval-seed` target

Show the command:
```bash
make eval-seed
# or: uv run --package orchestrator python scripts/seed_eval_dataset.py
```

---

## Part 3: The Experiment Runner — Connecting Agent to Evaluators

**Goal**: This is the core technical section. Walk through the task function, all four evaluators, and the experiment execution.

### 3.1 — The Task Function

Explain what Langfuse's `dataset.run_experiment()` expects: a callable that takes a dataset item and returns output for evaluators to score.

Show our task function with commentary on each critical decision:

- Reference: `scripts/run_eval.py:66-150` — the full `eval_task` function

**Key points to highlight with code**:

1. **State isolation** — Each item gets a fresh graph with its own `MemorySaver` and unique thread ID so one test case can't leak into another:
   ```python
   graph = _builder.compile(checkpointer=MemorySaver())
   thread_id = f"eval-{uuid.uuid4()}"
   ```
   - Reference: `scripts/run_eval.py:88-92`

2. **CallbackHandler for tracing** — The same handler that traces production conversations also traces eval runs. Every eval item execution is a full trace in Langfuse, so you can inspect the agent's tool calls and reasoning:
   ```python
   langfuse_handler = CallbackHandler()
   config = {
       "configurable": {"thread_id": thread_id},
       "callbacks": [langfuse_handler],
   }
   ```
   - Reference: `scripts/run_eval.py:94-103`

3. **Output extraction** — The task function returns a dict with `order_items`, `tool_calls`, and `response`. Each evaluator uses different keys from this dict:
   - Reference: `scripts/run_eval.py:116-150` — extracting order items, tool call sequence, and final response

> **Tip for the reader**: "The task function is the adapter between your agent and Langfuse's evaluation framework. Keep it thin — its job is to invoke your agent and reshape the output into a dict that evaluators can score."

### 3.2 — Designing the Evaluators

**Framing**: Three item-level evaluators, each catching a different class of failure. Plus one run-level aggregator. All deterministic — no LLM calls in the eval loop.

#### Evaluator 1: Order Correctness (0.0–1.0, weighted partial credit)

This is the primary metric. Did the agent get the order right?

- Reference: `scripts/run_eval.py:161-266` — full `order_correctness_evaluator`

**Walk through the scoring logic in detail** (this is the most interesting part for readers):

1. **Edge cases first** (lines 180-205):
   - Both expected and actual empty → 1.0 (greeting handled correctly)
   - Expected empty but got items → 0.0 (hallucination — the worst failure)
   - Expected items but got nothing → 0.0 (missed the order entirely)

2. **Order-independent matching by item_id** (lines 208-210):
   ```python
   expected_by_id = {item["item_id"]: item for item in expected_items}
   actual_by_id = {item["item_id"]: item for item in actual_items}
   ```
   Explain why this matters: the agent saying "hash brown, then McMuffin" vs "McMuffin, then hash brown" shouldn't affect the score.

3. **Weighted per-item scoring** (lines 221-253):

   | Component | Weight | Rationale |
   |-----------|--------|-----------|
   | Name match | 40% | Most important — did it identify the right item? |
   | Quantity match | 30% | Partial credit via ratio (ordered 2, got 3 → 0.3 * 2/3) |
   | Size match | 10% | Least critical — sensible defaults exist |
   | Modifier match | 20% | Jaccard similarity of modifier sets (order-independent) |

   Show the quantity partial credit logic:
   ```python
   ratio = min(act["quantity"], exp["quantity"]) / max(act["quantity"], exp["quantity"])
   item_score += 0.3 * ratio
   ```
   - Reference: `scripts/run_eval.py:233-237`

   Show the modifier Jaccard similarity:
   ```python
   intersection = exp_mod_ids & act_mod_ids
   union = exp_mod_ids | act_mod_ids
   item_score += 0.2 * (len(intersection) / len(union))
   ```
   - Reference: `scripts/run_eval.py:249-251`

> **Design decision callout**: "We chose partial credit over binary pass/fail because 'got the right item but wrong quantity' is fundamentally different from 'hallucinated an item that doesn't exist.' Binary scoring loses that signal."

#### Evaluator 2: Tool Call Accuracy (0.0–1.0, protocol compliance)

- Reference: `scripts/run_eval.py:269-343` — full `tool_call_accuracy_evaluator`

Explain what "protocol compliance" means for this agent:
- The agent MUST call `lookup_menu_item` before `add_item_to_order` (this is enforced in the system prompt rules 2-3)
- Reference: `src/orchestrator/orchestrator/graph.py:70-73` — system prompt rules requiring lookup before add
- Reference: `src/orchestrator/orchestrator/tools.py:16-31` — the `lookup_menu_item` tool docstring reinforcing this

**Why this matters independently of order correctness**: An agent could get the right answer by skipping the lookup and calling `add_item_to_order` directly with a guessed item_id. The order would be correct, but the process is wrong — and fragile.

Show the temporal ordering check:
```python
first_lookup = tool_calls.index("lookup_menu_item")
first_add = tool_calls.index("add_item_to_order")
if first_lookup < first_add:
    return Evaluation(name="tool_call_accuracy", value=1.0, ...)
```
- Reference: `scripts/run_eval.py:330-337`

Scoring breakdown:
- 1.0: Correct protocol (lookup before add)
- 0.5: Both called but in wrong order
- 0.3: Only one of the two called
- 0.0: Neither called when items were expected

#### Evaluator 3: No Hallucinated Items (binary 0 or 1)

- Reference: `scripts/run_eval.py:346-380` — full `no_hallucinated_items_evaluator`

The simplest evaluator but catches the worst failure mode: making up menu items that don't exist.

```python
menu = _get_menu()
valid_ids = {item.item_id for item in menu.items}
hallucinated = [item for item in actual_items if item["item_id"] not in valid_ids]
```
- Reference: `scripts/run_eval.py:365-368`

**Why binary and not a spectrum**: Hallucination is a hard failure. If the agent adds a "McChicken" to a breakfast order, partial credit makes no sense.

#### Evaluator 4: Average Order Correctness (run-level aggregate)

- Reference: `scripts/run_eval.py:386-405` — full `avg_order_correctness_evaluator`

This is a **run-level** evaluator (not item-level). It receives all item results and computes a single aggregate score.

```python
scores = [
    ev.value
    for result in item_results
    for ev in result.evaluations
    if ev.name == "order_correctness" and ev.value is not None
]
avg = sum(scores) / len(scores)
```
- Reference: `scripts/run_eval.py:390-401`

This is the number you compare between runs: "Prompt v1: 87%. Prompt v2: 92%. Ship it."

### 3.3 — Running the Experiment

Show the complete `run_experiment()` call and explain each parameter:

- Reference: `scripts/run_eval.py:433-449` — the `dataset.run_experiment()` invocation

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

**Key parameters to explain**:
- `evaluators` vs `run_evaluators`: Item-level vs run-level. Item evaluators score each dataset item independently. Run evaluators aggregate across all items.
- `max_concurrency=1`: Sequential execution for deterministic ordering and to avoid rate limits during development. Can be increased later.
- `metadata`: Attached to the run so you can filter/compare in the Langfuse UI.

Show the commands:
```bash
make eval                                    # Auto-generated run name
make eval ARGS='--run-name prompt-v2-test'   # Custom run name
```
- Reference: `Makefile:124-127` — the `make eval` target

---

## Part 4: The Langfuse v3 Integration Layer

**Goal**: Show the Langfuse-specific patterns that make this work. Useful for readers who are setting up Langfuse for the first time or migrating from v2.

### 4.1 — Client Initialization Pattern

Show the singleton pattern used across the codebase:

```python
langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_base_url,
)
```
- Reference: `scripts/run_eval.py:34-38` — eval runner initialization
- Reference: `src/orchestrator/orchestrator/config.py:43-46` — credentials in Settings

### 4.2 — Prompt Management

Explain the prompt versioning workflow:
1. Seed prompts with `production` label via `seed_langfuse_prompts.py`
2. Runtime fetches by label: `langfuse.get_prompt(name, label="production")`
3. Fallback to hardcoded prompt when Langfuse is unavailable

- Reference: `scripts/seed_langfuse_prompts.py:72-93` — the PROMPTS list with chat type and config
- Reference: `scripts/seed_langfuse_prompts.py:104-111` — `create_prompt()` with `labels=["production"]`
- Reference: `src/orchestrator/orchestrator/graph.py:101-134` — `_get_system_prompt_template()` with fallback logic

**Why this matters for evaluation**: When you change a prompt in Langfuse and re-run `make eval`, you're evaluating the new prompt version. The eval run metadata records which model and settings were used, so you can trace back exactly what was tested.

### 4.3 — CallbackHandler: Tracing as the Foundation for Evaluation

The same `CallbackHandler` traces both production conversations (in `main.py`) and evaluation runs (in `run_eval.py`):

- Production: `scripts/run_eval.py:83-98` — handler created per eval item
- CLI: `src/orchestrator/orchestrator/main.py:19-38` — `_create_langfuse_handler()` for CLI sessions

**Key insight for readers**: "You don't need separate instrumentation for production and evaluation. The same tracing setup captures both. Every evaluation item execution shows up as a full trace in Langfuse — you can click into any failing test case and see the exact LLM calls, tool invocations, and responses."

### 4.4 — Langfuse v3 SDK Methods Reference

Provide a quick-reference table of the SDK methods used across the project:

| Method | Where Used | Purpose |
|--------|-----------|---------|
| `Langfuse(public_key, secret_key, host)` | `run_eval.py:34` | Initialize client singleton |
| `langfuse.create_dataset(name, description, metadata)` | `seed_eval_dataset.py:410` | Create/upsert dataset |
| `langfuse.create_dataset_item(id, dataset_name, input, expected_output, metadata)` | `seed_eval_dataset.py:427` | Add test case (idempotent via deterministic id) |
| `langfuse.get_dataset(name)` | `run_eval.py:425` | Fetch dataset for experiment |
| `dataset.run_experiment(name, task, evaluators, run_evaluators, ...)` | `run_eval.py:433` | Run full experiment |
| `langfuse.create_prompt(name, type, prompt, config, labels)` | `seed_langfuse_prompts.py:105` | Seed versioned prompt |
| `langfuse.get_prompt(name, label)` | `graph.py:120` | Fetch prompt at runtime |
| `CallbackHandler()` | `run_eval.py:98`, `main.py:38` | LangChain/LangGraph tracing |
| `langfuse.flush()` | `run_eval.py:459` | Ensure all events are sent |
| `Evaluation(name, value, comment)` | `run_eval.py:176` | Return type for evaluator functions |

---

## Part 5: The Iteration Loop — How This Changes Your Development Workflow

**Goal**: Connect the technical implementation back to the developer experience. Make the reader feel how evaluation changes their daily work.

### 5.1 — The Workflow in Practice

Show the before/after contrast:

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

### 5.2 — What You Can Compare Across Runs

Give concrete examples of what developers actually test with this pipeline:
- **Model swaps**: Mistral Small → Mistral Large (is the accuracy gain worth the latency/cost?)
- **Prompt rewrites**: Reworded Rule #7 about multi-item handling → did multi-item scores improve?
- **Temperature changes**: 0.0 → 0.3 (does creativity help or hurt order accuracy?)
- **Tool definition changes**: Improved the `lookup_menu_item` docstring → did tool call accuracy go up?
- **Architecture changes**: Added a `reasoning` step → did complex cases improve?

### 5.3 — Using Metadata to Slice Results

Reference back to the metadata on dataset items (`category`, `difficulty`) and explain how to use the Langfuse UI to answer questions like:
- "How do we score on `hard` cases vs `easy`?"
- "Did the prompt change help `informal` phrasing but hurt `modifier` cases?"
- "Which specific test cases regressed?"

---

## Part 6: Lessons Learned and Practical Tips

**Goal**: Share hard-won insights. This is the section that distinguishes a blog post from documentation.

### Design Decisions That Paid Off

1. **Deterministic evaluators first, no LLM-as-Judge yet**: No LLM calls in the eval loop means fast (~2 min for 25 items), cheap ($0 eval cost), and perfectly reproducible runs. LLM-as-Judge adds variance — save it for subjective metrics later.

2. **Partial credit over binary pass/fail**: "Got the right item but wrong quantity" (score: 0.7) gives you actionable signal. Binary pass/fail would score this the same as "hallucinated a completely different item" (score: 0.0). The weighted scoring at `run_eval.py:221-253` makes regressions visible.

3. **Order-independent matching everywhere**: Items matched by `item_id` dict lookup, modifiers compared as sets. The agent saying items in a different order than expected doesn't affect scores. This required deliberate design in both the evaluators and the dataset structure.

4. **Idempotent everything**: Re-running `make eval-seed` is safe (upserts via deterministic IDs). Re-running `make eval` creates a new experiment run, never overwrites old ones. You can never accidentally destroy your baseline.

5. **Testing for absence, not just presence**: Five of our 25 test cases expect an empty order (greetings, questions, not-on-menu items). Without these, we'd never catch hallucination bugs where the agent invents items.

### What We'd Do Differently

1. **Start with evaluation earlier**: Designing the dataset forced us to articulate what "correct" means — which clarified the agent's requirements. This thinking should happen before building the agent, not after.

2. **More edge cases in v1**: 25 items is a minimum viable dataset. Production failures (once we have them) should feed back into the dataset as regression tests.

### What's Next (Not Yet Built)

1. **LLM-as-Judge evaluators** for tone, helpfulness, and response conciseness
2. **Multi-turn conversation evaluation** (full ordering flow: greeting → order → modify → confirm → finalize)
3. **CI integration** (run evaluations on every PR, fail the build if order correctness drops below threshold)
4. **Production traffic sampling** (evaluate 5% of live conversations offline)

---

## Part 7: Quick-Start Reference

**Goal**: Give the reader a copy-paste starting point to replicate this in their own project.

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
| `src/orchestrator/orchestrator/models.py` | Pydantic models (Item, Order, Menu) | `Order.__add__` L123-139 (quantity merging) |
| `src/orchestrator/orchestrator/config.py` | Settings with Langfuse credentials | `Settings` L16-46 |
| `Makefile` | `eval-seed` and `eval` targets | L119-127 |

### Evaluator Function Signatures (Langfuse v3 SDK)

For readers implementing their own evaluators, show the exact function signatures expected by `run_experiment()`:

```python
# Item-level evaluator: receives output and expected_output
def my_evaluator(*, output, expected_output, **kwargs) -> Evaluation:
    return Evaluation(name="my_metric", value=0.85, comment="details...")

# Run-level evaluator: receives all item_results
def my_run_evaluator(*, item_results, **kwargs) -> Evaluation:
    return Evaluation(name="aggregate_metric", value=0.9, comment="...")
```

Reference: `scripts/run_eval.py:161-173` (item-level signature), `scripts/run_eval.py:386-388` (run-level signature)
