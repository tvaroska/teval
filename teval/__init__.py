"""Trivial LLM eval - as simple as possible."""

from teval.metrics import EvaluationRubric, MetricDefinition
from teval.rubric_discovery import CommentPattern, DiscoveryAnalyzer, DiscoveryReport
from teval.alignment import (
    AlignmentAnalyzer,
    AlignmentReport,
    BiasPattern,
    MetricAlignment,
)

__version__ = "0.1.1"

__all__ = [
    "EvaluationRubric",
    "MetricDefinition",
    "CommentPattern",
    "DiscoveryAnalyzer",
    "DiscoveryReport",
    "AlignmentAnalyzer",
    "AlignmentReport",
    "BiasPattern",
    "MetricAlignment",
    "__version__",
]
