#!/usr/bin/env python3
"""
Example: Human Evaluation with File-Based Server Storage and Auto-Sync

This shows how the human evaluation app could be enhanced with:
1. Server-side file storage (no database needed)
2. Periodic auto-sync from client to server
3. Automatic backup and recovery
"""

from pathlib import Path
from datetime import datetime
import json
from typing import Optional

def create_evaluation_app_with_sync(
    rubric,
    title="Evaluation",
    storage_dir="./evaluations",
    sync_interval_seconds=30,
    enable_sync=True
):
    """
    Create evaluation app with file-based server storage and auto-sync.

    Args:
        rubric: The EvaluationRubric to use
        title: Title for the web UI
        storage_dir: Directory to store evaluation files on server
        sync_interval_seconds: How often to sync (0 to disable auto-sync)
        enable_sync: Whether to enable server-side storage
    """
    from fasthtml import FastHTML, Div, Script, Button, Form

    app = FastHTML()

    # Ensure storage directory exists
    if enable_sync:
        storage_path = Path(storage_dir)
        storage_path.mkdir(parents=True, exist_ok=True)

    # Server endpoint for syncing
    @app.post("/api/sync-evaluation")
    async def sync_evaluation(request):
        """Save evaluation to server filesystem."""
        if not enable_sync:
            return {"status": "sync_disabled"}

        data = await request.json()

        # Generate unique filename with timestamp and session ID
        session_id = data.get("session_id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_{session_id}_{timestamp}.json"

        # Save to file
        file_path = storage_path / filename

        # Also maintain a "latest" file for each session
        latest_path = storage_path / f"eval_{session_id}_latest.json"

        try:
            # Save timestamped version (for history)
            with open(file_path, 'w') as f:
                json.dump({
                    "rubric_id": rubric.rubric_id,
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "evaluation": data.get("evaluation", {}),
                    "metadata": data.get("metadata", {})
                }, f, indent=2)

            # Save/overwrite latest version (for easy access)
            with open(latest_path, 'w') as f:
                json.dump({
                    "rubric_id": rubric.rubric_id,
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "evaluation": data.get("evaluation", {}),
                    "metadata": data.get("metadata", {})
                }, f, indent=2)

            return {
                "status": "success",
                "filename": filename,
                "message": f"Saved to server: {filename}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # Server endpoint to retrieve evaluation (for recovery)
    @app.get("/api/get-evaluation/{session_id}")
    async def get_evaluation(session_id: str):
        """Retrieve latest evaluation for a session."""
        if not enable_sync:
            return {"status": "sync_disabled"}

        latest_path = storage_path / f"eval_{session_id}_latest.json"

        if latest_path.exists():
            with open(latest_path, 'r') as f:
                return json.load(f)

        return {"status": "not_found"}

    # Main UI with enhanced JavaScript for sync
    @app.get("/")
    async def home():
        # Generate the evaluation form HTML
        metrics_html = generate_metrics_form(rubric)

        # Enhanced JavaScript with sync functionality
        sync_script = f"""
        // Generate or retrieve session ID
        let sessionId = localStorage.getItem('eval_session_id');
        if (!sessionId) {{
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('eval_session_id', sessionId);
        }}

        // Auto-sync configuration
        const SYNC_ENABLED = {str(enable_sync).lower()};
        const SYNC_INTERVAL = {sync_interval_seconds * 1000};  // Convert to milliseconds

        // Sync function
        async function syncToServer() {{
            if (!SYNC_ENABLED) return;

            const evaluation = collectEvaluationData();
            const metadata = {{
                evaluator: localStorage.getItem('evaluator_name') || 'anonymous',
                startTime: localStorage.getItem('eval_start_time'),
                lastModified: new Date().toISOString()
            }};

            try {{
                const response = await fetch('/api/sync-evaluation', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        session_id: sessionId,
                        evaluation: evaluation,
                        metadata: metadata
                    }})
                }});

                const result = await response.json();

                // Update UI with sync status
                updateSyncStatus(result.status === 'success' ? 'Synced' : 'Sync failed');

                // Store last sync time
                if (result.status === 'success') {{
                    localStorage.setItem('last_sync', new Date().toISOString());
                }}
            }} catch (error) {{
                console.error('Sync error:', error);
                updateSyncStatus('Offline');
            }}
        }}

        // Try to recover from server on load
        async function tryRecover() {{
            if (!SYNC_ENABLED) return;

            try {{
                const response = await fetch(`/api/get-evaluation/${{sessionId}}`);
                const data = await response.json();

                if (data.status !== 'not_found' && data.evaluation) {{
                    // Ask user if they want to recover
                    if (confirm('Found previous evaluation on server. Recover?')) {{
                        restoreEvaluation(data.evaluation);
                    }}
                }}
            }} catch (error) {{
                console.log('No previous evaluation found');
            }}
        }}

        // Set up periodic sync
        if (SYNC_ENABLED && SYNC_INTERVAL > 0) {{
            setInterval(syncToServer, SYNC_INTERVAL);

            // Also sync on important events
            document.addEventListener('change', debounce(syncToServer, 5000));
            window.addEventListener('beforeunload', syncToServer);
        }}

        // Initialize
        window.addEventListener('load', () => {{
            tryRecover();
            if (SYNC_ENABLED) {{
                syncToServer();  // Initial sync
            }}
        }});

        // Manual sync button
        function manualSync() {{
            syncToServer().then(() => {{
                alert('Evaluation synced to server');
            }});
        }}
        """ if enable_sync else ""

        return Div(
            # Header with sync status
            Div(
                title,
                Div(
                    "Status: ",
                    Span("Local Only" if not enable_sync else "Ready", id="sync-status"),
                    style="float: right; padding: 5px; background: #f0f0f0; border-radius: 3px;"
                ) if enable_sync else "",
                style="padding: 10px; background: #333; color: white;"
            ),

            # Evaluation form
            Div(metrics_html, id="metrics-form"),

            # Action buttons
            Div(
                Button("Export JSON", onclick="exportJSON()"),
                Button("Sync Now", onclick="manualSync()") if enable_sync else "",
                Button("Clear", onclick="clearEvaluation()"),
                style="padding: 10px;"
            ),

            # JavaScript
            Script(sync_script)
        )

    return app


def analyze_synced_evaluations(storage_dir="./evaluations"):
    """
    Analyze all evaluations stored in the server directory.

    Returns summary statistics and individual results.
    """
    storage_path = Path(storage_dir)

    if not storage_path.exists():
        return {"error": "No evaluations directory found"}

    # Collect all latest evaluations (one per session)
    evaluations = []
    for latest_file in storage_path.glob("*_latest.json"):
        with open(latest_file, 'r') as f:
            data = json.load(f)
            evaluations.append(data)

    # Analyze results
    results = {
        "total_sessions": len(evaluations),
        "evaluations": evaluations,
        "metrics_summary": {},
        "completion_rate": 0
    }

    if evaluations:
        # Calculate metrics summary
        all_metrics = set()
        for eval_data in evaluations:
            if "evaluation" in eval_data:
                all_metrics.update(eval_data["evaluation"].keys())

        for metric in all_metrics:
            passed = sum(1 for e in evaluations
                        if e.get("evaluation", {}).get(metric, False))
            total = len(evaluations)
            results["metrics_summary"][metric] = {
                "passed": passed,
                "total": total,
                "pass_rate": passed / total if total > 0 else 0
            }

    return results


def generate_metrics_form(rubric):
    """Generate HTML form for metrics (placeholder for actual implementation)."""
    # This would be the actual form generation from teval.human
    form_html = f"<h2>Evaluate using {rubric.rubric_id}</h2>"

    form_html += "<h3>Mandatory Metrics</h3>"
    for metric in rubric.mandatory_metrics:
        form_html += f"""
        <div>
            <label>
                <input type="checkbox" id="{metric.id}" name="{metric.id}">
                {metric.rubric}
            </label>
        </div>
        """

    form_html += "<h3>Quality Metrics</h3>"
    for metric in rubric.cumulative_metrics:
        form_html += f"""
        <div>
            <label>
                <input type="checkbox" id="{metric.id}" name="{metric.id}">
                {metric.rubric}
            </label>
        </div>
        """

    return form_html


def example_usage():
    """
    Example of using the enhanced evaluation app with sync.
    """
    from teval import EvaluationRubric, MetricDefinition

    # Create a rubric
    rubric = EvaluationRubric(
        rubric_id="content_quality_v1",
        metrics=[
            MetricDefinition(
                id="factually_accurate",
                rubric="All factual claims are accurate and verifiable",
                mandatory=True
            ),
            MetricDefinition(
                id="well_structured",
                rubric="Content is well-organized with clear sections"
            ),
            MetricDefinition(
                id="engaging",
                rubric="Writing style is engaging and appropriate for audience"
            ),
        ],
        passing_score_threshold=1
    )

    # Create app with file-based sync
    app = create_evaluation_app_with_sync(
        rubric=rubric,
        title="Content Quality Evaluation",
        storage_dir="./evaluation_data",  # Server-side storage directory
        sync_interval_seconds=30,  # Auto-sync every 30 seconds
        enable_sync=True  # Enable server storage
    )

    print("""
    Enhanced Evaluation App Created!

    Features:
    ✓ Client-side localStorage (instant, offline-capable)
    ✓ Server-side file storage (no database needed)
    ✓ Auto-sync every 30 seconds
    ✓ Manual sync button
    ✓ Sync on page close
    ✓ Recovery on page load

    Storage structure:
    ./evaluation_data/
      ├── eval_session123_20240115_143022.json  (timestamped backup)
      ├── eval_session123_latest.json           (current state)
      ├── eval_session456_20240115_143122.json
      └── eval_session456_latest.json

    To run:
    from fasthtml import serve
    serve(app, port=5000)

    To analyze results:
    results = analyze_synced_evaluations("./evaluation_data")
    """)

    # Show what the stored files look like
    example_file = {
        "rubric_id": "content_quality_v1",
        "timestamp": "20240115_143022",
        "session_id": "session_1234567890_abc123",
        "evaluation": {
            "factually_accurate": True,
            "well_structured": True,
            "engaging": False
        },
        "metadata": {
            "evaluator": "john.doe@company.com",
            "startTime": "2024-01-15T14:25:00Z",
            "lastModified": "2024-01-15T14:30:22Z"
        }
    }

    print("\nExample stored evaluation file:")
    print(json.dumps(example_file, indent=2))

    return app


if __name__ == "__main__":
    app = example_usage()