"""
Rubric discovery from SME feedback.

This module provides tools to analyze free-form comments from human evaluations
to extract common themes and generate suggested metrics for rubric refinement.

The discovery process helps convert unstructured feedback into structured
evaluation rubrics by identifying patterns in evaluator comments.

Classes
-------
CommentPattern
    Represents a discovered pattern in evaluation comments.
DiscoveryReport
    Results container for rubric discovery analysis.
DiscoveryAnalyzer
    Main class for analyzing evaluation comments.

Examples
--------
Basic usage with simple keyword extraction:

>>> from teval.rubric_discovery import DiscoveryAnalyzer
>>>
>>> evaluations = [
...     {"evaluation": {"quality": False, "quality_reasoning": "Contains PII"}},
...     {"evaluation": {"quality": False, "quality_reasoning": "Shows email address"}},
... ]
>>> analyzer = DiscoveryAnalyzer()
>>> report = analyzer.analyze(evaluations)
>>> print(f"Found {len(report.patterns)} patterns")

With LLM for advanced pattern extraction:

>>> def my_llm(prompt: str) -> str:
...     # Your LLM call here (e.g., Gemini, OpenAI)
...     ...
>>> analyzer = DiscoveryAnalyzer(llm_callable=my_llm)
>>> report = analyzer.analyze(evaluations)

Generate rubric from discovered patterns:

>>> rubric = report.to_rubric(rubric_id="discovered_v1", min_frequency=3)
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from teval.metrics import EvaluationRubric, MetricDefinition


# Common English stopwords to filter out
STOPWORDS: Set[str] = {
    "a", "an", "the", "is", "it", "to", "and", "or", "of", "in", "on", "at",
    "for", "with", "as", "by", "from", "that", "this", "was", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "but", "not", "no", "if", "then", "so", "too", "also", "just", "only",
    "very", "more", "most", "some", "any", "all", "each", "every", "both",
    "few", "many", "much", "such", "other", "than", "into", "through",
    "during", "before", "after", "above", "below", "between", "under",
    "again", "further", "once", "here", "there", "when", "where", "why",
    "how", "what", "which", "who", "whom", "whose", "these", "those",
    "am", "are", "were", "he", "she", "they", "we", "you", "i", "me",
    "my", "your", "his", "her", "its", "our", "their", "them", "us",
    "response", "contains", "shows", "has", "gives", "provides", "includes",
}


@dataclass
class CommentPattern:
    """
    Represents a discovered pattern in evaluation comments.

    Attributes
    ----------
    pattern_id : str
        Unique identifier for this pattern.
    keywords : List[str]
        Key terms that characterize this pattern.
    sample_comments : List[str]
        Representative comments matching this pattern.
    frequency : int
        Number of times this pattern was observed.
    metric_id : Optional[str]
        If from a specific metric failure, the metric ID.
    suggested_rubric : Optional[str]
        Suggested rubric text based on this pattern.
    """
    pattern_id: str
    keywords: List[str]
    sample_comments: List[str]
    frequency: int
    metric_id: Optional[str] = None
    suggested_rubric: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "keywords": self.keywords,
            "sample_comments": self.sample_comments,
            "frequency": self.frequency,
            "metric_id": self.metric_id,
            "suggested_rubric": self.suggested_rubric,
        }


class DiscoveryReport(BaseModel):
    """
    Results container for rubric discovery analysis.

    Attributes
    ----------
    patterns : List[CommentPattern]
        Discovered patterns from comments.
    suggested_metrics : List[MetricDefinition]
        Generated metric definitions.
    total_evaluations : int
        Total number of evaluations analyzed.
    failed_evaluations : int
        Number of evaluations with failures (comments).
    total_comments : int
        Total number of comments analyzed.
    analysis_method : str
        Method used for analysis ("llm" or "keyword").
    """
    model_config = {"arbitrary_types_allowed": True}

    patterns: List[CommentPattern] = Field(default_factory=list)
    suggested_metrics: List[MetricDefinition] = Field(default_factory=list)
    total_evaluations: int = 0
    failed_evaluations: int = 0
    total_comments: int = 0
    analysis_method: str = "keyword"

    def to_rubric(
        self,
        rubric_id: str,
        min_frequency: int = 1,
        max_metrics: int = 10,
        passing_score_threshold: Optional[int] = None
    ) -> EvaluationRubric:
        """
        Generate an EvaluationRubric from discovered patterns.

        Parameters
        ----------
        rubric_id : str
            Unique identifier for the new rubric.
        min_frequency : int
            Minimum pattern frequency to include as metric.
        max_metrics : int
            Maximum number of metrics to include.
        passing_score_threshold : Optional[int]
            Threshold for passing. Defaults to all metrics.

        Returns
        -------
        EvaluationRubric
            Generated rubric based on discovered patterns.
        """
        # Filter patterns by frequency
        filtered = [p for p in self.patterns if p.frequency >= min_frequency]

        # Sort by frequency and take top N
        sorted_patterns = sorted(filtered, key=lambda p: p.frequency, reverse=True)
        top_patterns = sorted_patterns[:max_metrics]

        if not top_patterns:
            raise ValueError(
                f"No patterns meet min_frequency={min_frequency}. "
                f"Found {len(self.patterns)} patterns total."
            )

        # Convert to metrics
        metrics = []
        for pattern in top_patterns:
            # Generate metric ID from pattern
            metric_id = self._sanitize_id(pattern.pattern_id)

            # Use suggested rubric or generate from keywords
            rubric_text = pattern.suggested_rubric
            if not rubric_text:
                rubric_text = f"Response must not contain: {', '.join(pattern.keywords[:5])}"

            metric = MetricDefinition(
                id=metric_id,
                rubric=rubric_text,
                requires_comment_on_fail=True  # Discovery metrics need feedback
            )
            metrics.append(metric)

        # Default threshold: all must pass
        if passing_score_threshold is None:
            passing_score_threshold = len(metrics)

        return EvaluationRubric(
            rubric_id=rubric_id,
            metrics=metrics,
            passing_score_threshold=passing_score_threshold
        )

    def _sanitize_id(self, pattern_id: str) -> str:
        """Convert pattern ID to valid metric ID."""
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', pattern_id)
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"m_{sanitized}"
        # Ensure not empty
        if not sanitized:
            sanitized = "metric"
        return sanitized[:50]  # Reasonable length limit

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "patterns": [p.to_dict() for p in self.patterns],
            "suggested_metrics": [
                {"id": m.id, "rubric": m.rubric}
                for m in self.suggested_metrics
            ],
            "total_evaluations": self.total_evaluations,
            "failed_evaluations": self.failed_evaluations,
            "total_comments": self.total_comments,
            "analysis_method": self.analysis_method,
        }

    def to_markdown(self) -> str:
        """Generate markdown summary of discovery results."""
        lines = [
            "# Rubric Discovery Report",
            "",
            "## Summary",
            f"- Total evaluations analyzed: {self.total_evaluations}",
            f"- Evaluations with failures: {self.failed_evaluations}",
            f"- Total comments analyzed: {self.total_comments}",
            f"- Patterns discovered: {len(self.patterns)}",
            f"- Analysis method: {self.analysis_method}",
            "",
            "## Discovered Patterns",
            "",
        ]

        for i, pattern in enumerate(self.patterns, 1):
            lines.extend([
                f"### {i}. {pattern.pattern_id}",
                f"**Frequency:** {pattern.frequency}",
                f"**Keywords:** {', '.join(pattern.keywords[:10])}",
                "",
                "**Sample comments:**",
            ])
            for comment in pattern.sample_comments[:3]:
                # Truncate long comments
                truncated = comment[:200] + "..." if len(comment) > 200 else comment
                lines.append(f"- {truncated}")
            lines.append("")

            if pattern.suggested_rubric:
                lines.append(f"**Suggested rubric:** {pattern.suggested_rubric}")
                lines.append("")

        return "\n".join(lines)


@dataclass
class ExtractedComment:
    """Internal class for comment with metadata."""
    text: str
    metric_id: Optional[str] = None
    passed: bool = False
    item_id: Optional[str] = None


class DiscoveryAnalyzer:
    """
    Analyze evaluation comments to discover rubric patterns.

    Parameters
    ----------
    llm_callable : Optional[Callable[[str], str]]
        Optional LLM function that takes a prompt and returns response.
        If not provided, falls back to simple keyword extraction.
    min_keyword_length : int
        Minimum length for keywords to consider.
    max_sample_comments : int
        Maximum sample comments to store per pattern.
    """

    # Prompt template for LLM-based pattern extraction
    LLM_PROMPT_TEMPLATE = """Analyze the following evaluation comments from human reviewers.
These comments explain why LLM responses failed quality checks.

COMMENTS:
{comments}

TASK:
1. Identify 3-10 distinct patterns/themes in these comments
2. For each pattern, provide:
   - A short ID (snake_case, e.g., "pii_exposure", "medical_advice")
   - Key terms that characterize this pattern
   - A suggested rubric criterion (what the response should NOT do)

Return JSON in this exact format:
{{
  "patterns": [
    {{
      "pattern_id": "pattern_name",
      "keywords": ["keyword1", "keyword2"],
      "suggested_rubric": "Response must not [issue description]",
      "sample_indices": [0, 3, 5]
    }}
  ]
}}

Only return valid JSON, no other text."""

    def __init__(
        self,
        llm_callable: Optional[Callable[[str], str]] = None,
        min_keyword_length: int = 3,
        max_sample_comments: int = 5
    ):
        self.llm_callable = llm_callable
        self.min_keyword_length = min_keyword_length
        self.max_sample_comments = max_sample_comments

    def analyze(
        self,
        evaluations: List[Dict[str, Any]],
        include_global_comments: bool = True
    ) -> DiscoveryReport:
        """
        Analyze evaluations to discover patterns in comments.

        Parameters
        ----------
        evaluations : List[Dict[str, Any]]
            List of evaluation dictionaries. Expected format:
            {
                "evaluation": {"metric_id": bool, "metric_id_reasoning": str},
                "global_comment": str,
                "item_id": str
            }
        include_global_comments : bool
            Whether to include global_comment fields.

        Returns
        -------
        DiscoveryReport
            Analysis results with discovered patterns.
        """
        # Extract comments from evaluations
        comments = self._extract_comments(evaluations, include_global_comments)

        # Build report
        report = DiscoveryReport(
            total_evaluations=len(evaluations),
            failed_evaluations=sum(1 for c in comments if not c.passed),
            total_comments=len(comments)
        )

        if not comments:
            return report

        # Get comment texts
        comment_texts = [c.text for c in comments]

        # Use LLM if available, otherwise fall back to keyword extraction
        if self.llm_callable:
            try:
                patterns = self._extract_patterns_llm(comment_texts, comments)
                report.analysis_method = "llm"
            except Exception:
                # Fall back to keyword extraction on LLM failure
                patterns = self._extract_patterns_keyword(comment_texts, comments)
                report.analysis_method = "keyword_fallback"
        else:
            patterns = self._extract_patterns_keyword(comment_texts, comments)
            report.analysis_method = "keyword"

        report.patterns = patterns

        # Generate suggested metrics from patterns
        report.suggested_metrics = self._generate_metrics(patterns)

        return report

    def _extract_comments(
        self,
        evaluations: List[Dict[str, Any]],
        include_global: bool
    ) -> List[ExtractedComment]:
        """Extract comments from evaluation dictionaries."""
        comments = []

        for eval_data in evaluations:
            item_id = eval_data.get("item_id")

            # Handle different evaluation data structures
            evaluation = eval_data.get("evaluation", eval_data)

            # Extract metric-specific comments
            for key, value in evaluation.items():
                if key.endswith("_reasoning") and value:
                    metric_id = key[:-10]  # Remove "_reasoning"
                    metric_value = evaluation.get(metric_id)
                    passed = bool(metric_value) if metric_value is not None else False

                    # Only include comments for failed metrics
                    if not passed:
                        comments.append(ExtractedComment(
                            text=str(value).strip(),
                            metric_id=metric_id,
                            passed=passed,
                            item_id=item_id
                        ))

            # Extract global comments
            if include_global:
                global_comment = eval_data.get("global_comment")
                if global_comment and isinstance(global_comment, str):
                    comments.append(ExtractedComment(
                        text=global_comment.strip(),
                        metric_id=None,
                        passed=False,  # Global comments are typically for failures
                        item_id=item_id
                    ))

        # Filter empty comments
        return [c for c in comments if c.text]

    def _extract_patterns_llm(
        self,
        comment_texts: List[str],
        comments: List[ExtractedComment]
    ) -> List[CommentPattern]:
        """Extract patterns using LLM."""
        if not self.llm_callable:
            raise ValueError("LLM callable not provided")

        # Format comments for prompt
        formatted_comments = "\n".join(
            f"[{i}] {text[:500]}"  # Truncate very long comments
            for i, text in enumerate(comment_texts)
        )

        prompt = self.LLM_PROMPT_TEMPLATE.format(comments=formatted_comments)

        # Call LLM
        response = self.llm_callable(prompt)

        # Parse response
        patterns = self._parse_llm_response(response, comment_texts, comments)

        return patterns

    def _parse_llm_response(
        self,
        response: str,
        comment_texts: List[str],
        comments: List[ExtractedComment]
    ) -> List[CommentPattern]:
        """Parse LLM response into patterns."""
        patterns = []

        # Try to extract JSON from response
        try:
            # Find JSON in response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())
            raw_patterns = data.get("patterns", [])

            for raw in raw_patterns:
                pattern_id = raw.get("pattern_id", "unknown")
                keywords = raw.get("keywords", [])
                suggested_rubric = raw.get("suggested_rubric")
                sample_indices = raw.get("sample_indices", [])

                # Get sample comments
                samples = []
                for idx in sample_indices[:self.max_sample_comments]:
                    if 0 <= idx < len(comment_texts):
                        samples.append(comment_texts[idx])

                # Count frequency (how many comments match this pattern)
                frequency = len(sample_indices) if sample_indices else 1

                patterns.append(CommentPattern(
                    pattern_id=pattern_id,
                    keywords=keywords,
                    sample_comments=samples or [comment_texts[0]] if comment_texts else [],
                    frequency=frequency,
                    suggested_rubric=suggested_rubric
                ))

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # If parsing fails, create a single pattern from all comments
            patterns.append(CommentPattern(
                pattern_id="parse_error",
                keywords=["error"],
                sample_comments=comment_texts[:3],
                frequency=len(comment_texts),
                suggested_rubric=f"Error parsing LLM response: {e}"
            ))

        return patterns

    def _extract_patterns_keyword(
        self,
        comment_texts: List[str],
        comments: List[ExtractedComment]
    ) -> List[CommentPattern]:
        """Extract patterns using simple keyword analysis."""
        # Tokenize and count keywords
        all_keywords = Counter()
        comment_keywords: List[List[str]] = []

        for text in comment_texts:
            tokens = self._tokenize(text)
            keywords = [t for t in tokens if self._is_significant(t)]
            comment_keywords.append(keywords)
            all_keywords.update(keywords)

        if not all_keywords:
            return []

        # Find top keywords
        top_keywords = [kw for kw, _ in all_keywords.most_common(20)]

        # Group comments by shared keywords
        patterns = []
        used_comments: Set[int] = set()

        for keyword in top_keywords:
            matching_indices = [
                i for i, kws in enumerate(comment_keywords)
                if keyword in kws and i not in used_comments
            ]

            if len(matching_indices) >= 2:  # At least 2 comments for a pattern
                # Get sample comments
                samples = [
                    comment_texts[i]
                    for i in matching_indices[:self.max_sample_comments]
                ]

                # Find co-occurring keywords
                co_keywords = Counter()
                for idx in matching_indices:
                    co_keywords.update(comment_keywords[idx])
                related_keywords = [
                    kw for kw, _ in co_keywords.most_common(5)
                    if kw != keyword
                ]

                pattern = CommentPattern(
                    pattern_id=keyword,
                    keywords=[keyword] + related_keywords[:4],
                    sample_comments=samples,
                    frequency=len(matching_indices),
                    suggested_rubric=f"Response must not contain or reference: {keyword}"
                )
                patterns.append(pattern)

                # Mark comments as used
                used_comments.update(matching_indices)

        # Sort by frequency
        patterns.sort(key=lambda p: p.frequency, reverse=True)

        return patterns

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.split(r'[^a-z0-9]+', text)
        return [t for t in tokens if t]

    def _is_significant(self, token: str) -> bool:
        """Check if token is significant (not a stopword, etc.)."""
        if len(token) < self.min_keyword_length:
            return False
        if token in STOPWORDS:
            return False
        if token.isdigit():
            return False
        return True

    def _generate_metrics(
        self,
        patterns: List[CommentPattern]
    ) -> List[MetricDefinition]:
        """Generate MetricDefinition objects from patterns."""
        metrics = []
        seen_ids: Set[str] = set()

        for pattern in patterns:
            # Generate unique ID
            base_id = self._sanitize_id(pattern.pattern_id)
            metric_id = base_id
            counter = 1
            while metric_id in seen_ids:
                metric_id = f"{base_id}_{counter}"
                counter += 1
            seen_ids.add(metric_id)

            # Use suggested rubric or generate one
            rubric_text = pattern.suggested_rubric
            if not rubric_text:
                rubric_text = f"Response must not: {', '.join(pattern.keywords[:3])}"

            try:
                metric = MetricDefinition(
                    id=metric_id,
                    rubric=rubric_text,
                    requires_comment_on_fail=True
                )
                metrics.append(metric)
            except Exception:
                # Skip invalid metrics
                continue

        return metrics

    def _sanitize_id(self, text: str) -> str:
        """Convert text to valid metric ID."""
        # Replace spaces and special chars
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', text.lower())
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure doesn't start with digit
        if sanitized and sanitized[0].isdigit():
            sanitized = f"m_{sanitized}"
        # Ensure not empty
        if not sanitized:
            sanitized = "metric"
        return sanitized[:50]
