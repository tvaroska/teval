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
        include_reasoning: bool = True
    ):
        """Initialize the evaluation form."""
        self.rubric = rubric
        self.title = title or f"Evaluation: {rubric.rubric_id}"
        self.include_reasoning = include_reasoning

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
            components.append(
                Textarea(
                    placeholder="Reasoning (optional)...",
                    name=f"{metric_id}_reasoning",
                    rows="3",
                    cls="teval-reasoning"
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
            - mandatory_pass: Whether all mandatory metrics passed
            - score: Number of passed cumulative metrics
            - total: Total number of cumulative metrics
            - passes: Overall pass/fail status
            - timestamp: ISO format timestamp

        Examples
        --------
        >>> form_data = {
        ...     "M1": "true",
        ...     "C1": "false",
        ...     "M1_reasoning": "Looks good"
        ... }
        >>> results = form.process_submission(form_data)
        >>> print(results["results"])  # {"M1": True, "C1": False}
        """
        results = {}
        reasoning = {}

        for metric in self.rubric.metrics:
            mid = metric.id
            results[mid] = form_data.get(mid) == "true"

            if self.include_reasoning:
                reason_key = f"{mid}_reasoning"
                if reason_key in form_data and form_data[reason_key]:
                    reasoning[mid] = form_data[reason_key]

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

        return {
            "rubric_id": self.rubric.rubric_id,
            "results": results,
            "reasoning": reasoning,
            "mandatory_pass": mandatory_pass,
            "score": cumulative_score,
            "total": len(self.rubric.cumulative_metrics),
            "passes": passes,
            "timestamp": datetime.now().isoformat()
        }

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

        function updateProgress() {{
            const total = document.querySelectorAll('.teval-metric-card').length;
            const completed = document.querySelectorAll('.teval-metric-card input:checked').length;

            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');

            if (progressBar) progressBar.value = completed;
            if (progressText) {{
                progressText.textContent = 'Progress: ' + completed + '/' + total + ' metrics completed';
            }}

            // Enable submit button when all metrics are complete
            const submitBtn = document.getElementById('submit-btn');
            if (submitBtn) {{
                submitBtn.disabled = completed < total;
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

        // Initialize on load
        document.addEventListener('DOMContentLoaded', () => {{
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