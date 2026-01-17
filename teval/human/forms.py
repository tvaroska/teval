"""
Form components for human evaluation collection using FastHTML.

This module provides the EvaluationForm class that generates interactive
HTML forms for collecting human evaluations based on teval rubrics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

try:
    from fasthtml.common import (
        Form, Div, H2, P, Card, Span, Label, Input,
        Textarea, Button, Progress, Script
    )
except ImportError:
    raise ImportError(
        "FastHTML is required for the human evaluation interface. "
        "Install with: pip install teval[human] or uv add 'python-fasthtml>=0.4.0' --optional human"
    )

from teval.metrics import EvaluationRubric, MetricDefinition


class EvaluationForm:
    """
    Generate FastHTML forms for human evaluation collection.

    Creates an interactive form component using FastHTML and HTMX
    for collecting human evaluations based on a teval rubric.

    Parameters
    ----------
    rubric : EvaluationRubric
        The evaluation rubric defining metrics and criteria.
    title : str, optional
        Form title. Defaults to "Evaluation: {rubric_id}".
    include_reasoning : bool, default=True
        Whether to include optional reasoning textareas for each metric.

    Attributes
    ----------
    rubric : EvaluationRubric
        The evaluation rubric.
    title : str
        The form title.
    include_reasoning : bool
        Whether reasoning fields are included.

    Methods
    -------
    render()
        Render the evaluation form as FastHTML components.
    process_submission(form_data)
        Process form submission data and calculate results.

    Examples
    --------
    Create a basic evaluation form:

    >>> from teval import EvaluationRubric, MetricDefinition
    >>> from teval.human.forms import EvaluationForm
    >>>
    >>> rubric = EvaluationRubric(
    ...     rubric_id="test",
    ...     metrics=[
    ...         MetricDefinition(id="M1", rubric="Passes test", mandatory=True),
    ...         MetricDefinition(id="C1", rubric="Quality check")
    ...     ],
    ...     passing_score_threshold=1
    ... )
    >>>
    >>> form = EvaluationForm(rubric, title="Test Evaluation")
    >>> html = form.render()  # Returns FastHTML Form component

    Process submission data:

    >>> data = {"M1": "true", "C1": "false", "M1_reasoning": "Test passed"}
    >>> results = form.process_submission(data)
    >>> print(results["passes"])  # False (C1 failed, didn't meet threshold)

    Notes
    -----
    The form includes:
    - Separate sections for mandatory and cumulative metrics
    - Progress tracking showing X/Y metrics completed
    - Auto-save functionality to browser local storage
    - Keyboard shortcuts (Enter to submit when complete)
    - Dynamic filtering and search capabilities
    - JSON export functionality

    The rendered form uses HTMX for dynamic updates without page refreshes
    and includes JavaScript for enhanced interactivity while maintaining
    functionality without JavaScript enabled.

    See Also
    --------
    create_evaluation_app : Create a complete FastHTML application
    EvaluationRubric : Core rubric model from teval
    """

    def __init__(
        self,
        rubric: EvaluationRubric,
        title: Optional[str] = None,
        include_reasoning: bool = True,
        enable_sync: bool = False,
        sync_interval: int = 30,
        enable_items: bool = False,
        allow_skip: bool = True
    ):
        """Initialize the evaluation form."""
        self.rubric = rubric
        self.title = title or f"Evaluation: {rubric.rubric_id}"
        self.include_reasoning = include_reasoning
        self.enable_sync = enable_sync
        self.sync_interval = sync_interval
        self.enable_items = enable_items
        self.allow_skip = allow_skip

    def render(self) -> Form:
        """
        Render the evaluation form as FastHTML components.

        Returns
        -------
        Form
            FastHTML Form component with all metrics and controls.

        Notes
        -----
        The form is structured as follows:
        1. Filter bar for searching and filtering metrics
        2. Mandatory metrics section (if any exist)
        3. Cumulative metrics section (if any exist)
        4. Progress indicator showing completion status
        5. Action buttons (Submit, Export, Auto-save toggle)

        The form posts to "/submit" endpoint and updates "#result" div
        using HTMX for seamless interaction.
        """
        components = []

        # Add evaluator name field and sync status if sync is enabled
        if self.enable_sync:
            evaluator_section = Div(
                Div(
                    Label("Evaluator Name (Optional):", cls="teval-label"),
                    Input(
                        type="text",
                        id="evaluator-name",
                        name="evaluator_name",
                        placeholder="Your name or email (for tracking purposes)",
                        cls="teval-input",
                        onchange="saveEvaluatorName()"
                    ),
                    cls="teval-evaluator-section"
                ),
                Div(
                    Span("Sync Status: ", cls="teval-sync-label"),
                    Span("Not synced", id="sync-status", cls="teval-sync-status"),
                    Span("", id="last-sync-time", cls="teval-sync-time"),
                    cls="teval-sync-info"
                ),
                cls="teval-header-info"
            )
            components.append(evaluator_section)

        # Add filter bar
        filter_bar = self._create_filter_bar()
        if filter_bar:
            components.append(filter_bar)

        # Add mandatory metrics section
        if self.rubric.mandatory_metrics:
            mandatory_section = self._render_metric_section(
                self.rubric.mandatory_metrics,
                "Mandatory Criteria",
                "All must pass for evaluation to succeed"
            )
            components.append(mandatory_section)

        # Add cumulative metrics section
        if self.rubric.cumulative_metrics:
            cumulative_section = self._render_metric_section(
                self.rubric.cumulative_metrics,
                "Quality Criteria",
                f"Need {self.rubric.passing_score_threshold} of {len(self.rubric.cumulative_metrics)} to pass"
            )
            components.append(cumulative_section)

        # Add global comment field (only when reasoning is enabled)
        if self.include_reasoning:
            global_comment_section = Div(
                H2("Overall Comments", cls="teval-section-title"),
                P("Additional feedback or observations about this evaluation (optional)", cls="teval-section-desc"),
                Textarea(
                    placeholder="Enter any overall comments or feedback...",
                    name="global_comment",
                    rows="4",
                    cls="teval-global-comment"
                ),
                cls="teval-global-comment-section"
            )
            components.append(global_comment_section)

        # Add progress indicator
        progress = Div(
            Span(id="progress-text", cls="teval-progress-text"),
            Progress(
                id="progress-bar",
                value="0",
                max=str(len(self.rubric.metrics)),
                cls="teval-progress"
            ),
            cls="teval-progress-container"
        )
        components.append(progress)

        # Add action buttons
        actions = Div(
            Button(
                "Submit Evaluation",
                type="submit",
                cls="teval-btn-primary",
                id="submit-btn"
            ),
            Button(
                "Export JSON",
                onclick="exportResults()",
                type="button",
                cls="teval-btn-secondary"
            ),
            Button(
                "Auto-save: ON",
                id="autosave-toggle",
                onclick="toggleAutosave()",
                type="button",
                cls="teval-btn-secondary teval-autosave-on"
            ),
            cls="teval-actions"
        )
        components.append(actions)

        # Add JavaScript for enhanced functionality
        js_code = self._get_javascript()
        components.append(Script(js_code))

        return Form(
            *components,
            hx_post="/submit",
            hx_target="#result",
            cls="teval-form",
            id="evaluation-form"
        )

    def _create_filter_bar(self) -> Optional[Div]:
        """Create the filter bar for searching metrics."""
        if len(self.rubric.metrics) < 5:
            # Don't show filter for small forms
            return None

        return Div(
            Input(
                type="text",
                id="metric-search",
                placeholder="Search metrics...",
                cls="teval-search",
                onkeyup="filterMetrics()"
            ),
            Label(
                Input(
                    type="checkbox",
                    id="filter-mandatory",
                    onchange="filterMetrics()"
                ),
                " Show only mandatory",
                cls="teval-filter-option"
            ),
            Label(
                Input(
                    type="checkbox",
                    id="filter-incomplete",
                    onchange="filterMetrics()"
                ),
                " Show only incomplete",
                cls="teval-filter-option"
            ),
            cls="teval-filter-bar"
        )

    def _render_metric_section(
        self,
        metrics: List[MetricDefinition],
        title: str,
        description: str
    ) -> Div:
        """
        Render a section of metrics.

        Parameters
        ----------
        metrics : List[MetricDefinition]
            Metrics to render in this section.
        title : str
            Section title.
        description : str
            Section description.

        Returns
        -------
        Div
            Section containing all metrics.
        """
        metric_cards = [
            self._render_metric(metric) for metric in metrics
        ]

        return Div(
            H2(title, cls="teval-section-title"),
            P(description, cls="teval-section-desc"),
            *metric_cards,
            cls="teval-section"
        )

    def _render_metric(self, metric: MetricDefinition) -> Card:
        """
        Render a single metric input card.

        Parameters
        ----------
        metric : MetricDefinition
            The metric to render.

        Returns
        -------
        Card
            Card component containing the metric input.
        """
        metric_id = metric.id

        components = [
            Div(
                Span(metric_id, cls="teval-metric-id"),
                Span("MANDATORY", cls="teval-badge-mandatory")
                    if metric.mandatory else None,
                cls="teval-metric-header"
            ),
            P(metric.rubric, cls="teval-metric-rubric"),
            Div(
                Label(
                    Input(
                        type="radio",
                        name=metric_id,
                        value="true",
                        required=True,
                        onchange="updateProgress()"
                    ),
                    Span(" ✅ Pass", cls="teval-radio-label"),
                    cls="teval-radio"
                ),
                Label(
                    Input(
                        type="radio",
                        name=metric_id,
                        value="false",
                        required=True,
                        onchange="updateProgress()"
                    ),
                    Span(" ❌ Fail", cls="teval-radio-label"),
                    cls="teval-radio"
                ),
                cls="teval-metric-inputs"
            )
        ]

        if self.include_reasoning:
            # Check if comment is required on failure
            required_indicator = ""
            if metric.requires_comment_on_fail:
                required_indicator = Span(
                    " (required if fails)",
                    cls="teval-comment-required-indicator"
                )

            components.append(
                Div(
                    Label(
                        "Reasoning",
                        required_indicator,
                        cls="teval-reasoning-label"
                    ) if metric.requires_comment_on_fail else None,
                    Textarea(
                        placeholder="Reasoning (required if fails)..." if metric.requires_comment_on_fail else "Reasoning (optional)...",
                        name=f"{metric_id}_reasoning",
                        rows="3",
                        cls="teval-reasoning teval-reasoning-required" if metric.requires_comment_on_fail else "teval-reasoning",
                        data_required_on_fail="true" if metric.requires_comment_on_fail else "false"
                    ),
                    cls="teval-reasoning-container"
                )
            )

        return Card(
            *components,
            cls="teval-metric-card",
            data_metric_id=metric_id
        )

    def process_submission(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process form submission data and calculate results.

        Parameters
        ----------
        form_data : Dict[str, Any]
            Raw form data from the submission.

        Returns
        -------
        Dict[str, Any]
            Processed results including:
            - rubric_id: The rubric identifier
            - results: Dict of metric pass/fail values
            - reasoning: Dict of optional reasoning text
            - global_comment: Overall evaluation comment
            - mandatory_pass: Whether all mandatory metrics passed
            - score: Number of passed cumulative metrics
            - total: Total number of cumulative metrics
            - passes: Overall pass/fail status
            - timestamp: ISO format timestamp

        Raises
        ------
        ValueError
            If required comments are missing for failed metrics.

        Examples
        --------
        >>> form_data = {
        ...     "M1": "true",
        ...     "C1": "false",
        ...     "M1_reasoning": "Looks good",
        ...     "global_comment": "Overall good quality"
        ... }
        >>> results = form.process_submission(form_data)
        >>> print(results["results"])  # {"M1": True, "C1": False}
        """
        results = {}
        reasoning = {}

        # Check for required comments on failed metrics
        missing_required_comments = []

        for metric in self.rubric.metrics:
            mid = metric.id
            results[mid] = form_data.get(mid) == "true"

            if self.include_reasoning:
                reason_key = f"{mid}_reasoning"
                if reason_key in form_data and form_data[reason_key]:
                    reasoning[mid] = form_data[reason_key]

                # Validate required comments for failed metrics
                if metric.requires_comment_on_fail and not results[mid]:
                    comment = form_data.get(reason_key, "").strip()
                    if not comment:
                        missing_required_comments.append(mid)

        # Raise error if required comments are missing (strict validation)
        if missing_required_comments:
            raise ValueError(
                f"Required comments missing for failed metrics: {', '.join(missing_required_comments)}. "
                "These metrics failed and require explanatory comments."
            )

        # Extract global comment
        global_comment = form_data.get("global_comment", "").strip()
        if not global_comment:
            global_comment = None

        # Calculate scores
        mandatory_pass = all(
            results.get(m.id, False)
            for m in self.rubric.mandatory_metrics
        )

        cumulative_score = sum(
            results.get(m.id, False)
            for m in self.rubric.cumulative_metrics
        )

        passes = mandatory_pass and cumulative_score >= self.rubric.passing_score_threshold

        result_dict = {
            "rubric_id": self.rubric.rubric_id,
            "results": results,
            "reasoning": reasoning,
            "mandatory_pass": mandatory_pass,
            "score": cumulative_score,
            "total": len(self.rubric.cumulative_metrics),
            "passes": passes,
            "timestamp": datetime.now().isoformat()
        }

        # Include global comment if present
        if global_comment:
            result_dict["global_comment"] = global_comment

        return result_dict

    def _get_javascript(self) -> str:
        """Generate JavaScript code for form functionality."""
        # Inject rubric-specific constants
        mandatory_ids = [m.id for m in self.rubric.mandatory_metrics]
        cumulative_ids = [m.id for m in self.rubric.cumulative_metrics]

        js_template = f"""
        // Rubric constants
        const RUBRIC_ID = '{self.rubric.rubric_id}';
        const MANDATORY_METRICS = {json.dumps(mandatory_ids)};
        const CUMULATIVE_METRICS = {json.dumps(cumulative_ids)};
        const PASSING_THRESHOLD = {self.rubric.passing_score_threshold};
        const ENABLE_SYNC = {'true' if self.enable_sync else 'false'};
        const SYNC_INTERVAL = {self.sync_interval * 1000};  // Convert to milliseconds

        // Auto-save functionality
        let autosaveEnabled = true;
        let autosaveTimer = null;

        function toggleAutosave() {{
            autosaveEnabled = !autosaveEnabled;
            const btn = document.getElementById('autosave-toggle');
            btn.textContent = autosaveEnabled ? 'Auto-save: ON' : 'Auto-save: OFF';
            btn.classList.toggle('teval-autosave-on');
            btn.classList.toggle('teval-autosave-off');

            if (autosaveEnabled) {{
                startAutosave();
            }} else {{
                if (autosaveTimer) clearInterval(autosaveTimer);
            }}
        }}

        function startAutosave() {{
            if (autosaveTimer) clearInterval(autosaveTimer);
            autosaveTimer = setInterval(() => {{
                const formData = collectFormData();
                if (formData) {{
                    localStorage.setItem('teval_' + RUBRIC_ID + '_draft', JSON.stringify(formData));
                }}
            }}, 30000);
        }}

        function collectFormData() {{
            const form = document.getElementById('evaluation-form');
            if (!form) return null;

            const formData = new FormData(form);
            const results = {{}};
            const reasoning = {{}};

            for (const [key, value] of formData.entries()) {{
                if (key.endsWith('_reasoning')) {{
                    const metricId = key.replace('_reasoning', '');
                    reasoning[metricId] = value;
                }} else {{
                    results[key] = value === 'true';
                }}
            }}

            return {{
                rubric_id: RUBRIC_ID,
                results: results,
                reasoning: reasoning,
                timestamp: new Date().toISOString()
            }};
        }}

        function validateRequiredComments() {{
            // Check if any failed metrics require comments
            const cards = document.querySelectorAll('.teval-metric-card');
            let missingComments = [];

            cards.forEach(card => {{
                const metricId = card.dataset.metricId;
                const failRadio = card.querySelector('input[value="false"]:checked');
                const textarea = card.querySelector('textarea[data-required-on-fail="true"]');

                if (failRadio && textarea) {{
                    const comment = textarea.value.trim();
                    if (!comment) {{
                        missingComments.push(metricId);
                        textarea.classList.add('teval-error');
                    }} else {{
                        textarea.classList.remove('teval-error');
                    }}
                }}
            }});

            return missingComments;
        }}

        function updateProgress() {{
            const total = document.querySelectorAll('.teval-metric-card').length;
            const completed = document.querySelectorAll('.teval-metric-card input:checked').length;

            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');

            if (progressBar) progressBar.value = completed;
            if (progressText) {{
                progressText.textContent = 'Progress: ' + completed + '/' + total + ' metrics completed';
            }}

            // Validate required comments
            const missingComments = validateRequiredComments();

            // Enable submit button when all metrics are complete and required comments are filled
            const submitBtn = document.getElementById('submit-btn');
            if (submitBtn) {{
                submitBtn.disabled = completed < total || missingComments.length > 0;
            }}

            // Auto-save on change if enabled
            if (autosaveEnabled && completed > 0) {{
                const formData = collectFormData();
                if (formData) {{
                    localStorage.setItem('teval_' + RUBRIC_ID + '_draft', JSON.stringify(formData));
                }}
            }}
        }}

        function exportResults() {{
            const formData = collectFormData();
            if (!formData) return;

            const blob = new Blob([JSON.stringify(formData, null, 2)], {{
                type: 'application/json'
            }});

            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'evaluation_' + RUBRIC_ID + '_' + Date.now() + '.json';
            a.click();
            URL.revokeObjectURL(url);
        }}

        function exportLastResults(results) {{
            const blob = new Blob([JSON.stringify(results, null, 2)], {{
                type: 'application/json'
            }});

            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'evaluation_' + RUBRIC_ID + '_complete_' + Date.now() + '.json';
            a.click();
            URL.revokeObjectURL(url);
        }}

        function filterMetrics() {{
            const search = document.getElementById('metric-search')?.value.toLowerCase() || '';
            const onlyMandatory = document.getElementById('filter-mandatory')?.checked || false;
            const onlyIncomplete = document.getElementById('filter-incomplete')?.checked || false;

            document.querySelectorAll('.teval-metric-card').forEach(card => {{
                const text = card.textContent.toLowerCase();
                const isMandatory = card.querySelector('.teval-badge-mandatory') !== null;
                const isComplete = card.querySelector('input:checked') !== null;

                let show = true;

                if (search && !text.includes(search)) show = false;
                if (onlyMandatory && !isMandatory) show = false;
                if (onlyIncomplete && isComplete) show = false;

                card.style.display = show ? 'block' : 'none';
            }});
        }}

        // Session and sync management
        let sessionId = null;
        let syncTimer = null;
        let lastSyncTime = null;
        let syncRetryCount = 0;
        const MAX_RETRY = 3;

        function generateSessionId() {{
            // Try crypto API first, fallback to timestamp-based ID
            if (window.crypto && window.crypto.randomUUID) {{
                return crypto.randomUUID();
            }} else {{
                return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
            }}
        }}

        function getOrCreateSessionId() {{
            let storedId = localStorage.getItem('teval_session_id');
            if (!storedId) {{
                storedId = generateSessionId();
                localStorage.setItem('teval_session_id', storedId);
            }}
            return storedId;
        }}

        function saveEvaluatorName() {{
            const nameInput = document.getElementById('evaluator-name');
            if (nameInput) {{
                localStorage.setItem('teval_evaluator_name', nameInput.value);
            }}
        }}

        function loadEvaluatorName() {{
            const nameInput = document.getElementById('evaluator-name');
            const savedName = localStorage.getItem('teval_evaluator_name');
            if (nameInput && savedName) {{
                nameInput.value = savedName;
            }}
        }}

        async function syncToServer() {{
            if (!ENABLE_SYNC) return;

            const formData = collectFormData();
            if (!formData) return;

            const evaluatorName = document.getElementById('evaluator-name')?.value || 'anonymous';

            const syncData = {{
                session_id: sessionId,
                evaluation: formData,
                metadata: {{
                    evaluator: evaluatorName,
                    rubric_id: RUBRIC_ID,
                    client_timestamp: new Date().toISOString()
                }}
            }};

            try {{
                const response = await fetch('/api/sync', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify(syncData)
                }});

                if (response.ok) {{
                    const result = await response.json();
                    updateSyncStatus('success');
                    lastSyncTime = new Date();
                    syncRetryCount = 0;
                    return result;
                }} else {{
                    throw new Error('Sync failed: ' + response.status);
                }}
            }} catch (error) {{
                console.error('Sync error:', error);
                syncRetryCount++;

                if (syncRetryCount < MAX_RETRY) {{
                    // Retry with exponential backoff
                    setTimeout(() => syncToServer(), Math.pow(2, syncRetryCount) * 1000);
                    updateSyncStatus('retrying');
                }} else {{
                    updateSyncStatus('error');
                    syncRetryCount = 0;
                }}
            }}
        }}

        function updateSyncStatus(status) {{
            const statusEl = document.getElementById('sync-status');
            const timeEl = document.getElementById('last-sync-time');

            if (!statusEl) return;

            switch(status) {{
                case 'success':
                    statusEl.textContent = '✅ Synced';
                    statusEl.className = 'teval-sync-status teval-sync-success';
                    if (timeEl && lastSyncTime) {{
                        timeEl.textContent = ' (Last: ' + lastSyncTime.toLocaleTimeString() + ')';
                    }}
                    break;
                case 'syncing':
                    statusEl.textContent = '🔄 Syncing...';
                    statusEl.className = 'teval-sync-status teval-sync-syncing';
                    break;
                case 'retrying':
                    statusEl.textContent = '⚠️ Retrying...';
                    statusEl.className = 'teval-sync-status teval-sync-warning';
                    break;
                case 'error':
                    statusEl.textContent = '❌ Sync failed';
                    statusEl.className = 'teval-sync-status teval-sync-error';
                    break;
                default:
                    statusEl.textContent = 'Not synced';
                    statusEl.className = 'teval-sync-status';
            }}
        }}

        function startSyncTimer() {{
            if (!ENABLE_SYNC) return;

            if (syncTimer) clearInterval(syncTimer);

            // Initial sync
            syncToServer();

            // Set up periodic sync
            syncTimer = setInterval(() => {{
                syncToServer();
            }}, SYNC_INTERVAL);
        }}

        function stopSyncTimer() {{
            if (syncTimer) {{
                clearInterval(syncTimer);
                syncTimer = null;
            }}
        }}

        async function recoverSession() {{
            if (!ENABLE_SYNC || !sessionId) return;

            try {{
                const response = await fetch('/api/recover/' + sessionId);
                const result = await response.json();

                if (result.status === 'found' && result.data) {{
                    // Restore evaluation data
                    const data = result.data.evaluation;
                    if (data && data.results) {{
                        const form = document.getElementById('evaluation-form');
                        if (form) {{
                            // Restore metric values
                            for (const [metricId, value] of Object.entries(data.results)) {{
                                const radio = form.querySelector('input[name="' + metricId + '"][value="' + value + '"]');
                                if (radio) radio.checked = true;
                            }}
                            // Restore reasoning
                            if (data.reasoning) {{
                                for (const [metricId, text] of Object.entries(data.reasoning)) {{
                                    const textarea = form.querySelector('textarea[name="' + metricId + '_reasoning"]');
                                    if (textarea) textarea.value = text;
                                }}
                            }}
                        }}
                        updateProgress();
                        updateSyncStatus('success');
                        return true;
                    }}
                }}
            }} catch (error) {{
                console.error('Recovery error:', error);
            }}
            return false;
        }}

        // Initialize on load
        document.addEventListener('DOMContentLoaded', () => {{
            // Initialize session
            sessionId = getOrCreateSessionId();

            // Load evaluator name if saved
            loadEvaluatorName();
            // Load draft if exists
            const draft = localStorage.getItem('teval_' + RUBRIC_ID + '_draft');
            if (draft) {{
                try {{
                    const data = JSON.parse(draft);
                    if (confirm('Resume previous evaluation from ' + new Date(data.timestamp).toLocaleString() + '?')) {{
                        // Restore form data
                        const form = document.getElementById('evaluation-form');
                        if (form && data.results) {{
                            for (const [metricId, value] of Object.entries(data.results)) {{
                                const radio = form.querySelector('input[name="' + metricId + '"][value="' + value + '"]');
                                if (radio) radio.checked = true;
                            }}
                            if (data.reasoning) {{
                                for (const [metricId, text] of Object.entries(data.reasoning)) {{
                                    const textarea = form.querySelector('textarea[name="' + metricId + '_reasoning"]');
                                    if (textarea) textarea.value = text;
                                }}
                            }}
                        }}
                    }}
                }} catch (e) {{
                    console.error('Failed to restore draft:', e);
                }}
            }}

            // Try to recover session from server first if sync is enabled
            if (ENABLE_SYNC) {{
                recoverSession().then((recovered) => {{
                    if (!recovered) {{
                        // If no server recovery, try local draft
                        const localDraft = localStorage.getItem('teval_' + RUBRIC_ID + '_draft');
                        if (localDraft) {{
                            // ... existing draft recovery code ...
                        }}
                    }}
                    // Start sync timer after recovery attempt
                    startSyncTimer();
                }});
            }}

            // Start autosave
            if (autosaveEnabled) {{
                startAutosave();
            }}

            // Initial progress update
            updateProgress();

            // Add keyboard shortcuts
            document.addEventListener('keydown', (e) => {{
                // Ctrl+E for export
                if (e.ctrlKey && e.key === 'e') {{
                    e.preventDefault();
                    exportResults();
                }}

                // Enter to submit when form is complete
                if (e.key === 'Enter' && !e.shiftKey && e.target.tagName !== 'TEXTAREA') {{
                    const total = document.querySelectorAll('.teval-metric-card').length;
                    const completed = document.querySelectorAll('.teval-metric-card input:checked').length;
                    if (completed === total) {{
                        e.preventDefault();
                        const form = document.getElementById('evaluation-form');
                        if (form) form.submit();
                    }}
                }}
            }});
        }});
        """

        return js_template

    def render_with_item(self, item: Dict[str, Any], progress: Optional[Dict[str, Any]] = None) -> Form:
        """
        Render the evaluation form with an item display.

        Parameters
        ----------
        item : Dict[str, Any]
            Item to display with 'id', 'prompt', 'response' and optional 'metadata'.
        progress : Optional[Dict[str, Any]]
            Progress information from ItemsManager.

        Returns
        -------
        Form
            FastHTML Form component with item display and evaluation metrics.
        """
        components = []

        # Add item display section
        item_display = self._render_item_display(item)
        components.append(item_display)

        # Add navigation and progress
        if progress:
            nav_section = self._render_navigation(progress)
            components.append(nav_section)

        # Add evaluator name field and sync status if sync is enabled
        if self.enable_sync:
            evaluator_section = Div(
                Div(
                    Label("Evaluator Name (Optional):", cls="teval-label"),
                    Input(
                        type="text",
                        id="evaluator-name",
                        name="evaluator_name",
                        placeholder="Your name or email (for tracking purposes)",
                        cls="teval-input",
                        onchange="saveEvaluatorName()"
                    ),
                    cls="teval-evaluator-section"
                ),
                Div(
                    Span("Sync Status: ", cls="teval-sync-label"),
                    Span("Not synced", id="sync-status", cls="teval-sync-status"),
                    Span("", id="last-sync-time", cls="teval-sync-time"),
                    cls="teval-sync-info"
                ),
                cls="teval-header-info"
            )
            components.append(evaluator_section)

        # Add filter bar
        filter_bar = self._create_filter_bar()
        if filter_bar:
            components.append(filter_bar)

        # Add mandatory metrics section
        if self.rubric.mandatory_metrics:
            mandatory_section = self._render_metric_section(
                self.rubric.mandatory_metrics,
                "Mandatory Criteria",
                "All must pass for evaluation to succeed"
            )
            components.append(mandatory_section)

        # Add cumulative metrics section
        if self.rubric.cumulative_metrics:
            cumulative_section = self._render_metric_section(
                self.rubric.cumulative_metrics,
                "Quality Criteria",
                f"Need {self.rubric.passing_score_threshold} of {len(self.rubric.cumulative_metrics)} to pass"
            )
            components.append(cumulative_section)

        # Add progress indicator for metrics
        metric_progress = Div(
            Span(id="progress-text", cls="teval-progress-text"),
            Progress(
                id="progress-bar",
                value="0",
                max=str(len(self.rubric.metrics)),
                cls="teval-progress"
            ),
            cls="teval-progress-container"
        )
        components.append(metric_progress)

        # Add action buttons with item navigation
        actions = self._render_actions_with_navigation(item.get("id"), progress)
        components.append(actions)

        # Add JavaScript for enhanced functionality
        js_code = self._get_javascript_with_items(item, progress)
        components.append(Script(js_code))

        # Add hidden field for item_id
        components.append(Input(type="hidden", name="item_id", value=item.get("id", "")))

        return Form(
            *components,
            hx_post="/submit",
            hx_target="#result",
            cls="teval-form",
            id="evaluation-form"
        )

    def _render_item_display(self, item: Dict[str, Any]) -> Div:
        """
        Render the item content display area.

        Parameters
        ----------
        item : Dict[str, Any]
            Item to display.

        Returns
        -------
        Div
            Item display component.
        """
        components = []

        # Item header with ID
        if item.get("id"):
            components.append(
                Div(
                    Span(f"Item: {item['id']}", cls="teval-item-id"),
                    cls="teval-item-header"
                )
            )

        # Prompt section
        if item.get("prompt"):
            components.append(
                Div(
                    H2("Prompt", cls="teval-item-section-title"),
                    Div(item["prompt"], cls="teval-item-content"),
                    cls="teval-item-prompt"
                )
            )

        # Response section
        if item.get("response"):
            components.append(
                Div(
                    H2("Response", cls="teval-item-section-title"),
                    Div(item["response"], cls="teval-item-content"),
                    cls="teval-item-response"
                )
            )

        # Metadata section (if present)
        if item.get("metadata"):
            metadata_items = []
            for key, value in item["metadata"].items():
                metadata_items.append(
                    Span(f"{key}: {value}", cls="teval-item-metadata-item")
                )

            components.append(
                Div(
                    Span("Metadata: ", cls="teval-item-metadata-label"),
                    *metadata_items,
                    cls="teval-item-metadata"
                )
            )

        return Div(
            *components,
            cls="teval-item-display",
            id="item-display"
        )

    def _render_navigation(self, progress: Dict[str, Any]) -> Div:
        """
        Render navigation controls and progress display.

        Parameters
        ----------
        progress : Dict[str, Any]
            Progress information from ItemsManager.

        Returns
        -------
        Div
            Navigation component.
        """
        completed = progress.get("completed", 0)
        total = progress.get("total", 0)
        percentage = progress.get("percentage", 0)
        skipped = progress.get("skipped", 0)
        skip_count = progress.get("skip_count", 0)
        max_skips = progress.get("max_skips", 3)

        return Div(
            # Progress bar
            Div(
                Span(f"Item Progress: {completed}/{total} ({percentage:.0f}%)",
                     cls="teval-item-progress-text"),
                Progress(
                    id="item-progress-bar",
                    value=str(completed),
                    max=str(total),
                    cls="teval-item-progress-bar"
                ),
                cls="teval-item-progress"
            ),
            # Skip information
            Div(
                Span(f"Skips used: {skip_count}/{max_skips}",
                     cls="teval-skip-info") if self.allow_skip else None,
                Span(f" | Items skipped: {skipped}",
                     cls="teval-skip-info") if self.allow_skip and skipped > 0 else None,
                cls="teval-navigation-info"
            ) if self.allow_skip else None,
            cls="teval-navigation-section"
        )

    def _render_actions_with_navigation(self, item_id: str, progress: Optional[Dict] = None) -> Div:
        """
        Render action buttons with item navigation.

        Parameters
        ----------
        item_id : str
            Current item ID.
        progress : Optional[Dict]
            Progress information.

        Returns
        -------
        Div
            Actions component with navigation.
        """
        buttons = []

        # Skip button (if allowed and not at limit)
        if self.allow_skip and progress:
            skip_count = progress.get("skip_count", 0)
            max_skips = progress.get("max_skips", 3)
            if skip_count < max_skips:
                buttons.append(
                    Button(
                        "Skip Item",
                        onclick="skipCurrentItem()",
                        type="button",
                        cls="teval-btn-warning",
                        id="skip-btn"
                    )
                )

        # Submit and Next button
        buttons.append(
            Button(
                "Submit & Next",
                type="submit",
                cls="teval-btn-primary",
                id="submit-btn"
            )
        )

        # Export button
        buttons.append(
            Button(
                "Export JSON",
                onclick="exportResults()",
                type="button",
                cls="teval-btn-secondary"
            )
        )

        # Auto-save toggle
        buttons.append(
            Button(
                "Auto-save: ON",
                id="autosave-toggle",
                onclick="toggleAutosave()",
                type="button",
                cls="teval-btn-secondary teval-autosave-on"
            )
        )

        return Div(
            *buttons,
            cls="teval-actions"
        )

    def _get_javascript_with_items(self, item: Dict[str, Any], progress: Optional[Dict] = None) -> str:
        """Generate JavaScript code for form functionality with items."""
        # Get base JavaScript
        base_js = self._get_javascript()

        # Add item-specific JavaScript
        item_js = f"""
        // Current item data
        const CURRENT_ITEM = {json.dumps(item)};
        const CURRENT_PROGRESS = {json.dumps(progress or {})};

        // Skip item function
        async function skipCurrentItem() {{
            const skipCount = {progress.get('skip_count', 0) if progress else 0};
            const maxSkips = {progress.get('max_skips', 3) if progress else 3};

            if (skipCount >= maxSkips) {{
                alert('Maximum skips reached for this session');
                return;
            }}

            if (confirm('Skip this item and move to the next?')) {{
                try {{
                    const response = await fetch('/item/skip', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            item_id: CURRENT_ITEM.id,
                            session_id: sessionId
                        }})
                    }});

                    if (response.ok) {{
                        // Reload page to get next item
                        window.location.reload();
                    }} else {{
                        alert('Failed to skip item');
                    }}
                }} catch (error) {{
                    console.error('Skip error:', error);
                    alert('Error skipping item');
                }}
            }}
        }}

        // Override submit to include item_id
        const originalCollectFormData = window.collectFormData;
        window.collectFormData = function() {{
            const data = originalCollectFormData ? originalCollectFormData() : {{}};
            data.item_id = CURRENT_ITEM.id;
            data.item_content = {{
                prompt: CURRENT_ITEM.prompt,
                response: CURRENT_ITEM.response
            }};
            return data;
        }};

        // Add keyboard shortcuts for navigation
        document.addEventListener('keydown', (e) => {{
            // Alt+S to skip
            if (e.altKey && e.key === 's') {{
                e.preventDefault();
                const skipBtn = document.getElementById('skip-btn');
                if (skipBtn && !skipBtn.disabled) {{
                    skipCurrentItem();
                }}
            }}
        }});

        // Update progress display on load
        document.addEventListener('DOMContentLoaded', () => {{
            // Update item progress display
            const progressText = `Item ${{CURRENT_PROGRESS.completed + 1}} of ${{CURRENT_PROGRESS.total}}`;
            const itemProgressEl = document.querySelector('.teval-item-progress-text');
            if (itemProgressEl && !itemProgressEl.textContent.includes('Item Progress:')) {{
                itemProgressEl.textContent = progressText;
            }}
        }});
        """

        return base_js + "\n\n" + item_js