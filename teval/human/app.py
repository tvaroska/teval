"""
FastHTML application for human evaluation collection.

This module provides a web-based interface for collecting human evaluations
using FastHTML and HTMX for interactive forms without complex JavaScript.
"""

from typing import Optional, Callable, Dict, Any
from datetime import datetime

try:
    from fasthtml.common import (
        FastHTML, Html, Head, Body, Title, Meta, Div, H1, H3, P,
        Button, Link, Style, serve, Request, Form, Script
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
from teval.human.items import ItemsManager, normalize_items


def create_evaluation_app(
    rubric: EvaluationRubric,
    title: Optional[str] = None,
    storage_dir: Optional[str] = None,
    sync_interval: int = 30,
    enable_sync: bool = True,
    storage_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    port: int = 5000,
    # New parameters for items management
    evaluation_items: Optional[Any] = None,  # List[Dict], ItemSource, or filepath
    assignment_mode: str = "sequential",
    items_per_evaluator: Optional[int] = None,
    allow_skip: bool = True,
    max_skips: int = 3
) -> FastHTML:
    """
    Create a FastHTML app for human evaluation collection with optional file storage.

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
    evaluation_items : Optional[Any], default=None
        Items to evaluate. Can be:
        - List[Dict]: List of items with 'id', 'prompt', 'response' fields
        - ItemSource: Instance of ItemSource subclass
        - str/Path: Path to JSON or CSV file containing items
        If None, app runs in single-evaluation mode (backward compatible).
    assignment_mode : str, default="sequential"
        How to assign items to evaluators: "sequential", "random", "round_robin", "assigned".
    items_per_evaluator : Optional[int], default=None
        Maximum items each evaluator should complete. None means no limit.
    allow_skip : bool, default=True
        Whether evaluators can skip difficult items.
    max_skips : int, default=3
        Maximum number of items an evaluator can skip.

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
    Create app with file storage and auto-sync:

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
    >>> # With file storage enabled
    >>> app = create_evaluation_app(
    ...     rubric,
    ...     title="Code Review",
    ...     storage_dir="./evaluations",  # Enables file storage
    ...     sync_interval=30               # Auto-sync every 30 seconds
    ... )
    >>> # serve(app)  # Starts at http://localhost:5000

    Create app without file storage (client-only):

    >>> app = create_evaluation_app(
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
    - Dual storage: browser localStorage + server files (when storage_dir provided)
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

    # Determine if sync should be enabled
    sync_enabled = storage_dir is not None and enable_sync

    # Initialize items manager if items provided
    items_manager = None
    if evaluation_items is not None:
        items_list = normalize_items(evaluation_items)
        items_manager = ItemsManager(
            items=items_list,
            assignment_mode=assignment_mode,
            items_per_evaluator=items_per_evaluator,
            allow_skip=allow_skip,
            max_skips=max_skips
        )

    # Create form with items support if needed
    form = EvaluationForm(
        rubric,
        title=app_title,
        enable_sync=sync_enabled,
        sync_interval=sync_interval,
        enable_items=(items_manager is not None),
        allow_skip=allow_skip
    )

    @app.route("/")
    async def index(request: Request):
        """Render the main evaluation page."""
        # If items mode, get the current item for the evaluator
        if items_manager:
            # Get or create session ID from cookie/localStorage
            session_id = request.cookies.get("session_id", f"session_{datetime.now().timestamp()}")

            # Get current or next item
            current_item = items_manager.get_next_item(session_id)

            if current_item:
                # Get progress for this evaluator
                progress = items_manager.get_progress(session_id)

                # Render form with item
                form_html = form.render_with_item(current_item, progress)
            else:
                # No more items
                return Html(
                    Head(
                        Title(app_title),
                        Meta(charset="UTF-8"),
                        Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
                    ),
                    Body(
                        Div(
                            H1(app_title, cls="teval-title"),
                            Div(
                                H3("✅ All items completed!", cls="teval-complete-message"),
                                P("Thank you for completing all evaluation items."),
                                Button("View Results",
                                       onclick="window.location.href='/results'",
                                       cls="teval-btn-primary"),
                                cls="teval-completion"
                            ),
                            cls="teval-container"
                        )
                    )
                )
        else:
            # Regular single evaluation mode
            form_html = form.render()

        return Html(
            Head(
                Title(app_title),
                Meta(charset="UTF-8"),
                Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            ),
            Body(
                Div(
                    H1(app_title, cls="teval-title"),
                    form_html,
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

            # Get session ID for items mode
            session_id = request.cookies.get("session_id", f"session_{datetime.now().timestamp()}")

            # If items mode, handle item-specific logic
            if items_manager:
                item_id = data.get("item_id")

                if item_id:
                    # Mark item as completed
                    items_manager.mark_completed(session_id, item_id)

                    # Save with item association if storage enabled
                    if storage_dir:
                        storage = FileBasedStorage(storage_dir)
                        storage.save_item_evaluation(
                            session_id=session_id,
                            item_id=item_id,
                            evaluation_data=results,
                            item_content=dict(data) if "prompt" in data else None,
                            metadata={"evaluator": data.get("evaluator_name", "anonymous")}
                        )

            # Validate against rubric
            passes = rubric.validate_result(results["results"])

            # Store if callback provided
            if storage_callback:
                storage_callback(results)

            # For items mode, redirect to next item
            if items_manager:
                return Div(
                    H3("✅ Item Evaluated" if passes else "⚠️ Item Evaluated",
                       cls=f"teval-result-{'success' if passes else 'warning'}"),
                    P(f"Score: {results['score']}/{results['total']} cumulative metrics"),
                    P("Loading next item..."),
                    Script("setTimeout(() => window.location.href = '/', 1500);"),
                    cls="teval-result"
                )
            else:
                # Regular single evaluation response
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

    # Add item-specific endpoints if in items mode
    if items_manager:
        @app.route("/item/skip", methods=["POST"])
        async def skip_item(request: Request):
            """Skip current item and move to next."""
            data = await request.json()
            session_id = data.get("session_id")
            item_id = data.get("item_id")

            if session_id and item_id:
                success = items_manager.skip_item(session_id, item_id)
                if success:
                    return {"status": "success", "message": "Item skipped"}
                else:
                    return {"status": "error", "message": "Skip limit reached"}

            return {"status": "error", "message": "Missing session or item ID"}

        @app.route("/api/progress/<session_id>")
        async def get_progress(session_id: str):
            """Get progress for an evaluator."""
            progress = items_manager.get_progress(session_id)
            return progress

    # If storage_dir provided, add file storage and sync endpoints
    if storage_dir:
        storage = FileBasedStorage(storage_dir)
        app = create_sync_endpoints(app, storage, rubric)

    return app

