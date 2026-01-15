# Quick Start Guide

Get started with teval in 5 minutes.

## Installation (30 seconds)

teval requires Python 3.10 or later. Install it using pip:

```bash
pip install teval
```

> **Note**: If the package isn't on PyPI yet, you can install from the repository:
> ```bash
> pip install git+https://github.com/yourusername/teval.git
> ```

## Your First Evaluation (90 seconds)

Let's create a simple evaluation rubric and validate some results:

```python
from teval import EvaluationRubric, MetricDefinition

# Create a simple rubric with 2 metrics
rubric = EvaluationRubric(
    rubric_id="quick_start",
    metrics=[
        # Mandatory metric - MUST pass for evaluation to succeed
        MetricDefinition(
            id="M1",
            rubric="Answer is factually correct",
            mandatory=True
        ),
        # Cumulative metric - contributes to the total score
        MetricDefinition(
            id="C1",
            rubric="Answer is helpful"
        ),
    ],
    passing_score_threshold=1  # Need at least 1 cumulative metric to pass
)

# Example 1: Passing evaluation
result_pass = {"M1": True, "C1": True}
passes = rubric.validate_result(result_pass)
print(f"Result 1: {'PASS' if passes else 'FAIL'}")  # Output: Result 1: PASS

# Example 2: Failing evaluation (mandatory metric failed)
result_fail = {"M1": False, "C1": True}
passes = rubric.validate_result(result_fail)
print(f"Result 2: {'PASS' if passes else 'FAIL'}")  # Output: Result 2: FAIL
```

## Understanding the Two-Tier System (60 seconds)

teval uses two types of metrics:

1. **Mandatory metrics** (`mandatory=True`): ALL must pass
2. **Cumulative metrics** (`mandatory=False`, the default): Count toward a threshold

An evaluation passes only if:
- ✅ ALL mandatory metrics pass, AND
- ✅ The count of passed cumulative metrics meets the threshold

Here's an example showing different failure modes:

```python
# Create a rubric with more metrics
rubric = EvaluationRubric(
    rubric_id="detailed_review",
    metrics=[
        # Mandatory metric
        MetricDefinition(id="M1", rubric="No syntax errors", mandatory=True),
        # Cumulative metrics
        MetricDefinition(id="C1", rubric="Well formatted"),
        MetricDefinition(id="C2", rubric="Good variable names"),
        MetricDefinition(id="C3", rubric="Has comments"),
    ],
    passing_score_threshold=2  # Need at least 2 out of 3 cumulative metrics
)

# Scenario 1: Mandatory metric fails → FAIL
result1 = {"M1": False, "C1": True, "C2": True, "C3": True}
print(f"Mandatory failed: {rubric.validate_result(result1)}")  # False

# Scenario 2: Threshold not met → FAIL
result2 = {"M1": True, "C1": True, "C2": False, "C3": False}
print(f"Below threshold: {rubric.validate_result(result2)}")  # False (only 1/2)

# Scenario 3: Everything passes → PASS
result3 = {"M1": True, "C1": True, "C2": True, "C3": False}
print(f"Meets criteria: {rubric.validate_result(result3)}")  # True (2/2)
```

## LLM Integration (120 seconds)

Now let's see how to use teval with an LLM. The framework provides tools to generate prompts and validate LLM responses:

```python
from teval import EvaluationRubric, MetricDefinition

# Create a code review rubric
rubric = EvaluationRubric(
    rubric_id="code_review",
    metrics=[
        MetricDefinition(id="M1", rubric="Code has no syntax errors", mandatory=True),
        MetricDefinition(id="M2", rubric="No security vulnerabilities", mandatory=True),
        MetricDefinition(id="C1", rubric="Follows style guide"),
        MetricDefinition(id="C2", rubric="Has unit tests"),
        MetricDefinition(id="C3", rubric="Well documented"),
    ],
    passing_score_threshold=2  # Need 2 out of 3 cumulative metrics
)

# Step 1: Generate prompt text for your LLM
prompt_text = rubric.to_prompt_text()
print("=" * 50)
print("SEND THIS PROMPT TO YOUR LLM:")
print("=" * 50)
print(prompt_text)
print()

# Step 2: Get JSON schema for structured output (for OpenAI, Gemini, etc.)
schema = rubric.to_json_schema()
# Use this schema with your LLM's structured output feature

# Step 3: Simulate an LLM response (in practice, this comes from your LLM API)
# The LLM returns a JSON object with boolean values for each metric
llm_response = """{
    "M1": true,
    "M2": true,
    "C1": true,
    "C2": false,
    "C3": true,
    "M1_reasoning": "No syntax errors found",
    "M2_reasoning": "Code properly sanitizes inputs",
    "C1_reasoning": "Follows PEP 8 guidelines",
    "C2_reasoning": "No unit tests present",
    "C3_reasoning": "Has comprehensive docstrings"
}"""

# Step 4: Validate the LLM response
passes = rubric.validate_result(llm_response)
print(f"Code Review Result: {'PASS ✅' if passes else 'FAIL ❌'}")

# The evaluation passes because:
# - Both mandatory metrics (M1, M2) passed ✅
# - 2 out of 3 cumulative metrics (C1, C3) passed, meeting the threshold ✅
```

### Integration with Popular LLM Providers

For actual LLM integration, you would use the schema with your provider's API:

```python
# OpenAI example (pseudocode)
# response = openai.chat.completions.create(
#     model="gpt-4",
#     messages=[{"role": "user", "content": prompt_text}],
#     response_format={"type": "json_object", "schema": schema}
# )

# Google Gemini example (pseudocode)
# model = genai.GenerativeModel("gemini-pro")
# response = model.generate_content(
#     prompt_text,
#     generation_config={"response_schema": schema}
# )
```

## Next Steps

Now that you've completed the quick start:

### Learn More
- **Full Documentation**: See the complete [README](../README.md) for comprehensive API documentation
- **Real LLM Integration**: Check out [`example_usage.py`](../example_usage.py) for complete OpenAI and Gemini examples
- **Type-Safe Validation**: Explore [`example_pydantic.py`](../example_pydantic.py) for Pydantic model usage
- **Alignment Metrics**: See [`example_alignment.py`](../example_alignment.py) for comparing multiple evaluators
- **Report Generation**: Look at [`example_report.py`](../example_report.py) for creating evaluation reports

### Key Features to Explore
- **Dynamic Pydantic Models**: Use `rubric.to_pydantic_model()` for type-safe validation
- **Alignment Calculation**: Compare human and LLM evaluations with `calculate_alignment()`
- **Report Generation**: Create markdown reports with `generate_report()`
- **Custom Metrics**: Design domain-specific evaluation criteria

### Getting Help
- Check the [examples](../) directory for more complete implementations
- Read the [API documentation](../README.md#api-reference) for detailed method descriptions
- Report issues on [GitHub](https://github.com/yourusername/teval/issues)

---

**Congratulations!** You've successfully created your first LLM evaluation with teval. The framework's simplicity makes it easy to integrate into any Python application or evaluation pipeline.