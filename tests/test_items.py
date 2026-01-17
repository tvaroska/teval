"""
Unit tests for evaluation items management functionality.

Tests the ItemsManager, ItemSource classes, and integration
with the human evaluation app for queue-based evaluations.
"""

import pytest
import json
import csv
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
import os

# Skip all tests if FastHTML not installed
pytest.importorskip("fasthtml")

from teval import EvaluationRubric, MetricDefinition
from teval.human import (
    create_evaluation_app,
    ItemsManager,
    ItemSource,
    ListItemSource,
    FileItemSource,
    normalize_items,
    FileBasedStorage
)


def create_test_items(count=5):
    """Helper to create test evaluation items."""
    return [
        {
            "id": f"item_{i:03d}",
            "prompt": f"Test prompt {i}",
            "response": f"Test response {i}",
            "metadata": {"model": "test-model", "index": i}
        }
        for i in range(1, count + 1)
    ]


def create_test_rubric():
    """Helper to create a test rubric."""
    return EvaluationRubric(
        rubric_id="test_items",
        metrics=[
            MetricDefinition(id="M1", rubric="Test mandatory", mandatory=True),
            MetricDefinition(id="C1", rubric="Test cumulative 1"),
            MetricDefinition(id="C2", rubric="Test cumulative 2"),
        ],
        passing_score_threshold=1
    )


class TestItemsManager:
    """Test the ItemsManager class."""

    def test_initialization(self):
        """Test ItemsManager initialization."""
        items = create_test_items(3)
        manager = ItemsManager(items)

        assert len(manager.items) == 3
        assert manager.assignment_mode == "sequential"
        assert manager.items_per_evaluator is None
        assert manager.allow_skip is True
        assert manager.max_skips == 3

    def test_empty_items_error(self):
        """Test that empty items list raises error."""
        with pytest.raises(ValueError, match="Items list cannot be empty"):
            ItemsManager([])

    def test_auto_id_generation(self):
        """Test automatic ID generation for items without IDs."""
        items = [
            {"prompt": "Q1", "response": "A1"},
            {"prompt": "Q2", "response": "A2"}
        ]
        manager = ItemsManager(items)

        assert manager.items[0]["id"] == "item_0000"
        assert manager.items[1]["id"] == "item_0001"

    def test_sequential_assignment(self):
        """Test sequential item assignment."""
        items = create_test_items(3)
        manager = ItemsManager(items, assignment_mode="sequential")

        # First evaluator gets items in order
        item1 = manager.get_next_item("eval_1")
        assert item1["id"] == "item_001"
        manager.mark_completed("eval_1", "item_001")

        item2 = manager.get_next_item("eval_1")
        assert item2["id"] == "item_002"
        manager.mark_completed("eval_1", "item_002")

        item3 = manager.get_next_item("eval_1")
        assert item3["id"] == "item_003"
        manager.mark_completed("eval_1", "item_003")

        # No more items
        item4 = manager.get_next_item("eval_1")
        assert item4 is None

    def test_mark_completed(self):
        """Test marking items as completed."""
        items = create_test_items(3)
        manager = ItemsManager(items)

        # Get first item
        item = manager.get_next_item("eval_1")
        assert item["id"] == "item_001"

        # Mark as completed
        manager.mark_completed("eval_1", "item_001")

        # Next item should be item_002
        next_item = manager.get_next_item("eval_1")
        assert next_item["id"] == "item_002"

        # Check progress
        progress = manager.get_progress("eval_1")
        assert progress["completed"] == 1
        assert progress["total"] == 3

    def test_skip_functionality(self):
        """Test skipping items."""
        items = create_test_items(5)
        manager = ItemsManager(items, max_skips=2)

        # Get first item
        item = manager.get_next_item("eval_1")
        assert item["id"] == "item_001"

        # Skip it
        success = manager.skip_item("eval_1", "item_001")
        assert success is True

        # Next item should be item_002
        next_item = manager.get_next_item("eval_1")
        assert next_item["id"] == "item_002"

        # Skip another
        manager.skip_item("eval_1", "item_002")

        # Should be at skip limit
        next_item = manager.get_next_item("eval_1")
        assert next_item["id"] == "item_003"

        # Try to skip again - should fail (at limit)
        success = manager.skip_item("eval_1", "item_003")
        assert success is False  # Skip limit reached

    def test_random_assignment(self):
        """Test random item assignment."""
        items = create_test_items(10)
        manager = ItemsManager(items, assignment_mode="random")

        # Get items and check they're from the pool
        seen_ids = set()
        for _ in range(5):
            item = manager.get_next_item("eval_1")
            assert item is not None
            seen_ids.add(item["id"])
            manager.mark_completed("eval_1", item["id"])

        # Should have 5 unique items
        assert len(seen_ids) == 5

    def test_round_robin_assignment(self):
        """Test round-robin assignment for multiple evaluators."""
        items = create_test_items(6)
        manager = ItemsManager(items, assignment_mode="round_robin")

        # Simulate 3 evaluators taking turns
        item_e1_1 = manager.get_next_item("eval_1")
        item_e2_1 = manager.get_next_item("eval_2")
        item_e3_1 = manager.get_next_item("eval_3")

        # Each should get different items
        assert item_e1_1["id"] != item_e2_1["id"]
        assert item_e2_1["id"] != item_e3_1["id"]
        assert item_e1_1["id"] != item_e3_1["id"]

    def test_items_per_evaluator_limit(self):
        """Test limiting items per evaluator."""
        items = create_test_items(10)
        manager = ItemsManager(items, items_per_evaluator=3)

        # Complete 3 items
        for i in range(3):
            item = manager.get_next_item("eval_1")
            assert item is not None
            manager.mark_completed("eval_1", item["id"])

        # Should get None after limit
        item = manager.get_next_item("eval_1")
        assert item is None

        # But another evaluator can still get items
        item = manager.get_next_item("eval_2")
        assert item is not None

    def test_progress_tracking(self):
        """Test progress tracking for evaluators."""
        items = create_test_items(5)
        manager = ItemsManager(items)

        # Initial progress
        progress = manager.get_progress("eval_1")
        assert progress["completed"] == 0
        assert progress["total"] == 5
        assert progress["percentage"] == 0

        # Complete some items
        item = manager.get_next_item("eval_1")
        manager.mark_completed("eval_1", item["id"])

        item = manager.get_next_item("eval_1")
        manager.mark_completed("eval_1", item["id"])

        # Check updated progress
        progress = manager.get_progress("eval_1")
        assert progress["completed"] == 2
        assert progress["percentage"] == 40.0

    def test_global_progress(self):
        """Test global progress across all evaluators."""
        items = create_test_items(6)
        manager = ItemsManager(items)

        # Multiple evaluators complete items
        item1 = manager.get_next_item("eval_1")
        manager.mark_completed("eval_1", item1["id"])

        item2 = manager.get_next_item("eval_2")
        manager.mark_completed("eval_2", item2["id"])

        item3 = manager.get_next_item("eval_1")
        manager.mark_completed("eval_1", item3["id"])

        # Check global progress
        global_progress = manager.get_global_progress()
        assert global_progress["total_items"] == 6
        assert global_progress["total_completed"] == 3
        assert global_progress["percentage"] == 50.0
        assert global_progress["active_evaluators"] == 2


class TestItemSources:
    """Test different item source implementations."""

    def test_list_item_source(self):
        """Test ListItemSource."""
        items = create_test_items(3)
        source = ListItemSource(items)

        loaded_items = source.get_items()
        assert len(loaded_items) == 3
        assert loaded_items[0]["id"] == "item_001"

    def test_file_item_source_json(self):
        """Test FileItemSource with JSON file."""
        items = create_test_items(3)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(items, f)
            temp_file = f.name

        try:
            source = FileItemSource(temp_file)
            loaded_items = source.get_items()

            assert len(loaded_items) == 3
            assert loaded_items[0]["id"] == "item_001"
            assert loaded_items[0]["prompt"] == "Test prompt 1"
        finally:
            os.unlink(temp_file)

    def test_file_item_source_csv(self):
        """Test FileItemSource with CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'prompt', 'response'])
            writer.writeheader()
            for i in range(1, 4):
                writer.writerow({
                    'id': f'item_{i:03d}',
                    'prompt': f'Question {i}',
                    'response': f'Answer {i}'
                })
            temp_file = f.name

        try:
            source = FileItemSource(temp_file)
            loaded_items = source.get_items()

            assert len(loaded_items) == 3
            assert loaded_items[0]["id"] == "item_001"
            assert loaded_items[0]["prompt"] == "Question 1"
        finally:
            os.unlink(temp_file)

    def test_file_item_source_not_found(self):
        """Test FileItemSource with non-existent file."""
        with pytest.raises(FileNotFoundError):
            FileItemSource("nonexistent.json")

    def test_file_item_source_unsupported(self):
        """Test FileItemSource with unsupported file type."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file type"):
                FileItemSource(temp_file)
        finally:
            os.unlink(temp_file)

    def test_normalize_items(self):
        """Test normalize_items function with different inputs."""
        # From list
        items_list = create_test_items(2)
        normalized = normalize_items(items_list)
        assert len(normalized) == 2

        # From ItemSource
        source = ListItemSource(items_list)
        normalized = normalize_items(source)
        assert len(normalized) == 2

        # From file path
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(items_list, f)
            temp_file = f.name

        try:
            normalized = normalize_items(temp_file)
            assert len(normalized) == 2
        finally:
            os.unlink(temp_file)

        # Invalid type
        with pytest.raises(TypeError):
            normalize_items(123)


class TestItemsWithStorage:
    """Test items functionality with storage integration."""

    def setup_method(self):
        """Set up test directory before each test."""
        self.test_dir = tempfile.mkdtemp()
        self.storage = FileBasedStorage(self.test_dir)

    def teardown_method(self):
        """Clean up test directory after each test."""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    def test_save_item_evaluation(self):
        """Test saving evaluation with item association."""
        session_id = "test_session"
        item_id = "item_001"
        evaluation_data = {
            "results": {"M1": True, "C1": True, "C2": False},
            "reasoning": {"M1": "Good"},
            "passes": True
        }
        item_content = {
            "prompt": "Test prompt",
            "response": "Test response"
        }

        result = self.storage.save_item_evaluation(
            session_id, item_id, evaluation_data, item_content
        )

        assert result["status"] == "success"
        assert result["item_id"] == item_id

        # Verify files were created
        items_dir = Path(self.test_dir) / "items" / item_id / "evaluations"
        assert items_dir.exists()
        assert len(list(items_dir.glob("*.json"))) == 1

    def test_get_item_evaluations(self):
        """Test retrieving all evaluations for an item."""
        item_id = "item_001"

        # Save evaluations from multiple sessions
        for i in range(3):
            session_id = f"session_{i}"
            evaluation_data = {
                "results": {"M1": True, "C1": i % 2 == 0},
                "session": i
            }
            self.storage.save_item_evaluation(
                session_id, item_id, evaluation_data
            )

        # Retrieve all evaluations for the item
        evaluations = self.storage.get_item_evaluations(item_id)

        assert len(evaluations) == 3
        assert all(e["item_id"] == item_id for e in evaluations)

    def test_evaluator_progress_tracking(self):
        """Test tracking evaluator progress through storage."""
        session_id = "test_session"

        # Initial progress
        progress = self.storage.get_evaluator_progress(session_id)
        assert progress["completed_items"] == []
        assert progress["total_completed"] == 0

        # Update progress
        self.storage.update_evaluator_progress(
            session_id, "item_001", "completed"
        )
        self.storage.update_evaluator_progress(
            session_id, "item_002", "skipped"
        )
        self.storage.update_evaluator_progress(
            session_id, "item_003", "current"
        )

        # Check updated progress
        progress = self.storage.get_evaluator_progress(session_id)
        assert "item_001" in progress["completed_items"]
        assert "item_002" in progress["skipped_items"]
        assert progress["current_item"] == "item_003"
        assert progress["total_completed"] == 1


class TestAppWithItems:
    """Test create_evaluation_app with items functionality."""

    def test_app_creation_with_items(self):
        """Test creating app with items enabled."""
        rubric = create_test_rubric()
        items = create_test_items(5)

        with tempfile.TemporaryDirectory() as temp_dir:
            app = create_evaluation_app(
                rubric,
                title="Test with Items",
                storage_dir=temp_dir,
                evaluation_items=items,
                assignment_mode="sequential",
                allow_skip=True
            )

            assert app is not None
            assert hasattr(app, 'routes')

            # Verify storage directory was created
            assert Path(temp_dir).exists()
            assert (Path(temp_dir) / "sessions").exists()

    def test_app_backward_compatibility(self):
        """Test that app works without items (backward compatible)."""
        rubric = create_test_rubric()

        app = create_evaluation_app(
            rubric,
            title="Test without Items"
        )

        assert app is not None
        # Should work as before without items

    def test_app_with_file_items(self):
        """Test app with items loaded from file."""
        rubric = create_test_rubric()
        items = create_test_items(3)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(items, f)
            temp_file = f.name

        try:
            app = create_evaluation_app(
                rubric,
                evaluation_items=temp_file,  # Pass file path
                assignment_mode="random"
            )

            assert app is not None
        finally:
            os.unlink(temp_file)


class TestItemsIntegration:
    """Integration tests for complete items workflow."""

    def test_full_evaluation_workflow(self):
        """Test complete evaluation workflow with items."""
        rubric = create_test_rubric()
        items = create_test_items(3)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create app with items
            app = create_evaluation_app(
                rubric,
                storage_dir=temp_dir,
                evaluation_items=items,
                items_per_evaluator=2
            )

            # Simulate evaluation workflow
            storage = FileBasedStorage(temp_dir)
            session_id = "test_evaluator"

            # Save evaluations for items
            for i in range(2):
                item_id = f"item_{i+1:03d}"
                evaluation = {
                    "results": {"M1": True, "C1": True, "C2": False},
                    "passes": True
                }

                storage.save_item_evaluation(
                    session_id, item_id, evaluation
                )

                storage.update_evaluator_progress(
                    session_id, item_id, "completed"
                )

            # Check final progress
            progress = storage.get_evaluator_progress(session_id)
            assert len(progress["completed_items"]) == 2
            assert progress["total_completed"] == 2

    def test_multi_evaluator_scenario(self):
        """Test multiple evaluators working on same item set."""
        items = create_test_items(6)
        manager = ItemsManager(items, assignment_mode="sequential")

        # Simulate 3 evaluators
        evaluators = ["alice", "bob", "carol"]

        # Each takes and completes 2 items
        completed_by = {}
        for evaluator in evaluators:
            for _ in range(2):
                item = manager.get_next_item(evaluator)
                if item:
                    manager.mark_completed(evaluator, item["id"])
                    completed_by[item["id"]] = evaluator

        # Check that all items were distributed
        assert len(completed_by) == 6

        # Check global progress
        global_progress = manager.get_global_progress()
        assert global_progress["total_completed"] == 6
        assert global_progress["active_evaluators"] == 3