# teval

Trivial LLM eval - as simple as possible (maybe even a bit more simple)

A lightweight, straightforward evaluation framework for LLM outputs using Yes/No metrics with mandatory and cumulative scoring.

## Features

- **Two-tier metric system**: Mandatory metrics (all must pass) and cumulative metrics (threshold-based scoring)
- **Simple Yes/No evaluations**: Each metric is a binary pass/fail criterion
- **Count-based scoring**: Cumulative metrics contribute to a total score based on the number passed
- **Pydantic-based validation**: Type-safe metric definitions with built-in validation
- **Minimal dependencies**: Only requires Pydantic 2.7.4+ (< 3.0.0)

## Installation

**Requirements**: Python 3.10 - 3.14

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
from tevak import EvaluationRubric, MetricDefinition

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

## Project Structure

```
teval/
├── tevak/           # Main package
│   ├── __init__.py
│   └── metrics.py   # Core evaluation framework
├── tests/           # Test suite
│   ├── __init__.py
│   └── test_metrics.py
├── pyproject.toml   # Project configuration
└── README.md
```

## License

Apache License 2.0
