"""Tests for tevak.metrics module."""

import pytest
from pydantic import ValidationError

from tevak import EvaluationRubric, MetricDefinition


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
        with pytest.raises(ValidationError, match="Duplicate metric IDs"):
            EvaluationRubric(
                rubric_id="test_v1",
                metrics=[
                    MetricDefinition(id="M1", rubric="First"),
                    MetricDefinition(id="M1", rubric="Duplicate"),
                ],
                passing_score_threshold=0,
            )

    def test_threshold_exceeds_cumulative_count_rejected(self):
        """Test that threshold cannot exceed cumulative metric count."""
        with pytest.raises(
            ValidationError, match="cannot exceed the maximum possible cumulative"
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
        with pytest.raises(ValueError, match="Missing metric results for: C1"):
            rubric.validate_result(result)

    def test_validate_result_invalid_type(self):
        """Test validation fails when metric value is not boolean."""
        rubric = EvaluationRubric(
            rubric_id="test_v1",
            metrics=[
                MetricDefinition(id="M1", rubric="Test", mandatory=True),
            ],
            passing_score_threshold=0,
        )

        result = {"M1": "yes"}  # String instead of boolean
        with pytest.raises(ValueError, match="must be boolean"):
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
