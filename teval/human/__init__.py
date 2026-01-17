"""
Human evaluation interface for teval.

This module provides web-based forms for collecting human evaluations
using FastHTML and HTMX for interactive, modern UI without complex JavaScript.
It also includes bulk import utilities for processing evaluation data from
CSV, JSON, and Pandas DataFrame formats.

The human evaluation features are optional and require FastHTML:
    pip install teval[human]
    or
    uv add "python-fasthtml>=0.4.0" --optional human

Examples
--------
Create a standalone evaluation app:

>>> from teval import EvaluationRubric, MetricDefinition
>>> from teval.human import create_evaluation_app
>>>
>>> rubric = EvaluationRubric(
...     rubric_id="code_review",
...     metrics=[
...         MetricDefinition(id="M1", rubric="No errors", mandatory=True),
...         MetricDefinition(id="C1", rubric="Well documented")
...     ],
...     passing_score_threshold=1
... )
>>>
>>> app = create_evaluation_app(rubric, title="Code Review")
>>> # serve(app)  # Starts at http://localhost:5000

Use form components directly:

>>> from teval.human import EvaluationForm
>>> form = EvaluationForm(rubric)
>>> html_component = form.render()

Import evaluation data from files:

>>> from teval.human import import_evaluations
>>> results, report = import_evaluations("evaluations.csv", rubric)
>>> print(f"Imported {report.success_count} evaluations")

Notes
-----
The human evaluation interface provides:
- Interactive web forms with real-time validation
- Auto-save to browser local storage
- Progress tracking and filtering
- JSON export functionality
- Bulk import from CSV, JSON, and DataFrame formats
- Mobile-responsive design
- Keyboard shortcuts for efficiency
- HTMX-powered updates without page refreshes

All features work without JavaScript enabled, though with reduced
interactivity. The interface is designed to be accessible and
follows WCAG guidelines for contrast and keyboard navigation.
"""

try:
    from teval.human.app import create_evaluation_app
    from teval.human.forms import EvaluationForm
    from teval.human.importers import (
        import_evaluations,
        ImportReport,
        CSVImporter,
        JSONImporter,
        DataFrameImporter
    )
    from teval.human.sync_storage import (
        FileBasedStorage,
        create_sync_endpoints
    )
    from teval.human.items import (
        ItemsManager,
        ItemSource,
        ListItemSource,
        FileItemSource,
        normalize_items
    )

    __all__ = [
        "create_evaluation_app",
        "EvaluationForm",
        "import_evaluations",
        "ImportReport",
        "CSVImporter",
        "JSONImporter",
        "DataFrameImporter",
        "FileBasedStorage",
        "create_sync_endpoints",
        # Items management
        "ItemsManager",
        "ItemSource",
        "ListItemSource",
        "FileItemSource",
        "normalize_items",
    ]

except ImportError as e:
    # Provide helpful error message if FastHTML not installed
    import sys
    error_msg = (
        "FastHTML is required for human evaluation features.\n"
        "Install with: pip install teval[human]\n"
        "Or with uv: uv add 'python-fasthtml>=0.4.0' --optional human"
    )
    print(error_msg, file=sys.stderr)
    raise ImportError(error_msg) from e


# Version info
__version__ = "0.1.0"