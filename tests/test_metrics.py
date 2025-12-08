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
