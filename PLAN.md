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

#### S0-FE-1: Add File-Based Storage with Auto-Sync
**Status**: ✅ COMPLETED (2026-01-16)
**Plan**: `/home/boris/.claude/plans/drifting-knitting-truffle.md`
**Files**: `teval/human/app.py`, `teval/human/sync_storage.py`, `tests/test_sync_storage.py`
**Requirements**:
- Enhance human evaluation app with optional server-side file storage
- No database required - JSON files on filesystem
- Automatic periodic sync from client localStorage to server
- Single integrated API: `create_evaluation_app_with_storage()`
- Configurable sync intervals (default 30 seconds)
- Data integrity via checksums
- Session recovery after browser crashes
- Timestamped backups for audit trail
**API Design**:
```python
app = create_evaluation_app_with_storage(
    rubric=my_rubric,
    title="My Evaluation",
    storage_dir="./evaluations",  # Optional, enables storage
    sync_interval=30,  # seconds
    enable_sync=True  # Can disable for client-only mode
)
```
**Benefits**:
- Zero infrastructure setup (no database)
- Dual storage (client + server) for resilience
- Works offline with automatic sync when online
- Direct JSON access for analysis
- Backwards compatible (storage is optional)

#### S0-FE-2: Evaluation Items Management
**Status**: ✅ COMPLETED (2026-01-17)
**Plan**: `/home/boris/.claude/plans/recursive-plotting-metcalfe.md`
**Files**: `teval/human/app.py`, `teval/human/items.py`, `tests/test_items.py`
**Requirements**:
- Display prompt + response pairs for evaluation
- Item queue management (sequential, random, or assigned)
- Track which items each evaluator has completed
- Associate evaluations with specific item IDs
- Support multiple item sources (list, file, API, generator)
- Progress tracking (e.g., "Item 23 of 100")
- Skip/flag difficult items functionality
**UI Components**:
- Item display area (prompt, response, context)
- Navigation controls (previous, next, skip)
- Progress indicator
- Item metadata display (model, timestamp, etc.)
**API Design**:
```python
app = create_evaluation_app_with_storage(
    rubric=my_rubric,
    evaluation_items=[  # Items to evaluate
        {
            "id": "item_001",
            "prompt": "User question here",
            "response": "LLM response here",
            "metadata": {...}  # Optional context
        }
    ],
    assignment_mode="sequential",  # or "random", "round_robin"
    items_per_evaluator=None,  # Limit items per person
    allow_skip=True  # Can skip difficult items
)
```
**Data Structure**:
```json
{
    "item_id": "item_001",
    "evaluator_id": "alice@example.com",
    "session_id": "session_123",
    "timestamp": "2024-01-15T10:30:00Z",
    "evaluation": {
        "metric_1": true,
        "metric_2": false
    },
    "item_content": {
        "prompt": "...",
        "response": "..."
    }
}
```

#### S0-FE-3: Free-form Comments Support
**Status**: ✅ COMPLETED (2026-01-17)
**Plan**: `/home/boris/.claude/plans/quizzical-weaving-parasol.md`
**Files**: `teval/metrics.py`, `teval/human/forms.py`, `tests/test_comments.py`
**Requirements**:
- Add optional comment field for each metric evaluation
- Support global comment for entire evaluation
- Enable "OK/Not OK + Comment" simple rubric for initial discovery
- Store comments in evaluation results
- Export comments for rubric refinement analysis
**Use Cases**:
1. **Discovery Mode**: Start with binary OK/Not OK + mandatory comments to understand what matters
2. **Refinement Mode**: Capture reasoning for metric failures
3. **Edge Case Documentation**: Note unusual situations
**API Enhancement**:
```python
# Simple discovery rubric
discovery_rubric = EvaluationRubric(
    rubric_id="discovery_v1",
    metrics=[
        MetricDefinition(
            id="overall_quality",
            rubric="Is this response acceptable for production use?",
            requires_comment_on_fail=True  # Force comment when marking False
        )
    ],
    passing_score_threshold=1
)

# Evaluation result with comments
{
    "overall_quality": false,
    "overall_quality_comment": "Response contains PII and gives medical advice",
    "global_comment": "This response has multiple issues that need addressing"
}
```

#### S0-ALIGN-1: Rubric Discovery from SME Feedback
**Status**: TODO
**Files**: `teval/rubric_discovery.py`, `tests/test_discovery.py`
**Requirements**:
- Analyze free-form comments to extract common themes
- Identify patterns in OK/Not OK decisions
- Generate suggested metrics from comment patterns
- Cluster similar feedback across evaluators
- Export rubric recommendations
**Workflow**:
1. Start with simple OK/Not OK + comments
2. Collect 50-100 evaluations from SMEs
3. Extract patterns from comments
4. Generate structured rubric proposal
5. Validate with SMEs
**Example Analysis**:
```python
# Input: Comments from Not OK evaluations
comments = [
    "Contains customer email address",
    "Shows user's full name and account",
    "Exposes SSN in response",
    "Gives specific medical advice",
    "Recommends medication dosage"
]

# Output: Suggested metrics
suggested_metrics = [
    {
        "id": "no_pii",
        "pattern": "PII exposure (email, name, SSN)",
        "frequency": 45,
        "suggested_rubric": "Response must not expose PII"
    },
    {
        "id": "no_medical",
        "pattern": "Medical advice",
        "frequency": 23,
        "suggested_rubric": "Response must not give medical advice"
    }
]
```

#### S0-ALIGN-2: Human-LLM Alignment Analysis
**Status**: TODO
**Files**: `teval/alignment.py`, `tests/test_alignment.py`
**Requirements**:
- Calculate inter-rater reliability (Cohen's Kappa, Fleiss' Kappa)
- Measure human-LLM alignment rates per metric
- Generate disagreement analysis reports
- Identify systematic bias patterns
- Confidence scoring based on alignment levels
**Metrics**:
- Human-Human Agreement: κ > 0.7 (substantial agreement)
- Human-LLM Alignment: > 80% agreement rate
- Per-metric confidence scores
**API**:
```python
from teval.alignment import AlignmentAnalyzer

analyzer = AlignmentAnalyzer()
results = analyzer.analyze(
    human_evaluations=[...],
    llm_evaluations=[...]
)

print(f"Human agreement: {results.human_kappa:.2f}")
print(f"Human-LLM alignment: {results.alignment_rate:.1%}")
print(f"Problem metrics: {results.low_alignment_metrics}")
```

## Sprint 1: Evaluation Scale & Pipeline

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

### Multi-stage Evaluation Pipeline

#### S1-BE-1: Pipeline Architecture
**Status**: TODO
**Files**: `teval/pipeline.py`
**Requirements**:
- Composable evaluation stages
- Stage dependencies and conditions
- Data passing between stages
- Stop-on-fail support

#### S1-BE-2: Pipeline Configuration
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
- Inter-rater Reliability Metrics (Cohen's Kappa, Fleiss' Kappa, Krippendorff's Alpha)
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