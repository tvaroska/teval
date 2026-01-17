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
from teval.human.sync_storage import FileBasedStorage, create_sync_endpoints


def create_evaluation_app(
    rubric: EvaluationRubric,
    title: Optional[str] = None,
    storage_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    port: int = 5000,
    enable_sync: bool = False,
    sync_interval: int = 30
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

    form = EvaluationForm(
        rubric,
        title=app_title,
        enable_sync=enable_sync,
        sync_interval=sync_interval
    )

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


def create_evaluation_app_with_storage(
    rubric: EvaluationRubric,
    title: Optional[str] = None,
    storage_dir: Optional[str] = None,
    sync_interval: int = 30,
    enable_sync: bool = True,
    storage_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    port: int = 5000
) -> FastHTML:
    """
    Create a FastHTML app with file-based storage and auto-sync.

    Creates a web application for collecting human evaluations with optional
    server-side file storage and automatic synchronization from browser localStorage.
    When storage_dir is provided, enables dual storage (client + server) for resilience.

    Parameters
    ----------
    rubric : EvaluationRubric
        The evaluation rubric defining metrics and passing criteria.
    title : str, optional
        Custom title for the application. Defaults to "Evaluation: {rubric_id}".
    storage_dir : str, optional
        Directory for file-based storage. When provided, enables server-side storage
        with automatic sync. If None, only uses browser localStorage.
    sync_interval : int, default=30
        Seconds between automatic syncs to server (when storage_dir is provided).
    enable_sync : bool, default=True
        Whether to enable automatic sync. Can be set to False for client-only mode
        even when storage_dir is provided.
    storage_callback : Callable[[Dict[str, Any]], None], optional
        Additional callback for custom storage/processing of evaluation results.
    port : int, default=5000
        Port number for the web server when using serve().

    Returns
    -------
    FastHTML
        Configured FastHTML application with storage capabilities.

    Raises
    ------
    ImportError
        If FastHTML is not installed.
    ValueError
        If rubric has no metrics defined.

    Examples
    --------
    Create app with file storage and auto-sync:

    >>> from teval import EvaluationRubric, MetricDefinition
    >>> from teval.human import create_evaluation_app_with_storage
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
    >>> # With file storage enabled
    >>> app = create_evaluation_app_with_storage(
    ...     rubric,
    ...     title="Code Review",
    ...     storage_dir="./evaluations",  # Enables file storage
    ...     sync_interval=30               # Auto-sync every 30 seconds
    ... )
    >>> # serve(app)  # Starts at http://localhost:5000

    Create app without file storage (client-only):

    >>> app = create_evaluation_app_with_storage(
    ...     rubric,
    ...     title="Code Review"
    ...     # No storage_dir = client-only mode with localStorage
    ... )

    Notes
    -----
    Multi-User Support:
    - Each browser/device gets a unique session ID stored in localStorage
    - Sessions are isolated - evaluators cannot see each other's work
    - Optional evaluator name/email for tracking (no authentication)
    - Admin can generate aggregate reports across all sessions

    Storage Features:
    - Dual storage: browser localStorage + server files (when enabled)
    - Automatic sync at configured intervals
    - Session recovery after browser crashes
    - Timestamped backups for audit trail
    - Data integrity via checksums
    - Direct JSON file access for analysis

    File Structure (when storage_dir is provided):
    ```
    storage_dir/
    ├── sessions/
    │   ├── session_abc123/         # Each user's session
    │   │   ├── latest.json         # Current evaluation state
    │   │   └── eval_TIMESTAMP.json # Timestamped backups
    │   └── ...
    ├── archive/                     # Old sessions
    └── reports/                     # Aggregate reports
    ```

    The app remains fully functional without storage_dir, using only
    browser localStorage. This maintains backward compatibility while
    adding optional server-side persistence.

    See Also
    --------
    create_evaluation_app : Basic app without file storage
    FileBasedStorage : Storage backend implementation
    EvaluationRubric : Core rubric model from teval
    """
    # Determine if sync should be enabled
    sync_enabled = storage_dir is not None and enable_sync

    # Create base app with sync settings
    app = create_evaluation_app(
        rubric=rubric,
        title=title,
        storage_callback=storage_callback,
        port=port,
        enable_sync=sync_enabled,
        sync_interval=sync_interval
    )

    # If storage_dir provided, add file storage and sync endpoints
    if storage_dir:
        storage = FileBasedStorage(storage_dir)
        app = create_sync_endpoints(app, storage, rubric)

    return app