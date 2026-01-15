"""
Human evaluation interface for teval.

This module provides web-based forms for collecting human evaluations
using FastHTML and HTMX for interactive, modern UI without complex JavaScript.

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

Notes
-----
The human evaluation interface provides:
- Interactive web forms with real-time validation
- Auto-save to browser local storage
- Progress tracking and filtering
- JSON export functionality
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

    __all__ = [
        "create_evaluation_app",
        "EvaluationForm",
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