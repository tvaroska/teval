"""Tests for free-form comments support in teval."""

import pytest
from pydantic import ValidationError

from teval import EvaluationRubric, MetricDefinition


class TestMetricDefinitionComments:
    """Tests for MetricDefinition with comment requirements."""

    def test_metric_with_requires_comment_on_fail(self):
        """Test creating a metric that requires comments on failure."""
        metric = MetricDefinition(
            id="safety",
            rubric="Is the response safe and appropriate?",
            requires_comment_on_fail=True
        )
        assert metric.requires_comment_on_fail is True
        assert metric.mandatory is False  # Default

    def test_metric_without_requires_comment_default(self):
        """Test that requires_comment_on_fail defaults to False."""
        metric = MetricDefinition(
            id="M1",
            rubric="Test criterion"
        )
        assert metric.requires_comment_on_fail is False

    def test_metric_mandatory_with_comment_requirement(self):
        """Test a mandatory metric can also require comments on fail."""
        metric = MetricDefinition(
            id="critical",
            rubric="Critical safety check",
            mandatory=True,
            requires_comment_on_fail=True
        )
        assert metric.mandatory is True
        assert metric.requires_comment_on_fail is True


class TestCommentValidation:
    """Tests for validation of required comments."""

    def test_validation_passes_with_required_comment(self):
        """Test that validation passes when required comment is provided."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[
                MetricDefinition(
                    id="M1",
                    rubric="Test metric",
                    requires_comment_on_fail=True
                )
            ],
            passing_score_threshold=0
        )

        # Metric fails but has comment - should pass validation
        result = {
            "M1": False,
            "M1_reasoning": "This failed because of X reason"
        }
        assert rubric.validate_result(result) is True

    def test_validation_fails_without_required_comment(self):
        """Test that validation fails when required comment is missing."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[
                MetricDefinition(
                    id="M1",
                    rubric="Test metric",
                    requires_comment_on_fail=True
                )
            ],
            passing_score_threshold=0
        )

        # Metric fails without comment - should fail validation
        result = {"M1": False}
        with pytest.raises(ValueError, match="Missing required comments"):
            rubric.validate_result(result)

    def test_validation_with_empty_comment(self):
        """Test that empty/whitespace comments are rejected."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[
                MetricDefinition(
                    id="M1",
                    rubric="Test metric",
                    requires_comment_on_fail=True
                )
            ],
            passing_score_threshold=0
        )

        # Empty string comment
        result = {"M1": False, "M1_reasoning": ""}
        with pytest.raises(ValueError, match="Missing required comments"):
            rubric.validate_result(result)

        # Whitespace-only comment
        result = {"M1": False, "M1_reasoning": "   "}
        with pytest.raises(ValueError, match="Missing required comments"):
            rubric.validate_result(result)

    def test_validation_passes_when_metric_passes(self):
        """Test that no comment is required when metric passes."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[
                MetricDefinition(
                    id="M1",
                    rubric="Test metric",
                    requires_comment_on_fail=True
                )
            ],
            passing_score_threshold=1
        )

        # Metric passes - no comment needed
        result = {"M1": True}
        assert rubric.validate_result(result) is True

        # Comment is optional when metric passes
        result = {"M1": True, "M1_reasoning": "Good implementation"}
        assert rubric.validate_result(result) is True

    def test_multiple_metrics_with_mixed_requirements(self):
        """Test validation with multiple metrics having different comment requirements."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[
                MetricDefinition(id="M1", rubric="Requires comment", requires_comment_on_fail=True),
                MetricDefinition(id="M2", rubric="Optional comment", requires_comment_on_fail=False),
                MetricDefinition(id="M3", rubric="Also requires", requires_comment_on_fail=True),
            ],
            passing_score_threshold=0
        )

        # M1 and M3 fail without comments - should fail
        result = {"M1": False, "M2": False, "M3": False}
        with pytest.raises(ValueError, match="Missing required comments"):
            rubric.validate_result(result)

        # M1 has comment but M3 doesn't - should still fail
        result = {
            "M1": False, "M1_reasoning": "Failed due to X",
            "M2": False,
            "M3": False
        }
        with pytest.raises(ValueError, match="Missing required comments"):
            rubric.validate_result(result)

        # Both M1 and M3 have comments - validation should pass
        # But overall evaluation fails because all metrics are False
        result = {
            "M1": False, "M1_reasoning": "Failed due to X",
            "M2": False,  # No comment required
            "M3": False, "M3_reasoning": "Failed due to Y"
        }
        # With threshold=0, any number of passed metrics (including 0) is acceptable
        # So this actually passes despite all metrics being False
        assert rubric.validate_result(result) is True


class TestGlobalComments:
    """Tests for global comment support."""

    def test_json_schema_includes_global_comment(self):
        """Test that JSON schema includes global_comment field."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[MetricDefinition(id="M1", rubric="Test")],
            passing_score_threshold=0
        )

        schema = rubric.to_json_schema()
        assert "global_comment" in schema["properties"]
        assert schema["properties"]["global_comment"]["type"] == "string"
        assert "global_comment" not in schema["required"]  # Always optional

    def test_pydantic_model_includes_global_comment(self):
        """Test that Pydantic model includes global_comment field."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[MetricDefinition(id="M1", rubric="Test")],
            passing_score_threshold=0
        )

        ModelClass = rubric.to_pydantic_model()

        # Create instance with global comment
        instance = ModelClass(M1=True, global_comment="Overall good work")
        assert instance.global_comment == "Overall good work"

        # Create instance without global comment (should be None)
        instance = ModelClass(M1=True)
        assert instance.global_comment is None

    def test_validation_with_global_comment(self):
        """Test that validation works with global comments in results."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[MetricDefinition(id="M1", rubric="Test")],
            passing_score_threshold=1
        )

        # Result with global comment
        result = {
            "M1": True,
            "global_comment": "This is an overall comment about the evaluation"
        }
        assert rubric.validate_result(result) is True

        # Global comment is always optional
        result = {"M1": True}
        assert rubric.validate_result(result) is True


class TestDiscoveryRubric:
    """Tests for the discovery rubric builder."""

    def test_create_simple_discovery_rubric(self):
        """Test creating a simple discovery rubric."""
        rubric = EvaluationRubric.create_discovery_rubric(
            rubric_id="discovery_v1",
            criteria={
                "safety": "Is the response safe?",
                "accuracy": "Is it accurate?"
            }
        )

        assert rubric.rubric_id == "discovery_v1"
        assert len(rubric.metrics) == 2
        assert rubric.passing_score_threshold == 2  # Default: all must pass

        # Check that all metrics require comments on failure
        for metric in rubric.metrics:
            assert metric.requires_comment_on_fail is True
            assert metric.mandatory is False  # Uses cumulative scoring

    def test_discovery_rubric_with_custom_threshold(self):
        """Test discovery rubric with custom passing threshold."""
        rubric = EvaluationRubric.create_discovery_rubric(
            rubric_id="discovery_v2",
            criteria={
                "safety": "Is it safe?",
                "accuracy": "Is it accurate?",
                "helpful": "Is it helpful?"
            },
            passing_score_threshold=2  # Only 2 of 3 need to pass
        )

        assert rubric.passing_score_threshold == 2
        assert len(rubric.metrics) == 3

    def test_discovery_rubric_single_criterion(self):
        """Test discovery rubric with a single criterion."""
        rubric = EvaluationRubric.create_discovery_rubric(
            rubric_id="quick_check",
            criteria={"overall": "Is this acceptable for production?"}
        )

        assert len(rubric.metrics) == 1
        assert rubric.metrics[0].id == "overall"
        assert rubric.metrics[0].requires_comment_on_fail is True
        assert rubric.passing_score_threshold == 1

    def test_discovery_rubric_empty_criteria_raises(self):
        """Test that empty criteria raises ValueError."""
        with pytest.raises(ValueError, match="At least one criterion"):
            EvaluationRubric.create_discovery_rubric(
                rubric_id="empty",
                criteria={}
            )

    def test_discovery_rubric_validation(self):
        """Test that discovery rubric enforces comment requirements."""
        rubric = EvaluationRubric.create_discovery_rubric(
            rubric_id="test",
            criteria={"quality": "Is the quality acceptable?"}
        )

        # Failing without comment should raise
        with pytest.raises(ValueError, match="Missing required comments"):
            rubric.validate_result({"quality": False})

        # Failing with comment should work
        result = {"quality": False, "quality_reasoning": "Poor grammar and factual errors"}
        assert rubric.validate_result(result) is False  # Fails but validates

        # Passing doesn't require comment
        result = {"quality": True}
        assert rubric.validate_result(result) is True

    def test_discovery_rubric_with_various_ids(self):
        """Test discovery rubric with different ID formats."""
        rubric = EvaluationRubric.create_discovery_rubric(
            rubric_id="test",
            criteria={
                "safety_check": "Is it safe?",
                "accuracy_score": "Is it accurate?",
                "user_friendly": "Is it user-friendly?",
                "perf_01": "Performance acceptable?"
            }
        )

        assert len(rubric.metrics) == 4
        metric_ids = [m.id for m in rubric.metrics]
        assert "safety_check" in metric_ids
        assert "accuracy_score" in metric_ids
        assert "user_friendly" in metric_ids
        assert "perf_01" in metric_ids


class TestIntegrationScenarios:
    """Integration tests for comment features."""

    def test_full_evaluation_flow_with_comments(self):
        """Test a complete evaluation flow with all comment features."""
        # Create a rubric with mixed requirements
        rubric = EvaluationRubric(
            rubric_id="comprehensive",
            metrics=[
                MetricDefinition(
                    id="safety",
                    rubric="No harmful content",
                    mandatory=True,
                    requires_comment_on_fail=True
                ),
                MetricDefinition(
                    id="accuracy",
                    rubric="Information is accurate",
                    requires_comment_on_fail=False
                ),
                MetricDefinition(
                    id="clarity",
                    rubric="Response is clear",
                    requires_comment_on_fail=True
                )
            ],
            passing_score_threshold=1
        )

        # Create Pydantic model
        ResultModel = rubric.to_pydantic_model()

        # Test case 1: Successful evaluation with all required comments
        result = ResultModel(
            safety=True,
            accuracy=True,
            clarity=False,
            clarity_reasoning="Too technical for target audience",
            global_comment="Good attempt but needs simplification"
        )

        assert result.passes() is True  # Mandatory passed and score >= threshold
        assert result.global_comment == "Good attempt but needs simplification"

        # Test case 2: Missing required comment should fail validation
        # When clarity fails without a comment, validate_result should raise
        try:
            result2 = ResultModel(
                safety=True,
                accuracy=True,
                clarity=False  # Fails but no reasoning provided
            )
            # The passes() method will call validate_result which should raise
            result2.passes()
            assert False, "Should have raised ValueError for missing comment"
        except ValueError as e:
            assert "Missing required comments" in str(e)

    def test_json_schema_generation_with_comments(self):
        """Test JSON schema generation includes all comment fields."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[
                MetricDefinition(id="M1", rubric="Test 1", requires_comment_on_fail=True),
                MetricDefinition(id="M2", rubric="Test 2", requires_comment_on_fail=False),
            ],
            passing_score_threshold=1
        )

        schema = rubric.to_json_schema()

        # Check all expected fields
        assert "M1" in schema["properties"]
        assert "M1_reasoning" in schema["properties"]
        assert "M2" in schema["properties"]
        assert "M2_reasoning" in schema["properties"]
        assert "global_comment" in schema["properties"]

        # Check required fields (only metrics, not reasoning/comments)
        assert "M1" in schema["required"]
        assert "M2" in schema["required"]
        assert "M1_reasoning" not in schema["required"]
        assert "global_comment" not in schema["required"]

    def test_error_messages_are_helpful(self):
        """Test that error messages for missing comments are informative."""
        rubric = EvaluationRubric(
            rubric_id="test",
            metrics=[
                MetricDefinition(
                    id="safety",
                    rubric="Response must not contain harmful content",
                    requires_comment_on_fail=True
                ),
                MetricDefinition(
                    id="privacy",
                    rubric="Response must not expose PII",
                    requires_comment_on_fail=True
                )
            ],
            passing_score_threshold=0
        )

        result = {"safety": False, "privacy": False}

        with pytest.raises(ValueError) as exc_info:
            rubric.validate_result(result)

        error_message = str(exc_info.value)
        assert "Missing required comments" in error_message
        assert "safety" in error_message
        assert "privacy" in error_message
        assert "These metrics failed and require explanatory comments" in error_message