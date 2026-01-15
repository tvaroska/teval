"""
FastHTML application for human evaluation collection.

This module provides a web-based interface for collecting human evaluations
using FastHTML and HTMX for interactive forms without complex JavaScript.
"""

from typing import Optional, Callable, Dict, Any

try:
    from fasthtml.common import (
        FastHTML, Html, Head, Body, Title, Meta, Div, H1, H3, P,
        Button, Link, Style, serve, Request, Form
    )
except ImportError:
    raise ImportError(
        "FastHTML is required for the human evaluation interface. "
        "Install with: pip install teval[human] or uv add 'python-fasthtml>=0.4.0' --optional human"
    )

from teval.metrics import EvaluationRubric
from teval.human.forms import EvaluationForm
from teval.human.styles import get_styles


def create_evaluation_app(
    rubric: EvaluationRubric,
    title: Optional[str] = None,
    storage_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    port: int = 5000
) -> FastHTML:
    """
    Create a FastHTML app for human evaluation collection.

    Creates a standalone web application for collecting human evaluations
    based on the provided rubric. The app features HTMX-powered interactivity,
    auto-save capabilities, and real-time validation feedback.

    Parameters
    ----------
    rubric : EvaluationRubric
        The evaluation rubric defining metrics and passing criteria.
    title : str, optional
        Custom title for the application. Defaults to "Evaluation: {rubric_id}".
    storage_callback : Callable[[Dict[str, Any]], None], optional
        Function to call with evaluation results for custom storage.
        Receives a dictionary with results, reasoning, and metadata.
    port : int, default=5000
        Port number for the web server when using serve().

    Returns
    -------
    FastHTML
        Configured FastHTML application ready to serve.

    Raises
    ------
    ImportError
        If FastHTML is not installed.
    ValueError
        If rubric has no metrics defined.

    Examples
    --------
    Create and serve a basic evaluation app:

    >>> from teval import EvaluationRubric, MetricDefinition
    >>> from teval.human import create_evaluation_app
    >>>
    >>> rubric = EvaluationRubric(
    ...     rubric_id="code_review",
    ...     metrics=[
    ...         MetricDefinition(id="M1", rubric="Compiles without errors", mandatory=True),
    ...         MetricDefinition(id="C1", rubric="Follows style guide"),
    ...         MetricDefinition(id="C2", rubric="Well documented")
    ...     ],
    ...     passing_score_threshold=1
    ... )
    >>>
    >>> app = create_evaluation_app(rubric, title="Code Review")
    >>> serve(app, port=5000)  # Starts web server at http://localhost:5000

    With custom storage callback:

    >>> def save_results(data):
    ...     # Save to database, file, etc.
    ...     print(f"Evaluation complete: {data['passes']}")
    >>>
    >>> app = create_evaluation_app(rubric, storage_callback=save_results)

    Notes
    -----
    The application provides the following features:
    - Interactive form with real-time progress tracking
    - Auto-save to browser local storage every 30 seconds
    - JSON export functionality
    - Keyboard shortcuts (Enter to submit, Ctrl+E to export)
    - Dynamic filtering of metrics
    - Mobile-responsive design

    The storage_callback receives a dictionary with:
    - rubric_id: The evaluation rubric identifier
    - results: Dict[str, bool] of metric pass/fail values
    - reasoning: Dict[str, str] of optional reasoning text
    - mandatory_pass: Whether all mandatory metrics passed
    - score: Number of cumulative metrics that passed
    - total: Total number of cumulative metrics
    - passes: Overall pass/fail based on rubric criteria
    - timestamp: ISO format timestamp of submission

    See Also
    --------
    EvaluationForm : Form component for rendering evaluations
    EvaluationRubric : Core rubric model from teval
    """
    if not rubric.metrics:
        raise ValueError("Rubric must have at least one metric defined")

    app_title = title or f"Evaluation: {rubric.rubric_id}"

    app = FastHTML(
        hdrs=(
            Style(get_styles()),
        )
    )

    form = EvaluationForm(rubric, title=app_title)

    @app.route("/")
    def index():
        """Render the main evaluation page."""
        return Html(
            Head(
                Title(app_title),
                Meta(charset="UTF-8"),
                Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            ),
            Body(
                Div(
                    H1(app_title, cls="teval-title"),
                    form.render(),
                    Div(id="result", cls="teval-result-container"),
                    cls="teval-container"
                )
            )
        )

    @app.route("/submit", methods=["POST"])
    async def submit(request: Request):
        """Handle form submission and return results."""
        data = await request.form()

        try:
            results = form.process_submission(dict(data))

            # Validate against rubric
            passes = rubric.validate_result(results["results"])

            # Store if callback provided
            if storage_callback:
                storage_callback(results)

            # Return HTMX response for dynamic update
            return Div(
                H3("✅ Evaluation Complete" if passes else "❌ Evaluation Failed",
                   cls=f"teval-result-{'success' if passes else 'fail'}"),
                P(f"Score: {results['score']}/{results['total']} cumulative metrics"),
                P(f"Mandatory: {'All passed' if results['mandatory_pass'] else 'Failed'}"),
                Button("New Evaluation",
                       hx_get="/",
                       hx_target="body",
                       cls="teval-btn-primary"),
                Button("Export Results",
                       onclick=f"exportLastResults({results})",
                       cls="teval-btn-secondary"),
                cls="teval-result"
            )
        except Exception as e:
            return Div(
                H3("❌ Error Processing Evaluation"),
                P(f"Error: {str(e)}"),
                Button("Try Again",
                       hx_get="/",
                       hx_target="body",
                       cls="teval-btn-primary"),
                cls="teval-result teval-error"
            )

    return app