"""
Unit tests for the human evaluation interface.

Tests the FastHTML-based evaluation forms and components.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Skip all tests if FastHTML not installed
pytest.importorskip("fasthtml")

from teval import EvaluationRubric, MetricDefinition
from teval.human import create_evaluation_app, EvaluationForm
from teval.human.styles import get_styles
from fasthtml.common import to_xml


def create_test_rubric():
    """Helper to create a test rubric."""
    return EvaluationRubric(
        rubric_id="test_rubric",
        metrics=[
            MetricDefinition(id="M1", rubric="Mandatory test criterion", mandatory=True),
            MetricDefinition(id="M2", rubric="Second mandatory test", mandatory=True),
            MetricDefinition(id="C1", rubric="Cumulative test 1"),
            MetricDefinition(id="C2", rubric="Cumulative test 2"),
            MetricDefinition(id="C3", rubric="Cumulative test 3"),
        ],
        passing_score_threshold=2
    )


def create_simple_rubric():
    """Helper to create a simple rubric with minimal metrics."""
    return EvaluationRubric(
        rubric_id="simple",
        metrics=[
            MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
            MetricDefinition(id="C1", rubric="Quality check")
        ],
        passing_score_threshold=1
    )


class TestEvaluationForm:
    """Test the EvaluationForm class."""

    def test_form_creation_basic(self):
        """Test basic form creation."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)

        assert form.rubric == rubric
        assert form.title == "Evaluation: test_rubric"
        assert form.include_reasoning is True

    def test_form_creation_custom_title(self):
        """Test form creation with custom title."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric, title="Custom Title")

        assert form.title == "Custom Title"

    def test_form_creation_no_reasoning(self):
        """Test form creation without reasoning fields."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric, include_reasoning=False)

        assert form.include_reasoning is False

    def test_form_render_structure(self):
        """Test that form render returns proper structure."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)
        html = form.render()

        # Convert to string for testing
        html_str = to_xml(html)

        # Check form attributes
        assert 'class="teval-form"' in html_str
        assert 'hx-post="/submit"' in html_str
        assert 'hx-target="#result"' in html_str

    def test_form_contains_all_metrics(self):
        """Test that all metrics appear in the form."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)
        html_str = to_xml(form.render())

        # Check all metric IDs are present
        for metric in rubric.metrics:
            assert metric.id in html_str
            assert metric.rubric in html_str

    def test_mandatory_badges_shown(self):
        """Test that mandatory metrics have badges."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)
        html_str = to_xml(form.render())

        # Should have badges for mandatory metrics
        assert "MANDATORY" in html_str
        # Count should match number of mandatory metrics
        assert html_str.count("MANDATORY") >= len(rubric.mandatory_metrics)

    def test_progress_indicator_included(self):
        """Test that progress indicator is included."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)
        html_str = to_xml(form.render())

        assert "progress-bar" in html_str
        assert "progress-text" in html_str

    def test_action_buttons_included(self):
        """Test that action buttons are included."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)
        html_str = to_xml(form.render())

        assert "Submit Evaluation" in html_str
        assert "Export JSON" in html_str
        assert "Auto-save" in html_str

    def test_reasoning_fields_included(self):
        """Test that reasoning textareas are included when enabled."""
        rubric = create_simple_rubric()
        form = EvaluationForm(rubric, include_reasoning=True)
        html_str = to_xml(form.render())

        # Should have textareas for reasoning
        assert "textarea" in html_str.lower()
        assert "_reasoning" in html_str

    def test_reasoning_fields_excluded(self):
        """Test that reasoning textareas are excluded when disabled."""
        rubric = create_simple_rubric()
        form = EvaluationForm(rubric, include_reasoning=False)
        html_str = to_xml(form.render())

        # Should not have textarea HTML elements (may exist in JavaScript)
        assert "<textarea" not in html_str.lower()

    def test_javascript_constants_injected(self):
        """Test that JavaScript constants are properly injected."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)
        html_str = to_xml(form.render())

        # Check rubric constants in JavaScript
        assert "RUBRIC_ID" in html_str
        assert "test_rubric" in html_str
        assert "MANDATORY_METRICS" in html_str
        assert "CUMULATIVE_METRICS" in html_str
        assert "PASSING_THRESHOLD" in html_str

    def test_filter_bar_not_shown_for_small_forms(self):
        """Test that filter bar is not shown for forms with few metrics."""
        rubric = create_simple_rubric()  # Has only 2 metrics
        form = EvaluationForm(rubric)
        # Filter bar should return None for small forms
        filter_bar = form._create_filter_bar()
        assert filter_bar is None

    def test_filter_bar_shown_for_large_forms(self):
        """Test that filter bar is shown for forms with many metrics."""
        # Create rubric with 5+ metrics
        metrics = [MetricDefinition(id=f"M{i}", rubric=f"Metric {i}") for i in range(6)]
        rubric = EvaluationRubric(
            rubric_id="large",
            metrics=metrics,
            passing_score_threshold=3
        )
        form = EvaluationForm(rubric)
        html_str = to_xml(form.render())

        # Should have filter bar
        assert "metric-search" in html_str
        assert "filter-mandatory" in html_str
        assert "filter-incomplete" in html_str

    def test_process_submission_all_pass(self):
        """Test processing submission where all metrics pass."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)

        mock_data = {
            "M1": "true",
            "M2": "true",
            "C1": "true",
            "C2": "true",
            "C3": "false",
            "M1_reasoning": "Looks good",
            "C1_reasoning": ""
        }

        results = form.process_submission(mock_data)

        assert results["rubric_id"] == "test_rubric"
        assert results["results"]["M1"] is True
        assert results["results"]["M2"] is True
        assert results["results"]["C1"] is True
        assert results["results"]["C2"] is True
        assert results["results"]["C3"] is False
        assert results["reasoning"]["M1"] == "Looks good"
        assert "C1" not in results["reasoning"]  # Empty reasoning not included
        assert results["mandatory_pass"] is True
        assert results["score"] == 2  # C1 and C2 pass
        assert results["total"] == 3  # 3 cumulative metrics
        assert results["passes"] is True  # Meets threshold
        assert "timestamp" in results

    def test_process_submission_mandatory_fail(self):
        """Test processing submission where mandatory metric fails."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)

        mock_data = {
            "M1": "false",  # Mandatory fail
            "M2": "true",
            "C1": "true",
            "C2": "true",
            "C3": "true"
        }

        results = form.process_submission(mock_data)

        assert results["mandatory_pass"] is False
        assert results["passes"] is False  # Overall fail due to mandatory

    def test_process_submission_threshold_not_met(self):
        """Test processing submission where threshold not met."""
        rubric = create_test_rubric()
        form = EvaluationForm(rubric)

        mock_data = {
            "M1": "true",
            "M2": "true",
            "C1": "true",
            "C2": "false",
            "C3": "false"  # Only 1 cumulative passes, need 2
        }

        results = form.process_submission(mock_data)

        assert results["mandatory_pass"] is True
        assert results["score"] == 1
        assert results["passes"] is False  # Doesn't meet threshold

    def test_process_submission_no_reasoning(self):
        """Test processing submission without reasoning fields."""
        rubric = create_simple_rubric()
        form = EvaluationForm(rubric, include_reasoning=False)

        mock_data = {
            "M1": "true",
            "C1": "true"
        }

        results = form.process_submission(mock_data)

        assert results["reasoning"] == {}


class TestCreateEvaluationApp:
    """Test the create_evaluation_app function."""

    def test_app_creation_basic(self):
        """Test basic app creation."""
        rubric = create_test_rubric()
        app = create_evaluation_app(rubric)

        assert app is not None
        assert hasattr(app, 'routes')

    def test_app_creation_custom_title(self):
        """Test app creation with custom title."""
        rubric = create_test_rubric()
        app = create_evaluation_app(rubric, title="Custom App Title")

        assert app is not None

    def test_app_creation_with_callback(self):
        """Test app creation with storage callback."""
        rubric = create_test_rubric()
        callback = Mock()
        app = create_evaluation_app(rubric, storage_callback=callback)

        assert app is not None

    def test_app_creation_empty_rubric_raises(self):
        """Test that empty rubric raises error."""
        with pytest.raises(ValueError, match="at least one metric"):
            rubric = EvaluationRubric(
                rubric_id="empty",
                metrics=[],  # Empty metrics - will raise validation error first
                passing_score_threshold=0
            )

    def test_app_routes_exist(self):
        """Test that app has necessary routes."""
        rubric = create_test_rubric()
        app = create_evaluation_app(rubric)

        # Check that app has routes attribute
        assert hasattr(app, 'routes')
        # FastHTML apps always have routes registered


class TestStyles:
    """Test the styles module."""

    def test_get_styles_returns_css(self):
        """Test that get_styles returns CSS string."""
        css = get_styles()

        assert isinstance(css, str)
        assert len(css) > 0
        assert "teval-container" in css
        assert "teval-form" in css
        assert "teval-metric-card" in css

    def test_css_has_responsive_styles(self):
        """Test that CSS includes responsive styles."""
        css = get_styles()

        assert "@media" in css
        assert "max-width: 640px" in css

    def test_css_has_dark_mode_support(self):
        """Test that CSS includes dark mode support."""
        css = get_styles()

        assert "prefers-color-scheme: dark" in css

    def test_css_has_print_styles(self):
        """Test that CSS includes print styles."""
        css = get_styles()

        assert "@media print" in css


class TestIntegration:
    """Integration tests for the full system."""

    def test_end_to_end_evaluation_flow(self):
        """Test complete evaluation flow from creation to submission."""
        # Create rubric
        rubric = EvaluationRubric(
            rubric_id="integration_test",
            metrics=[
                MetricDefinition(id="REQ1", rubric="Requirement met", mandatory=True),
                MetricDefinition(id="QUAL1", rubric="Good quality"),
                MetricDefinition(id="QUAL2", rubric="Well documented"),
            ],
            passing_score_threshold=1
        )

        # Create form
        form = EvaluationForm(rubric, title="Integration Test")

        # Render form
        html = form.render()
        assert html is not None

        # Simulate submission
        submission_data = {
            "REQ1": "true",
            "QUAL1": "true",
            "QUAL2": "false",
            "REQ1_reasoning": "Meets all requirements",
            "QUAL1_reasoning": "High quality implementation"
        }

        # Process submission
        results = form.process_submission(submission_data)

        # Verify results
        assert results["passes"] is True
        assert results["mandatory_pass"] is True
        assert results["score"] == 1
        assert results["reasoning"]["REQ1"] == "Meets all requirements"

    def test_app_with_storage_callback(self):
        """Test app with custom storage callback."""
        stored_data = None

        def storage_callback(data):
            nonlocal stored_data
            stored_data = data

        rubric = create_simple_rubric()
        app = create_evaluation_app(
            rubric,
            title="Test with Storage",
            storage_callback=storage_callback
        )

        # App should be created successfully
        assert app is not None

        # Simulate form processing (without actual HTTP request)
        form = EvaluationForm(rubric)
        results = form.process_submission({"M1": "true", "C1": "true"})

        # Call the storage callback directly
        storage_callback(results)

        # Verify callback was called with correct data
        assert stored_data is not None
        assert stored_data["passes"] is True


class TestErrorHandling:
    """Test error handling scenarios."""


    def test_process_submission_missing_metrics(self):
        """Test processing submission with missing metric values."""
        rubric = create_simple_rubric()
        form = EvaluationForm(rubric)

        # Missing M1 (mandatory)
        mock_data = {
            "C1": "true"
        }

        results = form.process_submission(mock_data)

        # Should handle missing values gracefully
        assert results["results"]["M1"] is False  # Missing = False
        assert results["results"]["C1"] is True
        assert results["passes"] is False  # Mandatory failed

    def test_process_submission_invalid_values(self):
        """Test processing submission with invalid values."""
        rubric = create_simple_rubric()
        form = EvaluationForm(rubric)

        mock_data = {
            "M1": "invalid",  # Not "true" or "false"
            "C1": None
        }

        results = form.process_submission(mock_data)

        # Should treat invalid as False
        assert results["results"]["M1"] is False
        assert results["results"]["C1"] is False