"""Tests for alignment analysis module."""

import pytest

from teval.alignment import (
    AlignmentAnalyzer,
    AlignmentReport,
    BiasPattern,
    MetricAlignment,
)


class TestMetricAlignment:
    """Tests for MetricAlignment dataclass."""

    def test_basic_alignment(self):
        """Test creating a basic metric alignment."""
        alignment = MetricAlignment(
            metric_id="safety",
            agreement_rate=0.85,
            cohens_kappa=0.70,
            human_pass_rate=0.80,
            llm_pass_rate=0.82,
            sample_count=100,
        )
        assert alignment.metric_id == "safety"
        assert alignment.agreement_rate == 0.85
        assert alignment.cohens_kappa == 0.70
        assert alignment.bias_direction is None
        assert alignment.confidence_score == 0.0

    def test_alignment_with_bias(self):
        """Test alignment with bias direction."""
        alignment = MetricAlignment(
            metric_id="accuracy",
            agreement_rate=0.72,
            cohens_kappa=0.45,
            human_pass_rate=0.65,
            llm_pass_rate=0.85,
            sample_count=50,
            bias_direction="llm_lenient",
            confidence_score=0.75,
        )
        assert alignment.bias_direction == "llm_lenient"
        assert alignment.confidence_score == 0.75

    def test_to_dict(self):
        """Test conversion to dictionary."""
        alignment = MetricAlignment(
            metric_id="test",
            agreement_rate=0.90,
            cohens_kappa=0.80,
            human_pass_rate=0.85,
            llm_pass_rate=0.88,
            sample_count=100,
        )
        result = alignment.to_dict()
        assert result["metric_id"] == "test"
        assert result["agreement_rate"] == 0.90
        assert result["cohens_kappa"] == 0.80
        assert result["sample_count"] == 100


class TestBiasPattern:
    """Tests for BiasPattern dataclass."""

    def test_basic_pattern(self):
        """Test creating a basic bias pattern."""
        pattern = BiasPattern(
            pattern_type="llm_lenient",
            affected_metrics=["accuracy", "completeness"],
            description="LLM tends to pass more often than humans",
            severity="medium",
            sample_size=150,
        )
        assert pattern.pattern_type == "llm_lenient"
        assert len(pattern.affected_metrics) == 2
        assert pattern.severity == "medium"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        pattern = BiasPattern(
            pattern_type="llm_strict",
            affected_metrics=["safety"],
            description="LLM is stricter than humans",
            severity="low",
            sample_size=50,
        )
        result = pattern.to_dict()
        assert result["pattern_type"] == "llm_strict"
        assert result["affected_metrics"] == ["safety"]
        assert result["sample_size"] == 50


class TestAlignmentReport:
    """Tests for AlignmentReport class."""

    def test_empty_report(self):
        """Test creating an empty report."""
        report = AlignmentReport()
        assert report.human_kappa == 0.0
        assert report.alignment_rate == 0.0
        assert report.metric_alignments == []
        assert report.confidence_level == "low"

    def test_report_with_data(self):
        """Test report with alignment data."""
        alignments = [
            MetricAlignment(
                metric_id="m1",
                agreement_rate=0.90,
                cohens_kappa=0.80,
                human_pass_rate=0.85,
                llm_pass_rate=0.88,
                sample_count=100,
            )
        ]
        report = AlignmentReport(
            human_kappa=0.75,
            alignment_rate=0.85,
            metric_alignments=alignments,
            total_evaluations=200,
            total_items=100,
        )
        assert report.human_kappa == 0.75
        assert len(report.metric_alignments) == 1

    def test_passes_human_threshold(self):
        """Test human threshold property."""
        report = AlignmentReport(human_kappa=0.75)
        assert report.passes_human_threshold is True

        report_low = AlignmentReport(human_kappa=0.65)
        assert report_low.passes_human_threshold is False

    def test_passes_alignment_threshold(self):
        """Test alignment threshold property."""
        report = AlignmentReport(alignment_rate=0.85)
        assert report.passes_alignment_threshold is True

        report_low = AlignmentReport(alignment_rate=0.75)
        assert report_low.passes_alignment_threshold is False

    def test_to_dict(self):
        """Test report to dictionary conversion."""
        report = AlignmentReport(
            human_kappa=0.80,
            alignment_rate=0.85,
            total_evaluations=100,
            total_items=50,
            confidence_level="medium",
        )
        result = report.to_dict()
        assert result["human_kappa"] == 0.80
        assert result["alignment_rate"] == 0.85
        assert result["total_items"] == 50

    def test_to_markdown(self):
        """Test markdown report generation."""
        alignments = [
            MetricAlignment(
                metric_id="safety",
                agreement_rate=0.95,
                cohens_kappa=0.90,
                human_pass_rate=0.90,
                llm_pass_rate=0.92,
                sample_count=100,
            )
        ]
        report = AlignmentReport(
            human_kappa=0.75,
            human_llm_kappa=0.70,
            alignment_rate=0.85,
            metric_alignments=alignments,
            high_alignment_metrics=["safety"],
            total_evaluations=200,
            total_items=100,
        )

        markdown = report.to_markdown()
        assert "# Alignment Analysis Report" in markdown
        assert "Human Inter-rater" in markdown
        assert "safety" in markdown
        assert "0.85" in markdown or "85" in markdown

    def test_get_recommendations_low_human_agreement(self):
        """Test recommendations for low human agreement."""
        report = AlignmentReport(human_kappa=0.55)
        recommendations = report.get_recommendations()
        assert any("inter-rater" in r.lower() for r in recommendations)

    def test_get_recommendations_low_alignment(self):
        """Test recommendations for low alignment."""
        report = AlignmentReport(alignment_rate=0.65, human_kappa=0.8)
        recommendations = report.get_recommendations()
        assert any("alignment" in r.lower() for r in recommendations)

    def test_get_recommendations_low_confidence(self):
        """Test recommendations for low confidence."""
        report = AlignmentReport(confidence_level="low")
        recommendations = report.get_recommendations()
        assert any("sample" in r.lower() for r in recommendations)


class TestCohensKappa:
    """Tests for Cohen's Kappa calculation."""

    def test_perfect_agreement(self):
        """Kappa = 1.0 when raters perfectly agree."""
        analyzer = AlignmentAnalyzer()
        ratings_a = [True, True, False, False, True]
        ratings_b = [True, True, False, False, True]
        kappa = analyzer.calculate_cohens_kappa(ratings_a, ratings_b)
        assert kappa == 1.0

    def test_no_agreement_chance(self):
        """Kappa near 0.0 when agreement equals chance."""
        analyzer = AlignmentAnalyzer()
        # 50/50 split with exactly chance agreement
        ratings_a = [True, True, False, False]
        ratings_b = [True, False, True, False]
        kappa = analyzer.calculate_cohens_kappa(ratings_a, ratings_b)
        assert abs(kappa) < 0.1  # Near zero

    def test_perfect_disagreement(self):
        """Kappa < 0 when raters systematically disagree."""
        analyzer = AlignmentAnalyzer()
        ratings_a = [True, True, True, False, False]
        ratings_b = [False, False, False, True, True]
        kappa = analyzer.calculate_cohens_kappa(ratings_a, ratings_b)
        assert kappa < 0

    def test_empty_input(self):
        """Handle empty input gracefully."""
        analyzer = AlignmentAnalyzer()
        kappa = analyzer.calculate_cohens_kappa([], [])
        assert kappa == 0.0

    def test_mismatched_lengths(self):
        """Handle mismatched input lengths."""
        analyzer = AlignmentAnalyzer()
        kappa = analyzer.calculate_cohens_kappa([True, False], [True])
        assert kappa == 0.0

    def test_all_same_value(self):
        """Handle case where all ratings are same."""
        analyzer = AlignmentAnalyzer()
        ratings_a = [True, True, True, True]
        ratings_b = [True, True, True, True]
        kappa = analyzer.calculate_cohens_kappa(ratings_a, ratings_b)
        assert kappa == 1.0  # Perfect agreement

    def test_partial_agreement(self):
        """Test partial agreement scenario."""
        analyzer = AlignmentAnalyzer()
        # 80% agreement
        ratings_a = [True, True, True, True, False]
        ratings_b = [True, True, True, False, False]
        kappa = analyzer.calculate_cohens_kappa(ratings_a, ratings_b)
        assert 0 < kappa < 1  # Partial agreement


class TestFleissKappa:
    """Tests for Fleiss' Kappa calculation."""

    def test_three_raters_perfect(self):
        """Perfect agreement among 3 raters."""
        analyzer = AlignmentAnalyzer()
        matrix = [
            [True, True, True],
            [False, False, False],
            [True, True, True],
        ]
        kappa = analyzer.calculate_fleiss_kappa(matrix)
        assert kappa == 1.0

    def test_three_raters_partial(self):
        """Partial agreement among 3 raters."""
        analyzer = AlignmentAnalyzer()
        matrix = [
            [True, True, False],  # 2/3 agree
            [False, False, False],  # 3/3 agree
            [True, False, True],  # 2/3 agree
        ]
        kappa = analyzer.calculate_fleiss_kappa(matrix)
        assert 0 < kappa < 1

    def test_empty_matrix(self):
        """Handle empty matrix."""
        analyzer = AlignmentAnalyzer()
        kappa = analyzer.calculate_fleiss_kappa([])
        assert kappa == 0.0

    def test_single_item_matrix(self):
        """Handle matrix with single item."""
        analyzer = AlignmentAnalyzer()
        matrix = [[True, True, False]]
        kappa = analyzer.calculate_fleiss_kappa(matrix)
        # Should handle gracefully
        assert isinstance(kappa, float)

    def test_missing_values(self):
        """Handle None values in matrix."""
        analyzer = AlignmentAnalyzer()
        matrix = [
            [True, True, None],
            [False, False, False],
            [True, None, True],
        ]
        kappa = analyzer.calculate_fleiss_kappa(matrix)
        assert isinstance(kappa, float)


class TestAlignmentAnalyzer:
    """Integration tests for AlignmentAnalyzer."""

    def test_analyzer_init(self):
        """Test analyzer initialization."""
        analyzer = AlignmentAnalyzer()
        assert analyzer.alignment_threshold == 0.80
        assert analyzer.kappa_threshold == 0.70
        assert analyzer.min_samples_per_metric == 10

    def test_analyzer_custom_thresholds(self):
        """Test analyzer with custom thresholds."""
        analyzer = AlignmentAnalyzer(
            alignment_threshold=0.90,
            kappa_threshold=0.80,
            min_samples_per_metric=20,
        )
        assert analyzer.alignment_threshold == 0.90
        assert analyzer.kappa_threshold == 0.80

    def test_analyze_empty_evaluations(self):
        """Test analyzing empty evaluation list."""
        analyzer = AlignmentAnalyzer()
        report = analyzer.analyze([])
        assert report.total_evaluations == 0
        assert "No human evaluations" in report.warnings[0]

    def test_analyze_no_llm_evaluations(self):
        """Test analyzing human evaluations only."""
        analyzer = AlignmentAnalyzer()
        human_evals = [
            {"item_id": "1", "evaluator_id": "a", "evaluation": {"m1": True}},
            {"item_id": "1", "evaluator_id": "b", "evaluation": {"m1": True}},
            {"item_id": "2", "evaluator_id": "a", "evaluation": {"m1": False}},
            {"item_id": "2", "evaluator_id": "b", "evaluation": {"m1": False}},
        ]
        report = analyzer.analyze(human_evals)
        assert report.total_items == 2
        assert report.human_kappa > 0  # Should have agreement

    def test_analyze_with_llm_evaluations(self):
        """Test analyzing human and LLM evaluations."""
        analyzer = AlignmentAnalyzer()
        human_evals = [
            {"item_id": "1", "evaluation": {"m1": True, "m2": True}},
            {"item_id": "2", "evaluation": {"m1": True, "m2": False}},
        ]
        llm_evals = [
            {"item_id": "1", "evaluation": {"m1": True, "m2": True}},
            {"item_id": "2", "evaluation": {"m1": True, "m2": True}},  # Disagrees on m2
        ]
        report = analyzer.analyze(human_evals, llm_evals)
        assert report.total_items == 2
        assert len(report.metric_alignments) == 2

    def test_analyze_no_matching_items(self):
        """Test when no item_ids match."""
        analyzer = AlignmentAnalyzer()
        human_evals = [{"item_id": "a", "evaluation": {"m1": True}}]
        llm_evals = [{"item_id": "b", "evaluation": {"m1": True}}]
        report = analyzer.analyze(human_evals, llm_evals)
        assert any("No matching item_ids" in w for w in report.warnings)

    def test_high_alignment_scenario(self):
        """Test when human and LLM mostly agree."""
        analyzer = AlignmentAnalyzer()
        human_evals = [
            {"item_id": f"item_{i}", "evaluation": {"m1": True, "m2": True}}
            for i in range(20)
        ]
        llm_evals = [
            {"item_id": f"item_{i}", "evaluation": {"m1": True, "m2": True}}
            for i in range(20)
        ]
        report = analyzer.analyze(human_evals, llm_evals)
        assert report.alignment_rate == 1.0
        assert "m1" in report.high_alignment_metrics
        assert "m2" in report.high_alignment_metrics


class TestBiasDetection:
    """Tests for bias pattern detection."""

    def test_detect_llm_lenient(self):
        """Test detection of LLM leniency."""
        analyzer = AlignmentAnalyzer()
        # LLM passes more than humans
        human_evals = [
            {"item_id": f"item_{i}", "evaluation": {"quality": i < 30}}
            for i in range(100)
        ]
        llm_evals = [
            {"item_id": f"item_{i}", "evaluation": {"quality": i < 70}}
            for i in range(100)
        ]
        report = analyzer.analyze(human_evals, llm_evals)
        assert any(p.pattern_type == "llm_lenient" for p in report.bias_patterns)

    def test_detect_llm_strict(self):
        """Test detection of LLM strictness."""
        analyzer = AlignmentAnalyzer()
        # Humans pass more than LLM
        human_evals = [
            {"item_id": f"item_{i}", "evaluation": {"quality": i < 70}}
            for i in range(100)
        ]
        llm_evals = [
            {"item_id": f"item_{i}", "evaluation": {"quality": i < 30}}
            for i in range(100)
        ]
        report = analyzer.analyze(human_evals, llm_evals)
        assert any(p.pattern_type == "llm_strict" for p in report.bias_patterns)

    def test_no_bias_when_balanced(self):
        """Test no bias detected when rates are similar."""
        analyzer = AlignmentAnalyzer()
        human_evals = [
            {"item_id": f"item_{i}", "evaluation": {"quality": True}}
            for i in range(20)
        ]
        llm_evals = [
            {"item_id": f"item_{i}", "evaluation": {"quality": True}}
            for i in range(20)
        ]
        report = analyzer.analyze(human_evals, llm_evals)
        # Should not have lenient or strict patterns
        lenient_strict = [
            p for p in report.bias_patterns
            if p.pattern_type in ("llm_lenient", "llm_strict")
        ]
        assert len(lenient_strict) == 0

    def test_detect_inconsistent_pattern(self):
        """Test detection of inconsistent disagreement pattern."""
        analyzer = AlignmentAnalyzer()
        # Similar pass rates but random disagreements
        import random
        random.seed(42)

        human_evals = []
        llm_evals = []
        for i in range(100):
            # Both have ~50% pass rate but disagree on specific items
            human_val = random.random() < 0.5
            # LLM sometimes agrees, sometimes doesn't
            llm_val = human_val if random.random() < 0.5 else not human_val
            human_evals.append({"item_id": f"item_{i}", "evaluation": {"m1": human_val}})
            llm_evals.append({"item_id": f"item_{i}", "evaluation": {"m1": llm_val}})

        report = analyzer.analyze(human_evals, llm_evals)
        # With random disagreements, kappa should be low but rates similar
        if report.metric_alignments:
            m = report.metric_alignments[0]
            # Check if pattern was detected when conditions are met
            if m.cohens_kappa < 0.4 and abs(m.human_pass_rate - m.llm_pass_rate) < 0.1:
                assert any(p.pattern_type == "inconsistent" for p in report.bias_patterns)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_single_item(self):
        """Handle single item with low confidence."""
        analyzer = AlignmentAnalyzer()
        human_evals = [{"item_id": "1", "evaluation": {"m1": True}}]
        llm_evals = [{"item_id": "1", "evaluation": {"m1": True}}]
        report = analyzer.analyze(human_evals, llm_evals)
        assert report.confidence_level == "low"

    def test_missing_evaluation_key(self):
        """Handle missing evaluation key gracefully."""
        analyzer = AlignmentAnalyzer()
        human_evals = [{"item_id": "1"}]  # No evaluation key
        llm_evals = [{"item_id": "1", "evaluation": {"m1": True}}]
        report = analyzer.analyze(human_evals, llm_evals)
        # Should not crash

    def test_non_boolean_values(self):
        """Handle non-boolean values in evaluations."""
        analyzer = AlignmentAnalyzer()
        human_evals = [
            {"item_id": "1", "evaluation": {"m1": True, "m1_reasoning": "Good"}}
        ]
        llm_evals = [
            {"item_id": "1", "evaluation": {"m1": True, "m1_reasoning": "Also good"}}
        ]
        report = analyzer.analyze(human_evals, llm_evals)
        # Should only consider boolean values
        assert len(report.metric_alignments) == 1
        assert report.metric_alignments[0].metric_id == "m1"

    def test_multiple_human_evaluators_per_item(self):
        """Calculate inter-rater reliability among multiple humans."""
        analyzer = AlignmentAnalyzer()
        human_evals = [
            {"item_id": "1", "evaluator_id": "a", "evaluation": {"m1": True}},
            {"item_id": "1", "evaluator_id": "b", "evaluation": {"m1": True}},
            {"item_id": "1", "evaluator_id": "c", "evaluation": {"m1": False}},
            {"item_id": "2", "evaluator_id": "a", "evaluation": {"m1": False}},
            {"item_id": "2", "evaluator_id": "b", "evaluation": {"m1": False}},
            {"item_id": "2", "evaluator_id": "c", "evaluation": {"m1": False}},
        ]
        report = analyzer.analyze(human_evals)
        # Should calculate inter-rater reliability
        assert report.human_kappa > 0  # Some agreement

    def test_single_evaluator_warning(self):
        """Warn when only single evaluator."""
        analyzer = AlignmentAnalyzer()
        human_evals = [
            {"item_id": "1", "evaluation": {"m1": True}},
            {"item_id": "2", "evaluation": {"m1": False}},
        ]
        report = analyzer.analyze(human_evals)
        assert any("single" in w.lower() for w in report.warnings)

    def test_global_comment_excluded(self):
        """Global comment should not be treated as a metric."""
        analyzer = AlignmentAnalyzer()
        human_evals = [
            {
                "item_id": "1",
                "evaluation": {"m1": True, "global_comment": "Overall good"},
            }
        ]
        llm_evals = [{"item_id": "1", "evaluation": {"m1": True}}]
        report = analyzer.analyze(human_evals, llm_evals)
        metric_ids = [m.metric_id for m in report.metric_alignments]
        assert "global_comment" not in metric_ids


class TestIntegrationScenarios:
    """End-to-end integration tests."""

    def test_full_workflow(self):
        """Test complete alignment analysis workflow."""
        # Create realistic evaluation data
        human_evals = []
        llm_evals = []

        for i in range(50):
            # Humans and LLM mostly agree on safety
            safety_human = True
            safety_llm = True

            # LLM is more lenient on accuracy
            accuracy_human = i < 25  # 50% pass
            accuracy_llm = i < 40  # 80% pass

            # Good agreement on helpfulness
            helpful_human = i < 40
            helpful_llm = i < 38

            human_evals.append({
                "item_id": f"item_{i}",
                "evaluator_id": "human_1",
                "evaluation": {
                    "safety": safety_human,
                    "accuracy": accuracy_human,
                    "helpfulness": helpful_human,
                },
            })

            llm_evals.append({
                "item_id": f"item_{i}",
                "model": "gpt-4",
                "evaluation": {
                    "safety": safety_llm,
                    "accuracy": accuracy_llm,
                    "helpfulness": helpful_llm,
                },
            })

        analyzer = AlignmentAnalyzer()
        report = analyzer.analyze(human_evals, llm_evals)

        # Verify report structure
        assert report.total_items == 50
        assert len(report.metric_alignments) == 3

        # Safety should have high alignment
        safety_alignment = next(
            m for m in report.metric_alignments if m.metric_id == "safety"
        )
        assert safety_alignment.agreement_rate == 1.0

        # Accuracy should show LLM lenient bias
        accuracy_alignment = next(
            m for m in report.metric_alignments if m.metric_id == "accuracy"
        )
        assert accuracy_alignment.bias_direction == "llm_lenient"

        # Should detect bias pattern
        assert any(p.pattern_type == "llm_lenient" for p in report.bias_patterns)

        # Markdown should be valid
        markdown = report.to_markdown()
        assert "safety" in markdown
        assert "accuracy" in markdown

        # Recommendations should include accuracy fix
        recommendations = report.get_recommendations()
        assert any("accuracy" in r.lower() for r in recommendations)

    def test_confidence_levels(self):
        """Test confidence level determination."""
        analyzer = AlignmentAnalyzer()

        # Low confidence (< 10 items)
        report_low = analyzer.analyze(
            [{"item_id": f"i{i}", "evaluation": {"m1": True}} for i in range(5)],
            [{"item_id": f"i{i}", "evaluation": {"m1": True}} for i in range(5)],
        )
        assert report_low.confidence_level == "low"

        # Medium confidence (10-30 items)
        report_med = analyzer.analyze(
            [{"item_id": f"i{i}", "evaluation": {"m1": True}} for i in range(20)],
            [{"item_id": f"i{i}", "evaluation": {"m1": True}} for i in range(20)],
        )
        assert report_med.confidence_level == "medium"

        # Good confidence (30-100 items)
        report_good = analyzer.analyze(
            [{"item_id": f"i{i}", "evaluation": {"m1": True}} for i in range(50)],
            [{"item_id": f"i{i}", "evaluation": {"m1": True}} for i in range(50)],
        )
        assert report_good.confidence_level == "good"

        # High confidence (100+ items)
        report_high = analyzer.analyze(
            [{"item_id": f"i{i}", "evaluation": {"m1": True}} for i in range(120)],
            [{"item_id": f"i{i}", "evaluation": {"m1": True}} for i in range(120)],
        )
        assert report_high.confidence_level == "high"
