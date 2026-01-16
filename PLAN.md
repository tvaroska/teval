# teval Sprint Plan

## Sprint 0: Critical Foundation (ACTIVE)

### P0: Production Readiness Blockers

#### S0-DOC-1: Add Comprehensive API Docstrings
**Status**: ✅ COMPLETED (2026-01-14)
**Plan**: `/home/boris/.claude/plans/wiggly-discovering-pnueli.md`
**Files**: `teval/metrics.py`
**Requirements**:
- Add detailed docstrings to all public methods
- Include parameter descriptions with types
- Document return values and exceptions
- Add usage examples in docstrings
- Follow NumPy docstring style guide

#### S0-BUG-1: Fix Python Version Inconsistencies
**Status**: ✅ COMPLETED (2025-12-29, commit 7656ec8)
**Plan**: `/home/boris/.claude/plans/rippling-wondering-feigenbaum.md`
**Files**: `pyproject.toml`, `tox.ini`, `Dockerfile`
**Issue**: pyproject.toml restricts to <3.14 but tox.ini tests 3.14
**Fix**: Align all configuration files to support Python 3.10-3.13

#### S0-DOC-2: Create Quick Start Guide
**Status**: ✅ COMPLETED (2026-01-14)
**Plan**: `/home/boris/.claude/plans/replicated-painting-puffin.md`
**Files**: `docs/quickstart.md`, `README.md`
**Requirements**:
- 5-minute guide from zero to first evaluation
- pip installation instructions (not just uv)
- Minimal working example
- Link from README.md

### P1: Critical Documentation

#### S0-DOC-3: API Reference Documentation
**Status**: ✅ COMPLETED (2026-01-15)
**Plan**: `/home/boris/.claude/plans/snuggly-toasting-pinwheel.md`
**Files**: `docs/api.md`, `docs/generate_api_html.py`, `pyproject.toml`
**Requirements**:
- Complete API reference for all public classes/methods
- Generated from docstrings
- Include type information
- Cross-referenced examples


### P2: Production Robustness

#### S0-VAL-1: Improve Input Validation
**Status**: ✅ COMPLETED (2026-01-15)
**Plan**: `/home/boris/.claude/plans/compiled-dreaming-cook.md`
**Files**: `teval/metrics.py`, `tests/test_metrics.py`
**Requirements**:
- ✅ Validate metric IDs for JSON compatibility
- ✅ Check for empty metric lists
- ✅ Add maximum limits for metric counts (100 total, 20 mandatory)
- ✅ Better error messages with context

## Sprint 1: Human-LLM Alignment

### Human Evaluation Collection System

#### S1-FE-1: Create Web UI for Human Evaluation Collection
**Status**: ✅ COMPLETED (2026-01-15)
**Plan**: `/home/boris/.claude/plans/goofy-herding-gadget.md`
**Files**: `teval/human/app.py`, `teval/human/forms.py`, `teval/human/styles.py`, `teval/human/__init__.py`
**Implementation**: FastHTML-based web forms with HTMX interactivity
**Features**:
- Interactive evaluation forms with real-time progress tracking
- Auto-save to browser local storage
- JSON export functionality
- Keyboard shortcuts (Enter to submit, Ctrl+E to export)
- Dynamic metric filtering for large rubrics
- Mobile-responsive design
**Usage**:
```python
from teval.human import create_evaluation_app

# Create standalone app
app = create_evaluation_app(rubric, title="Evaluation")
# serve(app)  # Starts at http://localhost:5000
```

#### S1-FE-2: Bulk Import for Existing Human Data
**Status**: ✅ COMPLETED (2026-01-15)
**Plan**: `/home/boris/.claude/plans/parallel-crunching-shannon.md`
**Files**: `teval/human/importers.py`, `tests/test_importers.py`
**Implementation**: Standalone module for batch preparation of evaluation data
**Features**:
- Import from CSV, JSON, and Pandas DataFrame formats
- Best-effort validation with detailed import reports
- Handles missing/invalid data gracefully (defaults to False)
- Auto-detection of file formats
- Support for nested JSON structures
- Comprehensive test coverage (42 tests passing)
**Usage**:
```python
from teval.human import import_evaluations

# Import from various formats
results, report = import_evaluations("evaluations.csv", rubric)
results, report = import_evaluations(dataframe, rubric)
results, report = import_evaluations(json_data, rubric)

print(f"Imported {report.success_count}/{report.total_count} evaluations")
```

#### S1-BE-1: Inter-rater Reliability Metrics
**Status**: TODO
**Files**: `teval/metrics.py`, `teval/statistics.py`
**Metrics**: Cohen's Kappa, Fleiss' Kappa, Krippendorff's Alpha

#### S1-BE-2: Alignment Statistical Analysis
**Status**: TODO
**Files**: `teval/statistics.py`
**Features**: Confidence intervals, hypothesis testing, bootstrap sampling

### Multi-stage Evaluation Pipeline

#### S1-BE-3: Pipeline Architecture
**Status**: TODO
**Files**: `teval/pipeline.py`
**Requirements**:
- Composable evaluation stages
- Stage dependencies and conditions
- Data passing between stages
- Stop-on-fail support

#### S1-BE-4: Pipeline Configuration
**Status**: TODO
**Files**: `teval/pipeline.py`
**Features**: YAML/JSON config, versioning, dry-run mode

## Sprint 2: Domain-Specific Evaluators

### Library Architecture (Not Service)

#### S2-ARCH-1: Plugin Architecture Design
**Status**: TODO
**Design Principle**: teval remains a library that other frameworks integrate
```python
# Users bring their own LLM client
from openai import OpenAI
from teval import EvaluationRubric

client = OpenAI()
rubric = EvaluationRubric(...)

# teval just provides the schema/model
response = client.chat.completions.create(
    model="gpt-4",
    response_format=rubric.to_json_schema()
)

# And validates the result
passes = rubric.validate_result(response)
```

### RAG Evaluation Module

#### S2-RAG-1: RAG-Specific Metrics
**Status**: TODO
**Files**: `teval/domains/rag.py`
**Metrics**:
- Context relevance
- Answer attribution
- Hallucination detection
- Source citation accuracy

#### S2-RAG-2: Pre-built RAG Rubrics
**Status**: TODO
**Files**: `teval/domains/rag.py`
**Rubrics**: QA accuracy, retrieval quality, factual grounding

### Safety & Bias Module

#### S2-SAFE-1: Safety Detection Metrics
**Status**: TODO
**Files**: `teval/domains/safety.py`
**Metrics**: Harmful content, PII detection, prompt injection

#### S2-SAFE-2: Bias Detection Framework
**Status**: TODO
**Files**: `teval/domains/bias.py`
**Features**: Protected attributes, fairness metrics, demographic parity

## Backlog (Future Sprints)

### Performance & Scale
- Caching for Pydantic model generation (avoid recreation)
- Async evaluation support
- Batch processing optimizations
- Distributed evaluation
- SQL/NoSQL storage backends

### Advanced Analytics
- Evaluation trend analysis
- A/B testing framework
- Cost-quality trade-offs
- Model comparison tools

### Enterprise Features
- SAML/SSO for human evaluation UI
- Audit logging
- Role-based access control
- Data encryption at rest

## Design Decisions

### Library, Not Service
- teval provides building blocks, not a full platform
- Users integrate with their own LLM providers
- No vendor lock-in or API keys required
- Composable with any Python framework

### Focus Areas
1. **Documentation First**: Every feature fully documented
2. **Production Ready**: Built for real-world scale
3. **Framework Agnostic**: Works with any LLM provider
4. **Type Safe**: Full type hints and validation

## Notes
- Sprint 0 is highest priority - blocks v0.2.0 release
- Each sprint approximately 2-3 weeks
- Community feedback may adjust priorities
- Maintain backward compatibility in 0.x releases