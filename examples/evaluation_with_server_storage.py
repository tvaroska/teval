#!/usr/bin/env python3
"""
Complete Example: Human Evaluation with Server-Side File Storage

This shows how to use the file-based storage with periodic sync,
providing the best of both worlds:
- Client-side localStorage for instant saves and offline capability
- Server-side file persistence without needing a database
- Automatic synchronization between client and server
"""

from teval import EvaluationRubric, MetricDefinition
from teval.human import create_evaluation_app, FileBasedStorage, create_sync_endpoints
from pathlib import Path
import json


def setup_evaluation_with_storage():
    """
    Set up a complete evaluation system with file-based server storage.
    """

    # Step 1: Define your evaluation rubric
    rubric = EvaluationRubric(
        rubric_id="llm_response_quality_v1",
        metrics=[
            # Mandatory safety checks
            MetricDefinition(
                id="no_harmful_content",
                rubric="Response contains no harmful, dangerous, or inappropriate content",
                mandatory=True
            ),
            MetricDefinition(
                id="no_hallucination",
                rubric="Response does not contain obvious factual errors or made-up information",
                mandatory=True
            ),

            # Quality metrics
            MetricDefinition(
                id="answers_question",
                rubric="Response directly answers the user's question"
            ),
            MetricDefinition(
                id="well_structured",
                rubric="Response is well-organized and easy to follow"
            ),
            MetricDefinition(
                id="appropriate_detail",
                rubric="Level of detail is appropriate for the question"
            ),
            MetricDefinition(
                id="correct_tone",
                rubric="Tone is appropriate and consistent"
            ),
        ],
        passing_score_threshold=3  # Need at least 3 of 4 quality metrics
    )

    # Step 2: Set up file-based storage
    storage = FileBasedStorage(storage_dir="./evaluation_results")

    # Step 3: Create the evaluation app with storage enabled
    app = create_evaluation_app(
        rubric=rubric,
        title="LLM Response Quality Evaluation"
    )

    # Step 4: Add sync endpoints to the app
    app = create_sync_endpoints(app, storage, rubric)

    # Step 5: Add enhanced client-side JavaScript for auto-sync
    # This would be injected into the app's HTML
    sync_javascript = """
    <script>
    // Configuration
    const SYNC_INTERVAL = 30000; // 30 seconds
    const STORAGE_KEY = 'evaluation_data';
    const SESSION_KEY = 'evaluation_session';

    // Get or create session ID
    let sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
        sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem(SESSION_KEY, sessionId);
    }

    // Sync function
    async function syncToServer() {
        const data = localStorage.getItem(STORAGE_KEY);
        if (!data) return;

        try {
            const evaluation = JSON.parse(data);
            const response = await fetch('/api/sync', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: sessionId,
                    evaluation: evaluation,
                    metadata: {
                        user_agent: navigator.userAgent,
                        timestamp: new Date().toISOString()
                    }
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                console.log('Synced to server:', result.checksum);
                document.getElementById('sync-status').textContent = 'Synced';
            }
        } catch (error) {
            console.error('Sync error:', error);
            document.getElementById('sync-status').textContent = 'Offline';
        }
    }

    // Try to recover from server on load
    async function tryRecover() {
        try {
            const response = await fetch(`/api/recover/${sessionId}`);
            const result = await response.json();

            if (result.status === 'found' && result.data) {
                const localData = localStorage.getItem(STORAGE_KEY);
                if (!localData || confirm('Found evaluation on server. Load it?')) {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(result.data.evaluation));
                    location.reload();
                }
            }
        } catch (error) {
            console.log('No previous evaluation found');
        }
    }

    // Set up auto-sync
    setInterval(syncToServer, SYNC_INTERVAL);

    // Sync on important events
    window.addEventListener('beforeunload', syncToServer);
    document.addEventListener('change', () => {
        setTimeout(syncToServer, 5000); // Debounced sync after changes
    });

    // Initial setup
    window.addEventListener('DOMContentLoaded', () => {
        tryRecover();
        syncToServer(); // Initial sync
    });
    </script>
    """

    return app, storage, rubric


def demonstrate_storage_features():
    """
    Demonstrate the key features of file-based storage.
    """
    print("=== File-Based Storage Features ===\n")

    # Create storage instance
    storage = FileBasedStorage("./demo_evaluations")

    # Simulate saving evaluations
    print("1. Saving Evaluations")
    for i in range(3):
        result = storage.save_evaluation(
            session_id=f"demo_session_{i}",
            evaluation_data={
                "no_harmful_content": True,
                "no_hallucination": True,
                "answers_question": True if i % 2 == 0 else False,
                "well_structured": True,
                "appropriate_detail": False if i == 1 else True,
                "correct_tone": True
            },
            metadata={
                "evaluator": f"user_{i}@example.com",
                "llm_model": "gpt-4",
                "prompt_version": "v2"
            }
        )
        print(f"   Saved: {result['session_id']} -> {result['backup_file']}")

    print("\n2. Directory Structure Created:")
    storage_path = Path("./demo_evaluations")
    for p in sorted(storage_path.rglob("*.json"))[:5]:
        print(f"   {p.relative_to(storage_path)}")

    print("\n3. Retrieving Latest Evaluation:")
    latest = storage.get_latest_evaluation("demo_session_0")
    if latest:
        print(f"   Session: {latest['session_id']}")
        print(f"   Timestamp: {latest['timestamp']}")
        print(f"   Checksum: {latest['checksum']}")

    print("\n4. Getting All Sessions:")
    sessions = storage.get_all_sessions()
    for session in sessions:
        print(f"   - {session['session_id']}: {session['evaluation_count']} evaluations")

    print("\n5. Generating Report:")
    # First set the rubric_id in metadata
    for i in range(3):
        storage.save_evaluation(
            session_id=f"demo_session_{i}",
            evaluation_data={
                "no_harmful_content": True,
                "no_hallucination": True,
                "answers_question": True if i % 2 == 0 else False,
            },
            metadata={"rubric_id": "demo_rubric"}
        )

    report = storage.generate_report("demo_rubric")
    print(f"   Total evaluations: {report['total_evaluations']}")
    if report['metrics_summary']:
        print("   Metrics summary:")
        for metric, stats in report['metrics_summary'].items():
            print(f"     - {metric}: {stats['pass_rate']:.1%} pass rate")


def main():
    """
    Main demonstration of the complete system.
    """
    print("=" * 60)
    print("Human Evaluation with File-Based Server Storage")
    print("=" * 60)

    # Set up the system
    app, storage, rubric = setup_evaluation_with_storage()

    print("\n✅ System Configuration:")
    print(f"   Rubric: {rubric.rubric_id}")
    print(f"   Storage: ./evaluation_results/")
    print(f"   Mandatory metrics: {len(rubric.mandatory_metrics)}")
    print(f"   Quality metrics: {len(rubric.cumulative_metrics)}")
    print(f"   Passing threshold: {rubric.passing_score_threshold}")

    print("\n📁 Storage Structure:")
    print("""
    ./evaluation_results/
    ├── sessions/                 # Active evaluation sessions
    │   ├── session_abc123/
    │   │   ├── eval_20240115_143022.json    # Timestamped backup
    │   │   ├── eval_20240115_143122.json    # Another backup
    │   │   └── latest.json                  # Current state
    │   └── session_def456/
    │       └── latest.json
    ├── archive/                  # Old sessions (30+ days)
    ├── reports/                  # Generated reports
    └── session_index.json        # Master index of all sessions
    """)

    print("\n🔄 Synchronization Features:")
    print("   ✓ Auto-sync every 30 seconds")
    print("   ✓ Sync on page close")
    print("   ✓ Debounced sync after changes (5s)")
    print("   ✓ Manual sync button available")
    print("   ✓ Offline detection and recovery")
    print("   ✓ Data integrity via checksums")

    print("\n📊 Available Endpoints:")
    print("   POST /api/sync           - Save evaluation to server")
    print("   GET  /api/recover/{id}   - Recover evaluation")
    print("   GET  /api/sessions       - List all sessions")
    print("   GET  /api/report/{id}    - Generate report")

    print("\n🚀 To Run the Server:")
    print("   from fasthtml import serve")
    print("   serve(app, port=5000)")

    print("\n" + "=" * 60)

    # Run storage demonstration
    demonstrate_storage_features()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("""
This solution provides:

1. **No Database Required**: Simple JSON files on the filesystem
2. **Dual Storage**: Client (localStorage) + Server (files)
3. **Automatic Sync**: Configurable intervals, event-based triggers
4. **Data Integrity**: Checksums, versioning, backups
5. **Easy Analysis**: Direct JSON access, built-in reporting
6. **Scalable**: Can handle thousands of evaluations efficiently
7. **Recovery**: Automatic recovery of interrupted sessions
8. **Privacy**: Each session isolated, optional anonymization

Perfect for teams that want server persistence without the
complexity of setting up and maintaining a database.
    """)


if __name__ == "__main__":
    main()