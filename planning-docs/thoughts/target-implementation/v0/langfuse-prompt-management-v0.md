# Langfuse Prompt Management for Drive-Thru Voice AI

> **Related Documents:**
> - [LangGraph State Design](./langgraph-state-design-v0.md) – Workflow architecture, state schema, and Langfuse observability setup
> - [Langfuse Evaluation](./langfuse-evaluation-v0.md) – Systematic evaluation of application behavior
> - [Workflow Thoughts](./workflow-thoughts.md) – High-level ordering workflow requirements

---

## Table of Contents

- [Overview](#overview)
- [Langfuse Prompt Concepts](#langfuse-prompt-concepts)
  - [Prompt Types](#prompt-types)
  - [Labels and Versioning](#labels-and-versioning)
- [Prompt Organization Strategy](#prompt-organization-strategy)
  - [Naming Convention](#naming-convention)
  - [Prompt Catalog](#prompt-catalog)
- [Creating Prompts in Langfuse](#creating-prompts-in-langfuse)
  - [Via Python SDK](#via-python-sdk)
  - [Via Langfuse UI](#via-langfuse-ui)
- [Using Prompts in LangGraph Nodes](#using-prompts-in-langgraph-nodes)
  - [Basic Pattern](#basic-pattern)
  - [Linking Prompts to Traces](#linking-prompts-to-traces)
- [Prompt Testing Workflow](#prompt-testing-workflow)
  - [Local Development](#local-development)
  - [Evaluation with Datasets](#evaluation-with-datasets)
  - [Automated Evaluation](#automated-evaluation)
- [Deployment Strategy](#deployment-strategy)
  - [Label Promotion Flow](#label-promotion-flow)
  - [Code Pattern for Label-Based Fetching](#code-pattern-for-label-based-fetching)
  - [Cache Considerations](#cache-considerations)
- [Monitoring and Iteration](#monitoring-and-iteration)
  - [Key Metrics to Track](#key-metrics-to-track)
  - [Linking Metrics to Prompts](#linking-metrics-to-prompts)
  - [Analyzing Prompt Performance](#analyzing-prompt-performance)
- [Fallback Strategy](#fallback-strategy)
- [Best Practices Summary](#best-practices-summary)
- [Next Steps](#next-steps)

---

## Overview

This document outlines a consistent approach to managing prompts using Langfuse for the McDonald's drive-thru voice ordering system. Prompt management is critical for voice AI because:

1. **Prompts evolve independently of code** – Tuning tone, handling edge cases, and improving accuracy shouldn't require deployments
2. **A/B testing** – Compare prompt variants to find what works best for customers
3. **Audit trail** – Track what prompt version produced a specific interaction
4. **Rollback capability** – Revert to previous versions if a change degrades performance

---

## Langfuse Prompt Concepts

### Prompt Types

Langfuse supports two prompt types:

| Type | Use Case | Example |
|------|----------|---------|
| **Text** | System prompts, instructions | Drive-thru greeting prompt |
| **Chat** | Multi-message templates | Intent classification with examples |

### Labels and Versioning

- Each prompt has a **name** (unique identifier) and multiple **versions** (immutable snapshots)
- **Labels** (e.g., `production`, `staging`, `latest`) point to specific versions
- Fetching a prompt by name returns the `production` label by default
- Labels can be moved between versions without code changes (hot-swapping)

```
drive-thru-system-prompt
├── v1 (deprecated)
├── v2 ← staging
└── v3 ← production, latest
```

---

## Prompt Organization Strategy

### Naming Convention

Use a hierarchical naming scheme for consistency:

```
{domain}-{node}-{purpose}

Examples:
- drive-thru-greeting-system         # Greeting node system prompt
- drive-thru-intent-classifier       # Intent parsing prompt
- drive-thru-item-parser             # Item extraction prompt
- drive-thru-response-generator      # Customer-facing response
- drive-thru-order-confirmation      # Final order readback
- drive-thru-error-recovery          # Handling failures gracefully
```

### Prompt Catalog

| Prompt Name | Type | Purpose | Variables |
|-------------|------|---------|-----------|
| `drive-thru-greeting-system` | text | Initial greeting instructions | `location_name` |
| `drive-thru-intent-classifier` | chat | Classify customer intent | `customer_utterance` |
| `drive-thru-item-parser` | chat | Extract item details | `menu_items`, `customer_utterance` |
| `drive-thru-response-success` | text | Confirm item added | `item_name`, `quantity` |
| `drive-thru-response-failure` | text | Item not found | `requested_item`, `suggestions` |
| `drive-thru-order-confirmation` | text | Read back final order | `order_items`, `order_total` |

---

## Creating Prompts in Langfuse

### Via Python SDK

```python
from langfuse import get_client

langfuse = get_client()

# Create a text prompt
langfuse.create_prompt(
    name="drive-thru-greeting-system",
    prompt="""You are a friendly McDonald's drive-thru assistant at {{location_name}}.

Your responsibilities:
- Greet customers warmly
- Help them place their order
- Confirm items as they're added
- Read back the complete order when done

Guidelines:
- Keep responses under 15 words for voice
- Be upbeat but not excessive
- If unsure what the customer said, ask for clarification politely
- Never make up items not on the menu""",
    config={
        "model": "gpt-4o-mini",
        "temperature": 0.3,
    },
    labels=["production"],
)

# Create a chat prompt with examples (few-shot)
langfuse.create_prompt(
    name="drive-thru-intent-classifier",
    type="chat",
    prompt=[
        {
            "role": "system",
            "content": """Classify the customer's intent at a drive-thru.

Valid intents: add_item, remove_item, modify_item, read_order, done, unclear, greeting, question

Respond with JSON: {"intent": "...", "confidence": 0.0-1.0, "reasoning": "..."}"""
        },
        {
            "role": "user",
            "content": "I'll take a large coffee"
        },
        {
            "role": "assistant",
            "content": '{"intent": "add_item", "confidence": 0.95, "reasoning": "Customer is ordering a beverage"}'
        },
        {
            "role": "user",
            "content": "Actually never mind on the hash brown"
        },
        {
            "role": "assistant",
            "content": '{"intent": "remove_item", "confidence": 0.9, "reasoning": "Customer is canceling a previous item"}'
        },
        {
            "role": "user",
            "content": "{{customer_utterance}}"
        }
    ],
    config={
        "model": "gpt-4o-mini",
        "temperature": 0,
    },
    labels=["production"],
)
```

### Via Langfuse UI

1. Navigate to **Prompts** in the Langfuse dashboard
2. Click **+ New Prompt**
3. Enter name following the naming convention
4. Choose type (text or chat)
5. Write prompt with `{{variable}}` placeholders
6. Set model configuration
7. Save and assign `staging` label for testing
8. Promote to `production` after validation

---

## Using Prompts in LangGraph Nodes

### Basic Pattern

```python
from langfuse import get_client
from langchain_openai import ChatOpenAI

langfuse = get_client()

def get_prompt(name: str, label: str = "production") -> str:
    """Fetch a prompt by name with caching and error handling."""
    try:
        prompt = langfuse.get_prompt(name, label=label)
        return prompt
    except Exception as e:
        # Log error and fall back to hardcoded prompt
        logger.error(f"Failed to fetch prompt {name}: {e}")
        return FALLBACK_PROMPTS.get(name)


def parse_intent_node(state: DriveThruState) -> dict:
    """Parse customer intent using Langfuse-managed prompt."""
    prompt = get_prompt("drive-thru-intent-classifier")

    # Compile with variables
    messages = prompt.compile(
        customer_utterance=state["messages"][-1].content
    )

    # Use model config from prompt
    llm = ChatOpenAI(
        model=prompt.config.get("model", "gpt-4o-mini"),
        temperature=prompt.config.get("temperature", 0),
    )

    result = llm.with_structured_output(ParsedIntent).invoke(messages)
    return {"parsed_intent": result}
```

### Linking Prompts to Traces

When using prompts with the Langfuse callback handler, traces automatically link to prompt versions:

```python
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()

def generate_response_node(state: DriveThruState) -> dict:
    prompt = get_prompt("drive-thru-response-success")

    # Compile prompt
    system_message = prompt.compile(
        item_name=state["validation_result"].matched_item_name,
        quantity=state["parsed_item_request"].quantity,
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    # Trace will show which prompt version was used
    result = llm.invoke(
        [{"role": "system", "content": system_message}],
        config={"callbacks": [langfuse_handler]}
    )

    return {"response": result}
```

---

## Prompt Testing Workflow

### Local Development

```python
# Fetch staging version for testing
prompt = langfuse.get_prompt("drive-thru-intent-classifier", label="staging")

# Test with sample inputs
test_cases = [
    "I want a Big Mac",
    "Can I get two hash browns?",
    "That's all",
    "Wait, remove the coffee",
]

for utterance in test_cases:
    messages = prompt.compile(customer_utterance=utterance)
    result = llm.invoke(messages)
    print(f"Input: {utterance}")
    print(f"Output: {result}")
    print("---")
```

### Evaluation with Datasets

Create datasets in Langfuse to systematically evaluate prompt changes:

```python
# Create a dataset for intent classification
langfuse.create_dataset(
    name="intent-classification-eval",
    description="Test cases for drive-thru intent classification",
)

# Add items to dataset
test_items = [
    {"input": "I'll have a coffee", "expected": "add_item"},
    {"input": "That's everything", "expected": "done"},
    {"input": "Remove the fries", "expected": "remove_item"},
]

for item in test_items:
    langfuse.create_dataset_item(
        dataset_name="intent-classification-eval",
        input={"customer_utterance": item["input"]},
        expected_output={"intent": item["expected"]},
    )
```

### Automated Evaluation

```python
def evaluate_prompt_version(prompt_name: str, label: str, dataset_name: str):
    """Run evaluation against a dataset and score results."""
    prompt = langfuse.get_prompt(prompt_name, label=label)
    dataset = langfuse.get_dataset(dataset_name)

    correct = 0
    total = 0

    for item in dataset.items:
        messages = prompt.compile(**item.input)

        with langfuse.start_as_current_observation(
            name=f"eval-{prompt_name}",
            metadata={"label": label, "dataset": dataset_name}
        ) as span:
            result = llm.invoke(messages)

            # Check if result matches expected
            is_correct = result["intent"] == item.expected_output["intent"]

            langfuse.create_score(
                trace_id=span.trace_id,
                name="accuracy",
                value=1.0 if is_correct else 0.0,
            )

            if is_correct:
                correct += 1
            total += 1

    return {"accuracy": correct / total, "total": total}
```

---

## Deployment Strategy

### Label Promotion Flow

```
1. Create new version      →  v4 (no labels)
2. Test locally            →  Manual validation
3. Assign staging label    →  v4 ← staging
4. Run evaluation suite    →  Compare accuracy to production
5. Promote to production   →  v4 ← production, staging
6. Monitor traces          →  Watch for regressions
7. Rollback if needed      →  Move production label back to v3
```

### Code Pattern for Label-Based Fetching

```python
import os

# Environment determines which label to use
PROMPT_LABEL = os.environ.get("LANGFUSE_PROMPT_LABEL", "production")

def get_prompt(name: str) -> str:
    """Fetch prompt using environment-configured label."""
    return langfuse.get_prompt(name, label=PROMPT_LABEL)
```

### Cache Considerations

Prompts are cached by the SDK. For long-running services:

```python
# Default cache TTL is reasonable for most cases
# Force refresh if needed
prompt = langfuse.get_prompt(name, label=label, cache_ttl_seconds=0)
```

---

## Monitoring and Iteration

### Key Metrics to Track

1. **Intent classification accuracy** – Are we correctly understanding customers?
2. **Response latency** – Prompt length affects LLM response time
3. **Customer clarification rate** – How often do we need to ask for clarification?
4. **Order completion rate** – Do customers complete orders successfully?

### Linking Metrics to Prompts

```python
# After order completion
langfuse.create_score(
    trace_id=trace_id,
    name="order-completed",
    value=1.0 if order_completed else 0.0,
)

# Tag with prompt versions used
langfuse.update_trace(
    trace_id=trace_id,
    metadata={
        "intent_prompt_version": intent_prompt.version,
        "parser_prompt_version": parser_prompt.version,
    }
)
```

### Analyzing Prompt Performance

In Langfuse dashboard:
1. Filter traces by prompt name
2. Compare scores across prompt versions
3. Identify patterns in low-scoring traces
4. Export data for deeper analysis

---

## Fallback Strategy

Always have fallback prompts for resilience:

```python
FALLBACK_PROMPTS = {
    "drive-thru-greeting-system": """You are a McDonald's drive-thru assistant.
Greet the customer and help them place their order.
Keep responses brief and friendly.""",

    "drive-thru-intent-classifier": """Classify intent as one of:
add_item, remove_item, read_order, done, unclear, greeting, question.
Respond with JSON: {"intent": "...", "confidence": 0.0-1.0}""",
}

def get_prompt_safe(name: str) -> str:
    """Fetch prompt with fallback on failure."""
    try:
        prompt = langfuse.get_prompt(name, label="production")
        return prompt
    except Exception as e:
        logger.warning(f"Using fallback prompt for {name}: {e}")
        return FALLBACK_PROMPTS[name]
```

---

## Best Practices Summary

1. **Use consistent naming** – `{domain}-{node}-{purpose}` pattern
2. **Store config with prompts** – Model name, temperature, etc.
3. **Use labels for deployment** – `staging` → test → `production`
4. **Link traces to prompts** – Enables performance analysis
5. **Create evaluation datasets** – Systematic testing before promotion
6. **Monitor after deployment** – Watch for accuracy regressions
7. **Always have fallbacks** – Service should work even if Langfuse is down
8. **Keep prompts voice-friendly** – Short responses, clear language

---

## Next Steps

1. Create initial prompt set in Langfuse for all nodes
2. Build evaluation datasets with representative test cases
3. Implement `get_prompt_safe()` wrapper in codebase
4. Set up monitoring dashboard for prompt metrics
5. Document prompt change process for team
