"""
Item management for human evaluation queues.

This module provides classes for managing evaluation items, including
assignment strategies, progress tracking, and support for multiple item sources.
"""

from typing import List, Dict, Any, Optional, Union, Set
from abc import ABC, abstractmethod
from pathlib import Path
import json
import csv
import random
from datetime import datetime


class ItemsManager:
    """
    Manages evaluation items queue and assignments for multiple evaluators.

    Handles different assignment strategies (sequential, random, round-robin),
    tracks progress per evaluator, and supports skip functionality.

    Parameters
    ----------
    items : List[Dict[str, Any]]
        List of items to evaluate. Each item should have an 'id' field.
    assignment_mode : str, default="sequential"
        How to assign items: "sequential", "random", "round_robin", or "assigned".
    items_per_evaluator : Optional[int], default=None
        Maximum items per evaluator. None means no limit.
    allow_skip : bool, default=True
        Whether evaluators can skip items.
    max_skips : int, default=3
        Maximum number of skips allowed per evaluator.

    Attributes
    ----------
    items : List[Dict]
        All evaluation items.
    assignment_mode : str
        Current assignment strategy.
    assignments : Dict[str, List[str]]
        Tracks assigned item IDs per evaluator.
    completed : Dict[str, Set[str]]
        Tracks completed item IDs per evaluator.
    skipped : Dict[str, List[str]]
        Tracks skipped item IDs per evaluator.
    current_item : Dict[str, str]
        Current item ID per evaluator.

    Examples
    --------
    >>> items = [
    ...     {"id": "item_001", "prompt": "What is 2+2?", "response": "4"},
    ...     {"id": "item_002", "prompt": "What is 3+3?", "response": "6"}
    ... ]
    >>> manager = ItemsManager(items, assignment_mode="sequential")
    >>> next_item = manager.get_next_item("evaluator_1")
    >>> manager.mark_completed("evaluator_1", "item_001")
    """

    def __init__(
        self,
        items: List[Dict[str, Any]],
        assignment_mode: str = "sequential",
        items_per_evaluator: Optional[int] = None,
        allow_skip: bool = True,
        max_skips: int = 3
    ):
        """Initialize the items manager."""
        if not items:
            raise ValueError("Items list cannot be empty")

        # Ensure all items have IDs
        for i, item in enumerate(items):
            if "id" not in item:
                item["id"] = f"item_{i:04d}"

        self.items = items
        self.items_by_id = {item["id"]: item for item in items}
        self.assignment_mode = assignment_mode
        self.items_per_evaluator = items_per_evaluator
        self.allow_skip = allow_skip
        self.max_skips = max_skips

        # Tracking dictionaries
        self.assignments: Dict[str, List[str]] = {}
        self.completed: Dict[str, Set[str]] = {}
        self.skipped: Dict[str, List[str]] = {}
        self.current_item: Dict[str, str] = {}
        self.skip_counts: Dict[str, int] = {}

        # For round-robin assignment
        self.next_index = 0

        # Track globally completed items
        self.globally_completed: Set[str] = set()

    def get_next_item(self, evaluator_id: str) -> Optional[Dict[str, Any]]:
        """
        Get next item for evaluator based on assignment mode.

        Parameters
        ----------
        evaluator_id : str
            Unique identifier for the evaluator.

        Returns
        -------
        Optional[Dict[str, Any]]
            Next item to evaluate, or None if no items available.
        """
        # Initialize evaluator if new
        if evaluator_id not in self.assignments:
            self.assignments[evaluator_id] = []
            self.completed[evaluator_id] = set()
            self.skipped[evaluator_id] = []
            self.skip_counts[evaluator_id] = 0

        # Check if evaluator has reached item limit
        if self.items_per_evaluator:
            if len(self.completed[evaluator_id]) >= self.items_per_evaluator:
                return None

        # If there's a current item that hasn't been completed or skipped, return it
        current = self.current_item.get(evaluator_id)
        if current and current not in self.completed[evaluator_id] and current not in self.skipped.get(evaluator_id, []):
            return self.items_by_id[current].copy()

        # Get next item based on assignment mode
        if self.assignment_mode == "sequential":
            next_item_id = self._get_sequential_item(evaluator_id)
        elif self.assignment_mode == "random":
            next_item_id = self._get_random_item(evaluator_id)
        elif self.assignment_mode == "round_robin":
            next_item_id = self._get_round_robin_item(evaluator_id)
        elif self.assignment_mode == "assigned":
            next_item_id = self._get_assigned_item(evaluator_id)
        else:
            raise ValueError(f"Unknown assignment mode: {self.assignment_mode}")

        if next_item_id:
            self.current_item[evaluator_id] = next_item_id
            if next_item_id not in self.assignments[evaluator_id]:
                self.assignments[evaluator_id].append(next_item_id)
            return self.items_by_id[next_item_id].copy()

        return None

    def _get_sequential_item(self, evaluator_id: str) -> Optional[str]:
        """Get next sequential item not yet completed."""
        completed = self.completed[evaluator_id]
        skipped = self.skipped.get(evaluator_id, [])

        # Get assigned items (already in progress)
        assigned = set(self.assignments.get(evaluator_id, []))

        for item in self.items:
            item_id = item["id"]
            # Skip if already completed, globally completed, or currently skipped
            if (item_id not in completed and
                item_id not in self.globally_completed and
                item_id not in skipped):
                return item_id

        # Check skipped items if all others are done
        for item_id in self.skipped.get(evaluator_id, []):
            if item_id not in completed:
                return item_id

        return None

    def _get_random_item(self, evaluator_id: str) -> Optional[str]:
        """Get random item not yet completed."""
        completed = self.completed[evaluator_id]
        available = [
            item["id"] for item in self.items
            if item["id"] not in completed and item["id"] not in self.globally_completed
        ]

        if not available and self.skipped[evaluator_id]:
            # Try skipped items
            available = [
                item_id for item_id in self.skipped[evaluator_id]
                if item_id not in completed
            ]

        return random.choice(available) if available else None

    def _get_round_robin_item(self, evaluator_id: str) -> Optional[str]:
        """Get next item in round-robin fashion."""
        completed = self.completed[evaluator_id]

        # Start from next_index and wrap around
        start_idx = self.next_index
        checked = 0

        while checked < len(self.items):
            item = self.items[self.next_index]
            item_id = item["id"]
            self.next_index = (self.next_index + 1) % len(self.items)
            checked += 1

            if item_id not in completed and item_id not in self.globally_completed:
                return item_id

        # Check skipped items
        for item_id in self.skipped[evaluator_id]:
            if item_id not in completed:
                return item_id

        return None

    def _get_assigned_item(self, evaluator_id: str) -> Optional[str]:
        """Get pre-assigned item for evaluator."""
        # This mode requires pre-assignment setup
        # For now, fall back to sequential
        return self._get_sequential_item(evaluator_id)

    def mark_completed(self, evaluator_id: str, item_id: str):
        """
        Mark item as completed by evaluator.

        Parameters
        ----------
        evaluator_id : str
            Unique identifier for the evaluator.
        item_id : str
            ID of the completed item.
        """
        if evaluator_id not in self.completed:
            self.completed[evaluator_id] = set()

        self.completed[evaluator_id].add(item_id)

        # Add to globally completed items
        self.globally_completed.add(item_id)

        # Remove from skipped if it was there
        if evaluator_id in self.skipped and item_id in self.skipped[evaluator_id]:
            self.skipped[evaluator_id].remove(item_id)

        # Clear current item if it matches
        if self.current_item.get(evaluator_id) == item_id:
            del self.current_item[evaluator_id]

    def skip_item(self, evaluator_id: str, item_id: str, permanent: bool = False) -> bool:
        """
        Skip current item.

        Parameters
        ----------
        evaluator_id : str
            Unique identifier for the evaluator.
        item_id : str
            ID of the item to skip.
        permanent : bool, default=False
            If True, mark as permanently difficult. If False, move to end of queue.

        Returns
        -------
        bool
            True if skip was successful, False if skip limit reached.
        """
        if not self.allow_skip:
            return False

        if evaluator_id not in self.skip_counts:
            self.skip_counts[evaluator_id] = 0

        if not permanent and self.skip_counts[evaluator_id] >= self.max_skips:
            return False

        if evaluator_id not in self.skipped:
            self.skipped[evaluator_id] = []

        if item_id not in self.skipped[evaluator_id]:
            self.skipped[evaluator_id].append(item_id)
            if not permanent:
                self.skip_counts[evaluator_id] += 1

        # Clear current item
        if self.current_item.get(evaluator_id) == item_id:
            del self.current_item[evaluator_id]

        return True

    def get_progress(self, evaluator_id: str) -> Dict[str, Any]:
        """
        Get evaluator's progress statistics.

        Parameters
        ----------
        evaluator_id : str
            Unique identifier for the evaluator.

        Returns
        -------
        Dict[str, Any]
            Progress information including completed count, total items,
            skip count, and percentage complete.
        """
        if evaluator_id not in self.completed:
            self.completed[evaluator_id] = set()

        completed_count = len(self.completed[evaluator_id])
        total_items = len(self.items)

        if self.items_per_evaluator:
            total_items = min(total_items, self.items_per_evaluator)

        return {
            "completed": completed_count,
            "total": total_items,
            "skipped": len(self.skipped.get(evaluator_id, [])),
            "skip_count": self.skip_counts.get(evaluator_id, 0),
            "max_skips": self.max_skips,
            "percentage": (completed_count / total_items * 100) if total_items > 0 else 0,
            "current_item_id": self.current_item.get(evaluator_id)
        }

    def get_global_progress(self) -> Dict[str, Any]:
        """
        Get overall progress across all evaluators.

        Returns
        -------
        Dict[str, Any]
            Global progress statistics.
        """
        # Use globally_completed set for accurate count
        total_completed = len(self.globally_completed)

        return {
            "total_items": len(self.items),
            "total_completed": total_completed,
            "percentage": (total_completed / len(self.items) * 100) if self.items else 0,
            "active_evaluators": len(self.assignments),
            "items_per_evaluator": {
                eval_id: len(completed)
                for eval_id, completed in self.completed.items()
            }
        }


class ItemSource(ABC):
    """Abstract base class for different item sources."""

    @abstractmethod
    def get_items(self) -> List[Dict[str, Any]]:
        """
        Get all items for evaluation.

        Returns
        -------
        List[Dict[str, Any]]
            List of evaluation items.
        """
        pass


class ListItemSource(ItemSource):
    """
    Items from an in-memory list.

    Parameters
    ----------
    items : List[Dict[str, Any]]
        List of items to evaluate.
    """

    def __init__(self, items: List[Dict[str, Any]]):
        """Initialize with list of items."""
        self.items = items

    def get_items(self) -> List[Dict[str, Any]]:
        """Return the items list."""
        return self.items


class FileItemSource(ItemSource):
    """
    Items from a JSON or CSV file.

    Parameters
    ----------
    filepath : str or Path
        Path to the file containing items.

    Raises
    ------
    ValueError
        If file type is not supported (must be .json or .csv).
    FileNotFoundError
        If the specified file does not exist.
    """

    def __init__(self, filepath: Union[str, Path]):
        """Initialize with file path."""
        self.filepath = Path(filepath)

        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {self.filepath}")

        if self.filepath.suffix not in ['.json', '.csv']:
            raise ValueError(
                f"Unsupported file type: {self.filepath.suffix}. "
                "Supported types: .json, .csv"
            )

    def get_items(self) -> List[Dict[str, Any]]:
        """
        Load and return items from file.

        Returns
        -------
        List[Dict[str, Any]]
            Items loaded from the file.

        Raises
        ------
        json.JSONDecodeError
            If JSON file is malformed.
        csv.Error
            If CSV file is malformed.
        """
        if self.filepath.suffix == '.json':
            with open(self.filepath, 'r', encoding='utf-8') as f:
                items = json.load(f)
                if not isinstance(items, list):
                    raise ValueError(f"JSON file must contain a list of items, got {type(items)}")
                return items

        elif self.filepath.suffix == '.csv':
            with open(self.filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                items = list(reader)

                # Ensure each item has required fields
                if items and not all(key in items[0] for key in ['prompt', 'response']):
                    # Try to map common column names
                    for item in items:
                        if 'question' in item and 'prompt' not in item:
                            item['prompt'] = item['question']
                        if 'answer' in item and 'response' not in item:
                            item['response'] = item['answer']

                return items

        return []


def normalize_items(
    items: Union[List[Dict], ItemSource, str, Path]
) -> List[Dict[str, Any]]:
    """
    Normalize items from various input formats.

    Parameters
    ----------
    items : Union[List[Dict], ItemSource, str, Path]
        Items in various formats:
        - List of dicts
        - ItemSource instance
        - Path to file as string or Path object

    Returns
    -------
    List[Dict[str, Any]]
        Normalized list of items.

    Examples
    --------
    >>> # From list
    >>> items = normalize_items([{"prompt": "Q1", "response": "A1"}])
    >>>
    >>> # From file path
    >>> items = normalize_items("evaluation_items.json")
    >>>
    >>> # From ItemSource
    >>> source = FileItemSource("items.csv")
    >>> items = normalize_items(source)
    """
    if isinstance(items, list):
        return items
    elif isinstance(items, ItemSource):
        return items.get_items()
    elif isinstance(items, (str, Path)):
        source = FileItemSource(items)
        return source.get_items()
    else:
        raise TypeError(f"Unsupported items type: {type(items)}")