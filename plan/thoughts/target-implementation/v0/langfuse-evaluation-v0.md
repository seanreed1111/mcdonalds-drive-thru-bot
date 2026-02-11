# Langfuse Evaluation for Drive-Thru Voice AI

> **Related Documents:**
> - [LangGraph State Design](./langgraph-state-design-v0.md) – Workflow architecture, state schema, and Langfuse observability setup
> - [Langfuse Prompt Management](./langfuse-prompt-management-v0.md) – Prompt versioning, testing, and deployment strategies

---

## Table of Contents

- [Overview](#overview)
- [Why Evaluation Matters](#why-evaluation-matters)
- [Evaluation Framework](#evaluation-framework)
  - [What to Evaluate](#what-to-evaluate)
  - [Evaluation Dimensions](#evaluation-dimensions)
- [Datasets](#datasets)
  - [Dataset Design Principles](#dataset-design-principles)
  - [Creating Datasets](#creating-datasets)
  - [Dataset Categories](#dataset-categories)
  - [Maintaining Datasets](#maintaining-datasets)
- [Scoring Strategies](#scoring-strategies)
  - [Manual Scoring](#manual-scoring)
  - [Automated Scoring](#automated-scoring)
  - [LLM-as-Judge](#llm-as-judge)
  - [Composite Scores](#composite-scores)
- [Running Evaluations](#running-evaluations)
  - [Single Evaluation Run](#single-evaluation-run)
  - [Comparing Prompt Versions](#comparing-prompt-versions)
  - [Regression Testing](#regression-testing)
- [Continuous Evaluation Pipeline](#continuous-evaluation-pipeline)
  - [Production Sampling](#production-sampling)
  - [Automated Monitoring](#automated-monitoring)
  - [Alert Thresholds](#alert-thresholds)
- [Domain-Specific Evaluations](#domain-specific-evaluations)
  - [Intent Classification Evaluation](#intent-classification-evaluation)
  - [Item Extraction Evaluation](#item-extraction-evaluation)
  - [Response Quality Evaluation](#response-quality-evaluation)
  - [End-to-End Conversation Evaluation](#end-to-end-conversation-evaluation)
- [Analysis and Reporting](#analysis-and-reporting)
  - [Key Metrics](#key-metrics)
  - [Dashboard Setup](#dashboard-setup)
  - [Identifying Failure Patterns](#identifying-failure-patterns)
- [Best Practices](#best-practices)
- [Next Steps](#next-steps)

---

## Overview

This document outlines a thoughtful and consistent approach to evaluating the McDonald's drive-thru voice AI using Langfuse. Evaluation goes beyond observability—while tracing shows *what happened*, evaluation tells us *how well it worked* and *whether changes improve performance*.

Evaluation is the foundation for:
- Confident prompt iteration
- Safe production deployments
- Identifying edge cases and failure modes
- Measuring progress over time

---

## Why Evaluation Matters

Voice AI for drive-thru ordering has unique challenges that make systematic evaluation essential:

| Challenge | Without Evaluation | With Evaluation |
|-----------|-------------------|-----------------|
| Prompt changes | "It seems to work better" | "Accuracy improved from 87% to 92%" |
| Edge cases | Discovered by angry customers | Caught in test datasets |
| Regressions | Noticed days later in production | Blocked before deployment |
| Model updates | Hope for the best | Quantified impact before switching |

---

## Evaluation Framework

### What to Evaluate

Evaluation should cover every step where the system makes a decision or generates output:

```
Customer Utterance
       │
       ▼
┌─────────────────┐
│ Intent Parsing  │ ◄─── Evaluate: Is the intent correct?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Item Extraction │ ◄─── Evaluate: Are item details accurate?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Menu Validation │ ◄─── Evaluate: Is matching reliable?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Response Gen    │ ◄─── Evaluate: Is the response appropriate?
└─────────────────┘
```

### Evaluation Dimensions

Each component should be evaluated across multiple dimensions:

| Dimension | Description | Example Metric |
|-----------|-------------|----------------|
| **Correctness** | Does the output match expected behavior? | Intent accuracy (%) |
| **Robustness** | Does it handle variations and edge cases? | Accuracy on noisy input |
| **Consistency** | Does it produce stable results for similar inputs? | Variance across runs |
| **Latency** | Does it meet response time requirements? | p95 latency (ms) |
| **Tone** | Is the response voice-appropriate? | Tone score (1-5) |

---

## Datasets

Datasets are the foundation of consistent evaluation. A well-designed dataset enables repeatable testing and meaningful comparisons.

### Dataset Design Principles

1. **Representative** – Cover common cases weighted by actual frequency
2. **Comprehensive** – Include edge cases, errors, and boundary conditions
3. **Labeled** – Clear expected outputs for automated scoring
4. **Versioned** – Track dataset changes alongside prompt changes
5. **Growing** – Add real failures from production as they're discovered

### Creating Datasets

```python
from langfuse import get_client

langfuse = get_client()

# Create a dataset
langfuse.create_dataset(
    name="intent-classification-v1",
    description="Test cases for drive-thru intent classification",
    metadata={
        "version": "1.0",
        "created_date": "2025-01-15",
        "owner": "voice-ai-team",
    },
)

# Add dataset items with input, expected output, and metadata
def add_intent_test_case(
    utterance: str,
    expected_intent: str,
    category: str,
    difficulty: str = "normal",
):
    """Add a labeled test case to the intent dataset."""
    langfuse.create_dataset_item(
        dataset_name="intent-classification-v1",
        input={"customer_utterance": utterance},
        expected_output={
            "intent": expected_intent,
        },
        metadata={
            "category": category,
            "difficulty": difficulty,
        },
    )


# Common ordering patterns
add_intent_test_case(
    "I'd like a sausage McMuffin",
    expected_intent="add_item",
    category="ordering",
)
add_intent_test_case(
    "Can I get two hash browns please?",
    expected_intent="add_item",
    category="ordering",
)

# Completion signals
add_intent_test_case(
    "That's all",
    expected_intent="done",
    category="completion",
)
add_intent_test_case(
    "Nothing else, thank you",
    expected_intent="done",
    category="completion",
)

# Modifications
add_intent_test_case(
    "Actually, remove the coffee",
    expected_intent="remove_item",
    category="modification",
)

# Edge cases
add_intent_test_case(
    "Umm... let me think... maybe a...",
    expected_intent="unclear",
    category="edge_case",
    difficulty="hard",
)
add_intent_test_case(
    "What comes on the Big Breakfast?",
    expected_intent="question",
    category="inquiry",
)
```

### Dataset Categories

Create focused datasets for each evaluation target:

| Dataset Name | Purpose | Size Guidance |
|--------------|---------|---------------|
| `intent-classification-v1` | Intent parsing accuracy | 100-200 cases |
| `item-extraction-v1` | Item detail extraction | 150-250 cases |
| `modifier-handling-v1` | Modifier recognition | 50-100 cases |
| `response-quality-v1` | Response appropriateness | 50-100 cases |
| `e2e-conversations-v1` | Full conversation flows | 20-50 conversations |
| `regression-critical-v1` | Known failure cases | 30-50 cases |

### Maintaining Datasets

```python
def add_production_failure(
    dataset_name: str,
    trace_id: str,
    correct_output: dict,
    failure_reason: str,
):
    """Add a production failure to the regression dataset."""
    # Fetch the original trace
    trace = langfuse.get_trace(trace_id)

    langfuse.create_dataset_item(
        dataset_name=dataset_name,
        input=trace.input,
        expected_output=correct_output,
        metadata={
            "source": "production_failure",
            "original_trace_id": trace_id,
            "failure_reason": failure_reason,
            "added_date": "2025-01-15",
        },
    )
```

---

## Scoring Strategies

Langfuse supports multiple scoring approaches. Choose based on what you're evaluating.

### Manual Scoring

Best for: Response quality, tone, helpfulness—things that require human judgment.

```python
# In Langfuse UI or via SDK after human review
langfuse.create_score(
    trace_id="trace-abc-123",
    name="response-quality",
    value=4,  # 1-5 scale
    data_type="NUMERIC",
    comment="Response was friendly but slightly too long for drive-thru",
)

langfuse.create_score(
    trace_id="trace-abc-123",
    name="tone-appropriate",
    value="good",
    data_type="CATEGORICAL",
    comment="Matched brand voice",
)
```

### Automated Scoring

Best for: Correctness checks where expected output is known.

```python
def score_intent_accuracy(
    trace_id: str,
    predicted_intent: str,
    expected_intent: str,
) -> None:
    """Score intent classification accuracy."""
    is_correct = predicted_intent == expected_intent

    langfuse.create_score(
        trace_id=trace_id,
        name="intent-accuracy",
        value=1.0 if is_correct else 0.0,
        data_type="NUMERIC",
        comment=f"Predicted: {predicted_intent}, Expected: {expected_intent}",
    )


def score_item_extraction(
    trace_id: str,
    predicted: dict,
    expected: dict,
) -> None:
    """Score item extraction with partial credit."""
    score = 0.0
    max_score = 4.0

    # Item name match (most important)
    if predicted.get("item_name", "").lower() == expected.get("item_name", "").lower():
        score += 2.0

    # Quantity match
    if predicted.get("quantity") == expected.get("quantity"):
        score += 1.0

    # Size match
    if predicted.get("size") == expected.get("size"):
        score += 0.5

    # Modifiers match (jaccard similarity)
    pred_mods = set(predicted.get("modifiers", []))
    exp_mods = set(expected.get("modifiers", []))
    if pred_mods or exp_mods:
        jaccard = len(pred_mods & exp_mods) / len(pred_mods | exp_mods)
        score += 0.5 * jaccard

    langfuse.create_score(
        trace_id=trace_id,
        name="item-extraction-accuracy",
        value=score / max_score,
        data_type="NUMERIC",
    )
```

### LLM-as-Judge

Best for: Evaluating qualities that are hard to codify but easy for an LLM to assess.

```python
from langchain_openai import ChatOpenAI

judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)

JUDGE_PROMPT = """You are evaluating a drive-thru voice AI response.

Customer said: {customer_utterance}
AI responded: {ai_response}
Context: {context}

Evaluate the response on these criteria (1-5 scale):
1. Clarity: Is the response easy to understand when spoken aloud?
2. Brevity: Is it appropriately short for a drive-thru interaction?
3. Helpfulness: Does it move the order forward?
4. Tone: Does it match a friendly fast-food brand voice?

Respond with JSON:
{{"clarity": X, "brevity": X, "helpfulness": X, "tone": X, "reasoning": "..."}}
"""


def llm_judge_response(
    trace_id: str,
    customer_utterance: str,
    ai_response: str,
    context: str,
) -> dict:
    """Use LLM to judge response quality."""
    prompt = JUDGE_PROMPT.format(
        customer_utterance=customer_utterance,
        ai_response=ai_response,
        context=context,
    )

    result = judge_llm.invoke(prompt)
    scores = json.loads(result.content)

    # Record individual dimension scores
    for dimension in ["clarity", "brevity", "helpfulness", "tone"]:
        langfuse.create_score(
            trace_id=trace_id,
            name=f"response-{dimension}",
            value=scores[dimension],
            data_type="NUMERIC",
            comment=scores.get("reasoning"),
        )

    # Composite score
    avg_score = sum(scores[d] for d in ["clarity", "brevity", "helpfulness", "tone"]) / 4
    langfuse.create_score(
        trace_id=trace_id,
        name="response-quality-composite",
        value=avg_score,
        data_type="NUMERIC",
    )

    return scores
```

### Composite Scores

Combine multiple dimensions into a single score for easier comparison:

```python
def calculate_conversation_score(trace_id: str) -> float:
    """Calculate overall conversation quality score."""
    scores = langfuse.get_scores(trace_id=trace_id)

    weights = {
        "intent-accuracy": 0.3,
        "item-extraction-accuracy": 0.3,
        "response-quality-composite": 0.2,
        "order-completed": 0.2,
    }

    weighted_sum = 0.0
    total_weight = 0.0

    for score in scores:
        if score.name in weights:
            weighted_sum += score.value * weights[score.name]
            total_weight += weights[score.name]

    composite = weighted_sum / total_weight if total_weight > 0 else 0.0

    langfuse.create_score(
        trace_id=trace_id,
        name="conversation-quality",
        value=composite,
        data_type="NUMERIC",
    )

    return composite
```

---

## Running Evaluations

### Single Evaluation Run

Run the full dataset against the current prompt configuration:

```python
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()


def run_intent_evaluation(
    dataset_name: str,
    prompt_label: str = "production",
) -> dict:
    """Run intent classification evaluation on a dataset."""
    dataset = langfuse.get_dataset(dataset_name)
    prompt = langfuse.get_prompt("drive-thru-intent-classifier", label=prompt_label)

    results = {
        "total": 0,
        "correct": 0,
        "by_category": {},
        "failures": [],
    }

    for item in dataset.items:
        # Start a trace for this evaluation
        with langfuse.start_as_current_observation(
            name=f"eval-intent-{item.id}",
            metadata={
                "dataset": dataset_name,
                "prompt_label": prompt_label,
                "item_id": item.id,
            },
        ) as span:
            # Run the classification
            messages = prompt.compile(**item.input)
            llm = ChatOpenAI(
                model=prompt.config.get("model", "gpt-4o-mini"),
                temperature=prompt.config.get("temperature", 0),
            )

            result = llm.with_structured_output(ParsedIntent).invoke(
                messages,
                config={"callbacks": [langfuse_handler]},
            )

            # Score the result
            expected = item.expected_output["intent"]
            predicted = result.intent.value

            is_correct = predicted == expected
            score_intent_accuracy(span.trace_id, predicted, expected)

            # Track results
            results["total"] += 1
            if is_correct:
                results["correct"] += 1
            else:
                results["failures"].append({
                    "input": item.input,
                    "expected": expected,
                    "predicted": predicted,
                    "trace_id": span.trace_id,
                })

            # Track by category
            category = item.metadata.get("category", "unknown")
            if category not in results["by_category"]:
                results["by_category"][category] = {"total": 0, "correct": 0}
            results["by_category"][category]["total"] += 1
            if is_correct:
                results["by_category"][category]["correct"] += 1

    # Calculate final metrics
    results["accuracy"] = results["correct"] / results["total"]
    for category, counts in results["by_category"].items():
        counts["accuracy"] = counts["correct"] / counts["total"]

    return results
```

### Comparing Prompt Versions

Compare two prompt versions to decide whether to promote:

```python
def compare_prompt_versions(
    prompt_name: str,
    dataset_name: str,
    baseline_label: str = "production",
    candidate_label: str = "staging",
) -> dict:
    """Compare baseline and candidate prompt versions."""
    baseline_results = run_intent_evaluation(dataset_name, baseline_label)
    candidate_results = run_intent_evaluation(dataset_name, candidate_label)

    comparison = {
        "baseline": {
            "label": baseline_label,
            "accuracy": baseline_results["accuracy"],
            "by_category": baseline_results["by_category"],
        },
        "candidate": {
            "label": candidate_label,
            "accuracy": candidate_results["accuracy"],
            "by_category": candidate_results["by_category"],
        },
        "delta": candidate_results["accuracy"] - baseline_results["accuracy"],
        "recommendation": None,
    }

    # Determine recommendation
    if comparison["delta"] > 0.02:  # >2% improvement
        comparison["recommendation"] = "PROMOTE"
    elif comparison["delta"] < -0.02:  # >2% regression
        comparison["recommendation"] = "REJECT"
    else:
        comparison["recommendation"] = "NEEDS_REVIEW"

    # Check for category regressions
    category_regressions = []
    for category in baseline_results["by_category"]:
        if category in candidate_results["by_category"]:
            baseline_acc = baseline_results["by_category"][category]["accuracy"]
            candidate_acc = candidate_results["by_category"][category]["accuracy"]
            if candidate_acc < baseline_acc - 0.05:  # >5% category regression
                category_regressions.append({
                    "category": category,
                    "baseline": baseline_acc,
                    "candidate": candidate_acc,
                })

    if category_regressions:
        comparison["category_regressions"] = category_regressions
        comparison["recommendation"] = "NEEDS_REVIEW"

    return comparison
```

### Regression Testing

Run critical test cases before every deployment:

```python
def run_regression_tests(prompt_label: str = "staging") -> dict:
    """Run regression tests for critical failure cases."""
    results = run_intent_evaluation(
        dataset_name="regression-critical-v1",
        prompt_label=prompt_label,
    )

    # Regression tests must pass with 100% accuracy
    passed = results["accuracy"] == 1.0

    return {
        "passed": passed,
        "accuracy": results["accuracy"],
        "failures": results["failures"],
        "message": "All regression tests passed" if passed else f"{len(results['failures'])} regression(s) detected",
    }
```

---

## Continuous Evaluation Pipeline

### Production Sampling

Continuously evaluate a sample of production traffic:

```python
import random

SAMPLE_RATE = 0.05  # Evaluate 5% of production traffic


def should_evaluate_trace() -> bool:
    """Determine if this trace should be evaluated."""
    return random.random() < SAMPLE_RATE


def post_interaction_evaluation(
    trace_id: str,
    customer_utterance: str,
    predicted_intent: str,
    ai_response: str,
) -> None:
    """Run evaluation on a sampled production trace."""
    if not should_evaluate_trace():
        return

    # Run LLM-as-judge for response quality
    llm_judge_response(
        trace_id=trace_id,
        customer_utterance=customer_utterance,
        ai_response=ai_response,
        context="Production conversation",
    )

    # Tag trace as evaluated
    langfuse.update_trace(
        trace_id=trace_id,
        metadata={"evaluated": True, "evaluation_type": "production_sample"},
    )
```

### Automated Monitoring

Set up scheduled evaluation jobs:

```python
from datetime import datetime, timedelta


def daily_evaluation_report() -> dict:
    """Generate daily evaluation report from production samples."""
    yesterday = datetime.now() - timedelta(days=1)

    # Query evaluated traces from yesterday
    traces = langfuse.get_traces(
        filter={
            "metadata.evaluated": True,
            "timestamp": {"gte": yesterday.isoformat()},
        },
        limit=1000,
    )

    # Aggregate scores
    metrics = {
        "total_evaluated": len(traces),
        "scores": {},
    }

    for trace in traces:
        scores = langfuse.get_scores(trace_id=trace.id)
        for score in scores:
            if score.name not in metrics["scores"]:
                metrics["scores"][score.name] = []
            metrics["scores"][score.name].append(score.value)

    # Calculate averages
    for name, values in metrics["scores"].items():
        metrics["scores"][name] = {
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }

    return metrics
```

### Alert Thresholds

Define thresholds that trigger alerts:

```python
ALERT_THRESHOLDS = {
    "intent-accuracy": {"min": 0.85, "warning": 0.90},
    "response-quality-composite": {"min": 3.0, "warning": 3.5},  # 1-5 scale
    "item-extraction-accuracy": {"min": 0.80, "warning": 0.85},
}


def check_alert_thresholds(metrics: dict) -> list[dict]:
    """Check if any metrics have crossed alert thresholds."""
    alerts = []

    for metric_name, thresholds in ALERT_THRESHOLDS.items():
        if metric_name in metrics["scores"]:
            mean_value = metrics["scores"][metric_name]["mean"]

            if mean_value < thresholds["min"]:
                alerts.append({
                    "severity": "critical",
                    "metric": metric_name,
                    "value": mean_value,
                    "threshold": thresholds["min"],
                    "message": f"{metric_name} at {mean_value:.2%} is below critical threshold {thresholds['min']:.2%}",
                })
            elif mean_value < thresholds["warning"]:
                alerts.append({
                    "severity": "warning",
                    "metric": metric_name,
                    "value": mean_value,
                    "threshold": thresholds["warning"],
                    "message": f"{metric_name} at {mean_value:.2%} is below warning threshold {thresholds['warning']:.2%}",
                })

    return alerts
```

---

## Domain-Specific Evaluations

### Intent Classification Evaluation

```python
INTENT_CATEGORIES = {
    "add_item": [
        "I'll have a...",
        "Can I get...",
        "Give me...",
        "I want...",
        "Let me get...",
    ],
    "done": [
        "That's all",
        "Nothing else",
        "I'm good",
        "That'll be it",
        "That's everything",
    ],
    "remove_item": [
        "Actually, remove...",
        "Never mind on the...",
        "Cancel the...",
        "Take off the...",
    ],
}


def generate_intent_variants(base_items: list[str], category: str) -> list[dict]:
    """Generate test variants for intent classification."""
    variants = []
    prefixes = INTENT_CATEGORIES.get(category, [])

    for item in base_items:
        for prefix in prefixes:
            variants.append({
                "input": f"{prefix} {item}".strip(),
                "expected_intent": category,
                "item": item,
            })

    return variants
```

### Item Extraction Evaluation

```python
ITEM_EXTRACTION_CASES = [
    # Simple cases
    {
        "input": "I'll have a sausage McMuffin",
        "expected": {"item_name": "Sausage McMuffin", "quantity": 1, "size": None, "modifiers": []},
    },
    # Quantity
    {
        "input": "Two hash browns please",
        "expected": {"item_name": "Hash Brown", "quantity": 2, "size": None, "modifiers": []},
    },
    # Size
    {
        "input": "A large coffee",
        "expected": {"item_name": "Premium Roast Coffee", "quantity": 1, "size": "large", "modifiers": []},
    },
    # Modifiers
    {
        "input": "Egg McMuffin with no cheese",
        "expected": {"item_name": "Egg McMuffin", "quantity": 1, "size": None, "modifiers": ["no cheese"]},
    },
    # Complex
    {
        "input": "Can I get two medium iced coffees with extra cream",
        "expected": {"item_name": "Iced Coffee", "quantity": 2, "size": "medium", "modifiers": ["extra cream"]},
    },
]
```

### Response Quality Evaluation

```python
RESPONSE_QUALITY_CRITERIA = {
    "word_count": {"max": 20, "ideal": 10},  # Voice-friendly brevity
    "contains_confirmation": True,  # Should confirm item added
    "avoids_phrases": ["I'm sorry but", "Unfortunately", "I cannot"],  # Negative framing
    "ends_with_prompt": True,  # Should invite next item
}


def evaluate_response_quality(response: str, context: str) -> dict:
    """Evaluate response against quality criteria."""
    scores = {}

    # Word count
    word_count = len(response.split())
    if word_count <= RESPONSE_QUALITY_CRITERIA["word_count"]["ideal"]:
        scores["brevity"] = 1.0
    elif word_count <= RESPONSE_QUALITY_CRITERIA["word_count"]["max"]:
        scores["brevity"] = 0.7
    else:
        scores["brevity"] = 0.3

    # Negative phrasing
    has_negative = any(
        phrase.lower() in response.lower()
        for phrase in RESPONSE_QUALITY_CRITERIA["avoids_phrases"]
    )
    scores["positive_framing"] = 0.0 if has_negative else 1.0

    # Prompts for next action
    next_prompts = ["anything else", "what else", "something else", "would you like"]
    has_prompt = any(prompt in response.lower() for prompt in next_prompts)
    scores["invites_continuation"] = 1.0 if has_prompt else 0.5

    return scores
```

### End-to-End Conversation Evaluation

```python
E2E_CONVERSATIONS = [
    {
        "name": "simple_single_item",
        "turns": [
            {"customer": "Hi", "expected_intent": "greeting"},
            {"customer": "I'll have a sausage McMuffin", "expected_intent": "add_item"},
            {"customer": "That's all", "expected_intent": "done"},
        ],
        "expected_items": [{"name": "Sausage McMuffin", "quantity": 1}],
    },
    {
        "name": "multi_item_with_modification",
        "turns": [
            {"customer": "Can I get two hash browns", "expected_intent": "add_item"},
            {"customer": "And a large coffee", "expected_intent": "add_item"},
            {"customer": "Actually make that one hash brown", "expected_intent": "modify_item"},
            {"customer": "That's it", "expected_intent": "done"},
        ],
        "expected_items": [
            {"name": "Hash Brown", "quantity": 1},
            {"name": "Premium Roast Coffee", "quantity": 1, "size": "large"},
        ],
    },
]


def evaluate_e2e_conversation(conversation: dict) -> dict:
    """Evaluate a full conversation flow."""
    results = {
        "name": conversation["name"],
        "turns": [],
        "final_order_correct": False,
        "all_intents_correct": True,
    }

    # Simulate conversation
    state = initialize_state()

    for turn in conversation["turns"]:
        # Run through the graph
        result = graph.invoke(
            {"messages": [HumanMessage(content=turn["customer"])]},
            config={"callbacks": [langfuse_handler]},
        )

        # Check intent
        intent_correct = result["parsed_intent"].intent.value == turn["expected_intent"]
        if not intent_correct:
            results["all_intents_correct"] = False

        results["turns"].append({
            "customer": turn["customer"],
            "expected_intent": turn["expected_intent"],
            "actual_intent": result["parsed_intent"].intent.value,
            "correct": intent_correct,
        })

    # Check final order
    actual_items = [
        {"name": item.name, "quantity": item.quantity}
        for item in result["current_order"].items
    ]
    results["final_order_correct"] = actual_items == conversation["expected_items"]

    return results
```

---

## Analysis and Reporting

### Key Metrics

Track these metrics over time:

| Metric | Description | Target |
|--------|-------------|--------|
| Intent Accuracy | % of correctly classified intents | >90% |
| Item Extraction F1 | Harmonic mean of precision/recall | >85% |
| Response Quality | Average LLM-judge score (1-5) | >4.0 |
| Order Completion Rate | % of started orders that complete | >80% |
| Clarification Rate | % of turns requiring clarification | <15% |
| Latency p95 | 95th percentile response time | <2000ms |

### Dashboard Setup

Configure Langfuse dashboard widgets:

```python
# Example: Query for dashboard data
def get_weekly_metrics() -> dict:
    """Get metrics for the past week."""
    one_week_ago = datetime.now() - timedelta(days=7)

    # Get all traces from the past week
    traces = langfuse.get_traces(
        filter={"timestamp": {"gte": one_week_ago.isoformat()}},
        limit=10000,
    )

    # Aggregate by day
    daily_metrics = {}
    for trace in traces:
        day = trace.timestamp.date().isoformat()
        if day not in daily_metrics:
            daily_metrics[day] = {"traces": 0, "scores": {}}
        daily_metrics[day]["traces"] += 1

        # Collect scores
        scores = langfuse.get_scores(trace_id=trace.id)
        for score in scores:
            if score.name not in daily_metrics[day]["scores"]:
                daily_metrics[day]["scores"][score.name] = []
            daily_metrics[day]["scores"][score.name].append(score.value)

    return daily_metrics
```

### Identifying Failure Patterns

```python
def analyze_failures(
    dataset_name: str,
    prompt_label: str,
) -> dict:
    """Analyze patterns in evaluation failures."""
    results = run_intent_evaluation(dataset_name, prompt_label)

    if not results["failures"]:
        return {"message": "No failures to analyze"}

    # Group failures by predicted intent
    by_predicted = {}
    for failure in results["failures"]:
        pred = failure["predicted"]
        if pred not in by_predicted:
            by_predicted[pred] = []
        by_predicted[pred].append(failure)

    # Group failures by expected intent
    by_expected = {}
    for failure in results["failures"]:
        exp = failure["expected"]
        if exp not in by_expected:
            by_expected[exp] = []
        by_expected[exp].append(failure)

    # Find confusion pairs
    confusion_pairs = {}
    for failure in results["failures"]:
        pair = (failure["expected"], failure["predicted"])
        if pair not in confusion_pairs:
            confusion_pairs[pair] = 0
        confusion_pairs[pair] += 1

    return {
        "total_failures": len(results["failures"]),
        "by_predicted_intent": {k: len(v) for k, v in by_predicted.items()},
        "by_expected_intent": {k: len(v) for k, v in by_expected.items()},
        "top_confusion_pairs": sorted(confusion_pairs.items(), key=lambda x: -x[1])[:5],
        "sample_failures": results["failures"][:10],
    }
```

---

## Best Practices

1. **Start with datasets** – Build evaluation datasets before building features
2. **Automate early** – Set up automated scoring from day one
3. **Version everything** – Datasets, prompts, and evaluation code should all be versioned
4. **Use multiple scoring methods** – Combine automated, LLM-judge, and manual scoring
5. **Evaluate on production data** – Synthetic datasets miss real-world variation
6. **Set thresholds before changes** – Define what "better" means before experimenting
7. **Track trends, not snapshots** – A single evaluation tells you less than weekly trends
8. **Add failures to datasets** – Every production failure should become a test case
9. **Separate correctness from quality** – An accurate response can still be poorly phrased
10. **Review low-confidence predictions** – Traces with low confidence scores reveal edge cases

---

## Next Steps

1. Create initial evaluation datasets for each component (intent, extraction, response)
2. Implement automated scoring functions for correctness metrics
3. Set up LLM-as-judge for response quality evaluation
4. Build comparison tooling for prompt version evaluation
5. Configure production sampling (5% of traffic)
6. Set up daily metrics aggregation and alerting
7. Create regression test suite from known failure cases
8. Build dashboard for evaluation metrics visualization
