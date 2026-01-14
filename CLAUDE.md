# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**teval** is a trivial LLM evaluation framework designed to be as simple as possible. It provides a straightforward approach to evaluating LLM outputs using Yes/No metrics with mandatory and cumulative scoring.

## Development Environment

This project uses **uv** for dependency management:
- Python version: 3.10-3.14 (specified in .python-version and pyproject.toml)
- Virtual environment: `.venv/` (managed by uv)
- Dependencies: Pydantic 2.8.0+ (< 3.0.0)

### Common Commands

```bash
# Install dependencies (including dev dependencies)
uv sync --all-groups

# Install only production dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Run Python with the project's environment
uv run python <script.py>

# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_metrics.py

# Run a specific test
uv run pytest tests/test_metrics.py::TestEvaluationRubric::test_mandatory_metrics_property
```

## Code Architecture

### Core Module Structure

The codebase is organized in the `teval/` package:

- **teval/metrics.py**: Core evaluation framework defining the rubric and metric system

### Evaluation System Design

The evaluation framework uses a two-tier metric system:

1. **Mandatory Metrics** (metrics with `mandatory=True`)
   - Binary Yes/No evaluations
   - ALL must pass for the evaluation to succeed
   - Each failure immediately fails the entire evaluation

2. **Cumulative Metrics** (metrics with `mandatory=False`, the default)
   - Binary Yes/No evaluations that contribute to a total score
   - Score = count of passed metrics (each has implicit weight of 1.0)
   - Must meet or exceed `passing_score_threshold` count to pass
   - Maximum score = total number of cumulative metrics

### Key Data Models

**MetricDefinition**:
- `id`: Unique identifier (e.g., 'M1', 'code_style_pass')
- `rubric`: The specific pass/fail criterion text
- `mandatory`: Boolean flag (default: False). If True, this metric must pass for evaluation to pass.

**EvaluationRubric**:
- `rubric_id`: Unique identifier for the rubric
- `metrics`: Single list containing all metrics (both mandatory and cumulative)
- `passing_score_threshold`: Minimum count of passed cumulative metrics
- `mandatory_metrics` (property): Filters and returns metrics where `mandatory=True`
- `cumulative_metrics` (property): Filters and returns metrics where `mandatory=False`

### LLM Integration Methods

**EvaluationRubric.to_prompt_text()**:
- Generates formatted markdown text describing the rubric
- Use this to include evaluation criteria in LLM prompts
- Returns a string with mandatory criteria, cumulative criteria, and instructions

**EvaluationRubric.to_json_schema()**:
- Generates JSON Schema for structured LLM output
- Compatible with OpenAPI/Swagger specifications
- Defines boolean fields for each metric and optional reasoning fields
- Use with Gemini's `response_schema` or OpenAI's `response_format`

**EvaluationRubric.to_pydantic_model()**:
- Dynamically creates a Pydantic model class for type-safe validation
- Returns a `Type[BaseModel]` that can be instantiated or used with LLM libraries
- Includes required boolean fields for each metric and optional reasoning fields
- Provides automatic validation, JSON parsing, and type hints
- Recommended for use with libraries like `instructor` or direct Pydantic validation

**EvaluationRubric.validate_result(result: Union[str, Dict[str, Any]])**:
- Validates an LLM-generated evaluation result
- Accepts either a JSON string or a dictionary
- Checks that all mandatory metrics pass AND cumulative threshold is met
- Raises ValueError if required metrics are missing, have invalid types, or if JSON is malformed
- Returns True if evaluation passes, False otherwise

### Validation Rules

The `EvaluationRubric` model enforces:
- All metric IDs must be unique across the entire `metrics` list
- `passing_score_threshold` cannot exceed the count of cumulative (non-mandatory) metrics
- Pydantic strict mode (`extra = "forbid"`) prevents unexpected fields

## Development Notes

- The project is in early development (version 0.1.0)
- Test suite uses pytest (run with `uv run pytest`)
- Uses Apache 2.0 license
- Type hints are used throughout with Pydantic validators for runtime validation
