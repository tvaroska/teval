# API Reference

## Overview

The teval API provides a simple yet powerful framework for defining and validating evaluation rubrics for Large Language Model (LLM) outputs. The framework supports two types of metrics:

- **Mandatory Metrics**: Must all pass for the evaluation to succeed
- **Cumulative Metrics**: Contribute to a total score with configurable thresholds

### Installation

```python
pip install teval
```

### Basic Import

```python
from teval import EvaluationRubric, MetricDefinition
```

### Quick Links

- [MetricDefinition](#metricdefinition) - Define individual Yes/No evaluation metrics
- [EvaluationRubric](#evaluationrubric) - Complete evaluation rubric with metrics and thresholds
- [Common Usage Patterns](#common-usage-patterns) - Practical examples and patterns

---

## MetricDefinition

```python
class MetricDefinition(BaseModel)
```

Defines a single Yes/No evaluation metric with an optional mandatory flag.

### Constructor

```python
MetricDefinition(
    id: str,
    rubric: str,
    mandatory: bool = False
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | `str` | required | Unique identifier for the metric (e.g., 'M1', 'code_style_pass') |
| `rubric` | `str` | required | The specific pass/fail criterion text |
| `mandatory` | `bool` | `False` | If True, this metric must pass for the evaluation to pass |

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Unique metric identifier |
| `rubric` | `str` | The evaluation criterion |
| `mandatory` | `bool` | Whether this is a must-pass metric |

### Example

```python
# Create a mandatory metric
mandatory_metric = MetricDefinition(
    id="M1",
    rubric="Code compiles without errors",
    mandatory=True
)

# Create a cumulative (scored) metric
cumulative_metric = MetricDefinition(
    id="C1",
    rubric="Code follows style guidelines",
    mandatory=False  # Default value
)
```

### Validation Rules

- Extra fields are forbidden (Pydantic strict mode)
- Both `id` and `rubric` are required fields
- The `id` must be unique within an EvaluationRubric

---

## EvaluationRubric

```python
class EvaluationRubric(BaseModel)
```

Complete evaluation rubric containing all metrics and the passing threshold.

### Constructor

```python
EvaluationRubric(
    rubric_id: str,
    metrics: List[MetricDefinition],
    passing_score_threshold: int
)
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `rubric_id` | `str` | Unique identifier for this rubric |
| `metrics` | `List[MetricDefinition]` | All evaluation metrics (both mandatory and cumulative) |
| `passing_score_threshold` | `int` | Minimum count of passed cumulative metrics needed |

### Properties

#### mandatory_metrics

```python
@property
def mandatory_metrics(self) -> List[MetricDefinition]
```

Returns list of metrics where `mandatory=True`. These must all pass for evaluation to succeed.

**Returns:** `List[MetricDefinition]` - Filtered list of mandatory metrics

**Example:**
```python
rubric = EvaluationRubric(
    rubric_id="test",
    metrics=[
        MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        MetricDefinition(id="C1", rubric="Optional")
    ],
    passing_score_threshold=0
)
print(len(rubric.mandatory_metrics))  # Output: 1
print(rubric.mandatory_metrics[0].id)  # Output: 'M1'
```

#### cumulative_metrics

```python
@property
def cumulative_metrics(self) -> List[MetricDefinition]
```

Returns list of metrics where `mandatory=False`. These contribute to the cumulative score.

**Returns:** `List[MetricDefinition]` - Filtered list of cumulative metrics

**Example:**
```python
rubric = EvaluationRubric(
    rubric_id="test",
    metrics=[
        MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        MetricDefinition(id="C1", rubric="Optional 1"),
        MetricDefinition(id="C2", rubric="Optional 2")
    ],
    passing_score_threshold=1
)
print(len(rubric.cumulative_metrics))  # Output: 2
print([m.id for m in rubric.cumulative_metrics])  # Output: ['C1', 'C2']
```

### Methods

#### to_prompt_text()

```python
def to_prompt_text(self) -> str
```

Generate formatted markdown text for inclusion in LLM prompts.

**Returns:** `str` - Formatted markdown containing rubric criteria and instructions

**Example:**
```python
rubric = EvaluationRubric(
    rubric_id="code_review",
    metrics=[
        MetricDefinition(id="M1", rubric="No syntax errors", mandatory=True),
        MetricDefinition(id="C1", rubric="Good variable names")
    ],
    passing_score_threshold=1
)
prompt = rubric.to_prompt_text()
print(prompt)
# Output:
# # Evaluation Rubric: code_review
#
# ## Mandatory Criteria (ALL must pass)
#
# - **M1**: No syntax errors
#
# ## Cumulative Criteria
# (Must pass at least 1 of 1)
#
# - **C1**: Good variable names
#
# ## Instructions
# For each criterion above, evaluate whether it passes (Yes) or fails (No).
# - All 1 mandatory criteria must pass.
# - At least 1 cumulative criteria must pass.
```

#### to_json_schema()

```python
def to_json_schema(self) -> Dict[str, Any]
```

Generate JSON Schema for structured LLM output. Compatible with OpenAI's response_format and similar APIs.

**Returns:** `Dict[str, Any]` - JSON Schema with boolean fields for each metric and optional reasoning fields

**Example:**
```python
rubric = EvaluationRubric(
    rubric_id="test",
    metrics=[
        MetricDefinition(id="M1", rubric="Must pass", mandatory=True)
    ],
    passing_score_threshold=0
)
schema = rubric.to_json_schema()

# Use with OpenAI
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    response_format={"type": "json_schema", "json_schema": schema}
)
```

**Schema Structure:**
```json
{
    "type": "object",
    "properties": {
        "M1": {
            "type": "boolean",
            "description": "Does this pass the criterion: Must pass"
        },
        "M1_reasoning": {
            "type": "string",
            "description": "Explanation for the M1 evaluation"
        }
    },
    "required": ["M1"],
    "additionalProperties": false
}
```

#### to_pydantic_model()

```python
def to_pydantic_model(self) -> Type[BaseModel]
```

Create a dynamic Pydantic model class for type-safe validation.

**Returns:** `Type[BaseModel]` - Dynamically generated model class with validation

**Generated Model Methods:**
- `passes() -> bool` - Check if evaluation meets all requirements
- `get_failed_metrics() -> List[str]` - Get list of failed metric IDs
- `get_passed_metrics() -> List[str]` - Get list of passed metric IDs
- `to_report(title: Optional[str] = None) -> str` - Generate formatted report

**Example:**
```python
rubric = EvaluationRubric(
    rubric_id="test",
    metrics=[
        MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        MetricDefinition(id="C1", rubric="Optional")
    ],
    passing_score_threshold=0
)

# Create model class
ResultModel = rubric.to_pydantic_model()

# Instantiate with results
result = ResultModel(M1=True, C1=False, M1_reasoning="Well structured")

# Use helper methods
print(result.passes())  # Output: True
print(result.get_failed_metrics())  # Output: ['C1']
print(result.get_passed_metrics())  # Output: ['M1']
```

#### validate_result()

```python
def validate_result(
    self,
    result: Union[str, Dict[str, Any]]
) -> bool
```

Validate an LLM-generated evaluation result against this rubric.

**Parameters:**
- `result` (`str` or `Dict[str, Any]`) - JSON string or dictionary with boolean values for each metric ID

**Returns:** `bool` - True if all mandatory metrics pass AND cumulative threshold is met

**Raises:**
- `ValueError` - If required metrics missing, non-boolean values, or malformed JSON

**Example:**
```python
rubric = EvaluationRubric(
    rubric_id="test",
    metrics=[
        MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        MetricDefinition(id="C1", rubric="Optional")
    ],
    passing_score_threshold=0
)

# Validate dictionary
result1 = {"M1": True, "C1": False}
print(rubric.validate_result(result1))  # Output: True

# Validate JSON string
result2 = '{"M1": false, "C1": true}'
print(rubric.validate_result(result2))  # Output: False (mandatory failed)
```

#### generate_report()

```python
def generate_report(
    self,
    result: Dict[str, Any],
    reasoning: Optional[Dict[str, Optional[str]]] = None,
    title: Optional[str] = None
) -> str
```

Generate a formatted markdown report of evaluation results.

**Parameters:**
- `result` (`Dict[str, Any]`) - Dictionary mapping metric IDs to boolean values
- `reasoning` (`Optional[Dict[str, Optional[str]]]`) - Optional explanations for each metric
- `title` (`Optional[str]`) - Custom report title (default: "Evaluation Report: {rubric_id}")

**Returns:** `str` - Formatted markdown report

**Example:**
```python
rubric = EvaluationRubric(
    rubric_id="review",
    metrics=[
        MetricDefinition(id="M1", rubric="No errors", mandatory=True),
        MetricDefinition(id="C1", rubric="Good style")
    ],
    passing_score_threshold=1
)

result = {"M1": True, "C1": False}
reasoning = {"M1": "Code compiles", "C1": "Poor naming"}
report = rubric.generate_report(result, reasoning, "Code Review")
print(report)
```

**Output Format:**
```markdown
# Code Review

**Overall Result: FAIL**

## Mandatory Criteria (ALL must pass)

✓ **M1** [PASS]: No errors
  → Code compiles

## Cumulative Criteria
**Score: 0/1** (Required: 1)

✗ **C1** [FAIL]: Good style
  → Poor naming

⚠️ **Need 1 more cumulative metric(s) to pass**

## Requirements for Passing

**Mandatory criteria (ALL must pass):**
  ✓ M1

**Cumulative criteria:**
  - Need at least 1 of 1 to pass
  - Currently passed: 0
  - Still need: 1 more
```

#### calculate_alignment()

```python
def calculate_alignment(
    self,
    results_a: Union[BaseModel, List[BaseModel]],
    results_b: Union[BaseModel, List[BaseModel]]
) -> float
```

Calculate alignment between two sets of evaluation results. Useful for measuring human-LLM alignment or comparing models.

**Parameters:**
- `results_a` - Single result or list from `to_pydantic_model()`
- `results_b` - Single result or list to compare against

**Returns:** `float` - Alignment score (0.0 to 1.0)
- 1.0 = Perfect alignment (all pass/fail decisions match)
- 0.0 = No alignment (all decisions disagree)

**Raises:**
- `TypeError` - If inputs aren't BaseModel instances or types mismatch
- `ValueError` - If list lengths differ

**Example:**
```python
rubric = EvaluationRubric(
    rubric_id="test",
    metrics=[
        MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        MetricDefinition(id="C1", rubric="Optional")
    ],
    passing_score_threshold=1
)

ResultModel = rubric.to_pydantic_model()

# Single comparison
human = ResultModel(M1=True, C1=True)
llm = ResultModel(M1=True, C1=False)
alignment = rubric.calculate_alignment(human, llm)
print(f"Human-LLM alignment: {alignment:.0%}")  # Output: 100%

# Batch comparison
humans = [
    ResultModel(M1=True, C1=True),
    ResultModel(M1=False, C1=False)
]
llms = [
    ResultModel(M1=True, C1=False),
    ResultModel(M1=False, C1=True)
]
alignment = rubric.calculate_alignment(humans, llms)
print(f"Batch alignment: {alignment:.0%}")  # Output: 50%
```

### Validation Rules

1. **Unique Metric IDs**: All metric IDs must be unique across the metrics list
2. **Achievable Threshold**: `passing_score_threshold` cannot exceed count of cumulative metrics
3. **Strict Mode**: Extra fields are forbidden (Pydantic `extra="forbid"`)

### Example: Complete Rubric

```python
from teval import EvaluationRubric, MetricDefinition

# Define a comprehensive evaluation rubric
rubric = EvaluationRubric(
    rubric_id="code_quality_v1",
    metrics=[
        # Mandatory metrics - ALL must pass
        MetricDefinition(
            id="M1",
            rubric="Code executes without runtime errors",
            mandatory=True
        ),
        MetricDefinition(
            id="M2",
            rubric="No security vulnerabilities detected",
            mandatory=True
        ),

        # Cumulative metrics - scored
        MetricDefinition(
            id="C1",
            rubric="Code follows PEP 8 style guidelines"
        ),
        MetricDefinition(
            id="C2",
            rubric="Functions have descriptive docstrings"
        ),
        MetricDefinition(
            id="C3",
            rubric="Variables use meaningful names"
        ),
    ],
    passing_score_threshold=2  # Need at least 2 of 3 cumulative
)

# Validate a result
result = {
    "M1": True,   # Passes
    "M2": True,   # Passes
    "C1": True,   # Passes
    "C2": False,  # Fails
    "C3": True,   # Passes
}

if rubric.validate_result(result):
    print("✅ Evaluation PASSED")
else:
    print("❌ Evaluation FAILED")

# Output: ✅ Evaluation PASSED (both mandatory pass, 2/3 cumulative pass)
```

---

## Common Usage Patterns

### LLM Integration Examples

#### OpenAI Integration

```python
from openai import OpenAI
from teval import EvaluationRubric, MetricDefinition

# Create evaluation rubric
rubric = EvaluationRubric(
    rubric_id="helpful_answer_v1",
    metrics=[
        MetricDefinition(id="M1", rubric="Answer is factually accurate", mandatory=True),
        MetricDefinition(id="C1", rubric="Answer directly addresses the question"),
        MetricDefinition(id="C2", rubric="Answer provides helpful context"),
        MetricDefinition(id="C3", rubric="Answer uses clear language"),
    ],
    passing_score_threshold=2
)

# Generate evaluation prompt
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": rubric.to_prompt_text()},
        {"role": "user", "content": f"Evaluate this answer: {answer_to_evaluate}"}
    ],
    response_format={"type": "json_schema", "json_schema": rubric.to_json_schema()}
)

# Validate result
result = json.loads(response.choices[0].message.content)
if rubric.validate_result(result):
    print("Answer meets quality standards")
```

#### Anthropic Claude Integration

```python
import anthropic
from teval import EvaluationRubric, MetricDefinition

# Create rubric
rubric = EvaluationRubric(
    rubric_id="code_review",
    metrics=[
        MetricDefinition(id="M1", rubric="No syntax errors", mandatory=True),
        MetricDefinition(id="M2", rubric="No security vulnerabilities", mandatory=True),
        MetricDefinition(id="C1", rubric="Follows project conventions"),
        MetricDefinition(id="C2", rubric="Has appropriate error handling"),
    ],
    passing_score_threshold=1
)

# Use with Claude
client = anthropic.Anthropic()
ResultModel = rubric.to_pydantic_model()

prompt = f"""
{rubric.to_prompt_text()}

Review this code and provide your evaluation as JSON:
```python
{code_to_review}
```

Return a JSON object with boolean values for each metric ID.
"""

response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1000,
    messages=[{"role": "user", "content": prompt}]
)

# Parse and validate
import json
result = json.loads(response.content[0].text)
evaluation = ResultModel(**result)

if evaluation.passes():
    print("✅ Code review passed")
else:
    print(f"❌ Failed metrics: {evaluation.get_failed_metrics()}")
```

### Batch Evaluation

```python
from teval import EvaluationRubric, MetricDefinition
from typing import List, Dict

def batch_evaluate(rubric: EvaluationRubric, results: List[Dict[str, bool]]):
    """Evaluate multiple results and generate summary statistics."""

    passed = []
    failed = []

    for i, result in enumerate(results):
        try:
            if rubric.validate_result(result):
                passed.append(i)
            else:
                failed.append(i)
        except ValueError as e:
            print(f"Result {i} invalid: {e}")
            failed.append(i)

    # Calculate statistics
    total = len(results)
    pass_rate = len(passed) / total if total > 0 else 0

    print(f"Batch Evaluation Summary:")
    print(f"- Total evaluations: {total}")
    print(f"- Passed: {len(passed)} ({pass_rate:.1%})")
    print(f"- Failed: {len(failed)} ({(1-pass_rate):.1%})")

    return passed, failed

# Example usage
rubric = EvaluationRubric(
    rubric_id="quality_check",
    metrics=[
        MetricDefinition(id="M1", rubric="Meets requirements", mandatory=True),
        MetricDefinition(id="C1", rubric="Well documented"),
        MetricDefinition(id="C2", rubric="Efficient implementation"),
    ],
    passing_score_threshold=1
)

# Batch of evaluation results
results = [
    {"M1": True, "C1": True, "C2": False},   # Pass
    {"M1": True, "C1": True, "C2": True},    # Pass
    {"M1": False, "C1": True, "C2": True},   # Fail (mandatory)
    {"M1": True, "C1": False, "C2": False},  # Fail (threshold)
]

passed_indices, failed_indices = batch_evaluate(rubric, results)
```

### Human-LLM Alignment Measurement

```python
from teval import EvaluationRubric, MetricDefinition
import statistics

def measure_alignment(rubric: EvaluationRubric, human_results, llm_results):
    """Measure alignment between human and LLM evaluations."""

    ResultModel = rubric.to_pydantic_model()

    # Convert to Pydantic models
    human_models = [ResultModel(**r) for r in human_results]
    llm_models = [ResultModel(**r) for r in llm_results]

    # Calculate overall alignment
    alignment = rubric.calculate_alignment(human_models, llm_models)

    # Calculate per-metric agreement
    metric_agreements = {}
    for metric in rubric.metrics:
        agreements = [
            h.__dict__[metric.id] == l.__dict__[metric.id]
            for h, l in zip(human_models, llm_models)
        ]
        metric_agreements[metric.id] = sum(agreements) / len(agreements)

    print(f"Human-LLM Alignment Report:")
    print(f"Overall Pass/Fail Agreement: {alignment:.1%}")
    print(f"\nPer-Metric Agreement:")
    for metric_id, agreement in metric_agreements.items():
        print(f"  {metric_id}: {agreement:.1%}")

    return alignment, metric_agreements

# Example
rubric = EvaluationRubric(
    rubric_id="content_quality",
    metrics=[
        MetricDefinition(id="M1", rubric="Factually accurate", mandatory=True),
        MetricDefinition(id="C1", rubric="Clear and concise"),
        MetricDefinition(id="C2", rubric="Properly sourced"),
    ],
    passing_score_threshold=1
)

human_evaluations = [
    {"M1": True, "C1": True, "C2": False},
    {"M1": True, "C1": False, "C2": True},
    {"M1": False, "C1": True, "C2": True},
]

llm_evaluations = [
    {"M1": True, "C1": True, "C2": True},   # Disagrees on C2
    {"M1": True, "C1": False, "C2": True},  # Agrees fully
    {"M1": True, "C1": True, "C2": True},   # Disagrees on M1
]

alignment_score, metric_scores = measure_alignment(
    rubric, human_evaluations, llm_evaluations
)
```

### Custom Validation Workflows

```python
from teval import EvaluationRubric, MetricDefinition
import json
from pathlib import Path

class EvaluationPipeline:
    """Custom pipeline for evaluation workflows."""

    def __init__(self, rubric: EvaluationRubric):
        self.rubric = rubric
        self.ResultModel = rubric.to_pydantic_model()

    def evaluate_with_fallback(self, primary_result, fallback_result):
        """Try primary evaluation, fall back if it fails."""
        try:
            primary = self.ResultModel(**primary_result)
            if primary.passes():
                return primary, "primary"
        except:
            pass

        # Try fallback
        fallback = self.ResultModel(**fallback_result)
        return fallback, "fallback"

    def save_evaluation(self, result, filepath: Path):
        """Save evaluation result with metadata."""
        evaluation = self.ResultModel(**result)

        output = {
            "rubric_id": self.rubric.rubric_id,
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "passed": evaluation.passes(),
            "failed_metrics": evaluation.get_failed_metrics(),
            "passed_metrics": evaluation.get_passed_metrics(),
        }

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)

    def load_and_validate(self, filepath: Path):
        """Load and re-validate a saved evaluation."""
        with open(filepath) as f:
            data = json.load(f)

        # Re-validate with current rubric
        result = data['result']
        is_valid = self.rubric.validate_result(result)

        return {
            "original_passed": data['passed'],
            "current_passed": is_valid,
            "rubric_changed": data['passed'] != is_valid
        }

# Usage example
rubric = EvaluationRubric(
    rubric_id="api_response_v2",
    metrics=[
        MetricDefinition(id="M1", rubric="Returns valid JSON", mandatory=True),
        MetricDefinition(id="M2", rubric="Includes required fields", mandatory=True),
        MetricDefinition(id="C1", rubric="Response time under 1s"),
        MetricDefinition(id="C2", rubric="Includes helpful metadata"),
    ],
    passing_score_threshold=1
)

pipeline = EvaluationPipeline(rubric)

# Evaluate with fallback
primary = {"M1": False, "M2": True, "C1": True, "C2": False}
fallback = {"M1": True, "M2": True, "C1": False, "C2": True}

result, source = pipeline.evaluate_with_fallback(primary, fallback)
print(f"Used {source} evaluation: {result.passes()}")

# Save for audit
pipeline.save_evaluation(fallback, Path("evaluation_001.json"))
```

### Building Domain-Specific Rubrics

```python
from teval import EvaluationRubric, MetricDefinition

def create_code_generation_rubric():
    """Rubric for evaluating generated code."""
    return EvaluationRubric(
        rubric_id="code_gen_v1",
        metrics=[
            # Mandatory - correctness
            MetricDefinition(id="M1", rubric="Code is syntactically valid", mandatory=True),
            MetricDefinition(id="M2", rubric="Code produces expected output", mandatory=True),
            MetricDefinition(id="M3", rubric="No runtime errors on valid inputs", mandatory=True),

            # Cumulative - quality
            MetricDefinition(id="C1", rubric="Handles edge cases appropriately"),
            MetricDefinition(id="C2", rubric="Uses efficient algorithms/data structures"),
            MetricDefinition(id="C3", rubric="Includes error handling"),
            MetricDefinition(id="C4", rubric="Has clear variable/function names"),
            MetricDefinition(id="C5", rubric="Includes helpful comments"),
        ],
        passing_score_threshold=3  # Need 3 of 5 quality metrics
    )

def create_summarization_rubric():
    """Rubric for evaluating text summarization."""
    return EvaluationRubric(
        rubric_id="summary_v1",
        metrics=[
            # Mandatory - accuracy
            MetricDefinition(id="M1", rubric="No factual errors or hallucinations", mandatory=True),
            MetricDefinition(id="M2", rubric="Captures main points accurately", mandatory=True),

            # Cumulative - quality
            MetricDefinition(id="C1", rubric="Appropriate length (not too long/short)"),
            MetricDefinition(id="C2", rubric="Well-organized and coherent"),
            MetricDefinition(id="C3", rubric="Preserves important context"),
            MetricDefinition(id="C4", rubric="Uses clear, concise language"),
        ],
        passing_score_threshold=2  # Need 2 of 4 quality metrics
    )

def create_translation_rubric():
    """Rubric for evaluating translations."""
    return EvaluationRubric(
        rubric_id="translation_v1",
        metrics=[
            # Mandatory - correctness
            MetricDefinition(id="M1", rubric="Accurately conveys meaning", mandatory=True),
            MetricDefinition(id="M2", rubric="No significant omissions", mandatory=True),

            # Cumulative - quality
            MetricDefinition(id="C1", rubric="Natural and fluent in target language"),
            MetricDefinition(id="C2", rubric="Preserves tone and style"),
            MetricDefinition(id="C3", rubric="Handles idioms/cultural references well"),
            MetricDefinition(id="C4", rubric="Grammar and spelling are correct"),
        ],
        passing_score_threshold=3  # Need 3 of 4 quality metrics
    )

# Usage
code_rubric = create_code_generation_rubric()
summary_rubric = create_summarization_rubric()
translation_rubric = create_translation_rubric()

# Each rubric can be used with any LLM provider
print(code_rubric.to_prompt_text())
```

---

## See Also

- [Quick Start Guide](quickstart.md) - Get started with teval in 5 minutes
- [Roadmap](roadmap.md) - Future development plans
- [GitHub Repository](https://github.com/yourusername/teval) - Source code and issues