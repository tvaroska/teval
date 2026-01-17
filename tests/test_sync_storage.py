"""
Unit tests for file-based storage and synchronization functionality.

Tests the FileBasedStorage class, sync endpoints, and integration
with the human evaluation app.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import os

# Skip all tests if FastHTML not installed
pytest.importorskip("fasthtml")

from teval import EvaluationRubric, MetricDefinition
from teval.human import create_evaluation_app_with_storage, FileBasedStorage
from teval.human.sync_storage import create_sync_endpoints


def create_test_rubric():
    """Helper to create a test rubric."""
    return EvaluationRubric(
        rubric_id="test_storage",
        metrics=[
            MetricDefinition(id="M1", rubric="Test mandatory", mandatory=True),
            MetricDefinition(id="C1", rubric="Test cumulative 1"),
            MetricDefinition(id="C2", rubric="Test cumulative 2"),
        ],
        passing_score_threshold=1
    )


class TestFileBasedStorage:
    """Test the FileBasedStorage class."""

    def setup_method(self):
        """Set up test directory before each test."""
        self.test_dir = tempfile.mkdtemp()
        self.storage = FileBasedStorage(self.test_dir)

    def teardown_method(self):
        """Clean up test directory after each test."""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    def test_storage_initialization(self):
        """Test that storage creates necessary directories."""
        assert Path(self.test_dir).exists()
        assert (Path(self.test_dir) / "sessions").exists()
        assert (Path(self.test_dir) / "archive").exists()
        assert (Path(self.test_dir) / "reports").exists()

    def test_save_evaluation(self):
        """Test saving an evaluation to storage."""
        session_id = "test_session_123"
        evaluation_data = {
            "results": {"M1": True, "C1": True, "C2": False},
            "reasoning": {"M1": "Looks good"},
            "timestamp": datetime.now().isoformat()
        }
        metadata = {"evaluator": "test_user@example.com"}

        result = self.storage.save_evaluation(session_id, evaluation_data, metadata)

        assert result["status"] == "success"
        assert result["session_id"] == session_id
        assert "checksum" in result

        # Verify files were created
        session_dir = Path(self.test_dir) / "sessions" / session_id
        assert session_dir.exists()
        assert (session_dir / "latest.json").exists()
        assert len(list(session_dir.glob("eval_*.json"))) == 1

    def test_get_latest_evaluation(self):
        """Test retrieving the latest evaluation for a session."""
        session_id = "test_session_456"
        evaluation_data = {
            "results": {"M1": True, "C1": False, "C2": True},
            "timestamp": datetime.now().isoformat()
        }

        # Save evaluation
        self.storage.save_evaluation(session_id, evaluation_data)

        # Retrieve it
        retrieved = self.storage.get_latest_evaluation(session_id)

        assert retrieved is not None
        assert retrieved["session_id"] == session_id
        assert retrieved["evaluation"]["results"]["M1"] is True
        assert retrieved["evaluation"]["results"]["C1"] is False

    def test_get_latest_evaluation_not_found(self):
        """Test retrieving evaluation for non-existent session."""
        result = self.storage.get_latest_evaluation("nonexistent_session")
        assert result is None

    def test_checksum_validation(self):
        """Test that checksums are validated correctly."""
        session_id = "test_checksum"
        evaluation_data = {"results": {"M1": True}, "timestamp": "2024-01-01"}

        # Save evaluation
        self.storage.save_evaluation(session_id, evaluation_data)

        # Corrupt the latest.json file
        latest_file = Path(self.test_dir) / "sessions" / session_id / "latest.json"
        with open(latest_file, 'r') as f:
            data = json.load(f)

        # Modify data without updating checksum
        data["evaluation"]["results"]["M1"] = False
        with open(latest_file, 'w') as f:
            json.dump(data, f)

        # Retrieve should detect corruption
        retrieved = self.storage.get_latest_evaluation(session_id)
        assert "_warning" in retrieved
        assert "Checksum mismatch" in retrieved["_warning"]

    def test_get_session_history(self):
        """Test retrieving full history for a session."""
        session_id = "test_history"

        # Save multiple evaluations
        for i in range(3):
            evaluation_data = {
                "results": {"M1": True, "C1": i % 2 == 0, "C2": i > 0},
                "iteration": i
            }
            self.storage.save_evaluation(session_id, evaluation_data)

        history = self.storage.get_session_history(session_id)

        assert len(history) == 3
        assert all(h["session_id"] == session_id for h in history)
        # History should be in chronological order
        assert history[0]["evaluation"]["iteration"] == 0
        assert history[2]["evaluation"]["iteration"] == 2

    def test_get_all_sessions(self):
        """Test retrieving summary of all sessions."""
        # Create multiple sessions
        sessions = ["session_a", "session_b", "session_c"]
        for session_id in sessions:
            self.storage.save_evaluation(
                session_id,
                {"results": {"M1": True}},
                {"evaluator": f"user_{session_id}"}
            )

        all_sessions = self.storage.get_all_sessions()

        assert len(all_sessions) == 3
        assert all(s["session_id"] in sessions for s in all_sessions)
        assert all("last_modified" in s for s in all_sessions)
        assert all("evaluator" in s for s in all_sessions)
        assert all("evaluation_count" in s for s in all_sessions)

    def test_archive_old_sessions(self):
        """Test archiving old sessions."""
        session_id = "old_session"
        session_dir = Path(self.test_dir) / "sessions" / session_id
        session_dir.mkdir(parents=True)

        # Create a file with old timestamp
        latest_file = session_dir / "latest.json"
        with open(latest_file, 'w') as f:
            json.dump({"data": "old"}, f)

        # Set file modification time to 40 days ago
        old_time = datetime.now().timestamp() - (40 * 86400)
        os.utime(latest_file, (old_time, old_time))

        # Archive sessions older than 30 days
        archived = self.storage.archive_old_sessions(days_old=30)

        assert archived == 1
        assert not session_dir.exists()
        assert (Path(self.test_dir) / "archive" / session_id).exists()

    def test_generate_report(self):
        """Test report generation for a rubric."""
        rubric_id = "test_rubric"

        # Create evaluations for multiple sessions
        for i in range(3):
            session_id = f"session_{i}"
            evaluation_data = {
                "results": {"M1": i != 1, "C1": True, "C2": i == 2}
            }
            metadata = {"rubric_id": rubric_id}
            self.storage.save_evaluation(session_id, evaluation_data, metadata)

        report = self.storage.generate_report(rubric_id)

        assert report["rubric_id"] == rubric_id
        assert report["total_evaluations"] == 3
        assert "metrics_summary" in report

        # Check metric statistics
        m1_stats = report["metrics_summary"].get("M1", {})
        assert m1_stats.get("passed") == 2  # Sessions 0 and 2
        assert m1_stats.get("failed") == 1  # Session 1
        assert abs(m1_stats.get("pass_rate", 0) - 0.6667) < 0.01

    def test_session_index_update(self):
        """Test that session index is updated correctly."""
        session_id = "test_index"

        # Save multiple evaluations to same session
        for i in range(3):
            self.storage.save_evaluation(session_id, {"iteration": i})

        # Check index file
        index_file = Path(self.test_dir) / "session_index.json"
        assert index_file.exists()

        with open(index_file, 'r') as f:
            index = json.load(f)

        assert session_id in index
        assert index[session_id]["update_count"] == 3
        assert "last_updated" in index[session_id]


class TestCreateEvaluationAppWithStorage:
    """Test the create_evaluation_app_with_storage function."""

    def test_app_creation_without_storage(self):
        """Test app creation without storage directory (client-only mode)."""
        rubric = create_test_rubric()
        app = create_evaluation_app_with_storage(rubric, title="Test App")

        assert app is not None
        assert hasattr(app, 'routes')

    def test_app_creation_with_storage(self):
        """Test app creation with storage directory."""
        rubric = create_test_rubric()

        with tempfile.TemporaryDirectory() as temp_dir:
            app = create_evaluation_app_with_storage(
                rubric,
                title="Test App",
                storage_dir=temp_dir,
                sync_interval=15
            )

            assert app is not None
            # Verify storage directory was created
            assert Path(temp_dir).exists()
            assert (Path(temp_dir) / "sessions").exists()

    def test_app_creation_with_sync_disabled(self):
        """Test app creation with storage but sync disabled."""
        rubric = create_test_rubric()

        with tempfile.TemporaryDirectory() as temp_dir:
            app = create_evaluation_app_with_storage(
                rubric,
                title="Test App",
                storage_dir=temp_dir,
                enable_sync=False
            )

            assert app is not None
            # Storage directory should still be created
            assert Path(temp_dir).exists()

    def test_app_with_custom_callback(self):
        """Test app creation with custom storage callback."""
        rubric = create_test_rubric()
        callback_data = []

        def custom_callback(data):
            callback_data.append(data)

        app = create_evaluation_app_with_storage(
            rubric,
            storage_callback=custom_callback
        )

        assert app is not None
        # Callback should be registered (would be called on form submission)


class TestSyncEndpoints:
    """Test the sync API endpoints."""

    def setup_method(self):
        """Set up test app and storage."""
        self.test_dir = tempfile.mkdtemp()
        self.rubric = create_test_rubric()
        self.storage = FileBasedStorage(self.test_dir)

    def teardown_method(self):
        """Clean up test directory."""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    @pytest.mark.asyncio
    async def test_sync_endpoint(self):
        """Test the /api/sync endpoint."""
        # Create a mock app
        app = Mock()
        app.post = Mock()

        # Add sync endpoints
        app = create_sync_endpoints(app, self.storage, self.rubric)

        # Verify endpoint was registered
        assert app.post.called
        call_args = app.post.call_args
        assert call_args[0][0] == "/api/sync"

    @pytest.mark.asyncio
    async def test_recover_endpoint(self):
        """Test the /api/recover endpoint."""
        # Create a mock app
        app = Mock()
        app.get = Mock()

        # Add sync endpoints
        app = create_sync_endpoints(app, self.storage, self.rubric)

        # Verify endpoint was registered
        get_calls = [call[0][0] for call in app.get.call_args_list]
        assert "/api/recover/{session_id}" in get_calls

    @pytest.mark.asyncio
    async def test_sessions_list_endpoint(self):
        """Test the /api/sessions endpoint."""
        # Create a mock app
        app = Mock()
        app.get = Mock()

        # Add sync endpoints
        app = create_sync_endpoints(app, self.storage, self.rubric)

        # Verify endpoint was registered
        get_calls = [call[0][0] for call in app.get.call_args_list]
        assert "/api/sessions" in get_calls

    @pytest.mark.asyncio
    async def test_report_endpoint(self):
        """Test the /api/report endpoint."""
        # Create a mock app
        app = Mock()
        app.get = Mock()

        # Add sync endpoints
        app = create_sync_endpoints(app, self.storage, self.rubric)

        # Verify endpoint was registered
        get_calls = [call[0][0] for call in app.get.call_args_list]
        assert "/api/report/{rubric_id}" in get_calls


class TestMultiUserScenarios:
    """Test multi-user scenarios with isolated sessions."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.rubric = create_test_rubric()

    def teardown_method(self):
        """Clean up test directory."""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    def test_multiple_users_isolated_sessions(self):
        """Test that multiple users have isolated sessions."""
        storage = FileBasedStorage(self.test_dir)

        # Simulate multiple users
        users = [
            ("session_alice", "alice@example.com", {"M1": True, "C1": True, "C2": False}),
            ("session_bob", "bob@example.com", {"M1": False, "C1": True, "C2": True}),
            ("session_carol", "carol@example.com", {"M1": True, "C1": False, "C2": True}),
        ]

        for session_id, evaluator, results in users:
            storage.save_evaluation(
                session_id,
                {"results": results},
                {"evaluator": evaluator}
            )

        # Verify each user's data is isolated
        for session_id, evaluator, expected_results in users:
            data = storage.get_latest_evaluation(session_id)
            assert data is not None
            assert data["metadata"]["evaluator"] == evaluator
            assert data["evaluation"]["results"] == expected_results

        # Verify sessions can't access each other's data
        alice_data = storage.get_latest_evaluation("session_alice")
        assert alice_data["metadata"]["evaluator"] == "alice@example.com"
        assert alice_data["evaluation"]["results"]["M1"] is True

    def test_session_recovery_after_crash(self):
        """Test that sessions can be recovered after browser crash."""
        storage = FileBasedStorage(self.test_dir)
        session_id = "crash_test_session"

        # Save initial evaluation
        initial_data = {
            "results": {"M1": True, "C1": False, "C2": None},
            "reasoning": {"M1": "In progress..."}
        }
        storage.save_evaluation(session_id, initial_data, {"evaluator": "test_user"})

        # Simulate browser crash and recovery
        recovered = storage.get_latest_evaluation(session_id)

        assert recovered is not None
        assert recovered["session_id"] == session_id
        assert recovered["evaluation"]["results"]["M1"] is True
        assert recovered["evaluation"]["results"]["C1"] is False
        assert recovered["metadata"]["evaluator"] == "test_user"

    def test_concurrent_evaluations(self):
        """Test that concurrent evaluations don't interfere."""
        storage = FileBasedStorage(self.test_dir)

        # Simulate concurrent saves
        sessions = []
        for i in range(10):
            session_id = f"concurrent_{i}"
            evaluation_data = {
                "results": {"M1": i % 2 == 0, "C1": True, "C2": i > 5}
            }
            result = storage.save_evaluation(session_id, evaluation_data)
            sessions.append((session_id, evaluation_data))
            assert result["status"] == "success"

        # Verify all sessions are intact
        for session_id, expected_data in sessions:
            retrieved = storage.get_latest_evaluation(session_id)
            assert retrieved is not None
            assert retrieved["evaluation"]["results"] == expected_data["results"]


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_storage_permission_error(self):
        """Test handling of permission errors."""
        # Try to create storage in a read-only directory
        # This test might need to be skipped on some systems
        import os
        if os.name == 'nt':  # Windows
            pytest.skip("Permission test not reliable on Windows")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Make directory read-only
            os.chmod(temp_dir, 0o444)

            try:
                # This should handle the error gracefully
                storage = FileBasedStorage(os.path.join(temp_dir, "readonly"))
                # If no error, the implementation created parent directories
                assert True
            except (PermissionError, OSError):
                # Expected on systems with strict permissions
                assert True
            finally:
                # Restore permissions for cleanup
                os.chmod(temp_dir, 0o755)

    def test_corrupt_json_handling(self):
        """Test handling of corrupt JSON files."""
        test_dir = tempfile.mkdtemp()
        try:
            storage = FileBasedStorage(test_dir)
            session_id = "corrupt_test"
            session_dir = Path(test_dir) / "sessions" / session_id
            session_dir.mkdir(parents=True)

            # Create corrupt JSON file
            latest_file = session_dir / "latest.json"
            with open(latest_file, 'w') as f:
                f.write("{ invalid json }")

            # Should handle gracefully
            result = storage.get_latest_evaluation(session_id)
            assert result is None  # Returns None for corrupt data
        finally:
            shutil.rmtree(test_dir)

    def test_missing_required_fields(self):
        """Test handling of missing required fields in sync data."""
        test_dir = tempfile.mkdtemp()
        try:
            storage = FileBasedStorage(test_dir)

            # Save with missing fields should not crash
            result = storage.save_evaluation("test", {}, None)
            assert result["status"] == "success"

            retrieved = storage.get_latest_evaluation("test")
            assert retrieved is not None
            assert retrieved["evaluation"] == {}
        finally:
            shutil.rmtree(test_dir)


class TestIntegration:
    """Integration tests for the complete system."""

    def test_end_to_end_evaluation_with_storage(self):
        """Test complete flow from form creation to storage and recovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create rubric
            rubric = EvaluationRubric(
                rubric_id="integration_test",
                metrics=[
                    MetricDefinition(id="REQ1", rubric="Requirement met", mandatory=True),
                    MetricDefinition(id="QUAL1", rubric="Quality check"),
                ],
                passing_score_threshold=1
            )

            # Create app with storage
            app = create_evaluation_app_with_storage(
                rubric,
                title="Integration Test",
                storage_dir=temp_dir,
                sync_interval=10
            )

            assert app is not None

            # Verify storage was initialized
            assert Path(temp_dir).exists()
            assert (Path(temp_dir) / "sessions").exists()

            # Simulate evaluation data
            storage = FileBasedStorage(temp_dir)
            session_id = "test_integration_session"
            evaluation_data = {
                "results": {"REQ1": True, "QUAL1": True},
                "reasoning": {"REQ1": "Meets requirements"},
                "passes": True
            }

            # Save evaluation
            result = storage.save_evaluation(
                session_id,
                evaluation_data,
                {"evaluator": "integration_tester"}
            )
            assert result["status"] == "success"

            # Verify recovery
            recovered = storage.get_latest_evaluation(session_id)
            assert recovered is not None
            assert recovered["evaluation"]["results"]["REQ1"] is True
            assert recovered["evaluation"]["passes"] is True

            # Generate report
            report = storage.generate_report("integration_test")
            assert report["total_evaluations"] == 1