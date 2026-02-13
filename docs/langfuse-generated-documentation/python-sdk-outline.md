<!-- modified: 2026-02-12 -->

# Langfuse Python SDK v3 - Beginner Outline

> SDK v3 is built on OpenTelemetry. This outline covers v3 only.

## Table of Contents

- [1. Installation & Setup](#1-installation--setup)
- [2. Tracing (Observability)](#2-tracing-observability)
  - [2a. @observe decorator](#2a-observe-decorator-recommended)
  - [2b. Context managers](#2b-context-managers)
  - [2c. Manual observations](#2c-manual-observations)
  - [Trace attributes](#trace-attributes)
  - [Flushing](#flushing)
- [3. Prompt Management](#3-prompt-management)
  - [3.1 create_prompt()](#31-create_prompt)
  - [3.2 get_prompt()](#32-get_prompt)
  - [3.3 update_prompt()](#33-update_prompt)
  - [3.4 Prompt Object Properties & Methods](#34-prompt-object-properties--methods)
  - [3.5 Compilation — compile()](#35-compilation--compile)
  - [3.6 Versioning & Labels](#36-versioning--labels)
  - [3.7 Config](#37-config)
  - [3.8 SDK Caching](#38-sdk-caching)
  - [3.9 Linking Prompts to Traces](#39-linking-prompts-to-traces)
  - [3.10 LangChain Integration — get_langchain_prompt()](#310-langchain-integration--get_langchain_prompt)
  - [3.11 Prompt Folders](#311-prompt-folders)
- [4. Scores & Evaluation](#4-scores--evaluation)
- [5. Datasets & Experiments](#5-datasets--experiments)
  - [5.1 Dataset CRUD](#51-dataset-crud)
  - [5.2 Dataset Items](#52-dataset-items)
  - [5.3 Dataset Versioning](#53-dataset-versioning)
  - [5.4 Running Experiments (High-Level API)](#54-running-experiments-high-level-api)
  - [5.5 Task Function](#55-task-function)
  - [5.6 Evaluators (Item-Level)](#56-evaluators-item-level)
  - [5.7 The Evaluation Object](#57-the-evaluation-object)
  - [5.8 Run Evaluators (Aggregate)](#58-run-evaluators-aggregate)
  - [5.9 ExperimentResult Object](#59-experimentresult-object)
  - [5.10 Low-Level Dataset Iteration](#510-low-level-dataset-iteration)
  - [5.11 AutoEvals Integration](#511-autoevals-integration)
  - [5.12 Comparing Runs in the UI](#512-comparing-runs-in-the-ui)
- [6. Framework Integrations](#6-framework-integrations)
- [7. Additional Configuration](#7-additional-configuration)
- [8. Feature Checklist](#8-feature-checklist)
- [Quick Reference](#quick-reference)

---

## 1. Installation & Setup

```bash
pip install langfuse
```

### Authentication (environment variables)

| Variable | Purpose |
|---|---|
| `LANGFUSE_SECRET_KEY` | Secret API key |
| `LANGFUSE_PUBLIC_KEY` | Public API key |
| `LANGFUSE_BASE_URL` | Server URL (EU: `https://cloud.langfuse.com`, US: `https://us.cloud.langfuse.com`) |

### Client initialization

```python
from langfuse import get_client

langfuse = get_client()  # reads env vars automatically
```

---

## 2. Tracing (Observability)

Core concepts: **traces** (one per request) contain nested **observations** (individual steps).

Observation types: `span`, `generation`, `event`, `agent`, `tool`, `chain`, `retriever`, `evaluator`, `embedding`, `guardrail`.

### 2a. `@observe` decorator (recommended)

```python
from langfuse import observe

@observe()
def my_function(data):
    return process(data)

@observe(as_type="generation", name="llm-call")
async def call_llm(prompt):
    ...
```

### 2b. Context managers

```python
with langfuse.start_as_current_observation(as_type="span", name="step") as span:
    span.update(output="done")
```

### 2c. Manual observations

```python
span = langfuse.start_observation(name="parent")
child = span.start_observation(name="child", as_type="generation")
child.end()
span.end()
```

### Trace attributes

```python
from langfuse import propagate_attributes

with propagate_attributes(
    user_id="user_123",
    session_id="session_abc",
    metadata={"experiment": "v1"},
    tags=["test"],
):
    my_function()
```

### Flushing

Short-lived scripts must call `langfuse.flush()` or `langfuse.shutdown()` before exit. Long-running servers flush automatically in the background.

---

## 3. Prompt Management

### 3.1 `create_prompt()`

```python
langfuse.create_prompt(
    name="movie-critic",              # required, unique name (use / for folders)
    type="text",                      # required: "text" or "chat" (immutable after creation)
    prompt="As a {{level}} critic, rate {{movie}}.",  # required
    labels=["production"],            # optional, version labels
    config={                          # optional, arbitrary JSON
        "model": "gpt-4o",
        "temperature": 0.7,
    },
)
```

Calling `create_prompt` with an existing name creates a **new version** (auto-incrementing).

#### Text prompts

`prompt` is a single string:

```python
langfuse.create_prompt(
    name="greeting",
    type="text",
    prompt="Hello {{name}}, you are a {{role}}.",
)
```

#### Chat prompts

`prompt` is a list of message objects with `role` and `content`:

```python
langfuse.create_prompt(
    name="assistant",
    type="chat",
    prompt=[
        {"role": "system", "content": "You are a {{role}}"},
        {"role": "user", "content": "{{query}}"},
    ],
)
```

#### Chat prompts with message placeholders

Insert dynamic message arrays (e.g. chat history) at a specific position:

```python
langfuse.create_prompt(
    name="chat-with-history",
    type="chat",
    prompt=[
        {"role": "system", "content": "You are {{role}}"},
        {"type": "placeholder", "name": "chat_history"},
        {"role": "user", "content": "{{query}}"},
    ],
)
```

### 3.2 `get_prompt()`

```python
prompt = langfuse.get_prompt(
    name="movie-critic",            # required
    version=None,                   # optional int, specific version number
    label=None,                     # optional str, defaults to "production"
    type=None,                      # optional: "text" or "chat" (for type hints)
    cache_ttl_seconds=60,           # optional, SDK cache TTL (0 to disable)
    fallback=None,                  # optional, used when fetch fails and no cache
)
```

`version` and `label` are mutually exclusive. When neither is set, `label="production"` is implied.

Returns `TextPromptClient` or `ChatPromptClient`.

#### Fetch examples

```python
prompt = langfuse.get_prompt("movie-critic")                    # production label, 60s cache
prompt = langfuse.get_prompt("movie-critic", version=3)         # exact version
prompt = langfuse.get_prompt("movie-critic", label="staging")   # custom label
prompt = langfuse.get_prompt("movie-critic", label="latest", cache_ttl_seconds=0)  # dev: no cache
```

#### Fallback

Provide a fallback prompt for guaranteed availability when the API is unreachable and no cache exists:

```python
prompt = langfuse.get_prompt(
    "movie-critic",
    fallback="As a movie critic, what do you think of {{movie}}?",
)

if prompt.is_fallback:
    print("Using fallback — API unavailable")
```

For chat prompts, pass a list of messages as the fallback. When a fallback is used, no link is created between the prompt and traces.

### 3.3 `update_prompt()`

Assign labels to an existing version (labels are merged, not replaced):

```python
langfuse.update_prompt(
    name="movie-critic",    # required
    version=3,              # required, version to update
    new_labels=["production", "approved"],  # required
)
```

The `"latest"` label is auto-managed and cannot be set manually.

### 3.4 Prompt Object Properties & Methods

```python
prompt = langfuse.get_prompt("movie-critic")

# Properties
prompt.name          # str
prompt.version       # int
prompt.prompt        # str (text) or list[dict] (chat)
prompt.config        # dict
prompt.labels        # list[str]
prompt.type          # "text" or "chat"
prompt.is_fallback   # bool — True when using fallback
```

### 3.5 Compilation — `compile()`

Replaces `{{variable}}` placeholders with values.

#### Text prompts

```python
prompt = langfuse.get_prompt("greeting")
compiled = prompt.compile(name="Alice", role="developer")
# -> "Hello Alice, you are a developer."
```

#### Chat prompts

```python
prompt = langfuse.get_prompt("assistant", type="chat")
compiled = prompt.compile(role="helpful assistant", query="What is AI?")
# -> [{"role": "system", "content": "You are a helpful assistant"},
#     {"role": "user", "content": "What is AI?"}]
```

#### Chat prompts with placeholders

Pass variables as the first dict and placeholders as the second:

```python
prompt = langfuse.get_prompt("chat-with-history", type="chat")
compiled = prompt.compile(
    {"role": "helpful", "query": "What now?"},
    {
        "chat_history": [
            {"role": "user", "content": "I like sci-fi"},
            {"role": "assistant", "content": "Try Dune"},
        ]
    },
)
# -> [{"role": "system", "content": "You are helpful"},
#     {"role": "user", "content": "I like sci-fi"},
#     {"role": "assistant", "content": "Try Dune"},
#     {"role": "user", "content": "What now?"}]
```

### 3.6 Versioning & Labels

- Each `create_prompt` call with the same name increments the version (1, 2, 3, ...).
- **`production`** — default label fetched by `get_prompt`.
- **`latest`** — auto-maintained, always points to the newest version.
- **Custom labels** — `"staging"`, `"tenant-a"`, `"experiment-v2"`, etc.

Promote a version:

```python
langfuse.update_prompt(name="movie-critic", version=5, new_labels=["production"])
```

Rollback:

```python
langfuse.update_prompt(name="movie-critic", version=3, new_labels=["production"])
```

### 3.7 Config

The `config` field is an arbitrary JSON object versioned alongside the prompt. Common uses:

```python
config = {
    "model": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 1000,
    "response_format": {"type": "json_schema", "json_schema": {...}},
    "tools": [{"type": "function", "function": {...}}],
    "tool_choice": "auto",
}
```

Access after fetching:

```python
prompt = langfuse.get_prompt("invoice-extractor")
model = prompt.config.get("model")
tools = prompt.config.get("tools", [])
```

### 3.8 SDK Caching

The SDK uses a **stale-while-revalidate** pattern:

| State | Behavior |
|---|---|
| Cache fresh | Return immediately |
| Cache stale | Return stale value, refetch in background |
| Cache miss | Block and fetch from API |
| Network failure + no cache | Use `fallback` if provided, else raise |

Control TTL per call:

```python
langfuse.get_prompt("x", cache_ttl_seconds=300)  # 5-minute cache
langfuse.get_prompt("x", cache_ttl_seconds=0)    # always fetch fresh
```

Pre-fetch on startup to warm the cache:

```python
def warmup():
    langfuse.get_prompt("prompt-a")
    langfuse.get_prompt("prompt-b")

warmup()
```

### 3.9 Linking Prompts to Traces

Linking lets Langfuse track metrics per prompt version (latency, tokens, cost, scores).

#### With the OpenAI wrapper

```python
from langfuse.openai import OpenAI

client = OpenAI()
prompt = langfuse.get_prompt("calculator")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=prompt.compile(base=10),
    langfuse_prompt=prompt,          # links generation to this prompt version
)
```

#### With `@observe`

```python
from langfuse import observe, get_client

@observe(as_type="generation")
def call_llm():
    prompt = get_client().get_prompt("movie-critic")
    get_client().update_current_generation(prompt=prompt)
    # ... LLM call ...

@observe()
def main():
    call_llm()
```

#### With context managers

```python
prompt = langfuse.get_prompt("movie-critic")

with langfuse.start_as_current_observation(
    as_type="generation", name="critic", model="gpt-4o", prompt=prompt,
) as gen:
    gen.update(output="Great movie!")
```

### 3.10 LangChain Integration — `get_langchain_prompt()`

Converts `{{var}}` to `{var}` for LangChain compatibility. Optionally pre-compiles some variables.

#### Text prompts

```python
from langchain_core.prompts import PromptTemplate

langfuse_prompt = langfuse.get_prompt("movie-critic")

langchain_prompt = PromptTemplate.from_template(
    langfuse_prompt.get_langchain_prompt()              # {{var}} -> {var}
)
# or pre-compile some variables
langchain_prompt = PromptTemplate.from_template(
    langfuse_prompt.get_langchain_prompt(country="USA") # country resolved, rest converted
)
```

#### Chat prompts

```python
from langchain_core.prompts import ChatPromptTemplate

langfuse_prompt = langfuse.get_prompt("assistant", type="chat")

langchain_prompt = ChatPromptTemplate.from_messages(
    langfuse_prompt.get_langchain_prompt()
)
```

#### Link prompt to LangChain traces

Set metadata on the **PromptTemplate** (not the LLM):

```python
langchain_prompt.metadata = {"langfuse_prompt": langfuse_prompt}

chain = langchain_prompt | llm
chain.invoke({"query": "Hello"}, config={"callbacks": [handler]})
```

### 3.11 Prompt Folders

Use `/` in names to organize prompts into virtual folders (requires `langfuse >= 3.0.2`):

```python
langfuse.create_prompt(name="agents/support/greeting", type="text", prompt="Hi {{name}}")
langfuse.get_prompt("agents/support/greeting")
```

The UI renders these as a folder tree. No limit on nesting depth.

---

## 4. Scores & Evaluation

### Score types

| Type | Example values |
|---|---|
| `NUMERIC` | `0.0` - `1.0` (or custom range) |
| `CATEGORICAL` | `"correct"`, `"incorrect"` |
| `BOOLEAN` | `0` or `1` |

### Creating scores

```python
# Low-level
langfuse.create_score(trace_id="...", name="accuracy", value=0.9, data_type="NUMERIC")

# Inside a context manager
with langfuse.start_as_current_observation(as_type="span", name="op") as span:
    span.score(name="accuracy", value=0.9, data_type="NUMERIC")
    span.score_trace(name="overall", value=0.95)

# From anywhere in an observed call stack
langfuse.score_current_span(name="accuracy", value=0.9)
langfuse.score_current_trace(name="overall", value=0.95)
```

### LLM-as-a-Judge

Automated evaluation using LLMs, configured in the Langfuse UI. Runs on traces, observations, or dataset runs.

---

## 5. Datasets & Experiments

### 5.1 Dataset CRUD

#### `create_dataset()`

```python
langfuse.create_dataset(
    name="qa-set",                          # required, unique within project
    description="QA pairs",                 # optional
    metadata={"author": "alice"},           # optional, any JSON object
    input_schema={...},                     # optional, JSON Schema for item inputs
    expected_output_schema={...},           # optional, JSON Schema for item expected outputs
)
```

Use `/` in names for folder organization (e.g. `"evaluation/qa-set"`).

#### `get_dataset()`

```python
dataset = langfuse.get_dataset("qa-set")                        # latest version
dataset = langfuse.get_dataset("qa-set", version=some_datetime)  # snapshot at timestamp
```

Returns a dataset object with a `.items` attribute containing all ACTIVE items.

#### `get_datasets()`

Returns a list of all datasets in the project.

### 5.2 Dataset Items

#### `create_dataset_item()`

```python
langfuse.create_dataset_item(
    dataset_name="qa-set",                    # required
    input={"question": "What is Langfuse?"},  # any Python object
    expected_output="An observability tool",  # any Python object
    metadata={"difficulty": "easy"},          # optional
    source_trace_id="trace_abc",              # optional, link to an existing trace
    source_observation_id="obs_xyz",          # optional, link to a specific observation
    id="item-001",                            # optional, enables upsert
    status="ACTIVE",                          # "ACTIVE" (default) or "ARCHIVED"
)
```

Key behaviors:

- **Upsert**: Providing `id` updates an existing item with that ID instead of creating a new one.
- **Schema validation**: If the parent dataset has `input_schema` or `expected_output_schema`, items are validated on creation.
- **From traces**: Set `source_trace_id` (and optionally `source_observation_id`) to record where the item originated. Also available via the "Add to dataset" button in the UI.

#### Item status

| Status | Behavior |
|---|---|
| `ACTIVE` | Included in experiment runs (default) |
| `ARCHIVED` | Excluded from future experiment runs |

Archive or restore by upserting with the `id` and new `status`.

### 5.3 Dataset Versioning

Every add, update, or archive of items produces a new dataset version (identified by timestamp). Fetch a historical snapshot:

```python
from datetime import datetime, timezone

dataset = langfuse.get_dataset(
    "qa-set",
    version=datetime(2026, 1, 15, 6, 30, 0, tzinfo=timezone.utc),
)
```

Omit `version` to get the latest state.

---

### 5.4 Running Experiments (High-Level API)

Two entry points depending on data source:

#### On a Langfuse dataset

```python
dataset = langfuse.get_dataset("qa-set")

result = dataset.run_experiment(
    name="baseline",                   # required
    description="First attempt",       # optional
    task=my_task,                      # required, callable
    evaluators=[accuracy_eval],        # optional, item-level evaluators
    run_evaluators=[avg_accuracy],     # optional, run-level (aggregate) evaluators
    run_name="baseline-2026-02-12",    # optional, custom run name
    max_concurrency=3,                 # optional, default 3
    metadata={"model": "gpt-4o"},      # optional, attached to all traces
)
```

Creates a **dataset run** in Langfuse (visible in UI for comparison).

#### On local data

```python
result = langfuse.run_experiment(
    name="local-test",
    data=[                             # list of dicts with input/expected_output
        {"input": "What is AI?", "expected_output": "Artificial Intelligence"},
    ],
    task=my_task,
    evaluators=[accuracy_eval],
    run_evaluators=[avg_accuracy],
    max_concurrency=5,
    metadata={"model": "gpt-4o"},
)
```

Creates traces only (no dataset run).

---

### 5.5 Task Function

The `task` callable receives a dataset item and returns the application output.

```python
# For Langfuse datasets — item is a DatasetItemClient object
def my_task(*, item, **kwargs):
    question = item.input           # attribute access
    expected = item.expected_output
    meta = item.metadata
    return call_my_llm(question)

# For local data — item is a plain dict
def my_task(*, item, **kwargs):
    question = item["input"]        # dict access
    return call_my_llm(question)
```

Async tasks are fully supported:

```python
async def my_task(*, item, **kwargs):
    client = AsyncOpenAI()
    resp = await client.chat.completions.create(...)
    return resp.choices[0].message.content
```

---

### 5.6 Evaluators (Item-Level)

An evaluator receives the task's input, output, and expected output, and returns an `Evaluation`.

```python
from langfuse import Evaluation

def accuracy_eval(*, input, output, expected_output, metadata, item, langfuse, **kwargs):
    match = expected_output and expected_output.lower() in output.lower()
    return Evaluation(
        name="accuracy",            # required
        value=1.0 if match else 0.0,# required (float for NUMERIC, str for CATEGORICAL)
        comment="Exact substring match", # optional
        data_type="NUMERIC",        # optional: "NUMERIC", "CATEGORICAL", "BOOLEAN"
    )
```

Available kwargs passed by the framework:

| Kwarg | Type | Description |
|---|---|---|
| `input` | any | Input passed to the task |
| `output` | any | Output returned by the task |
| `expected_output` | any | Expected output from the dataset item |
| `metadata` | dict | Metadata from the dataset item |
| `item` | object/dict | Full dataset item |
| `langfuse` | client | Langfuse client instance |

Pass multiple evaluators as a list:

```python
evaluators=[accuracy_eval, relevance_eval, length_eval]
```

Async evaluators are supported with the same signature.

### 5.7 The `Evaluation` Object

```python
Evaluation(
    name="accuracy",         # str, required — score name
    value=0.9,               # float | str, required — score value
    comment="Looks correct", # str, optional — reasoning
    data_type="NUMERIC",     # str, optional — "NUMERIC", "CATEGORICAL", "BOOLEAN"
)
```

### 5.8 Run Evaluators (Aggregate)

Run evaluators receive all item results after the experiment completes and return aggregate metrics.

```python
def avg_accuracy(*, item_results, **kwargs):
    scores = [
        e.value
        for r in item_results
        for e in r.evaluations
        if e.name == "accuracy"
    ]
    avg = sum(scores) / len(scores) if scores else 0.0
    return Evaluation(name="avg_accuracy", value=avg, comment=f"{avg:.2%}")
```

Pass via `run_evaluators=[avg_accuracy]`.

---

### 5.9 `ExperimentResult` Object

```python
result = dataset.run_experiment(...)

# Formatted table of results
print(result.format())

# Access aggregate scores programmatically
for ev in result.run_evaluations:
    print(ev.name, ev.value)
```

#### Use in CI / pytest

```python
def test_quality_threshold():
    result = langfuse.run_experiment(
        name="ci-check", data=test_data, task=my_task,
        evaluators=[accuracy_eval], run_evaluators=[avg_accuracy],
    )
    avg = next(e.value for e in result.run_evaluations if e.name == "avg_accuracy")
    assert avg >= 0.8, f"Accuracy {avg:.2f} below threshold"
```

---

### 5.10 Low-Level Dataset Iteration

For full control, iterate items manually with the `item.run()` context manager:

```python
from langfuse import get_client

langfuse = get_client()
dataset = langfuse.get_dataset("qa-set")
run_name = f"manual-{datetime.now().isoformat()}"

for item in dataset.items:
    with item.run(
        run_name=run_name,                  # required, include timestamp for uniqueness
        run_description="Manual run",       # optional
        run_metadata={"model": "gpt-4o"},   # optional
    ) as root_span:
        output = my_app(item.input)

        langfuse.update_current_trace(input=item.input, output=output)

        root_span.score_trace(
            name="correctness",
            value=my_eval(item.input, output, item.expected_output),
        )

langfuse.flush()
```

The high-level `run_experiment()` is recommended over manual iteration for most use cases.

---

### 5.11 AutoEvals Integration

```python
from langfuse.experiment import create_evaluator_from_autoevals
from autoevals.llm import Factuality

evaluator = create_evaluator_from_autoevals(Factuality())

result = langfuse.run_experiment(
    name="factuality-check",
    data=test_data,
    task=my_task,
    evaluators=[evaluator],
)
```

### 5.12 Comparing Runs in the UI

1. Navigate to **Datasets > select dataset > Runs** tab.
2. Each run shows aggregated scores, cost, and latency.
3. Select multiple runs and click **Compare** for side-by-side view: aggregate metric charts, item-level output diffs, score differences, and trace links for debugging.

---

## 6. Framework Integrations

### OpenAI (drop-in wrapper)

```python
from langfuse.openai import OpenAI   # swap import, everything else unchanged

client = OpenAI()
client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
    name="greeting",
    metadata={"key": "value"},
)
```

Async variant: `from langfuse.openai import AsyncOpenAI`.

### LangChain / LangGraph

```python
from langfuse.langchain import CallbackHandler

handler = CallbackHandler()

# LangChain
chain.invoke(input, config={"callbacks": [handler]})

# LangGraph (same mechanism — LangGraph is built on LangChain)
graph.invoke(input, config={"callbacks": [handler]})
```

### LlamaIndex

Automatic instrumentation via OpenTelemetry when the Langfuse SDK is initialized.

---

## 7. Additional Configuration

| Environment variable | Purpose |
|---|---|
| `LANGFUSE_TRACING_ENVIRONMENT` | Tag traces with environment (production, staging, etc.) |
| `LANGFUSE_TRACING_RELEASE` | Tag traces with release version |
| `LANGFUSE_OBSERVE_DECORATOR_IO_CAPTURE_ENABLED` | Enable/disable I/O capture on `@observe` |

---

## 8. Feature Checklist

- **Sessions** - group traces by conversation
- **Environments** - production / staging / dev separation
- **Tags & metadata** - flexible categorization and key-value storage
- **User tracking** - attribute traces to end users
- **Token & cost tracking** - automatic for supported models
- **Sampling** - control trace volume
- **Masking** - PII protection
- **Media upload** - images and other media in traces
- **Distributed tracing** - W3C Trace Context propagation

---

## Quick Reference

| Task | Code |
|---|---|
| Initialize client | `langfuse = get_client()` |
| Trace a function | `@observe()` |
| Trace an LLM call | `@observe(as_type="generation")` |
| Fetch a prompt | `langfuse.get_prompt("name")` |
| Score a trace | `langfuse.score_current_trace(name="x", value=0.9)` |
| Run an experiment | `dataset.run_experiment(name="x", task=fn, evaluators=[...])` |
| Flush before exit | `langfuse.flush()` |
