"""Tests for rubric discovery module."""

import pytest

from teval import EvaluationRubric, MetricDefinition
from teval.rubric_discovery import (
    CommentPattern,
    DiscoveryAnalyzer,
    DiscoveryReport,
    ExtractedComment,
)


class TestCommentPattern:
    """Tests for CommentPattern dataclass."""

    def test_basic_pattern(self):
        """Test creating a basic comment pattern."""
        pattern = CommentPattern(
            pattern_id="pii_exposure",
            keywords=["pii", "email", "address"],
            sample_comments=["Contains email address", "Shows PII"],
            frequency=5
        )
        assert pattern.pattern_id == "pii_exposure"
        assert len(pattern.keywords) == 3
        assert pattern.frequency == 5
        assert pattern.metric_id is None
        assert pattern.suggested_rubric is None

    def test_pattern_with_all_fields(self):
        """Test pattern with all optional fields."""
        pattern = CommentPattern(
            pattern_id="medical_advice",
            keywords=["medical", "advice", "treatment"],
            sample_comments=["Gives medical advice"],
            frequency=10,
            metric_id="safety",
            suggested_rubric="Response must not give medical advice"
        )
        assert pattern.metric_id == "safety"
        assert pattern.suggested_rubric == "Response must not give medical advice"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        pattern = CommentPattern(
            pattern_id="test",
            keywords=["kw1", "kw2"],
            sample_comments=["comment1"],
            frequency=3,
            suggested_rubric="Test rubric"
        )
        result = pattern.to_dict()
        assert result["pattern_id"] == "test"
        assert result["keywords"] == ["kw1", "kw2"]
        assert result["frequency"] == 3


class TestDiscoveryReport:
    """Tests for DiscoveryReport class."""

    def test_empty_report(self):
        """Test creating an empty report."""
        report = DiscoveryReport()
        assert report.patterns == []
        assert report.suggested_metrics == []
        assert report.total_evaluations == 0

    def test_report_with_patterns(self):
        """Test report with patterns."""
        patterns = [
            CommentPattern(
                pattern_id="pattern1",
                keywords=["kw1"],
                sample_comments=["comment1"],
                frequency=5,
                suggested_rubric="Must not do X"
            )
        ]
        report = DiscoveryReport(
            patterns=patterns,
            total_evaluations=10,
            failed_evaluations=5,
            total_comments=5
        )
        assert len(report.patterns) == 1
        assert report.total_evaluations == 10

    def test_to_rubric_basic(self):
        """Test generating a rubric from patterns."""
        patterns = [
            CommentPattern(
                pattern_id="pii_exposure",
                keywords=["pii", "email"],
                sample_comments=["Shows email"],
                frequency=10,
                suggested_rubric="Response must not expose PII"
            ),
            CommentPattern(
                pattern_id="medical_advice",
                keywords=["medical", "advice"],
                sample_comments=["Gives medical advice"],
                frequency=5,
                suggested_rubric="Response must not give medical advice"
            )
        ]
        report = DiscoveryReport(patterns=patterns)

        rubric = report.to_rubric(rubric_id="discovered_v1")
        assert rubric.rubric_id == "discovered_v1"
        assert len(rubric.metrics) == 2
        assert rubric.passing_score_threshold == 2

    def test_to_rubric_with_min_frequency(self):
        """Test rubric generation with minimum frequency filter."""
        patterns = [
            CommentPattern(
                pattern_id="common",
                keywords=["common"],
                sample_comments=["Common issue"],
                frequency=10,
                suggested_rubric="Avoid common issue"
            ),
            CommentPattern(
                pattern_id="rare",
                keywords=["rare"],
                sample_comments=["Rare issue"],
                frequency=2,
                suggested_rubric="Avoid rare issue"
            )
        ]
        report = DiscoveryReport(patterns=patterns)

        rubric = report.to_rubric(rubric_id="test", min_frequency=5)
        assert len(rubric.metrics) == 1
        assert rubric.metrics[0].id == "common"

    def test_to_rubric_with_max_metrics(self):
        """Test rubric generation with max metrics limit."""
        patterns = [
            CommentPattern(
                pattern_id=f"pattern_{i}",
                keywords=[f"kw{i}"],
                sample_comments=[f"comment{i}"],
                frequency=10 - i,
                suggested_rubric=f"Rule {i}"
            )
            for i in range(5)
        ]
        report = DiscoveryReport(patterns=patterns)

        rubric = report.to_rubric(rubric_id="test", max_metrics=3)
        assert len(rubric.metrics) == 3
        # Should be top 3 by frequency
        assert rubric.metrics[0].id == "pattern_0"

    def test_to_rubric_empty_patterns_raises(self):
        """Test that empty patterns raise ValueError."""
        report = DiscoveryReport(patterns=[])
        with pytest.raises(ValueError, match="No patterns meet"):
            report.to_rubric(rubric_id="test")

    def test_to_rubric_no_matching_frequency_raises(self):
        """Test error when no patterns meet frequency threshold."""
        patterns = [
            CommentPattern(
                pattern_id="low_freq",
                keywords=["kw"],
                sample_comments=["comment"],
                frequency=2,
                suggested_rubric="Rule"
            )
        ]
        report = DiscoveryReport(patterns=patterns)

        with pytest.raises(ValueError, match="No patterns meet min_frequency=10"):
            report.to_rubric(rubric_id="test", min_frequency=10)

    def test_to_dict(self):
        """Test report to dictionary conversion."""
        report = DiscoveryReport(
            total_evaluations=100,
            failed_evaluations=25,
            total_comments=50,
            analysis_method="llm"
        )
        result = report.to_dict()
        assert result["total_evaluations"] == 100
        assert result["analysis_method"] == "llm"

    def test_to_markdown(self):
        """Test markdown report generation."""
        patterns = [
            CommentPattern(
                pattern_id="test_pattern",
                keywords=["keyword1", "keyword2"],
                sample_comments=["Sample comment 1", "Sample comment 2"],
                frequency=5,
                suggested_rubric="Must not do X"
            )
        ]
        report = DiscoveryReport(
            patterns=patterns,
            total_evaluations=10,
            failed_evaluations=5,
            total_comments=5,
            analysis_method="keyword"
        )

        markdown = report.to_markdown()
        assert "# Rubric Discovery Report" in markdown
        assert "test_pattern" in markdown
        assert "keyword1" in markdown
        assert "Sample comment 1" in markdown


class TestDiscoveryAnalyzer:
    """Tests for DiscoveryAnalyzer class."""

    def test_analyzer_init(self):
        """Test analyzer initialization."""
        analyzer = DiscoveryAnalyzer()
        assert analyzer.llm_callable is None
        assert analyzer.min_keyword_length == 3

    def test_analyzer_with_llm(self):
        """Test analyzer with LLM callable."""
        def mock_llm(prompt: str) -> str:
            return '{"patterns": []}'

        analyzer = DiscoveryAnalyzer(llm_callable=mock_llm)
        assert analyzer.llm_callable is not None

    def test_analyze_empty_evaluations(self):
        """Test analyzing empty evaluation list."""
        analyzer = DiscoveryAnalyzer()
        report = analyzer.analyze([])
        assert report.total_evaluations == 0
        assert report.total_comments == 0
        assert len(report.patterns) == 0

    def test_analyze_no_comments(self):
        """Test analyzing evaluations without comments."""
        analyzer = DiscoveryAnalyzer()
        evaluations = [
            {"evaluation": {"metric1": True}},
            {"evaluation": {"metric1": False}},  # No reasoning
        ]
        report = analyzer.analyze(evaluations)
        assert report.total_evaluations == 2
        assert report.total_comments == 0

    def test_analyze_with_metric_reasoning(self):
        """Test analyzing evaluations with metric reasoning."""
        analyzer = DiscoveryAnalyzer()
        evaluations = [
            {
                "evaluation": {
                    "quality": False,
                    "quality_reasoning": "Contains PII - email address exposed"
                }
            },
            {
                "evaluation": {
                    "quality": False,
                    "quality_reasoning": "Shows user email in response"
                }
            },
            {
                "evaluation": {
                    "quality": False,
                    "quality_reasoning": "Exposes customer email"
                }
            }
        ]
        report = analyzer.analyze(evaluations)

        assert report.total_evaluations == 3
        assert report.total_comments == 3
        assert len(report.patterns) > 0
        assert report.analysis_method == "keyword"

        # Should find "email" as a pattern
        pattern_ids = [p.pattern_id for p in report.patterns]
        assert "email" in pattern_ids

    def test_analyze_with_global_comments(self):
        """Test analyzing evaluations with global comments."""
        analyzer = DiscoveryAnalyzer()
        evaluations = [
            {
                "evaluation": {"quality": True},
                "global_comment": "Response includes private information"
            },
            {
                "evaluation": {"quality": True},
                "global_comment": "Private data was exposed"
            }
        ]
        report = analyzer.analyze(evaluations, include_global_comments=True)

        assert report.total_comments == 2

    def test_analyze_excludes_global_comments(self):
        """Test excluding global comments from analysis."""
        analyzer = DiscoveryAnalyzer()
        evaluations = [
            {
                "evaluation": {"quality": False, "quality_reasoning": "Bad"},
                "global_comment": "This should be ignored"
            }
        ]
        report = analyzer.analyze(evaluations, include_global_comments=False)

        assert report.total_comments == 1

    def test_analyze_only_failed_metrics(self):
        """Test that only failed metrics' comments are extracted."""
        analyzer = DiscoveryAnalyzer()
        evaluations = [
            {
                "evaluation": {
                    "metric1": True,
                    "metric1_reasoning": "This should be ignored - metric passed",
                    "metric2": False,
                    "metric2_reasoning": "This should be included - metric failed"
                }
            }
        ]
        report = analyzer.analyze(evaluations)

        # Only the failed metric's reasoning should be included
        assert report.total_comments == 1

    def test_keyword_extraction_stopwords(self):
        """Test that stopwords are filtered from keywords."""
        analyzer = DiscoveryAnalyzer()
        evaluations = [
            {"evaluation": {"q": False, "q_reasoning": "The response is not good"}},
            {"evaluation": {"q": False, "q_reasoning": "This response is bad"}},
            {"evaluation": {"q": False, "q_reasoning": "Response was poor quality"}},
        ]
        report = analyzer.analyze(evaluations)

        # Stopwords like "the", "is", "not" should not be pattern IDs
        pattern_ids = [p.pattern_id.lower() for p in report.patterns]
        assert "the" not in pattern_ids
        assert "is" not in pattern_ids

    def test_keyword_min_length(self):
        """Test minimum keyword length filter."""
        analyzer = DiscoveryAnalyzer(min_keyword_length=4)
        evaluations = [
            {"evaluation": {"q": False, "q_reasoning": "Bad AI response here"}},
            {"evaluation": {"q": False, "q_reasoning": "AI did a bad job here"}},
        ]
        report = analyzer.analyze(evaluations)

        # "AI" (2 chars) should not appear, but "response" should
        pattern_ids = [p.pattern_id.lower() for p in report.patterns]
        assert "ai" not in pattern_ids

    def test_generates_suggested_metrics(self):
        """Test that suggested metrics are generated from patterns."""
        analyzer = DiscoveryAnalyzer()
        evaluations = [
            {"evaluation": {"q": False, "q_reasoning": "Privacy violation detected"}},
            {"evaluation": {"q": False, "q_reasoning": "Privacy issue found"}},
            {"evaluation": {"q": False, "q_reasoning": "Privacy concern here"}},
        ]
        report = analyzer.analyze(evaluations)

        assert len(report.suggested_metrics) > 0
        # All suggested metrics should require comments on fail
        for metric in report.suggested_metrics:
            assert metric.requires_comment_on_fail is True


class TestDiscoveryAnalyzerWithLLM:
    """Tests for LLM-based pattern extraction."""

    def test_llm_extraction_success(self):
        """Test successful LLM-based extraction."""
        def mock_llm(prompt: str) -> str:
            return '''
            {
                "patterns": [
                    {
                        "pattern_id": "pii_exposure",
                        "keywords": ["pii", "email", "personal"],
                        "suggested_rubric": "Response must not expose PII",
                        "sample_indices": [0, 1]
                    }
                ]
            }
            '''

        analyzer = DiscoveryAnalyzer(llm_callable=mock_llm)
        evaluations = [
            {"evaluation": {"q": False, "q_reasoning": "Contains PII"}},
            {"evaluation": {"q": False, "q_reasoning": "Shows email"}},
        ]
        report = analyzer.analyze(evaluations)

        assert report.analysis_method == "llm"
        assert len(report.patterns) == 1
        assert report.patterns[0].pattern_id == "pii_exposure"

    def test_llm_extraction_with_markdown(self):
        """Test LLM response wrapped in markdown code block."""
        def mock_llm(prompt: str) -> str:
            return '''
            Here's the analysis:
            ```json
            {
                "patterns": [
                    {
                        "pattern_id": "test",
                        "keywords": ["test"],
                        "suggested_rubric": "Test rubric",
                        "sample_indices": [0]
                    }
                ]
            }
            ```
            '''

        analyzer = DiscoveryAnalyzer(llm_callable=mock_llm)
        evaluations = [{"evaluation": {"q": False, "q_reasoning": "Test comment"}}]
        report = analyzer.analyze(evaluations)

        assert len(report.patterns) == 1

    def test_llm_fallback_on_error(self):
        """Test fallback to keyword extraction on LLM error."""
        def failing_llm(prompt: str) -> str:
            raise Exception("API Error")

        analyzer = DiscoveryAnalyzer(llm_callable=failing_llm)
        evaluations = [
            {"evaluation": {"q": False, "q_reasoning": "Privacy issue found"}},
            {"evaluation": {"q": False, "q_reasoning": "Privacy problem here"}},
        ]
        report = analyzer.analyze(evaluations)

        assert report.analysis_method == "keyword_fallback"
        assert len(report.patterns) > 0

    def test_llm_fallback_on_invalid_json(self):
        """Test fallback on invalid JSON response."""
        def bad_json_llm(prompt: str) -> str:
            return "This is not valid JSON at all!"

        analyzer = DiscoveryAnalyzer(llm_callable=bad_json_llm)
        # Need at least 2 comments with shared keywords to form a pattern
        evaluations = [
            {"evaluation": {"q": False, "q_reasoning": "Privacy issue detected"}},
            {"evaluation": {"q": False, "q_reasoning": "Privacy problem found"}},
        ]
        report = analyzer.analyze(evaluations)

        # Should fall back to keyword extraction
        assert report.analysis_method == "keyword_fallback"
        # Should find patterns from keywords (privacy appears in both)
        assert len(report.patterns) >= 1


class TestExtractedComment:
    """Tests for ExtractedComment internal class."""

    def test_basic_comment(self):
        """Test creating a basic extracted comment."""
        comment = ExtractedComment(text="Test comment")
        assert comment.text == "Test comment"
        assert comment.metric_id is None
        assert comment.passed is False

    def test_comment_with_metadata(self):
        """Test comment with all metadata."""
        comment = ExtractedComment(
            text="Test",
            metric_id="quality",
            passed=True,
            item_id="item_001"
        )
        assert comment.metric_id == "quality"
        assert comment.passed is True
        assert comment.item_id == "item_001"


class TestIntegrationScenarios:
    """Integration tests for end-to-end scenarios."""

    def test_full_discovery_workflow(self):
        """Test complete discovery workflow from comments to rubric."""
        # Sample evaluations with various issues
        evaluations = [
            {"evaluation": {"q": False, "q_reasoning": "Contains customer email address"}},
            {"evaluation": {"q": False, "q_reasoning": "Shows user's email in response"}},
            {"evaluation": {"q": False, "q_reasoning": "Email address was exposed"}},
            {"evaluation": {"q": False, "q_reasoning": "Gives specific medical advice"}},
            {"evaluation": {"q": False, "q_reasoning": "Medical treatment recommendation"}},
            {"evaluation": {"q": False, "q_reasoning": "Suggests medication dosage"}},
        ]

        # Analyze
        analyzer = DiscoveryAnalyzer()
        report = analyzer.analyze(evaluations)

        # Verify report
        assert report.total_evaluations == 6
        assert report.total_comments == 6
        assert len(report.patterns) >= 2  # Should find email and medical patterns

        # Generate rubric
        rubric = report.to_rubric(rubric_id="discovered_v1", min_frequency=2)

        # Verify rubric
        assert isinstance(rubric, EvaluationRubric)
        assert len(rubric.metrics) >= 1

        # All metrics should require comments
        for metric in rubric.metrics:
            assert metric.requires_comment_on_fail is True

    def test_discovery_with_mixed_evaluations(self):
        """Test discovery with mix of passed and failed evaluations."""
        evaluations = [
            {
                "evaluation": {
                    "safety": True,
                    "safety_reasoning": "Passed safety check",
                    "quality": False,
                    "quality_reasoning": "Poor grammar throughout"
                }
            },
            {
                "evaluation": {
                    "safety": False,
                    "safety_reasoning": "Contains harmful content",
                    "quality": True
                }
            },
            {
                "evaluation": {
                    "safety": False,
                    "safety_reasoning": "Harmful advice given",
                    "quality": False,
                    "quality_reasoning": "Bad grammar here too"
                }
            }
        ]

        analyzer = DiscoveryAnalyzer()
        report = analyzer.analyze(evaluations)

        # Should only extract comments from failed metrics
        assert report.total_comments == 4  # 2 safety fails + 2 quality fails

    def test_discovery_markdown_report(self):
        """Test generating a markdown report."""
        evaluations = [
            {"evaluation": {"q": False, "q_reasoning": "Issue type A"}},
            {"evaluation": {"q": False, "q_reasoning": "Issue type A again"}},
            {"evaluation": {"q": False, "q_reasoning": "Different issue B"}},
        ]

        analyzer = DiscoveryAnalyzer()
        report = analyzer.analyze(evaluations)
        markdown = report.to_markdown()

        # Verify markdown structure
        assert "# Rubric Discovery Report" in markdown
        assert "## Summary" in markdown
        assert "## Discovered Patterns" in markdown
        assert "Total evaluations analyzed: 3" in markdown
