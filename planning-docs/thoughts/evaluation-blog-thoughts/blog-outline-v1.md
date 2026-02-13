<!-- created: 2026-02-13 -->

# Blog Outline: Building an Evaluation Pipeline for a Drive-Thru Ordering Agent with Langfuse v3

## Target Audience

Developers building LLM-powered agents who need to move beyond "vibes-based" testing toward structured, repeatable evaluation — especially those using LangGraph and Langfuse v3.

---

## Proposed Title Options

1. "From Vibes to Metrics: Building an Evaluation Pipeline for an AI Drive-Thru Agent"
2. "Evaluating LLM Agents the Right Way: Langfuse v3 + LangGraph in Practice"
3. "How We Built a Repeatable Evaluation System for Our AI Ordering Agent"

---

## Part 1: The Problem — Why You Can't Just Chat With Your Agent and Call It Tested

**Key points:**

- The agent: a McDonald's breakfast drive-thru chatbot built with LangGraph + Mistral, traced with Langfuse v3
- The temptation: manually testing a few orders, seeing them work, and shipping
- Why that fails:
  - No baseline to compare against when you change prompts or models
  - Can't detect regressions ("it used to handle 'gimme two hash browns' fine...")
  - No visibility into _how wrong_ a failure is (partial credit matters)
  - Impossible to systematically cover edge cases (informal phrasing, not-on-menu items, ambiguity)
- The goal: a pipeline where you change a prompt, run one command, and get a score you can compare to the last run

---

## Part 2: Designing the Evaluation Dataset

### 2.1 — What to Evaluate (Scoping)

- Decision to focus on **single-turn order correctness** first — the highest-impact capability
- Deliberately deferred: multi-turn flows, tone/politeness, response latency
- Rationale: start with deterministic, objective metrics before adding subjective ones

### 2.2 — Dataset Design Philosophy

- Why 25 well-chosen items beats 500 random ones
- Category-based coverage strategy:
  - **Easy (5):** Single items with straightforward names ("I'll have an Egg McMuffin")
  - **Quantity (2):** "Two hash browns", "three hotcakes"
  - **Multi-item (3):** "McMuffin and a coffee" — tests item separation
  - **Modifiers (3):** "Sausage McMuffin with egg" — tests modifier extraction
  - **Not on menu (3):** "Big Mac", "Quarter Pounder" — tests hallucination resistance
  - **Greetings/questions (2):** "Hi" / "What's on the menu?" — should add zero items
  - **Informal/colloquial (2):** "gimme", "uhh yeah lemme get..." — tests robustness to casual speech
  - **Ambiguous/complex (2):** Partial names, quantity + modifier combos

### 2.3 — Dataset Item Structure

- Each item: `input` (customer utterance), `expected_output` (expected items with id, name, qty, size, modifiers), `metadata` (category, difficulty)
- Why metadata matters: enables slicing results ("how do we do on hard cases vs easy?")

### 2.4 — Building the Seed Script (`seed_eval_dataset.py`)

- Langfuse v3 dataset API: `create_dataset()` + `create_dataset_item()`
- Idempotent design: deterministic IDs (`order-correctness-001`, `002`, ...) enable re-running without duplicates
- One-time execution via `make eval-seed`

---

## Part 3: The Experiment Runner — Connecting Agent to Evaluators

### 3.1 — The Task Function

- What Langfuse's `dataset.run_experiment()` expects: a function that takes a dataset item and returns output
- Our task function:
  1. Compiles a fresh LangGraph graph per item (state isolation via `MemorySaver` + unique thread ID)
  2. Invokes the agent with the customer utterance
  3. Extracts structured output: `order_items`, `tool_calls`, `response`
- Why state isolation matters: one test case must never leak into another

### 3.2 — Designing the Evaluators

**Three item-level evaluators, each measuring a different failure mode:**

#### Evaluator 1: Order Correctness (0.0–1.0, weighted partial credit)

- The primary metric — did the agent get the order right?
- Order-independent matching by `item_id` (not list position)
- Weighted scoring per item:
  - Name match: 40% (most important — did it identify the right item?)
  - Quantity match: 30% (partial credit for close quantities via ratio)
  - Modifier match: 20% (Jaccard similarity of modifier sets)
  - Size match: 10% (least critical, has sensible defaults)
- Special cases:
  - Both empty (greeting handled correctly) → 1.0
  - Expected empty but got items (hallucination) → 0.0
  - Expected items but got nothing (missed order) → 0.0

#### Evaluator 2: Tool Call Accuracy (0.0–1.0, protocol compliance)

- Does the agent follow the required workflow? (`lookup_menu_item` before `add_item_to_order`)
- Why this matters independently of order correctness: an agent could get the right answer through the wrong process
- Temporal ordering check: tool calls are a sequence, not a set

#### Evaluator 3: No Hallucinated Items (binary 0 or 1)

- Every item in the order must exist on the breakfast menu
- Catches the worst failure mode: making up menu items that don't exist
- Binary because hallucination is a hard failure, not a spectrum

**One run-level evaluator:**

#### Evaluator 4: Average Order Correctness (aggregate)

- Averages order correctness scores across all 25 items
- Provides the single number you compare between runs
- Enables quick "did this prompt change help or hurt?" decisions

### 3.3 — Running the Experiment

- `make eval` / `make eval ARGS='--run-name my-experiment'`
- Sequential execution (`max_concurrency=1`) for deterministic ordering
- Metadata attached to each run: model name, temperature, dataset version
- Results land in Langfuse UI under Datasets → Runs for side-by-side comparison

---

## Part 4: The Iteration Loop — How This Changes Your Development Workflow

### 4.1 — Before: The Old Way

```
1. Change prompt
2. Chat with agent manually
3. "Seems good" → ship
4. Users report broken orders → panic
```

### 4.2 — After: The Evaluation-Driven Way

```
1. Establish baseline: make eval → 87% order correctness
2. Change prompt (or model, or temperature)
3. Run again: make eval ARGS='--run-name after-prompt-v2' → 92%
4. Compare in Langfuse UI: which categories improved? Any regressions?
5. Decide: promote or revert
```

### 4.3 — What You Can Compare

- Model swaps (Mistral Small → Mistral Large)
- Prompt rewrites
- Temperature changes
- Tool definition changes
- Architecture changes (e.g., adding a reasoning step)

---

## Part 5: Langfuse v3 Integration Patterns

### 5.1 — v3 Migration Notes (for teams coming from v2)

- Import path change: `langfuse.langchain.CallbackHandler` (not `langfuse.callback`)
- Credentials on `Langfuse()` singleton, not on handler constructor
- Session ID via `config["metadata"]["langfuse_session_id"]` (not handler parameter)
- Flush via `get_client().flush()` (not `handler.flush()`)

### 5.2 — Prompt Management

- `seed_langfuse_prompts.py`: seeding versioned prompts with `production` label
- `get_prompt(name, label="production")` for runtime retrieval
- Fallback to hardcoded prompt when Langfuse is unavailable (graceful degradation)

### 5.3 — Observability as a Foundation for Evaluation

- The same `CallbackHandler` that traces production conversations also traces evaluation runs
- Every evaluation item execution is a full trace in Langfuse — you can inspect the agent's reasoning
- Session grouping: all turns in a conversation under one session ID

---

## Part 6: Lessons Learned & Practical Tips

### Design Decisions That Paid Off

1. **Deterministic evaluators first** — No LLM calls in the evaluation loop means fast, cheap, reproducible runs. Add LLM-as-Judge later for subjective quality.
2. **Partial credit over binary pass/fail** — "Got the right item but wrong quantity" is useful signal; binary scoring loses it.
3. **Order-independent matching** — Items matched by ID, not list position. The agent saying "hash brown, then McMuffin" vs "McMuffin, then hash brown" shouldn't affect the score.
4. **Idempotent everything** — Re-running seed scripts is safe. Re-running evaluations creates new runs, not duplicates.
5. **Metadata on dataset items** — Categories and difficulty labels enable sliced analysis without changing the dataset.

### What We'd Do Differently

1. Start with evaluation earlier — the dataset design forced us to articulate what "correct" means, which clarified the agent's requirements
2. More edge cases in v1 — 25 items is a starting point; production failures should feed back into the dataset

### What's Next (Not Yet Built)

1. LLM-as-Judge evaluators for tone, helpfulness, brevity
2. Multi-turn conversation evaluation (full ordering flow)
3. CI integration (run evaluations on every PR)
4. Production sampling (evaluate 5% of live traffic)

---

## Part 7: Quick-Start Reference

### Reproduce This in Your Own Project

```bash
# 1. Install Langfuse SDK
uv add langfuse

# 2. Set environment variables
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com  # or self-hosted

# 3. Seed your dataset
python scripts/seed_eval_dataset.py

# 4. Run your first experiment
python scripts/run_eval.py

# 5. View results in Langfuse UI
# Datasets → your-dataset → Runs tab
```

### Key Langfuse v3 SDK Methods Used

| Method | Purpose |
|--------|---------|
| `Langfuse()` | Initialize singleton with credentials |
| `langfuse.create_dataset(name)` | Create or get dataset |
| `langfuse.create_dataset_item(...)` | Add item with input/expected/metadata |
| `dataset.run_experiment(task_fn, evaluators=[], run_evaluators=[])` | Run full experiment |
| `langfuse.get_prompt(name, label)` | Fetch versioned prompt |
| `CallbackHandler()` | LangChain/LangGraph tracing |

---

## Appendix: File Map

| File | Role |
|------|------|
| `scripts/seed_eval_dataset.py` | Creates 25-item dataset in Langfuse |
| `scripts/run_eval.py` | Experiment runner with 4 evaluators |
| `scripts/seed_langfuse_prompts.py` | Seeds prompts with production labels |
| `docs/evaluations/langfuse-evaluations-tutorial.md` | Evaluation concepts guide |
| `planning-docs/thoughts/langfuse-evaluation-thoughts.md` | Original design brainstorm |
| `docs/architecture/architecture-decisions/009-langfuse-v3-observability.md` | ADR for Langfuse v3 integration |
| `src/orchestrator/orchestrator/main.py` | Langfuse handler setup |
| `src/orchestrator/orchestrator/graph.py` | Agent graph with prompt fallback |
| `Makefile` | `eval-seed` and `eval` targets |
