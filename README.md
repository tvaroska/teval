# teval

Trivial LLM eval - as simple as possible (maybe even a bit more simple)

A lightweight, straightforward evaluation framework for LLM outputs using Yes/No metrics with mandatory and cumulative scoring.

## Features

- **Two-tier metric system**: Mandatory metrics (all must pass) and cumulative metrics (threshold-based scoring)
- **Simple Yes/No evaluations**: Each metric is a binary pass/fail criterion
- **Count-based scoring**: Cumulative metrics contribute to a total score based on the number passed
- **LLM integration ready**: Generate prompts, JSON schemas, and Pydantic models for structured LLM evaluation
- **Dynamic Pydantic models**: Automatically create type-safe Pydantic classes from rubrics
- **Flexible validation**: Accepts both JSON strings and dictionaries for LLM response validation
- **Type safety**: Full IDE autocomplete and type checking support
- **Minimal dependencies**: Only requires Pydantic 2.7.4+ (< 3.0.0)

## Quick Start

New to teval? Check out the [5-minute Quick Start Guide](docs/quickstart.md) to get up and running fast.

## Documentation

- **[Quick Start Guide](docs/quickstart.md)** - Get started in 5 minutes
- **[API Reference](docs/api.md)** - Complete API documentation for all classes and methods
- **[Roadmap](docs/roadmap.md)** - Future development plans

For complete usage details, continue reading below.

## Installation

**Requirements**: Python 3.10 - 3.13 (Python 3.14 support pending Pydantic compatibility)

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
```

## How It Works

### Evaluation System

The framework uses two types of metrics:

1. **Mandatory Metrics**: All must pass (Yes=1) for the evaluation to succeed
2. **Cumulative Metrics**: Contribute to a total score (count of passed metrics)

An evaluation passes if:
- ALL mandatory metrics pass, AND
- The count of passed cumulative metrics meets or exceeds the `passing_score_threshold`

### Example Structure

```python
from teval import EvaluationRubric, MetricDefinition

rubric = EvaluationRubric(
    rubric_id="code_review_v1",
    metrics=[
        # Mandatory metrics (must all pass)
        MetricDefinition(id="M1", rubric="Code compiles without errors", mandatory=True),
        MetricDefinition(id="M2", rubric="No security vulnerabilities detected", mandatory=True),
        # Cumulative metrics (contribute to score count)
        MetricDefinition(id="C1", rubric="Follows project style guide"),
        MetricDefinition(id="C2", rubric="Includes appropriate comments"),
        MetricDefinition(id="C3", rubric="Uses meaningful variable names"),
        MetricDefinition(id="C4", rubric="Has proper error handling"),
    ],
    passing_score_threshold=3  # At least 3 of 4 cumulative metrics must pass
)

# Access mandatory and cumulative metrics via properties
print(f"Mandatory: {len(rubric.mandatory_metrics)}")  # 2
print(f"Cumulative: {len(rubric.cumulative_metrics)}")  # 4
```

## LLM Integration

The framework provides built-in methods to integrate with LLM APIs for automated evaluation.

### 1. Generate Prompt Text

Use `to_prompt_text()` to create formatted instructions for LLM evaluators:

```python
prompt_text = rubric.to_prompt_text()
# Returns formatted markdown with:
# - Mandatory criteria (all must pass)
# - Cumulative criteria (with threshold)
# - Clear evaluation instructions

# Use in your LLM prompt:
evaluation_prompt = f"""
Evaluate the following code submission:

{rubric.to_prompt_text()}

Code to evaluate:
{code_to_evaluate}
"""
```

### 2. Generate JSON Schema or Pydantic Model

**Option A: JSON Schema** - Use `to_json_schema()` for structured LLM outputs:

```python
schema = rubric.to_json_schema()
# Returns OpenAPI/Swagger-compatible JSON Schema with:
# - Boolean fields for each metric
# - Optional reasoning fields (metric_id + "_reasoning")
# - Proper required/optional specifications

# Example with Gemini:
import google.generativeai as genai

response = model.generate_content(
    evaluation_prompt,
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=schema
    )
)

# Example with OpenAI:
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": evaluation_prompt}],
    response_format={"type": "json_schema", "json_schema": schema}
)
```

**Option B: Pydantic Model** - Use `to_pydantic_model()` for type-safe validation (recommended):

```python
ResultModel = rubric.to_pydantic_model()
# Returns a dynamically created Pydantic model class with:
# - Boolean fields for each metric (required)
# - Optional string fields for reasoning
# - Automatic validation and type checking

# Use with libraries that support Pydantic models
# Example with instructor (OpenAI):
import instructor
from openai import OpenAI

client = instructor.from_openai(OpenAI())

result = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": evaluation_prompt}],
    response_model=ResultModel  # Type-safe response
)

# Direct access to fields with type safety
print(result.M1)  # IDE autocomplete works!
print(result.M1_reasoning)

# Or parse JSON manually
json_response = '{"M1": true, "C1": false}'
result = ResultModel.model_validate_json(json_response)

# Export to dict
result_dict = result.model_dump()
```

### 3. Validate LLM Responses

Use `validate_result()` to check if the evaluation passes (accepts JSON string or dict):

```python
# Option A: Pass JSON string directly
passes = rubric.validate_result(response.text)

# Option B: Pass parsed dictionary
import json
result_dict = json.loads(response.text)
passes = rubric.validate_result(result_dict)

if passes:
    print("✓ Evaluation passed!")
    # All mandatory metrics passed AND
    # Cumulative threshold met
else:
    print("✗ Evaluation failed")
    # Either a mandatory metric failed OR
    # Cumulative threshold not met
```

### Complete Example

```python
from teval import EvaluationRubric, MetricDefinition
import json

# 1. Define rubric
rubric = EvaluationRubric(
    rubric_id="code_review_v1",
    metrics=[
        MetricDefinition(id="M1", rubric="Code compiles", mandatory=True),
        MetricDefinition(id="M2", rubric="No security issues", mandatory=True),
        MetricDefinition(id="C1", rubric="Follows style guide"),
        MetricDefinition(id="C2", rubric="Has tests"),
    ],
    passing_score_threshold=1
)

# 2. Get prompt and schema for LLM
prompt = rubric.to_prompt_text()
schema = rubric.to_json_schema()

# 3. Get LLM evaluation (your API call here)
llm_response = '{"M1": true, "M2": true, "C1": true, "C2": false}'

# 4. Validate result
passes = rubric.validate_result(llm_response)
print(f"Result: {'PASS' if passes else 'FAIL'}")
# Output: Result: PASS
# (Both mandatory metrics passed, 1 of 2 cumulative metrics passed)
```

See `example_usage.py` and `example_pydantic.py` for complete working examples.

## Why Use Pydantic Models?

The `to_pydantic_model()` approach provides significant advantages over plain JSON schemas:

### ✅ Type Safety
```python
ResultModel = rubric.to_pydantic_model()
result = ResultModel(M1=True, C1=False)

# IDE knows these types:
result.M1  # bool (autocomplete works!)
result.M1_reasoning  # Optional[str]
```

### ✅ Automatic Validation
```python
# Wrong type - caught immediately
result = ResultModel(M1="yes")  # ❌ ValidationError

# Missing required field - caught immediately
result = ResultModel(M1=True)  # ❌ ValidationError (missing C1)

# Extra fields - rejected
result = ResultModel(M1=True, C1=False, extra="bad")  # ❌ ValidationError
```

### ✅ Better Developer Experience
```python
# Direct attribute access (not dict keys)
if result.M1:  # Clear and type-safe
    print(result.M1_reasoning)

# Easy serialization
json_str = result.model_dump_json()
dict_data = result.model_dump(exclude_none=True)

# Easy parsing
result = ResultModel.model_validate_json(llm_response)
```

### ✅ Integration with LLM Libraries
```python
# Works seamlessly with instructor
import instructor
from openai import OpenAI

client = instructor.from_openai(OpenAI())

# Returns a validated Pydantic instance
result = client.chat.completions.create(
    model="gpt-4",
    response_model=ResultModel,  # ← Type-safe!
    messages=[...]
)
```

### When to Use What

- **Use `to_pydantic_model()`** when:
  - You want type safety and IDE support
  - You're using libraries like `instructor`, `marvin`, or `langchain`
  - You want automatic validation
  - You prefer Python objects over dictionaries

- **Use `to_json_schema()`** when:
  - You need a plain JSON schema for API specifications
  - You're working with non-Python systems
  - You need OpenAPI/Swagger documentation
  - The LLM API only accepts JSON schemas

## Project Structure

```
teval/
├── teval/                          # Main package
│   ├── __init__.py
│   └── metrics.py                  # Core evaluation framework
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── test_metrics.py             # Unit tests
│   ├── test_integration_vertex_ai.py  # Vertex AI integration tests
│   └── INTEGRATION_TESTS.md        # Integration test documentation
├── example_usage.py                # Complete LLM integration example
├── example_pydantic.py             # Pydantic model examples
├── pyproject.toml                  # Project configuration
├── CLAUDE.md                       # Development guide
└── README.md
```

## Testing

### Unit Tests

Run the core framework tests (no external dependencies):

```bash
# Run all unit tests
uv run pytest tests/test_metrics.py -v

# Or exclude integration tests
uv run pytest -m "not integration" -v
```

### Integration Tests

Integration tests with Vertex AI require Google Cloud credentials:

```bash
# Install integration test dependencies
uv sync --group integration-tests

# Set up credentials
export GOOGLE_CLOUD_PROJECT=your-project-id
gcloud auth application-default login

# Run integration tests
uv run pytest tests/test_integration_vertex_ai.py -v
```

See `tests/INTEGRATION_TESTS.md` for detailed setup instructions.

## License

Apache License 2.0
