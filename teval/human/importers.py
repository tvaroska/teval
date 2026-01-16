"""
Bulk import utilities for human evaluation data.

This module provides importers for converting evaluation data from various
formats (CSV, JSON, Pandas DataFrame) into the teval evaluation format.
Focuses on batch preparation for evaluation workflows.

The importers follow a best-effort approach: invalid or missing data is
handled gracefully with defaults (False for missing metrics) and detailed
reporting of any issues encountered during import.

Classes
-------
ImportReport
    Report containing statistics and issues from an import operation.
BaseImporter
    Abstract base class for format-specific importers.
CSVImporter
    Import evaluations from CSV files.
JSONImporter
    Import evaluations from JSON files or strings.
DataFrameImporter
    Import evaluations from Pandas DataFrames.

Functions
---------
import_evaluations
    Main entry point for importing evaluation data.

Examples
--------
Import from CSV file:

>>> from teval import EvaluationRubric, MetricDefinition
>>> from teval.human.importers import import_evaluations
>>>
>>> rubric = EvaluationRubric(
...     rubric_id="test",
...     metrics=[
...         MetricDefinition(id="M1", rubric="Required", mandatory=True),
...         MetricDefinition(id="C1", rubric="Quality")
...     ],
...     passing_score_threshold=1
... )
>>>
>>> results, report = import_evaluations("evaluations.csv", rubric)
>>> print(f"Imported {report.success_count} evaluations")

Import from DataFrame:

>>> import pandas as pd
>>> df = pd.DataFrame({
...     "item_id": ["item1", "item2"],
...     "M1": [True, False],
...     "C1": [True, True],
...     "M1_reasoning": ["Good", "Failed"]
... })
>>> results, report = import_evaluations(df, rubric, format="dataframe")

Notes
-----
The importers are designed to be flexible and handle various data formats:
- Boolean values: true/false, 1/0, yes/no, True/False
- Missing values: treated as False for metrics
- Reasoning fields: optional, suffix with "_reasoning"
- Metadata: additional columns preserved in output
"""

import csv
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from teval.metrics import EvaluationRubric


@dataclass
class ImportReport:
    """
    Report containing statistics and issues from an import operation.

    Attributes
    ----------
    success_count : int
        Number of successfully imported evaluations.
    failure_count : int
        Number of evaluations that failed to import.
    total_count : int
        Total number of evaluations processed.
    warnings : List[str]
        List of warning messages.
    errors : List[str]
        List of error messages.
    skipped_items : List[Dict[str, Any]]
        Details of items that were skipped due to errors.

    Methods
    -------
    add_warning(message)
        Add a warning message to the report.
    add_error(message, item_data)
        Add an error message with associated item data.
    to_dict()
        Convert report to dictionary format.

    Examples
    --------
    >>> report = ImportReport()
    >>> report.add_warning("Missing reasoning field for C1")
    >>> report.success_count = 10
    >>> print(f"Success rate: {report.success_rate:.1%}")
    Success rate: 100.0%
    """
    success_count: int = 0
    failure_count: int = 0
    total_count: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    skipped_items: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count

    def add_warning(self, message: str) -> None:
        """Add a warning message to the report."""
        self.warnings.append(message)

    def add_error(self, message: str, item_data: Optional[Dict[str, Any]] = None) -> None:
        """Add an error message with optional associated item data."""
        self.errors.append(message)
        if item_data:
            self.skipped_items.append(item_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary format."""
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_count": self.total_count,
            "success_rate": self.success_rate,
            "warnings": self.warnings,
            "errors": self.errors,
            "skipped_items": self.skipped_items
        }


class BaseImporter(ABC):
    """
    Abstract base class for evaluation data importers.

    Provides common functionality for validating and processing evaluation
    data from various formats. Subclasses must implement the _load_data
    method to handle format-specific loading.

    Parameters
    ----------
    rubric : EvaluationRubric
        The evaluation rubric to validate against.

    Attributes
    ----------
    rubric : EvaluationRubric
        The evaluation rubric.
    metric_ids : set
        Set of valid metric IDs from the rubric.
    report : ImportReport
        Report tracking import statistics and issues.

    Methods
    -------
    import_data(source)
        Import evaluations from the given source.
    _load_data(source)
        Abstract method to load data from source (format-specific).
    _process_item(item_data)
        Process a single evaluation item.
    _parse_boolean(value)
        Parse various boolean representations.
    _validate_and_convert(item_data)
        Validate and convert item data to evaluation format.
    """

    def __init__(self, rubric: EvaluationRubric):
        """Initialize the importer with a rubric."""
        self.rubric = rubric
        self.metric_ids = {metric.id for metric in rubric.metrics}
        self.report = ImportReport()

    @abstractmethod
    def _load_data(self, source: Any) -> List[Dict[str, Any]]:
        """
        Load data from the source into a list of dictionaries.

        Parameters
        ----------
        source : Any
            The data source (file path, string, DataFrame, etc.).

        Returns
        -------
        List[Dict[str, Any]]
            List of item dictionaries to process.

        Raises
        ------
        ValueError
            If the source data cannot be loaded.
        """
        pass

    def import_data(self, source: Any) -> Tuple[List[Dict[str, Any]], ImportReport]:
        """
        Import evaluations from the given source.

        Parameters
        ----------
        source : Any
            The data source to import from.

        Returns
        -------
        Tuple[List[Dict[str, Any]], ImportReport]
            Tuple of (processed evaluations list, import report).

        Examples
        --------
        >>> importer = CSVImporter(rubric)
        >>> results, report = importer.import_data("evaluations.csv")
        >>> print(f"Imported {len(results)} evaluations")
        """
        self.report = ImportReport()  # Reset report for each import
        results = []

        try:
            items = self._load_data(source)
            self.report.total_count = len(items)

            for item_data in items:
                try:
                    processed = self._process_item(item_data)
                    if processed:
                        results.append(processed)
                        self.report.success_count += 1
                    else:
                        self.report.failure_count += 1
                except Exception as e:
                    self.report.failure_count += 1
                    self.report.add_error(
                        f"Failed to process item: {str(e)}",
                        item_data
                    )

        except Exception as e:
            self.report.add_error(f"Failed to load data: {str(e)}")

        return results, self.report

    def _process_item(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single evaluation item.

        Parameters
        ----------
        item_data : Dict[str, Any]
            Raw item data from the source.

        Returns
        -------
        Optional[Dict[str, Any]]
            Processed evaluation in standard format, or None if failed.
        """
        return self._validate_and_convert(item_data)

    def _parse_boolean(self, value: Any) -> bool:
        """
        Parse various boolean representations.

        Parameters
        ----------
        value : Any
            Value to parse as boolean.

        Returns
        -------
        bool
            Parsed boolean value.

        Notes
        -----
        Handles: true/false, True/False, 1/0, yes/no, y/n.
        Returns False for None, empty string, or unrecognized values.
        """
        if value is None or value == "":
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        if isinstance(value, str):
            lower = value.lower().strip()
            if lower in ("true", "yes", "y", "1"):
                return True
            elif lower in ("false", "no", "n", "0"):
                return False

        # Default to False for unrecognized values
        return False

    def _validate_and_convert(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and convert item data to evaluation format.

        Parameters
        ----------
        item_data : Dict[str, Any]
            Raw item data to validate and convert.

        Returns
        -------
        Dict[str, Any]
            Converted evaluation in standard format.

        Notes
        -----
        Format matches EvaluationForm.process_submission() output:
        - rubric_id: The rubric identifier
        - results: Dict of metric pass/fail values
        - reasoning: Dict of optional reasoning text
        - mandatory_pass: Whether all mandatory metrics passed
        - score: Number of passed cumulative metrics
        - total: Total number of cumulative metrics
        - passes: Overall pass/fail status
        - timestamp: ISO format timestamp
        - item_id: Item identifier (if present)
        """
        results = {}
        reasoning = {}

        # Extract metric results
        for metric_id in self.metric_ids:
            if metric_id in item_data:
                results[metric_id] = self._parse_boolean(item_data[metric_id])
            else:
                # Best-effort: default missing metrics to False
                results[metric_id] = False
                self.report.add_warning(
                    f"Missing metric '{metric_id}' for item, defaulting to False"
                )

        # Extract reasoning fields (format: {metric_id}_reasoning)
        for key, value in item_data.items():
            if key.endswith("_reasoning"):
                metric_id = key[:-10]  # Remove "_reasoning" suffix
                if metric_id in self.metric_ids and value:
                    reasoning[metric_id] = str(value)

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

        # Build output format
        output = {
            "rubric_id": self.rubric.rubric_id,
            "results": results,
            "reasoning": reasoning,
            "mandatory_pass": mandatory_pass,
            "score": cumulative_score,
            "total": len(self.rubric.cumulative_metrics),
            "passes": passes,
            "timestamp": datetime.now().isoformat()
        }

        # Preserve item_id if present
        if "item_id" in item_data:
            output["item_id"] = str(item_data["item_id"])

        # Preserve additional metadata
        # If metadata is already a dict, use it directly
        if "metadata" in item_data and isinstance(item_data["metadata"], dict):
            output["metadata"] = item_data["metadata"]
        else:
            # Collect other metadata fields
            metadata_keys = set(item_data.keys()) - set(results.keys()) - {
                k + "_reasoning" for k in results.keys()
            } - {"item_id", "metadata"}

            if metadata_keys:
                output["metadata"] = {
                    key: item_data[key]
                    for key in metadata_keys
                    if item_data[key] is not None
                }

        return output


class CSVImporter(BaseImporter):
    """
    Import evaluations from CSV files.

    Handles CSV files with columns for metrics and optional reasoning.
    Supports various delimiters and boolean representations.

    Parameters
    ----------
    rubric : EvaluationRubric
        The evaluation rubric to validate against.
    delimiter : str, optional
        CSV delimiter. If None, will auto-detect.
    encoding : str, default="utf-8"
        File encoding.

    Examples
    --------
    >>> importer = CSVImporter(rubric)
    >>> results, report = importer.import_data("evaluations.csv")

    CSV format:
    ```
    item_id,M1,M2,C1,C2,M1_reasoning
    item_001,true,true,false,true,"Meets requirement"
    item_002,false,true,true,false,"Failed validation"
    ```
    """

    def __init__(self, rubric: EvaluationRubric, delimiter: Optional[str] = None,
                 encoding: str = "utf-8"):
        """Initialize CSV importer."""
        super().__init__(rubric)
        self.delimiter = delimiter
        self.encoding = encoding

    def _detect_delimiter(self, sample: str) -> str:
        """Auto-detect CSV delimiter from sample text."""
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
        except csv.Error:
            # Default to comma if detection fails
            return ","

    def _load_data(self, source: Union[str, Path]) -> List[Dict[str, Any]]:
        """Load data from CSV file."""
        path = Path(source)
        if not path.exists():
            raise ValueError(f"CSV file not found: {path}")

        items = []

        with open(path, "r", encoding=self.encoding, newline="") as f:
            # Auto-detect delimiter if not specified
            if self.delimiter is None:
                sample = f.read(1024)
                f.seek(0)
                self.delimiter = self._detect_delimiter(sample)

            reader = csv.DictReader(f, delimiter=self.delimiter)

            for row in reader:
                # Remove empty string values (treat as None)
                cleaned_row = {
                    k: v if v != "" else None
                    for k, v in row.items()
                }
                items.append(cleaned_row)

        return items


class JSONImporter(BaseImporter):
    """
    Import evaluations from JSON files or strings.

    Handles both flat and nested JSON structures. Supports arrays of
    evaluations or single evaluation objects.

    Parameters
    ----------
    rubric : EvaluationRubric
        The evaluation rubric to validate against.

    Examples
    --------
    >>> importer = JSONImporter(rubric)
    >>> results, report = importer.import_data("evaluations.json")

    JSON format (array):
    ```json
    {
      "evaluations": [
        {
          "item_id": "item_001",
          "results": {"M1": true, "C1": false},
          "reasoning": {"M1": "Good"}
        }
      ]
    }
    ```

    JSON format (flat):
    ```json
    [
      {
        "item_id": "item_001",
        "M1": true,
        "C1": false,
        "M1_reasoning": "Good"
      }
    ]
    ```
    """

    def _load_data(self, source: Union[str, Path, Dict, List]) -> List[Dict[str, Any]]:
        """Load data from JSON file, string, or object."""
        # Handle file path
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                # Try parsing as JSON string
                try:
                    data = json.loads(source)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON: {e}")
        else:
            data = source

        # Normalize to list of items
        items = []

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Check for common wrapper keys
            if "evaluations" in data:
                items = data["evaluations"]
            elif "items" in data:
                items = data["items"]
            elif "data" in data:
                items = data["data"]
            else:
                # Single evaluation object
                items = [data]

        # Flatten nested structures if necessary
        flattened_items = []
        for item in items:
            flattened = self._flatten_item(item)
            flattened_items.append(flattened)

        return flattened_items

    def _flatten_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested evaluation structure to flat dictionary.

        Handles nested formats like:
        {
          "results": {"M1": true},
          "reasoning": {"M1": "text"}
        }
        """
        flattened = {}

        # Copy item_id and metadata
        for key in ["item_id", "metadata", "context", "evaluator", "timestamp"]:
            if key in item:
                flattened[key] = item[key]

        # Handle nested results
        if "results" in item and isinstance(item["results"], dict):
            for metric_id, value in item["results"].items():
                flattened[metric_id] = value
        else:
            # Already flat, copy metric values
            for metric_id in self.metric_ids:
                if metric_id in item:
                    flattened[metric_id] = item[metric_id]

        # Handle nested reasoning
        if "reasoning" in item and isinstance(item["reasoning"], dict):
            for metric_id, text in item["reasoning"].items():
                flattened[f"{metric_id}_reasoning"] = text
        else:
            # Copy reasoning fields from flat structure
            for key, value in item.items():
                if key.endswith("_reasoning"):
                    flattened[key] = value

        return flattened


class DataFrameImporter(BaseImporter):
    """
    Import evaluations from Pandas DataFrames.

    Handles DataFrames with columns for metrics and optional reasoning.
    Supports various dtypes and multi-index DataFrames.

    Parameters
    ----------
    rubric : EvaluationRubric
        The evaluation rubric to validate against.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     "item_id": ["item1", "item2"],
    ...     "M1": [True, False],
    ...     "C1": [1, 0],
    ...     "M1_reasoning": ["Good", "Failed"]
    ... })
    >>> importer = DataFrameImporter(rubric)
    >>> results, report = importer.import_data(df)

    Notes
    -----
    Requires pandas to be installed. Install with:
    pip install teval[human]
    """

    def _load_data(self, source: Any) -> List[Dict[str, Any]]:
        """Load data from Pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Pandas is required for DataFrame import. "
                "Install with: pip install pandas"
            )

        if not isinstance(source, pd.DataFrame):
            raise ValueError("Source must be a pandas DataFrame")

        df = source.copy()

        # Handle multi-index by resetting
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()

        # Convert to list of dictionaries
        items = df.to_dict("records")

        # Handle pandas NA values
        cleaned_items = []
        for item in items:
            cleaned_item = {}
            for key, value in item.items():
                # Convert pandas NA to None
                if pd.isna(value):
                    cleaned_item[key] = None
                else:
                    cleaned_item[key] = value
            cleaned_items.append(cleaned_item)

        return cleaned_items


def import_evaluations(
    source: Union[str, Path, Dict, List, Any],
    rubric: EvaluationRubric,
    format: Optional[str] = None,
    **kwargs
) -> Tuple[List[Dict[str, Any]], ImportReport]:
    """
    Import evaluation data from various formats.

    Main entry point for importing evaluation data. Automatically detects
    format if not specified.

    Parameters
    ----------
    source : Union[str, Path, Dict, List, Any]
        Data source - file path, data structure, or DataFrame.
    rubric : EvaluationRubric
        The evaluation rubric to validate against.
    format : str, optional
        Format type: "csv", "json", "dataframe". Auto-detected if None.
    **kwargs
        Additional arguments passed to specific importer.

    Returns
    -------
    Tuple[List[Dict[str, Any]], ImportReport]
        Tuple of (list of processed evaluations, import report).

    Raises
    ------
    ValueError
        If format cannot be determined or is unsupported.

    Examples
    --------
    Import from CSV with auto-detection:

    >>> results, report = import_evaluations("evaluations.csv", rubric)
    >>> print(f"Success rate: {report.success_rate:.1%}")

    Import from DataFrame explicitly:

    >>> import pandas as pd
    >>> df = pd.read_excel("evaluations.xlsx")
    >>> results, report = import_evaluations(
    ...     df,
    ...     rubric,
    ...     format="dataframe"
    ... )

    Import from JSON string:

    >>> json_data = '[{"item_id": "1", "M1": true, "C1": false}]'
    >>> results, report = import_evaluations(
    ...     json_data,
    ...     rubric,
    ...     format="json"
    ... )

    Check import report:

    >>> if report.warnings:
    ...     print("Warnings:", report.warnings)
    >>> if report.errors:
    ...     print("Errors:", report.errors)
    >>> print(f"Imported {report.success_count}/{report.total_count}")
    """
    # Auto-detect format if not specified
    if format is None:
        format = _detect_format(source)

    # Select appropriate importer
    if format == "csv":
        importer = CSVImporter(rubric, **kwargs)
    elif format == "json":
        importer = JSONImporter(rubric, **kwargs)
    elif format == "dataframe":
        importer = DataFrameImporter(rubric, **kwargs)
    else:
        raise ValueError(
            f"Unsupported format: {format}. "
            "Supported formats: csv, json, dataframe"
        )

    return importer.import_data(source)


def _detect_format(source: Any) -> str:
    """
    Auto-detect the format of the data source.

    Parameters
    ----------
    source : Any
        The data source to detect.

    Returns
    -------
    str
        Detected format: "csv", "json", or "dataframe".

    Raises
    ------
    ValueError
        If format cannot be determined.
    """
    # Check for DataFrame
    try:
        import pandas as pd
        if isinstance(source, pd.DataFrame):
            return "dataframe"
    except ImportError:
        pass

    # Check for dict/list (JSON data)
    if isinstance(source, (dict, list)):
        return "json"

    # Check file extensions
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.exists():
            suffix = path.suffix.lower()
            if suffix in (".csv", ".tsv", ".txt"):
                return "csv"
            elif suffix == ".json":
                return "json"

        # Try to parse as JSON string
        if isinstance(source, str):
            try:
                json.loads(source)
                return "json"
            except (json.JSONDecodeError, ValueError):
                pass

    raise ValueError(
        "Could not detect format. Please specify format parameter as "
        "'csv', 'json', or 'dataframe'"
    )