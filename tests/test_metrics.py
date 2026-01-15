"""Tests for teval.metrics module."""

import pytest
from pydantic import ValidationError, BaseModel

from teval import EvaluationRubric, MetricDefinition


class TestMetricDefinition:
    """Tests for MetricDefinition model."""

    def test_metric_definition_basic(self):
        """Test basic metric definition creation."""
        metric = MetricDefinition(id="M1", rubric="Code compiles without errors")
        assert metric.id == "M1"
        assert metric.rubric == "Code compiles without errors"
        assert metric.mandatory is False  # Default

    def test_metric_definition_mandatory(self):
        """Test metric definition with mandatory=True."""
        metric = MetricDefinition(
            id="M1", rubric="Code compiles without errors", mandatory=True
        )
        assert metric.mandatory is True

    def test_metric_definition_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            MetricDefinition(
                id="M1", rubric="Test rubric", extra_field="not allowed"
            )

    def test_metric_definition_missing_required_fields(self):
        """Test that required fields must be provided."""
        with pytest.raises(ValidationError):
            MetricDefinition(id="M1")  # Missing rubric

        with pytest.raises(ValidationError):
            MetricDefinition(rubric="Test rubric")  # Missing id

    def test_metric_id_validation_valid(self):
        """Test valid metric IDs are accepted."""
        # Valid IDs should work
        valid_ids = ["M1", "metric_1", "_private", "camelCase", "UPPER_CASE"]
        for valid_id in valid_ids:
            metric = MetricDefinition(id=valid_id, rubric="Test")
            assert metric.id == valid_id

    def test_metric_id_validation_empty(self):
        """Test empty metric ID is rejected."""
        with pytest.raises(ValidationError, match="Metric ID cannot be empty"):
            MetricDefinition(id="", rubric="Test")

    def test_metric_id_validation_too_long(self):
        """Test metric ID length limit."""
        long_id = "a" * 101  # 101 characters, over the 100 limit
        with pytest.raises(ValidationError, match="too long"):
            MetricDefinition(id=long_id, rubric="Test")

    def test_metric_id_validation_invalid_identifier(self):
        """Test invalid Python identifiers are rejected."""
        invalid_ids = ["1metric", "metric-1", "metric.1", "metric name", "metric@test"]
        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError, match="not a valid identifier"):
                MetricDefinition(id=invalid_id, rubric="Test")

    def test_metric_id_validation_python_keyword(self):
        """Test Python keywords are rejected as metric IDs."""
        keywords = ["class", "def", "return", "if", "for", "import"]
        for keyword_id in keywords:
            with pytest.raises(ValidationError, match="Python keyword"):
                MetricDefinition(id=keyword_id, rubric="Test")

    def test_metric_id_validation_reserved_attributes(self):
        """Test reserved Pydantic attributes are rejected."""
        reserved_ids = ["dict", "json", "model_dump", "model_config", "passes",
                       "get_failed_metrics", "get_passed_metrics", "to_report"]
        for reserved_id in reserved_ids:
            with pytest.raises(ValidationError, match="conflicts with reserved"):
                MetricDefinition(id=reserved_id, rubric="Test")


class TestEvaluationRubric:
    """Tests for EvaluationRubric model."""

    def test_evaluation_rubric_basic(self):
        """Test basic rubric creation."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
                MetricDefinition(id="C1", rubric="Optional 1"),
                MetricDefinition(id="C2", rubric="Optional 2"),
            ],
            passing_score_threshold=1,
        )
        assert rubric.rubric_id == "test_v1"
        assert len(rubric.metrics) == 3
        assert rubric.passing_score_threshold == 1

    def test_mandatory_metrics_property(self):
        """Test mandatory_metrics property filters correctly."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory 1", mandatory=True),
                MetricDefinition(id="M2", rubric="Mandatory 2", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
            ],
            passing_score_threshold=1,
        )
        mandatory = rubric.mandatory_metrics
        assert len(mandatory) == 2
        assert all(m.mandatory for m in mandatory)
        assert {m.id for m in mandatory} == {"M1", "M2"}

    def test_cumulative_metrics_property(self):
        """Test cumulative_metrics property filters correctly."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory 1", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
                MetricDefinition(id="C3", rubric="Cumulative 3"),
            ],
            passing_score_threshold=2,
        )
        cumulative = rubric.cumulative_metrics
        assert len(cumulative) == 3
        assert all(not m.mandatory for m in cumulative)
        assert {m.id for m in cumulative} == {"C1", "C2", "C3"}

    def test_duplicate_metric_ids_rejected(self):
        """Test that duplicate metric IDs are rejected."""
        with pytest.raises(ValidationError, match="Duplicate metric IDs found: M1"):
            EvaluationRubric(
                rubric_id="test_v1",
                metrics=[
                    MetricDefinition(id="M1", rubric="First"),
                    MetricDefinition(id="M1", rubric="Duplicate"),
                ],
                passing_score_threshold=0,
            )

    def test_empty_metrics_list_rejected(self):
        """Test that empty metrics list is rejected."""
        with pytest.raises(ValidationError, match="Evaluation rubric must contain at least one metric"):
            EvaluationRubric(
                rubric_id="test_v1",
                metrics=[],
                passing_score_threshold=0,
            )

    def test_maximum_total_metrics_limit(self):
        """Test that total metrics cannot exceed maximum limit."""
        # Create 101 metrics (exceeds limit of 100)
        too_many_metrics = [
            MetricDefinition(id=f"M{i}", rubric=f"Metric {i}")
            for i in range(101)
        ]
        with pytest.raises(ValidationError, match="Too many metrics: 101 exceeds maximum of 100"):
            EvaluationRubric(
                rubric_id="test_v1",
                metrics=too_many_metrics,
                passing_score_threshold=0,
            )

    def test_maximum_mandatory_metrics_limit(self):
        """Test that mandatory metrics cannot exceed maximum limit."""
        # Create 21 mandatory metrics (exceeds limit of 20)
        too_many_mandatory = [
            MetricDefinition(id=f"M{i}", rubric=f"Mandatory {i}", mandatory=True)
            for i in range(21)
        ]
        with pytest.raises(ValidationError, match="Too many mandatory metrics: 21 exceeds maximum of 20"):
            EvaluationRubric(
                rubric_id="test_v1",
                metrics=too_many_mandatory,
                passing_score_threshold=0,
            )

    def test_metrics_at_limit_accepted(self):
        """Test that metrics at the limit are accepted."""
        # Create exactly 100 metrics with 20 mandatory (at limits)
        metrics_at_limit = []
        # Add 20 mandatory metrics
        for i in range(20):
            metrics_at_limit.append(
                MetricDefinition(id=f"M{i}", rubric=f"Mandatory {i}", mandatory=True)
            )
        # Add 80 cumulative metrics
        for i in range(20, 100):
            metrics_at_limit.append(
                MetricDefinition(id=f"C{i}", rubric=f"Cumulative {i}")
            )

        # This should work without raising an exception
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=metrics_at_limit,
            passing_score_threshold=40,
        )
        assert len(rubric.metrics) == 100
        assert len(rubric.mandatory_metrics) == 20
        assert len(rubric.cumulative_metrics) == 80

    def test_threshold_exceeds_cumulative_count_rejected(self):
        """Test that threshold cannot exceed cumulative metric count."""
        with pytest.raises(
            ValidationError, match="Invalid passing threshold.*exceeds the number of.*cumulative metrics.*Please set passing_score_threshold"
        ):
            EvaluationRubric(
                rubric_id="test_v1",
                metrics=[
                    MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                    MetricDefinition(id="C1", rubric="Cumulative 1"),
                    MetricDefinition(id="C2", rubric="Cumulative 2"),
                ],
                passing_score_threshold=3,  # Only 2 cumulative metrics!
            )

    def test_threshold_zero_allowed(self):
        """Test that threshold of 0 is allowed."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="C1", rubric="Cumulative 1"),
            ],
            passing_score_threshold=0,
        )
        assert rubric.passing_score_threshold == 0

    def test_threshold_equals_cumulative_count_allowed(self):
        """Test that threshold can equal cumulative count."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
            ],
            passing_score_threshold=2,
        )
        assert rubric.passing_score_threshold == 2

    def test_only_mandatory_metrics(self):
        """Test rubric with only mandatory metrics."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory 1", mandatory=True),
                MetricDefinition(id="M2", rubric="Mandatory 2", mandatory=True),
            ],
            passing_score_threshold=0,  # No cumulative metrics
        )
        assert len(rubric.mandatory_metrics) == 2
        assert len(rubric.cumulative_metrics) == 0

    def test_to_prompt_text(self):
        """Test prompt text generation."""
        rubric = EvaluationRubric(
            rubric_id="code_review_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Code compiles without errors", mandatory=True),
                MetricDefinition(id="M2", rubric="No security vulnerabilities", mandatory=True),
                MetricDefinition(id="C1", rubric="Follows style guide"),
                MetricDefinition(id="C2", rubric="Has unit tests"),
                MetricDefinition(id="C3", rubric="Well documented"),
            ],
            passing_score_threshold=2,
        )

        prompt = rubric.to_prompt_text()

        # Check that all components are present
        assert "# Evaluation Rubric: code_review_v1" in prompt
        assert "## Mandatory Criteria (ALL must pass)" in prompt
        assert "## Cumulative Criteria" in prompt
        assert "(Must pass at least 2 of 3)" in prompt
        assert "## Instructions" in prompt

        # Check that all metrics are included
        assert "**M1**: Code compiles without errors" in prompt
        assert "**M2**: No security vulnerabilities" in prompt
        assert "**C1**: Follows style guide" in prompt
        assert "**C2**: Has unit tests" in prompt
        assert "**C3**: Well documented" in prompt

        # Check instructions
        assert "All 2 mandatory criteria must pass" in prompt
        assert "At least 2 cumulative criteria must pass" in prompt

    def test_to_prompt_text_only_mandatory(self):
        """Test prompt text with only mandatory metrics."""
        rubric = EvaluationRubric(
            rubric_id="minimal_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Must compile", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        prompt = rubric.to_prompt_text()

        assert "## Mandatory Criteria (ALL must pass)" in prompt
        assert "## Cumulative Criteria" not in prompt
        assert "**M1**: Must compile" in prompt

    def test_to_prompt_text_only_cumulative(self):
        """Test prompt text with only cumulative metrics."""
        rubric = EvaluationRubric(
            rubric_id="optional_v1",
            metrics=[
                MetricDefinition(id="C1", rubric="Has tests"),
                MetricDefinition(id="C2", rubric="Has docs"),
            ],
            passing_score_threshold=1,
        )

        prompt = rubric.to_prompt_text()

        assert "## Mandatory Criteria" not in prompt
        assert "## Cumulative Criteria" in prompt
        assert "(Must pass at least 1 of 2)" in prompt

    def test_to_json_schema(self):
        """Test JSON schema generation."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="First check", mandatory=True),
                MetricDefinition(id="C1", rubric="Second check"),
            ],
            passing_score_threshold=0,
        )

        schema = rubric.to_json_schema()

        # Check schema structure
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert schema["additionalProperties"] is False
        assert "test_v1" in schema["description"]

        # Check metric fields
        assert "M1" in schema["properties"]
        assert schema["properties"]["M1"]["type"] == "boolean"
        assert "First check" in schema["properties"]["M1"]["description"]

        assert "C1" in schema["properties"]
        assert schema["properties"]["C1"]["type"] == "boolean"
        assert "Second check" in schema["properties"]["C1"]["description"]

        # Check reasoning fields
        assert "M1_reasoning" in schema["properties"]
        assert schema["properties"]["M1_reasoning"]["type"] == "string"
        assert "C1_reasoning" in schema["properties"]
        assert schema["properties"]["C1_reasoning"]["type"] == "string"

        # Check required fields (only the boolean metric fields, not reasoning)
        assert "M1" in schema["required"]
        assert "C1" in schema["required"]
        assert "M1_reasoning" not in schema["required"]
        assert "C1_reasoning" not in schema["required"]

    def test_validate_result_all_pass(self):
        """Test validation when all criteria pass."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
            ],
            passing_score_threshold=1,
        )

        result = {"M1": True, "C1": True, "C2": False}
        assert rubric.validate_result(result) is True

    def test_validate_result_mandatory_fails(self):
        """Test validation when mandatory metric fails."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
            ],
            passing_score_threshold=0,
        )

        result = {"M1": False, "C1": True}
        assert rubric.validate_result(result) is False

    def test_validate_result_cumulative_fails(self):
        """Test validation when cumulative threshold not met."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
                MetricDefinition(id="C3", rubric="Cumulative 3"),
            ],
            passing_score_threshold=2,
        )

        result = {"M1": True, "C1": True, "C2": False, "C3": False}
        assert rubric.validate_result(result) is False

    def test_validate_result_missing_metric(self):
        """Test validation fails when metric is missing."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=0,
        )

        result = {"M1": True}  # Missing C1
        with pytest.raises(ValueError) as exc_info:
            rubric.validate_result(result)

        error_msg = str(exc_info.value)
        assert "Missing evaluation results for 1 metric(s)" in error_msg
        assert "Cumulative: C1" in error_msg

    def test_validate_result_missing_multiple_metrics(self):
        """Test enhanced error message for multiple missing metrics."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory 1", mandatory=True),
                MetricDefinition(id="M2", rubric="Mandatory 2", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
            ],
            passing_score_threshold=0,
        )

        result = {"C1": True}  # Missing M1, M2, C2
        with pytest.raises(ValueError) as exc_info:
            rubric.validate_result(result)

        error_msg = str(exc_info.value)
        assert "Missing evaluation results for 3 metric(s)" in error_msg
        assert "Mandatory: M1, M2" in error_msg
        assert "Cumulative: C2" in error_msg

    def test_validate_result_invalid_type(self):
        """Test validation fails when metric value is not boolean."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test validation check with a long description", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        result = {"M1": "yes"}  # String instead of boolean
        with pytest.raises(ValueError, match="Invalid result for metric 'M1': expected boolean, got str"):
            rubric.validate_result(result)

    def test_validate_result_ignores_extra_fields(self):
        """Test that validation allows extra fields like reasoning."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        result = {"M1": True, "M1_reasoning": "It works!", "extra_field": "ignored"}
        assert rubric.validate_result(result) is True

    def test_validate_result_json_string_pass(self):
        """Test validation with JSON string that passes."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=1,
        )

        json_result = '{"M1": true, "C1": true}'
        assert rubric.validate_result(json_result) is True

    def test_validate_result_json_string_fail(self):
        """Test validation with JSON string that fails."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=1,
        )

        json_result = '{"M1": false, "C1": true}'
        assert rubric.validate_result(json_result) is False

    def test_validate_result_json_string_with_reasoning(self):
        """Test validation with JSON string including reasoning fields."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        json_result = '{"M1": true, "M1_reasoning": "Looks good"}'
        assert rubric.validate_result(json_result) is True

    def test_validate_result_invalid_json(self):
        """Test validation fails with malformed JSON."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        invalid_json = '{"M1": true'  # Missing closing brace
        with pytest.raises(ValueError, match="Invalid JSON string"):
            rubric.validate_result(invalid_json)

    def test_validate_result_json_array_rejected(self):
        """Test validation fails when JSON is an array instead of object."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        json_array = '[{"M1": true}]'
        with pytest.raises(ValueError, match="must be a JSON string or dictionary"):
            rubric.validate_result(json_array)

    def test_validate_result_non_string_non_dict_rejected(self):
        """Test validation fails when result is neither string nor dict."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        with pytest.raises(ValueError, match="must be a JSON string or dictionary"):
            rubric.validate_result(123)

    def test_generate_report_basic(self):
        """Test basic report generation with mixed metrics."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory check", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative check 1"),
                MetricDefinition(id="C2", rubric="Cumulative check 2"),
            ],
            passing_score_threshold=1,
        )

        result = {"M1": True, "C1": True, "C2": False}
        report = rubric.generate_report(result)

        # Check basic structure
        assert "# Evaluation Report: test_v1" in report
        assert "**Overall Result: PASS**" in report
        assert "## Mandatory Criteria (ALL must pass)" in report
        assert "## Cumulative Criteria" in report
        assert "**Score: 1/2**" in report
        assert "## Requirements for Passing" in report

    def test_generate_report_with_reasoning(self):
        """Test report generation includes reasoning."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test metric", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        result = {"M1": True}
        reasoning = {"M1": "This is the reason it passed"}
        report = rubric.generate_report(result, reasoning)

        assert "This is the reason it passed" in report
        assert "→" in report

    def test_generate_report_custom_title(self):
        """Test report generation with custom title."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        result = {"M1": True}
        report = rubric.generate_report(result, title="My Custom Report")

        assert "# My Custom Report" in report
        assert "# Evaluation Report: test_v1" not in report

    def test_generate_report_all_pass(self):
        """Test report when all metrics pass."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
            ],
            passing_score_threshold=2,
        )

        result = {"M1": True, "C1": True, "C2": True}
        report = rubric.generate_report(result)

        assert "**Overall Result: PASS**" in report
        assert "✓" in report
        assert "✗" not in report
        assert "⚠️" not in report

    def test_generate_report_mandatory_fails(self):
        """Test report shows failed mandatory metrics."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory 1", mandatory=True),
                MetricDefinition(id="M2", rubric="Mandatory 2", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=1,
        )

        result = {"M1": True, "C1": True, "M2": False}
        report = rubric.generate_report(result)

        assert "**Overall Result: FAIL**" in report
        assert "⚠️  **1 mandatory metric(s) failed:** M2" in report
        assert "✗ **M2** [FAIL]" in report

    def test_generate_report_cumulative_fails(self):
        """Test report shows cumulative score deficit."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
                MetricDefinition(id="C3", rubric="Cumulative 3"),
            ],
            passing_score_threshold=3,
        )

        result = {"M1": True, "C1": True, "C2": False, "C3": False}
        report = rubric.generate_report(result)

        assert "**Overall Result: FAIL**" in report
        assert "**Score: 1/3**" in report
        assert "⚠️  **Need 2 more cumulative metric(s) to pass**" in report
        assert "Still need: 2 more" in report

    def test_generate_report_only_mandatory(self):
        """Test report with only mandatory metrics."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory 1", mandatory=True),
                MetricDefinition(id="M2", rubric="Mandatory 2", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        result = {"M1": True, "M2": True}
        report = rubric.generate_report(result)

        assert "## Mandatory Criteria (ALL must pass)" in report
        assert "## Cumulative Criteria" not in report
        assert "**Overall Result: PASS**" in report

    def test_generate_report_only_cumulative(self):
        """Test report with only cumulative metrics."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
            ],
            passing_score_threshold=1,
        )

        result = {"C1": True, "C2": False}
        report = rubric.generate_report(result)

        assert "## Mandatory Criteria" not in report
        assert "## Cumulative Criteria" in report
        assert "**Score: 1/2**" in report

    def test_to_pydantic_model_basic(self):
        """Test Pydantic model generation."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="First check", mandatory=True),
                MetricDefinition(id="C1", rubric="Second check"),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()

        # Check the model class name
        assert ResultModel.__name__ == "EvaluationResult_test_v1"

        # Create a valid instance
        result = ResultModel(M1=True, C1=False)
        assert result.M1 is True
        assert result.C1 is False

    def test_to_pydantic_model_with_reasoning(self):
        """Test Pydantic model with reasoning fields."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()

        # Create instance with reasoning
        result = ResultModel(M1=True, M1_reasoning="Looks good!")
        assert result.M1 is True
        assert result.M1_reasoning == "Looks good!"

    def test_to_pydantic_model_validation_required_fields(self):
        """Test that Pydantic model enforces required fields."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test 1"),
                MetricDefinition(id="M2", rubric="Test 2"),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()

        # Missing required field should raise error
        with pytest.raises(ValidationError):
            ResultModel(M1=True)  # Missing M2

    def test_to_pydantic_model_validation_type_checking(self):
        """Test that Pydantic model enforces type checking."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test"),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()

        # Invalid type should raise error
        with pytest.raises(ValidationError):
            ResultModel(M1=123)  # Should be boolean

        # Also test with dict - Pydantic coerces some strings but not all
        with pytest.raises(ValidationError):
            ResultModel(M1=None)  # Should be boolean, not None

    def test_to_pydantic_model_extra_fields_forbidden(self):
        """Test that Pydantic model forbids extra fields."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test"),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()

        # Extra fields should raise error
        with pytest.raises(ValidationError):
            ResultModel(M1=True, extra_field="not allowed")

    def test_to_pydantic_model_json_parsing(self):
        """Test that Pydantic model can parse JSON."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test"),
                MetricDefinition(id="C1", rubric="Test 2"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()

        # Parse from JSON string
        json_data = '{"M1": true, "C1": false, "M1_reasoning": "Good"}'
        result = ResultModel.model_validate_json(json_data)

        assert result.M1 is True
        assert result.C1 is False
        assert result.M1_reasoning == "Good"

    def test_to_pydantic_model_dict_export(self):
        """Test that Pydantic model can export to dict."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test"),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()
        result = ResultModel(M1=True, M1_reasoning="Good")

        # Export to dict
        result_dict = result.model_dump()
        assert result_dict["M1"] is True
        assert result_dict["M1_reasoning"] == "Good"

        # Export to dict excluding None values
        result2 = ResultModel(M1=False)
        result_dict2 = result2.model_dump(exclude_none=True)
        assert "M1_reasoning" not in result_dict2

    def test_to_pydantic_model_json_schema_compatibility(self):
        """Test that Pydantic model schema matches to_json_schema()."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="First check"),
                MetricDefinition(id="C1", rubric="Second check"),
            ],
            passing_score_threshold=0,
        )

        # Get both schemas
        json_schema = rubric.to_json_schema()
        ResultModel = rubric.to_pydantic_model()
        pydantic_schema = ResultModel.model_json_schema()

        # Check that required fields match
        assert set(json_schema["required"]) == set(pydantic_schema["required"])

        # Check that all metric fields are present in both
        for metric in rubric.metrics:
            assert metric.id in json_schema["properties"]
            assert metric.id in pydantic_schema["properties"]

    def test_to_pydantic_model_with_validate_result(self):
        """Test that Pydantic model output works with validate_result()."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()

        # Create a passing result
        result = ResultModel(M1=True, C1=True)
        result_dict = result.model_dump()

        # Should pass validation
        assert rubric.validate_result(result_dict) is True

        # Create a failing result
        result2 = ResultModel(M1=False, C1=True)
        result_dict2 = result2.model_dump()

        # Should fail validation (mandatory metric failed)
        assert rubric.validate_result(result_dict2) is False

    def test_pydantic_model_get_failed_metrics(self):
        """Test get_failed_metrics() helper method."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()

        # Test with some failing
        result = ResultModel(M1=True, C1=False, C2=False)
        assert result.get_failed_metrics() == ["C1", "C2"]

        # Test with all passing
        result2 = ResultModel(M1=True, C1=True, C2=True)
        assert result2.get_failed_metrics() == []

        # Test with all failing
        result3 = ResultModel(M1=False, C1=False, C2=False)
        assert set(result3.get_failed_metrics()) == {"M1", "C1", "C2"}

    def test_pydantic_model_get_passed_metrics(self):
        """Test get_passed_metrics() helper method."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative 1"),
                MetricDefinition(id="C2", rubric="Cumulative 2"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()

        # Test with some passing
        result = ResultModel(M1=True, C1=True, C2=False)
        assert set(result.get_passed_metrics()) == {"M1", "C1"}

        # Test with all passing
        result2 = ResultModel(M1=True, C1=True, C2=True)
        assert set(result2.get_passed_metrics()) == {"M1", "C1", "C2"}

        # Test with all failing
        result3 = ResultModel(M1=False, C1=False, C2=False)
        assert result3.get_passed_metrics() == []

    def test_pydantic_model_to_report(self):
        """Test to_report() helper method."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory check", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative check"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()

        # Test basic report generation
        result = ResultModel(M1=True, C1=True)
        report = result.to_report()
        assert "# Evaluation Report: test_v1" in report
        assert "**Overall Result: PASS**" in report

        # Test with custom title
        report_custom = result.to_report(title="My Custom Title")
        assert "# My Custom Title" in report_custom
        assert "# Evaluation Report: test_v1" not in report_custom

        # Test with reasoning fields
        result_with_reasoning = ResultModel(
            M1=True,
            C1=False,
            M1_reasoning="This passed because...",
            C1_reasoning="This failed because..."
        )
        report_reasoning = result_with_reasoning.to_report()
        assert "This passed because..." in report_reasoning
        assert "This failed because..." in report_reasoning


class TestAlignmentCalculation:
    """Tests for calculate_alignment() method."""

    def test_single_result_both_pass(self):
        """Test alignment when both single results pass."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()
        result_a = ResultModel(M1=True, C1=True)
        result_b = ResultModel(M1=True, C1=True)

        alignment = rubric.calculate_alignment(result_a, result_b)
        assert alignment == 1.0

    def test_single_result_both_fail(self):
        """Test alignment when both single results fail."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()
        result_a = ResultModel(M1=False, C1=False)
        result_b = ResultModel(M1=False, C1=True)

        alignment = rubric.calculate_alignment(result_a, result_b)
        assert alignment == 1.0

    def test_single_result_disagree(self):
        """Test alignment when single results disagree on pass/fail."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()
        result_a = ResultModel(M1=True, C1=True)  # Passes
        result_b = ResultModel(M1=False, C1=True)  # Fails (mandatory failed)

        alignment = rubric.calculate_alignment(result_a, result_b)
        assert alignment == 0.0

    def test_batch_all_aligned(self):
        """Test batch comparison when all results are aligned."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()
        results_a = [
            ResultModel(M1=True, C1=True),   # Pass
            ResultModel(M1=False, C1=False), # Fail (mandatory failed)
            ResultModel(M1=True, C1=True),   # Pass
        ]
        results_b = [
            ResultModel(M1=True, C1=True),   # Pass (aligned)
            ResultModel(M1=False, C1=True),  # Fail (aligned - mandatory failed)
            ResultModel(M1=True, C1=True),   # Pass (aligned)
        ]

        alignment = rubric.calculate_alignment(results_a, results_b)
        assert alignment == 1.0

    def test_batch_none_aligned(self):
        """Test batch comparison when no results are aligned."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=1,
        )

        ResultModel = rubric.to_pydantic_model()
        results_a = [
            ResultModel(M1=True, C1=True),   # Pass
            ResultModel(M1=True, C1=True),   # Pass
        ]
        results_b = [
            ResultModel(M1=False, C1=False), # Fail
            ResultModel(M1=False, C1=True),  # Fail
        ]

        alignment = rubric.calculate_alignment(results_a, results_b)
        assert alignment == 0.0

    def test_batch_partial_alignment(self):
        """Test batch comparison with partial alignment."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
                MetricDefinition(id="C1", rubric="Cumulative"),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()
        results_a = [
            ResultModel(M1=True, C1=True),   # Pass
            ResultModel(M1=False, C1=False), # Fail
            ResultModel(M1=True, C1=True),   # Pass
            ResultModel(M1=False, C1=False), # Fail
        ]
        results_b = [
            ResultModel(M1=True, C1=False),  # Pass
            ResultModel(M1=False, C1=True),  # Fail
            ResultModel(M1=False, C1=False), # Fail (disagree)
            ResultModel(M1=True, C1=True),   # Pass (disagree)
        ]

        alignment = rubric.calculate_alignment(results_a, results_b)
        assert alignment == 0.5  # 2 out of 4 aligned

    def test_batch_75_percent_alignment(self):
        """Test batch comparison with 75% alignment."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Mandatory", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()
        results_a = [
            ResultModel(M1=True),   # Pass
            ResultModel(M1=False),  # Fail
            ResultModel(M1=True),   # Pass
            ResultModel(M1=False),  # Fail
        ]
        results_b = [
            ResultModel(M1=True),   # Pass (aligned)
            ResultModel(M1=False),  # Fail (aligned)
            ResultModel(M1=True),   # Pass (aligned)
            ResultModel(M1=True),   # Pass (not aligned)
        ]

        alignment = rubric.calculate_alignment(results_a, results_b)
        assert alignment == 0.75  # 3 out of 4 aligned

    def test_empty_lists(self):
        """Test alignment with empty lists."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        alignment = rubric.calculate_alignment([], [])
        assert alignment == 1.0

    def test_different_list_lengths_raises_error(self):
        """Test that different list lengths raise ValueError."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()
        results_a = [ResultModel(M1=True), ResultModel(M1=False)]
        results_b = [ResultModel(M1=True)]

        with pytest.raises(ValueError, match="must have the same length"):
            rubric.calculate_alignment(results_a, results_b)

    def test_mixed_single_and_list_raises_error(self):
        """Test that mixing single instance and list raises TypeError."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()
        result_single = ResultModel(M1=True)
        results_list = [ResultModel(M1=True)]

        with pytest.raises(TypeError, match="must be either single instances or lists"):
            rubric.calculate_alignment(result_single, results_list)

    def test_non_basemodel_instance_raises_error(self):
        """Test that non-BaseModel instances raise TypeError."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()
        result_valid = ResultModel(M1=True)

        # When one is BaseModel and one is dict, it triggers the "single instances or lists" check
        with pytest.raises(TypeError, match="must be either single instances or lists"):
            rubric.calculate_alignment(result_valid, {"M1": True})

    def test_non_basemodel_in_list_raises_error(self):
        """Test that non-BaseModel items in list raise TypeError."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()
        results_a = [ResultModel(M1=True), ResultModel(M1=False)]
        results_b = [ResultModel(M1=True), {"M1": False}]

        with pytest.raises(TypeError, match="results_b\\[1\\] is not a BaseModel instance"):
            rubric.calculate_alignment(results_a, results_b)

    def test_non_basemodel_in_results_a_list_raises_error(self):
        """Test that non-BaseModel items in results_a list raise TypeError."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        ResultModel = rubric.to_pydantic_model()
        results_a = [ResultModel(M1=True), {"M1": False}]
        results_b = [ResultModel(M1=True), ResultModel(M1=False)]

        with pytest.raises(TypeError, match="results_a\\[1\\] is not a BaseModel instance"):
            rubric.calculate_alignment(results_a, results_b)

    def test_non_list_input_raises_error(self):
        """Test that non-list inputs (when not single instance) raise TypeError."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        with pytest.raises(TypeError, match="must be BaseModel instances or lists"):
            rubric.calculate_alignment({"M1": True}, {"M1": False})

    def test_model_without_passes_method_raises_error(self):
        """Test that models without passes() method raise TypeError."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        # Create a basic Pydantic model without passes() method
        class FakeModel(BaseModel):
            M1: bool

        fake_a = FakeModel(M1=True)
        fake_b = FakeModel(M1=False)

        with pytest.raises(TypeError, match="must be instances from to_pydantic_model.*with passes\\(\\) method"):
            rubric.calculate_alignment(fake_a, fake_b)
