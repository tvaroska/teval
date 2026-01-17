"""
File-based storage and synchronization for human evaluations.

This module provides server-side file storage with automatic client sync,
without requiring a database. All evaluations are stored as JSON files.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import json
import hashlib
import time


class FileBasedStorage:
    """
    Simple file-based storage for evaluation data.

    Each evaluation session gets:
    - Timestamped backups for history
    - A 'latest' file for current state
    - Optional compression for old files
    """

    def __init__(self, storage_dir: str = "./evaluations"):
        """
        Initialize file storage.

        Args:
            storage_dir: Directory to store evaluation files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        self.sessions_dir = self.storage_dir / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)

        self.archive_dir = self.storage_dir / "archive"
        self.archive_dir.mkdir(exist_ok=True)

        self.reports_dir = self.storage_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    def save_evaluation(
        self,
        session_id: str,
        evaluation_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save evaluation to filesystem.

        Args:
            session_id: Unique session identifier
            evaluation_data: The evaluation results
            metadata: Optional metadata (evaluator, timestamp, etc.)

        Returns:
            Dict with status and file info
        """
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        # Create session directory if needed
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(exist_ok=True)

        # Prepare data package
        data_package = {
            "session_id": session_id,
            "timestamp": timestamp.isoformat(),
            "evaluation": evaluation_data,
            "metadata": metadata or {},
            "version": "1.0"
        }

        # Calculate checksum for data integrity
        data_json = json.dumps(data_package, sort_keys=True)
        checksum = hashlib.md5(data_json.encode()).hexdigest()
        data_package["checksum"] = checksum

        # Save timestamped backup (for history)
        backup_file = session_dir / f"eval_{timestamp_str}.json"
        with open(backup_file, 'w') as f:
            json.dump(data_package, f, indent=2)

        # Save/update latest file
        latest_file = session_dir / "latest.json"
        with open(latest_file, 'w') as f:
            json.dump(data_package, f, indent=2)

        # Update session index
        self._update_session_index(session_id, timestamp)

        return {
            "status": "success",
            "session_id": session_id,
            "backup_file": str(backup_file.name),
            "checksum": checksum
        }

    def get_latest_evaluation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest evaluation for a session.

        Args:
            session_id: Session identifier

        Returns:
            Latest evaluation data or None if not found
        """
        latest_file = self.sessions_dir / session_id / "latest.json"

        if latest_file.exists():
            with open(latest_file, 'r') as f:
                data = json.load(f)

            # Verify checksum
            stored_checksum = data.pop("checksum", None)
            calculated_checksum = hashlib.md5(
                json.dumps(data, sort_keys=True).encode()
            ).hexdigest()

            if stored_checksum != calculated_checksum:
                data["_warning"] = "Checksum mismatch - data may be corrupted"

            data["checksum"] = stored_checksum
            return data

        return None

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all evaluations for a session (chronological order).

        Args:
            session_id: Session identifier

        Returns:
            List of all evaluations for this session
        """
        session_dir = self.sessions_dir / session_id

        if not session_dir.exists():
            return []

        history = []
        for eval_file in sorted(session_dir.glob("eval_*.json")):
            with open(eval_file, 'r') as f:
                history.append(json.load(f))

        return history

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get summary of all evaluation sessions.

        Returns:
            List of session summaries
        """
        sessions = []

        for session_dir in self.sessions_dir.iterdir():
            if session_dir.is_dir():
                latest_file = session_dir / "latest.json"
                if latest_file.exists():
                    with open(latest_file, 'r') as f:
                        data = json.load(f)

                    sessions.append({
                        "session_id": session_dir.name,
                        "last_modified": data.get("timestamp"),
                        "evaluator": data.get("metadata", {}).get("evaluator", "anonymous"),
                        "evaluation_count": len(list(session_dir.glob("eval_*.json")))
                    })

        return sorted(sessions, key=lambda x: x.get("last_modified", ""), reverse=True)

    def archive_old_sessions(self, days_old: int = 30) -> int:
        """
        Archive sessions older than specified days.

        Args:
            days_old: Archive sessions older than this many days

        Returns:
            Number of sessions archived
        """
        archived_count = 0
        cutoff_time = time.time() - (days_old * 86400)

        for session_dir in self.sessions_dir.iterdir():
            if session_dir.is_dir():
                latest_file = session_dir / "latest.json"
                if latest_file.exists():
                    if latest_file.stat().st_mtime < cutoff_time:
                        # Move to archive
                        archive_path = self.archive_dir / session_dir.name
                        session_dir.rename(archive_path)
                        archived_count += 1

        return archived_count

    def _update_session_index(self, session_id: str, timestamp: datetime):
        """Update the master session index."""
        index_file = self.storage_dir / "session_index.json"

        if index_file.exists():
            with open(index_file, 'r') as f:
                index = json.load(f)
        else:
            index = {}

        index[session_id] = {
            "last_updated": timestamp.isoformat(),
            "update_count": index.get(session_id, {}).get("update_count", 0) + 1
        }

        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

    def generate_report(
        self,
        rubric_id: str,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate aggregate report for all evaluations.

        Args:
            rubric_id: Rubric identifier to filter by
            output_format: Format for report (json, csv, html)

        Returns:
            Aggregated statistics and results
        """
        all_evaluations = []

        # Collect all evaluations
        for session_dir in self.sessions_dir.iterdir():
            if session_dir.is_dir():
                latest_file = session_dir / "latest.json"
                if latest_file.exists():
                    with open(latest_file, 'r') as f:
                        data = json.load(f)
                        if data.get("metadata", {}).get("rubric_id") == rubric_id:
                            all_evaluations.append(data)

        # Calculate statistics
        report = {
            "rubric_id": rubric_id,
            "total_evaluations": len(all_evaluations),
            "generated_at": datetime.now().isoformat(),
            "metrics_summary": {},
            "evaluations": all_evaluations
        }

        if all_evaluations:
            # Get all metric names
            all_metrics = set()
            for eval_data in all_evaluations:
                all_metrics.update(eval_data.get("evaluation", {}).keys())

            # Calculate per-metric statistics
            for metric in all_metrics:
                passed = sum(
                    1 for e in all_evaluations
                    if e.get("evaluation", {}).get(metric, False)
                )
                total = len(all_evaluations)

                report["metrics_summary"][metric] = {
                    "passed": passed,
                    "failed": total - passed,
                    "pass_rate": passed / total if total > 0 else 0
                }

        # Save report
        report_file = self.reports_dir / f"report_{rubric_id}_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        return report


def create_sync_endpoints(app, storage: FileBasedStorage, rubric):
    """
    Add sync endpoints to a FastHTML app.

    Args:
        app: FastHTML application instance
        storage: FileBasedStorage instance
        rubric: EvaluationRubric being used
    """

    @app.post("/api/sync")
    async def sync_evaluation(request):
        """Sync evaluation from client to server."""
        data = await request.json()

        result = storage.save_evaluation(
            session_id=data.get("session_id"),
            evaluation_data=data.get("evaluation"),
            metadata={
                **data.get("metadata", {}),
                "rubric_id": rubric.rubric_id,
                "synced_at": datetime.now().isoformat()
            }
        )

        return result

    @app.get("/api/recover/{session_id}")
    async def recover_evaluation(session_id: str):
        """Recover evaluation for a session."""
        data = storage.get_latest_evaluation(session_id)

        if data:
            return {"status": "found", "data": data}
        else:
            return {"status": "not_found"}

    @app.get("/api/sessions")
    async def list_sessions():
        """List all evaluation sessions."""
        return {"sessions": storage.get_all_sessions()}

    @app.get("/api/report/{rubric_id}")
    async def generate_report(rubric_id: str):
        """Generate report for a rubric."""
        return storage.generate_report(rubric_id)

    return app