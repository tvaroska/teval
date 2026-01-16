"""
Unit tests for evaluation data importers.

Tests the bulk import functionality for CSV, JSON, and DataFrame formats.
"""

import json
import csv
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from teval import EvaluationRubric, MetricDefinition
from teval.human.importers import (
    ImportReport, BaseImporter, CSVImporter, JSONImporter,
    DataFrameImporter, import_evaluations
)


def _check_pandas_available():
    """Helper to check if pandas is available."""
    try:
        import pandas
        return True
    except ImportError:
        return False


# Fixtures for testing
@pytest.fixture
def sample_rubric():
    """Create a sample rubric for testing."""
    return EvaluationRubric(
        rubric_id="test_rubric",
        metrics=[
            MetricDefinition(id="M1", rubric="Mandatory metric 1", mandatory=True),
            MetricDefinition(id="M2", rubric="Mandatory metric 2", mandatory=True),
            MetricDefinition(id="C1", rubric="Cumulative metric 1"),
            MetricDefinition(id="C2", rubric="Cumulative metric 2"),
            MetricDefinition(id="C3", rubric="Cumulative metric 3"),
        ],
        passing_score_threshold=2
    )


@pytest.fixture
def simple_rubric():
    """Create a simple rubric with minimal metrics."""
    return EvaluationRubric(
        rubric_id="simple",
        metrics=[
            MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
            MetricDefinition(id="C1", rubric="Quality check")
        ],
        passing_score_threshold=1
    )


class TestImportReport:
    """Test the ImportReport class."""

    def test_report_initialization(self):
        """Test report initializes with correct defaults."""
        report = ImportReport()
        assert report.success_count == 0
        assert report.failure_count == 0
        assert report.total_count == 0
        assert report.warnings == []
        assert report.errors == []
        assert report.skipped_items == []

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        report = ImportReport()
        assert report.success_rate == 0.0  # No items

        report.total_count = 10
        report.success_count = 8
        assert report.success_rate == 0.8

        report.total_count = 100
        report.success_count = 100
        assert report.success_rate == 1.0

    def test_add_warning(self):
        """Test adding warnings to report."""
        report = ImportReport()
        report.add_warning("Missing field X")
        report.add_warning("Invalid value Y")

        assert len(report.warnings) == 2
        assert "Missing field X" in report.warnings
        assert "Invalid value Y" in report.warnings

    def test_add_error_without_item(self):
        """Test adding errors without item data."""
        report = ImportReport()
        report.add_error("Parse error")

        assert len(report.errors) == 1
        assert "Parse error" in report.errors
        assert len(report.skipped_items) == 0

    def test_add_error_with_item(self):
        """Test adding errors with item data."""
        report = ImportReport()
        item_data = {"item_id": "test_001", "M1": "invalid"}
        report.add_error("Invalid boolean value", item_data)

        assert len(report.errors) == 1
        assert len(report.skipped_items) == 1
        assert report.skipped_items[0]["item_id"] == "test_001"

    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = ImportReport()
        report.success_count = 5
        report.failure_count = 2
        report.total_count = 7
        report.add_warning("Test warning")

        result = report.to_dict()

        assert result["success_count"] == 5
        assert result["failure_count"] == 2
        assert result["total_count"] == 7
        assert result["success_rate"] == 5/7
        assert "Test warning" in result["warnings"]


class TestBaseImporter:
    """Test the BaseImporter abstract class."""

    def test_parse_boolean_true_values(self, sample_rubric):
        """Test parsing various true boolean representations."""
        class TestImporter(BaseImporter):
            def _load_data(self, source):
                return []

        importer = TestImporter(sample_rubric)

        # Test true values
        assert importer._parse_boolean(True) is True
        assert importer._parse_boolean("true") is True
        assert importer._parse_boolean("True") is True
        assert importer._parse_boolean("TRUE") is True
        assert importer._parse_boolean("yes") is True
        assert importer._parse_boolean("Yes") is True
        assert importer._parse_boolean("y") is True
        assert importer._parse_boolean("Y") is True
        assert importer._parse_boolean("1") is True
        assert importer._parse_boolean(1) is True
        assert importer._parse_boolean(1.0) is True

    def test_parse_boolean_false_values(self, sample_rubric):
        """Test parsing various false boolean representations."""
        class TestImporter(BaseImporter):
            def _load_data(self, source):
                return []

        importer = TestImporter(sample_rubric)

        # Test false values
        assert importer._parse_boolean(False) is False
        assert importer._parse_boolean("false") is False
        assert importer._parse_boolean("False") is False
        assert importer._parse_boolean("FALSE") is False
        assert importer._parse_boolean("no") is False
        assert importer._parse_boolean("No") is False
        assert importer._parse_boolean("n") is False
        assert importer._parse_boolean("N") is False
        assert importer._parse_boolean("0") is False
        assert importer._parse_boolean(0) is False
        assert importer._parse_boolean(0.0) is False

    def test_parse_boolean_invalid_values(self, sample_rubric):
        """Test parsing invalid/missing values defaults to False."""
        class TestImporter(BaseImporter):
            def _load_data(self, source):
                return []

        importer = TestImporter(sample_rubric)

        # Test invalid/missing values
        assert importer._parse_boolean(None) is False
        assert importer._parse_boolean("") is False
        assert importer._parse_boolean("maybe") is False
        assert importer._parse_boolean("unknown") is False
        assert importer._parse_boolean([]) is False
        assert importer._parse_boolean({}) is False

    def test_validate_and_convert_complete_data(self, sample_rubric):
        """Test validation and conversion with complete data."""
        class TestImporter(BaseImporter):
            def _load_data(self, source):
                return []

        importer = TestImporter(sample_rubric)

        item_data = {
            "item_id": "test_001",
            "M1": "true",
            "M2": "true",
            "C1": "true",
            "C2": "true",
            "C3": "false",
            "M1_reasoning": "Looks good",
            "C1_reasoning": "High quality",
            "context": "Test context"
        }

        result = importer._validate_and_convert(item_data)

        assert result["rubric_id"] == "test_rubric"
        assert result["results"]["M1"] is True
        assert result["results"]["M2"] is True
        assert result["results"]["C1"] is True
        assert result["results"]["C2"] is True
        assert result["results"]["C3"] is False
        assert result["reasoning"]["M1"] == "Looks good"
        assert result["reasoning"]["C1"] == "High quality"
        assert result["mandatory_pass"] is True
        assert result["score"] == 2  # C1 and C2 pass
        assert result["total"] == 3  # 3 cumulative metrics
        assert result["passes"] is True
        assert result["item_id"] == "test_001"
        assert result["metadata"]["context"] == "Test context"
        assert "timestamp" in result

    def test_validate_and_convert_missing_metrics(self, sample_rubric):
        """Test validation with missing metrics defaults to False."""
        class TestImporter(BaseImporter):
            def _load_data(self, source):
                return []

        importer = TestImporter(sample_rubric)

        # Missing M2 and C2
        item_data = {
            "item_id": "test_002",
            "M1": "true",
            "C1": "true",
            "C3": "true"
        }

        result = importer._validate_and_convert(item_data)

        assert result["results"]["M1"] is True
        assert result["results"]["M2"] is False  # Missing -> False
        assert result["results"]["C1"] is True
        assert result["results"]["C2"] is False  # Missing -> False
        assert result["results"]["C3"] is True
        assert result["mandatory_pass"] is False  # M2 is False
        assert result["passes"] is False
        assert len(importer.report.warnings) == 2  # Warnings for missing metrics

    def test_validate_and_convert_mandatory_failure(self, sample_rubric):
        """Test that mandatory failure causes overall failure."""
        class TestImporter(BaseImporter):
            def _load_data(self, source):
                return []

        importer = TestImporter(sample_rubric)

        item_data = {
            "M1": "false",  # Mandatory fail
            "M2": "true",
            "C1": "true",
            "C2": "true",
            "C3": "true"
        }

        result = importer._validate_and_convert(item_data)

        assert result["mandatory_pass"] is False
        assert result["score"] == 3  # All cumulative pass
        assert result["passes"] is False  # Overall fail due to mandatory

    def test_validate_and_convert_threshold_not_met(self, sample_rubric):
        """Test that not meeting threshold causes failure."""
        class TestImporter(BaseImporter):
            def _load_data(self, source):
                return []

        importer = TestImporter(sample_rubric)

        item_data = {
            "M1": "true",
            "M2": "true",
            "C1": "true",
            "C2": "false",
            "C3": "false"  # Only 1 cumulative passes, need 2
        }

        result = importer._validate_and_convert(item_data)

        assert result["mandatory_pass"] is True
        assert result["score"] == 1
        assert result["passes"] is False  # Doesn't meet threshold


class TestCSVImporter:
    """Test the CSVImporter class."""

    def test_import_valid_csv(self, sample_rubric, tmp_path):
        """Test importing a valid CSV file."""
        # Create a test CSV file
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["item_id", "M1", "M2", "C1", "C2", "C3", "M1_reasoning"])
            writer.writerow(["item_001", "true", "true", "true", "true", "false", "Good"])
            writer.writerow(["item_002", "false", "true", "yes", "no", "1", "Failed"])

        importer = CSVImporter(sample_rubric)
        results, report = importer.import_data(csv_file)

        assert len(results) == 2
        assert report.success_count == 2
        assert report.failure_count == 0

        # Check first item
        assert results[0]["item_id"] == "item_001"
        assert results[0]["results"]["M1"] is True
        assert results[0]["passes"] is True

        # Check second item
        assert results[1]["item_id"] == "item_002"
        assert results[1]["results"]["M1"] is False
        assert results[1]["passes"] is False

    def test_import_csv_with_missing_columns(self, sample_rubric, tmp_path):
        """Test importing CSV with missing metric columns."""
        csv_file = tmp_path / "incomplete.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["item_id", "M1", "C1"])  # Missing M2, C2, C3
            writer.writerow(["item_001", "true", "true"])

        importer = CSVImporter(sample_rubric)
        results, report = importer.import_data(csv_file)

        assert len(results) == 1
        assert results[0]["results"]["M2"] is False  # Missing defaults to False
        assert results[0]["passes"] is False  # M2 mandatory failed
        assert len(report.warnings) > 0  # Should have warnings about missing metrics

    def test_import_csv_with_different_delimiter(self, sample_rubric, tmp_path):
        """Test importing CSV with tab delimiter."""
        csv_file = tmp_path / "tab_delimited.tsv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["item_id", "M1", "M2", "C1", "C2", "C3"])
            writer.writerow(["item_001", "true", "true", "true", "true", "true"])

        importer = CSVImporter(sample_rubric, delimiter="\t")
        results, report = importer.import_data(csv_file)

        assert len(results) == 1
        assert results[0]["passes"] is True

    def test_import_csv_auto_detect_delimiter(self, sample_rubric, tmp_path):
        """Test auto-detection of CSV delimiter."""
        # Test with semicolon delimiter
        csv_file = tmp_path / "semicolon.csv"
        with open(csv_file, "w", newline="") as f:
            f.write("item_id;M1;M2;C1;C2;C3\n")
            f.write("item_001;true;true;true;true;false\n")

        importer = CSVImporter(sample_rubric)  # No delimiter specified
        results, report = importer.import_data(csv_file)

        assert len(results) == 1
        assert results[0]["item_id"] == "item_001"

    def test_import_csv_with_empty_values(self, sample_rubric, tmp_path):
        """Test handling empty values in CSV."""
        csv_file = tmp_path / "empty_values.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["item_id", "M1", "M2", "C1", "C2", "C3", "M1_reasoning"])
            writer.writerow(["item_001", "", "true", "", "", "", ""])  # Empty values

        importer = CSVImporter(sample_rubric)
        results, report = importer.import_data(csv_file)

        assert len(results) == 1
        assert results[0]["results"]["M1"] is False  # Empty -> False
        assert results[0]["reasoning"] == {}  # Empty reasoning ignored

    def test_import_nonexistent_csv(self, sample_rubric):
        """Test error handling for nonexistent file."""
        importer = CSVImporter(sample_rubric)
        results, report = importer.import_data("nonexistent.csv")

        assert len(results) == 0
        assert report.failure_count == 0
        assert len(report.errors) > 0
        assert "not found" in report.errors[0]


class TestJSONImporter:
    """Test the JSONImporter class."""

    def test_import_json_array(self, sample_rubric, tmp_path):
        """Test importing JSON array format."""
        json_file = tmp_path / "array.json"
        data = [
            {
                "item_id": "item_001",
                "M1": True,
                "M2": True,
                "C1": True,
                "C2": False,
                "C3": False,
                "M1_reasoning": "Perfect"
            },
            {
                "item_id": "item_002",
                "M1": False,
                "M2": True,
                "C1": True,
                "C2": True,
                "C3": True
            }
        ]
        with open(json_file, "w") as f:
            json.dump(data, f)

        importer = JSONImporter(sample_rubric)
        results, report = importer.import_data(json_file)

        assert len(results) == 2
        assert report.success_count == 2
        assert results[0]["item_id"] == "item_001"
        assert results[0]["reasoning"]["M1"] == "Perfect"

    def test_import_json_nested_format(self, sample_rubric, tmp_path):
        """Test importing nested JSON format."""
        json_file = tmp_path / "nested.json"
        data = {
            "evaluations": [
                {
                    "item_id": "item_001",
                    "results": {
                        "M1": True,
                        "M2": True,
                        "C1": False,
                        "C2": True,
                        "C3": False
                    },
                    "reasoning": {
                        "M1": "Good",
                        "C2": "Excellent"
                    },
                    "metadata": {
                        "evaluator": "user1",
                        "timestamp": "2024-01-01"
                    }
                }
            ]
        }
        with open(json_file, "w") as f:
            json.dump(data, f)

        importer = JSONImporter(sample_rubric)
        results, report = importer.import_data(json_file)

        assert len(results) == 1
        assert results[0]["results"]["M1"] is True
        assert results[0]["results"]["C1"] is False
        assert results[0]["reasoning"]["M1"] == "Good"
        assert results[0]["metadata"]["evaluator"] == "user1"

    def test_import_json_string(self, sample_rubric):
        """Test importing from JSON string."""
        json_string = json.dumps([
            {"item_id": "1", "M1": True, "M2": True, "C1": True, "C2": True, "C3": False}
        ])

        importer = JSONImporter(sample_rubric)
        results, report = importer.import_data(json_string)

        assert len(results) == 1
        assert results[0]["item_id"] == "1"
        assert results[0]["passes"] is True

    def test_import_json_single_object(self, sample_rubric):
        """Test importing single JSON object (not array)."""
        json_data = {
            "item_id": "single",
            "M1": True,
            "M2": True,
            "C1": True,
            "C2": True,
            "C3": True
        }

        importer = JSONImporter(sample_rubric)
        results, report = importer.import_data(json_data)

        assert len(results) == 1
        assert results[0]["item_id"] == "single"

    def test_import_json_with_wrapper_keys(self, sample_rubric):
        """Test importing JSON with different wrapper keys."""
        # Test "items" wrapper
        data1 = {"items": [{"M1": True, "M2": True, "C1": True, "C2": True, "C3": False}]}
        importer = JSONImporter(sample_rubric)
        results1, _ = importer.import_data(data1)
        assert len(results1) == 1

        # Test "data" wrapper
        data2 = {"data": [{"M1": True, "M2": True, "C1": True, "C2": True, "C3": False}]}
        results2, _ = importer.import_data(data2)
        assert len(results2) == 1

    def test_import_invalid_json_string(self, sample_rubric):
        """Test error handling for invalid JSON."""
        importer = JSONImporter(sample_rubric)
        results, report = importer.import_data("{invalid json}")

        assert len(results) == 0
        assert len(report.errors) > 0
        assert "Invalid JSON" in report.errors[0]


class TestDataFrameImporter:
    """Test the DataFrameImporter class."""

    @pytest.mark.skipif(
        not pytest.importorskip("pandas"),
        reason="Pandas not installed"
    )
    def test_import_dataframe(self, sample_rubric):
        """Test importing from pandas DataFrame."""
        import pandas as pd

        df = pd.DataFrame({
            "item_id": ["item_001", "item_002", "item_003"],
            "M1": [True, False, True],
            "M2": [True, True, True],
            "C1": [1, 0, 1],  # Integer representation
            "C2": [0, 1, 1],
            "C3": [False, False, True],
            "M1_reasoning": ["Good", "Failed", None]
        })

        importer = DataFrameImporter(sample_rubric)
        results, report = importer.import_data(df)

        assert len(results) == 3
        assert report.success_count == 3

        # Check conversions
        assert results[0]["results"]["C1"] is True  # 1 -> True
        assert results[1]["results"]["C1"] is False  # 0 -> False
        assert results[2]["reasoning"].get("M1") is None  # None reasoning ignored

    @pytest.mark.skipif(
        not pytest.importorskip("pandas"),
        reason="Pandas not installed"
    )
    def test_import_dataframe_with_na_values(self, sample_rubric):
        """Test handling of pandas NA values."""
        import pandas as pd
        import numpy as np

        df = pd.DataFrame({
            "item_id": ["item_001"],
            "M1": [True],
            "M2": [pd.NA],  # pandas NA
            "C1": [np.nan],  # numpy NaN
            "C2": [None],  # Python None
            "C3": [True]
        })

        importer = DataFrameImporter(sample_rubric)
        results, report = importer.import_data(df)

        assert len(results) == 1
        assert results[0]["results"]["M2"] is False  # NA -> False
        assert results[0]["results"]["C1"] is False  # NaN -> False
        assert results[0]["results"]["C2"] is False  # None -> False

    @pytest.mark.skipif(
        not pytest.importorskip("pandas"),
        reason="Pandas not installed"
    )
    def test_import_dataframe_with_multiindex(self, sample_rubric):
        """Test handling of multi-index DataFrames."""
        import pandas as pd

        # Create multi-index DataFrame
        index = pd.MultiIndex.from_tuples(
            [("group1", "item_001"), ("group1", "item_002")],
            names=["group", "item_id"]
        )
        df = pd.DataFrame({
            "M1": [True, False],
            "M2": [True, True],
            "C1": [True, True],
            "C2": [False, True],
            "C3": [False, True]
        }, index=index)

        importer = DataFrameImporter(sample_rubric)
        results, report = importer.import_data(df)

        assert len(results) == 2
        assert "item_id" in results[0]  # Index should be converted to column

    def test_import_invalid_dataframe(self, sample_rubric):
        """Test error handling for non-DataFrame input."""
        importer = DataFrameImporter(sample_rubric)
        results, report = importer.import_data({"not": "a dataframe"})

        assert len(results) == 0
        assert len(report.errors) > 0

    @pytest.mark.skipif(
        "pandas" in sys.modules or _check_pandas_available(),
        reason="Pandas is installed"
    )
    def test_import_dataframe_without_pandas(self, sample_rubric):
        """Test error when pandas is not installed."""
        importer = DataFrameImporter(sample_rubric)

        with pytest.raises(ImportError, match="Pandas is required"):
            importer._load_data([])


class TestImportEvaluationsFunction:
    """Test the main import_evaluations function."""

    def test_auto_detect_csv(self, simple_rubric, tmp_path):
        """Test auto-detection of CSV format."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["M1", "C1"])
            writer.writerow(["true", "true"])

        results, report = import_evaluations(csv_file, simple_rubric)

        assert len(results) == 1
        assert results[0]["passes"] is True

    def test_auto_detect_json_file(self, simple_rubric, tmp_path):
        """Test auto-detection of JSON file format."""
        json_file = tmp_path / "test.json"
        with open(json_file, "w") as f:
            json.dump([{"M1": True, "C1": True}], f)

        results, report = import_evaluations(json_file, simple_rubric)

        assert len(results) == 1
        assert results[0]["passes"] is True

    def test_auto_detect_json_string(self, simple_rubric):
        """Test auto-detection of JSON string format."""
        json_string = '[{"M1": true, "C1": false}]'
        results, report = import_evaluations(json_string, simple_rubric)

        assert len(results) == 1
        assert results[0]["results"]["C1"] is False

    def test_auto_detect_json_object(self, simple_rubric):
        """Test auto-detection of dict/list as JSON."""
        data = [{"M1": True, "C1": True}]
        results, report = import_evaluations(data, simple_rubric)

        assert len(results) == 1

    @pytest.mark.skipif(
        not pytest.importorskip("pandas"),
        reason="Pandas not installed"
    )
    def test_auto_detect_dataframe(self, simple_rubric):
        """Test auto-detection of DataFrame."""
        import pandas as pd

        df = pd.DataFrame({"M1": [True], "C1": [True]})
        results, report = import_evaluations(df, simple_rubric)

        assert len(results) == 1

    def test_explicit_format_override(self, simple_rubric):
        """Test explicit format specification overrides auto-detection."""
        # JSON data but specify CSV format (will fail)
        json_data = [{"M1": True, "C1": True}]

        # This should fail because we're forcing CSV format on JSON data
        results, report = import_evaluations(
            json_data,
            simple_rubric,
            format="csv"
        )

        assert len(report.errors) > 0

    def test_unsupported_format(self, simple_rubric):
        """Test error for unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            import_evaluations("data.txt", simple_rubric, format="xml")

    def test_cannot_detect_format(self, simple_rubric):
        """Test error when format cannot be detected."""
        with pytest.raises(ValueError, match="Could not detect format"):
            import_evaluations(12345, simple_rubric)  # Integer input

    def test_kwargs_passed_to_importer(self, simple_rubric, tmp_path):
        """Test that kwargs are passed to specific importer."""
        csv_file = tmp_path / "semicolon.csv"
        with open(csv_file, "w") as f:
            f.write("M1;C1\n")
            f.write("true;true\n")

        # Pass delimiter kwarg to CSVImporter
        results, report = import_evaluations(
            csv_file,
            simple_rubric,
            format="csv",
            delimiter=";"
        )

        assert len(results) == 1
        assert results[0]["passes"] is True


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def test_large_batch_import(self, sample_rubric, tmp_path):
        """Test importing a large batch of evaluations."""
        csv_file = tmp_path / "large_batch.csv"

        # Create CSV with 1000 rows
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["item_id", "M1", "M2", "C1", "C2", "C3"])

            for i in range(1000):
                writer.writerow([
                    f"item_{i:04d}",
                    "true" if i % 2 == 0 else "false",
                    "true",
                    "true" if i % 3 == 0 else "false",
                    "true" if i % 5 == 0 else "false",
                    "false"
                ])

        results, report = import_evaluations(csv_file, sample_rubric)

        assert len(results) == 1000
        assert report.total_count == 1000
        assert report.success_count == 1000

    def test_mixed_valid_invalid_data(self, sample_rubric, tmp_path):
        """Test batch with mix of valid and invalid data."""
        json_file = tmp_path / "mixed.json"
        data = [
            {"item_id": "valid_1", "M1": True, "M2": True, "C1": True, "C2": True, "C3": False},
            {"item_id": "missing", "M1": True},  # Missing M2 mandatory
            {"item_id": "valid_2", "M1": True, "M2": True, "C1": False, "C2": False, "C3": False},
            {"item_id": "invalid", "M1": "maybe", "M2": "unknown"},  # Invalid values
        ]
        with open(json_file, "w") as f:
            json.dump(data, f)

        results, report = import_evaluations(json_file, sample_rubric)

        assert len(results) == 4  # All imported with best-effort
        assert report.warnings  # Should have warnings about missing/invalid data

        # Check specific items
        valid_items = [r for r in results if r["passes"]]
        assert len(valid_items) == 1  # Only first item fully passes

    def test_unicode_and_special_characters(self, simple_rubric, tmp_path):
        """Test handling of unicode and special characters."""
        csv_file = tmp_path / "unicode.csv"
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["item_id", "M1", "C1", "M1_reasoning"])
            writer.writerow(["item_🚀", "true", "true", "Excellent résumé! 你好"])
            writer.writerow(["item_002", "true", "false", "Contains\nnewline"])

        results, report = import_evaluations(csv_file, simple_rubric)

        assert len(results) == 2
        assert results[0]["item_id"] == "item_🚀"
        assert results[0]["reasoning"]["M1"] == "Excellent résumé! 你好"
        assert "newline" in results[1]["reasoning"]["M1"]

    def test_real_world_workflow(self, sample_rubric, tmp_path):
        """Test a complete real-world workflow."""
        # Step 1: Import from CSV
        csv_file = tmp_path / "batch1.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["item_id", "M1", "M2", "C1", "C2", "C3"])
            writer.writerow(["prompt_001", "yes", "yes", "no", "yes", "no"])
            writer.writerow(["prompt_002", "1", "1", "1", "0", "1"])

        results1, report1 = import_evaluations(csv_file, sample_rubric)

        # Step 2: Import from JSON
        json_data = {
            "evaluations": [
                {
                    "item_id": "prompt_003",
                    "results": {"M1": True, "M2": True, "C1": True, "C2": True, "C3": False}
                }
            ]
        }
        results2, report2 = import_evaluations(json_data, sample_rubric, format="json")

        # Step 3: Combine results
        all_results = results1 + results2

        assert len(all_results) == 3
        assert all(r["rubric_id"] == "test_rubric" for r in all_results)

        # Step 4: Filter passing evaluations
        passing = [r for r in all_results if r["passes"]]
        assert len(passing) == 2  # prompt_002 and prompt_003 pass

        # Step 5: Export summary
        summary = {
            "total_evaluations": len(all_results),
            "passing_evaluations": len(passing),
            "success_rate": len(passing) / len(all_results),
            "items": [r["item_id"] for r in all_results]
        }

        assert summary["success_rate"] == 2/3