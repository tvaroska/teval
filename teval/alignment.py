"""
Human-LLM alignment analysis for evaluation results.

This module provides tools to calculate inter-rater reliability metrics
(Cohen's Kappa, Fleiss' Kappa) and measure alignment between human evaluations
and LLM-generated evaluations.

Classes
-------
MetricAlignment
    Alignment statistics for a single metric.
BiasPattern
    Represents a detected systematic bias pattern.
AlignmentReport
    Complete alignment analysis results.
AlignmentAnalyzer
    Main class for analyzing evaluation alignment.

Examples
--------
Basic usage with human and LLM evaluations:

>>> from teval.alignment import AlignmentAnalyzer
>>>
>>> human_evals = [
...     {"item_id": "1", "evaluation": {"safety": True, "accuracy": False}},
...     {"item_id": "2", "evaluation": {"safety": True, "accuracy": True}},
... ]
>>> llm_evals = [
...     {"item_id": "1", "evaluation": {"safety": True, "accuracy": True}},
...     {"item_id": "2", "evaluation": {"safety": True, "accuracy": True}},
... ]
>>> analyzer = AlignmentAnalyzer()
>>> report = analyzer.analyze(human_evals, llm_evals)
>>> print(f"Alignment: {report.alignment_rate:.1%}")

Calculate inter-rater reliability among humans:

>>> human_evals = [
...     {"item_id": "1", "evaluator_id": "a", "evaluation": {"m1": True}},
...     {"item_id": "1", "evaluator_id": "b", "evaluation": {"m1": True}},
...     {"item_id": "2", "evaluator_id": "a", "evaluation": {"m1": False}},
...     {"item_id": "2", "evaluator_id": "b", "evaluation": {"m1": False}},
... ]
>>> report = analyzer.analyze(human_evals)
>>> print(f"Human agreement (kappa): {report.human_kappa:.2f}")
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

from pydantic import BaseModel, Field


@dataclass
class MetricAlignment:
    """
    Alignment statistics for a single metric.

    Attributes
    ----------
    metric_id : str
        The metric identifier.
    agreement_rate : float
        Proportion of evaluations where human and LLM agreed (0.0 to 1.0).
    cohens_kappa : float
        Cohen's Kappa for this metric (between two raters).
    human_pass_rate : float
        Rate at which humans marked this metric as passing.
    llm_pass_rate : float
        Rate at which LLM marked this metric as passing.
    sample_count : int
        Number of paired evaluations analyzed.
    bias_direction : Optional[str]
        "llm_lenient", "llm_strict", or None if balanced.
    confidence_score : float
        Confidence in the alignment measurement (0.0 to 1.0).
    """

    metric_id: str
    agreement_rate: float
    cohens_kappa: float
    human_pass_rate: float
    llm_pass_rate: float
    sample_count: int
    bias_direction: Optional[str] = None
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_id": self.metric_id,
            "agreement_rate": self.agreement_rate,
            "cohens_kappa": self.cohens_kappa,
            "human_pass_rate": self.human_pass_rate,
            "llm_pass_rate": self.llm_pass_rate,
            "sample_count": self.sample_count,
            "bias_direction": self.bias_direction,
            "confidence_score": self.confidence_score,
        }


@dataclass
class BiasPattern:
    """
    Represents a detected systematic bias pattern.

    Attributes
    ----------
    pattern_type : str
        Type of bias: "llm_lenient", "llm_strict", "inconsistent".
    affected_metrics : List[str]
        Metrics showing this bias pattern.
    description : str
        Human-readable description of the bias.
    severity : str
        "low", "medium", or "high".
    sample_size : int
        Number of samples supporting this finding.
    """

    pattern_type: str
    affected_metrics: List[str]
    description: str
    severity: str
    sample_size: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_type": self.pattern_type,
            "affected_metrics": self.affected_metrics,
            "description": self.description,
            "severity": self.severity,
            "sample_size": self.sample_size,
        }


class AlignmentReport(BaseModel):
    """
    Complete alignment analysis results.

    Attributes
    ----------
    human_kappa : float
        Inter-rater reliability among human evaluators (Fleiss' Kappa).
    human_llm_kappa : float
        Cohen's Kappa between aggregated human and LLM evaluations.
    alignment_rate : float
        Overall agreement rate between human and LLM (0.0 to 1.0).
    metric_alignments : List[MetricAlignment]
        Per-metric alignment statistics.
    low_alignment_metrics : List[str]
        Metrics with alignment below threshold (< 80%).
    high_alignment_metrics : List[str]
        Metrics with alignment at or above threshold (>= 80%).
    bias_patterns : List[BiasPattern]
        Detected systematic bias patterns.
    total_evaluations : int
        Total number of evaluations analyzed.
    total_items : int
        Number of unique items evaluated.
    confidence_level : str
        Overall confidence: "low", "medium", "high".
    warnings : List[str]
        Any warnings about data quality or sample size.
    """

    model_config = {"arbitrary_types_allowed": True}

    human_kappa: float = 0.0
    human_llm_kappa: float = 0.0
    alignment_rate: float = 0.0
    metric_alignments: List[MetricAlignment] = Field(default_factory=list)
    low_alignment_metrics: List[str] = Field(default_factory=list)
    high_alignment_metrics: List[str] = Field(default_factory=list)
    bias_patterns: List[BiasPattern] = Field(default_factory=list)
    total_evaluations: int = 0
    total_items: int = 0
    confidence_level: str = "low"
    warnings: List[str] = Field(default_factory=list)

    @property
    def passes_human_threshold(self) -> bool:
        """Check if human agreement meets kappa > 0.7 threshold."""
        return self.human_kappa > 0.7

    @property
    def passes_alignment_threshold(self) -> bool:
        """Check if human-LLM alignment meets > 80% threshold."""
        return self.alignment_rate > 0.80

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "human_kappa": self.human_kappa,
            "human_llm_kappa": self.human_llm_kappa,
            "alignment_rate": self.alignment_rate,
            "metric_alignments": [m.to_dict() for m in self.metric_alignments],
            "low_alignment_metrics": self.low_alignment_metrics,
            "high_alignment_metrics": self.high_alignment_metrics,
            "bias_patterns": [b.to_dict() for b in self.bias_patterns],
            "total_evaluations": self.total_evaluations,
            "total_items": self.total_items,
            "confidence_level": self.confidence_level,
            "warnings": self.warnings,
        }

    def to_markdown(self) -> str:
        """Generate markdown summary of alignment results."""
        lines = [
            "# Alignment Analysis Report",
            "",
            "## Summary",
            f"- Total evaluations: {self.total_evaluations}",
            f"- Total items: {self.total_items}",
            f"- Confidence level: {self.confidence_level}",
            "",
            "## Agreement Metrics",
            "",
            f"| Metric | Value | Threshold | Status |",
            f"|--------|-------|-----------|--------|",
            f"| Human Inter-rater (Fleiss' κ) | {self.human_kappa:.3f} | > 0.70 | {'✓' if self.passes_human_threshold else '✗'} |",
            f"| Human-LLM (Cohen's κ) | {self.human_llm_kappa:.3f} | - | - |",
            f"| Human-LLM Agreement Rate | {self.alignment_rate:.1%} | > 80% | {'✓' if self.passes_alignment_threshold else '✗'} |",
            "",
        ]

        # Kappa interpretation
        lines.extend([
            "### Kappa Interpretation",
            "",
            "| Range | Interpretation |",
            "|-------|----------------|",
            "| < 0.00 | Poor (less than chance) |",
            "| 0.00 - 0.20 | Slight agreement |",
            "| 0.21 - 0.40 | Fair agreement |",
            "| 0.41 - 0.60 | Moderate agreement |",
            "| 0.61 - 0.80 | Substantial agreement |",
            "| 0.81 - 1.00 | Almost perfect agreement |",
            "",
        ])

        # Per-metric alignment
        if self.metric_alignments:
            lines.extend([
                "## Per-Metric Alignment",
                "",
                "| Metric | Agreement | κ | Human Pass | LLM Pass | Bias | Samples |",
                "|--------|-----------|---|------------|----------|------|---------|",
            ])
            for m in sorted(self.metric_alignments, key=lambda x: x.agreement_rate):
                bias = m.bias_direction or "-"
                lines.append(
                    f"| {m.metric_id} | {m.agreement_rate:.1%} | {m.cohens_kappa:.2f} | "
                    f"{m.human_pass_rate:.1%} | {m.llm_pass_rate:.1%} | {bias} | {m.sample_count} |"
                )
            lines.append("")

        # Problem metrics
        if self.low_alignment_metrics:
            lines.extend([
                "## Problem Metrics (< 80% alignment)",
                "",
            ])
            for metric_id in self.low_alignment_metrics:
                lines.append(f"- **{metric_id}**")
            lines.append("")

        # Bias patterns
        if self.bias_patterns:
            lines.extend([
                "## Detected Bias Patterns",
                "",
            ])
            for pattern in self.bias_patterns:
                lines.append(f"### {pattern.pattern_type.replace('_', ' ').title()}")
                lines.append(f"**Severity:** {pattern.severity}")
                lines.append(f"**Description:** {pattern.description}")
                lines.append(f"**Affected metrics:** {', '.join(pattern.affected_metrics)}")
                lines.append(f"**Sample size:** {pattern.sample_size}")
                lines.append("")

        # Warnings
        if self.warnings:
            lines.extend([
                "## Warnings",
                "",
            ])
            for warning in self.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)

    def get_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []

        # Low human agreement
        if self.human_kappa < 0.7 and self.human_kappa > 0:
            recommendations.append(
                f"Human inter-rater agreement (κ={self.human_kappa:.2f}) is below the 0.70 threshold. "
                "Consider clarifying rubric definitions or providing calibration examples."
            )

        # Low alignment rate
        if self.alignment_rate < 0.80 and self.alignment_rate > 0:
            recommendations.append(
                f"Human-LLM alignment ({self.alignment_rate:.1%}) is below 80%. "
                "Review LLM prompt engineering or consider fine-tuning on human-labeled data."
            )

        # Address specific problem metrics
        for metric_id in self.low_alignment_metrics[:3]:  # Top 3
            alignment = next(
                (m for m in self.metric_alignments if m.metric_id == metric_id), None
            )
            if alignment:
                if alignment.bias_direction == "llm_lenient":
                    recommendations.append(
                        f"Metric '{metric_id}': LLM is too lenient (passes {alignment.llm_pass_rate:.0%} vs "
                        f"human {alignment.human_pass_rate:.0%}). Strengthen the failure criteria in the prompt."
                    )
                elif alignment.bias_direction == "llm_strict":
                    recommendations.append(
                        f"Metric '{metric_id}': LLM is too strict (passes {alignment.llm_pass_rate:.0%} vs "
                        f"human {alignment.human_pass_rate:.0%}). Relax the criteria or add positive examples."
                    )

        # Low sample size warning
        if self.confidence_level == "low":
            recommendations.append(
                "Sample size is low. Collect more evaluations to increase confidence in alignment metrics."
            )

        # Inconsistency pattern
        for pattern in self.bias_patterns:
            if pattern.pattern_type == "inconsistent":
                recommendations.append(
                    f"Metrics {', '.join(pattern.affected_metrics)} show inconsistent disagreement patterns. "
                    "Consider adding more specific examples to the LLM prompt."
                )

        return recommendations


class AlignmentAnalyzer:
    """
    Analyze alignment between human evaluations and LLM evaluations.

    Calculates inter-rater reliability metrics and identifies
    systematic biases in LLM evaluations compared to human ground truth.

    Parameters
    ----------
    alignment_threshold : float
        Minimum alignment rate to consider a metric well-aligned (default: 0.80).
    kappa_threshold : float
        Minimum Cohen's Kappa for substantial agreement (default: 0.70).
    min_samples_per_metric : int
        Minimum paired samples needed for reliable metric analysis (default: 10).

    Examples
    --------
    >>> from teval.alignment import AlignmentAnalyzer
    >>> analyzer = AlignmentAnalyzer()
    >>> results = analyzer.analyze(
    ...     human_evaluations=[...],
    ...     llm_evaluations=[...]
    ... )
    >>> print(f"Human agreement: {results.human_kappa:.2f}")
    >>> print(f"Human-LLM alignment: {results.alignment_rate:.1%}")
    """

    def __init__(
        self,
        alignment_threshold: float = 0.80,
        kappa_threshold: float = 0.70,
        min_samples_per_metric: int = 10,
    ):
        self.alignment_threshold = alignment_threshold
        self.kappa_threshold = kappa_threshold
        self.min_samples_per_metric = min_samples_per_metric

    def analyze(
        self,
        human_evaluations: List[Dict[str, Any]],
        llm_evaluations: Optional[List[Dict[str, Any]]] = None,
        rubric: Optional[Any] = None,
    ) -> AlignmentReport:
        """
        Perform comprehensive alignment analysis.

        Parameters
        ----------
        human_evaluations : List[Dict[str, Any]]
            List of human evaluation dictionaries. Each should contain:
            - "item_id": Identifier for the evaluated item
            - "evaluator_id": Identifier for the human evaluator (optional)
            - "evaluation": Dict[str, bool] mapping metric IDs to pass/fail
        llm_evaluations : Optional[List[Dict[str, Any]]]
            List of LLM evaluation dictionaries with same structure.
            If None, only human inter-rater reliability is calculated.
        rubric : Optional[EvaluationRubric]
            The evaluation rubric used. If provided, enables validation.

        Returns
        -------
        AlignmentReport
            Complete analysis results.
        """
        report = AlignmentReport(
            total_evaluations=len(human_evaluations) + (len(llm_evaluations) if llm_evaluations else 0)
        )

        if not human_evaluations:
            report.warnings.append("No human evaluations provided")
            return report

        # Extract metric IDs from evaluations
        metric_ids = self._extract_metric_ids(human_evaluations, llm_evaluations)

        # Calculate human inter-rater reliability if multiple evaluators
        human_by_item = self._group_by_item(human_evaluations)
        report.total_items = len(human_by_item)

        if self._has_multiple_evaluators(human_evaluations):
            report.human_kappa = self._calculate_human_agreement(
                human_evaluations, metric_ids
            )
        else:
            report.warnings.append(
                "Single human evaluator - cannot calculate inter-rater reliability"
            )

        # Calculate human-LLM alignment if LLM evaluations provided
        if llm_evaluations:
            llm_by_item = self._group_by_item(llm_evaluations)
            matched_items = set(human_by_item.keys()) & set(llm_by_item.keys())

            if not matched_items:
                report.warnings.append(
                    "No matching item_ids between human and LLM evaluations"
                )
            else:
                # Calculate per-metric alignment
                report.metric_alignments = self._calculate_per_metric_alignment(
                    human_by_item, llm_by_item, matched_items, metric_ids
                )

                # Calculate overall alignment rate
                if report.metric_alignments:
                    total_agreements = sum(
                        m.agreement_rate * m.sample_count for m in report.metric_alignments
                    )
                    total_samples = sum(m.sample_count for m in report.metric_alignments)
                    if total_samples > 0:
                        report.alignment_rate = total_agreements / total_samples

                    # Calculate overall human-LLM kappa
                    report.human_llm_kappa = self._calculate_overall_kappa(
                        human_by_item, llm_by_item, matched_items, metric_ids
                    )

                # Categorize metrics
                for m in report.metric_alignments:
                    if m.agreement_rate >= self.alignment_threshold:
                        report.high_alignment_metrics.append(m.metric_id)
                    else:
                        report.low_alignment_metrics.append(m.metric_id)

                # Detect bias patterns
                report.bias_patterns = self.detect_bias_patterns(report.metric_alignments)

        # Set confidence level
        report.confidence_level = self._determine_confidence_level(report)

        return report

    def calculate_cohens_kappa(
        self, ratings_a: List[bool], ratings_b: List[bool]
    ) -> float:
        """
        Calculate Cohen's Kappa between two raters.

        Parameters
        ----------
        ratings_a : List[bool]
            Ratings from first rater (True=pass, False=fail).
        ratings_b : List[bool]
            Ratings from second rater.

        Returns
        -------
        float
            Cohen's Kappa coefficient (-1.0 to 1.0).
        """
        n = len(ratings_a)
        if n == 0 or len(ratings_b) != n:
            return 0.0

        # Count agreements and marginals
        both_pass = sum(1 for a, b in zip(ratings_a, ratings_b) if a and b)
        both_fail = sum(1 for a, b in zip(ratings_a, ratings_b) if not a and not b)
        a_pass = sum(ratings_a)
        b_pass = sum(ratings_b)
        a_fail = n - a_pass
        b_fail = n - b_pass

        # Observed agreement
        p_o = (both_pass + both_fail) / n

        # Expected agreement by chance
        p_e = (a_pass * b_pass + a_fail * b_fail) / (n * n)

        # Handle edge case where p_e = 1 (all same ratings)
        if p_e >= 1.0:
            return 1.0 if p_o >= 1.0 else 0.0

        kappa = (p_o - p_e) / (1 - p_e)
        return kappa

    def calculate_fleiss_kappa(
        self, ratings_matrix: List[List[Optional[bool]]]
    ) -> float:
        """
        Calculate Fleiss' Kappa for multiple raters.

        Parameters
        ----------
        ratings_matrix : List[List[Optional[bool]]]
            Matrix where each row is an item and each column is a rater.
            Values are True (pass), False (fail), or None (missing).

        Returns
        -------
        float
            Fleiss' Kappa coefficient (-1.0 to 1.0).
        """
        if not ratings_matrix:
            return 0.0

        # For binary categories (pass=True, fail=False)
        categories = [True, False]

        # For each item, count how many raters assigned each category
        item_counts = []
        for row in ratings_matrix:
            valid_ratings = [r for r in row if r is not None]
            n_raters = len(valid_ratings)
            if n_raters < 2:
                continue
            pass_count = sum(1 for r in valid_ratings if r)
            fail_count = n_raters - pass_count
            item_counts.append({True: pass_count, False: fail_count, "n": n_raters})

        if not item_counts:
            return 0.0

        n = len(item_counts)

        # Calculate P_i for each item (proportion of agreeing rater pairs)
        P_values = []
        for counts in item_counts:
            n_i = counts["n"]
            if n_i < 2:
                continue
            p_i = sum(counts[cat] * (counts[cat] - 1) for cat in categories)
            p_i = p_i / (n_i * (n_i - 1))
            P_values.append(p_i)

        if not P_values:
            return 0.0

        P_bar = sum(P_values) / len(P_values)

        # Calculate p_j for each category (overall proportion)
        total_ratings = sum(counts["n"] for counts in item_counts)
        p_j = {}
        for cat in categories:
            p_j[cat] = sum(counts[cat] for counts in item_counts) / total_ratings

        # P_bar_e = sum of p_j^2
        P_bar_e = sum(p**2 for p in p_j.values())

        if P_bar_e >= 1.0:
            return 1.0 if P_bar >= 1.0 else 0.0

        kappa = (P_bar - P_bar_e) / (1 - P_bar_e)
        return kappa

    def detect_bias_patterns(
        self, metric_alignments: List[MetricAlignment]
    ) -> List[BiasPattern]:
        """
        Detect systematic bias patterns from metric alignments.

        Parameters
        ----------
        metric_alignments : List[MetricAlignment]
            Per-metric alignment data.

        Returns
        -------
        List[BiasPattern]
            Detected bias patterns.
        """
        patterns = []
        bias_threshold = 0.15  # 15% difference threshold

        # Pattern 1: LLM Lenient - LLM passes more than humans
        lenient_metrics = [
            m
            for m in metric_alignments
            if m.llm_pass_rate > m.human_pass_rate + bias_threshold
            and m.sample_count >= self.min_samples_per_metric
        ]
        if lenient_metrics:
            severity = "high" if len(lenient_metrics) > 3 else "medium" if len(lenient_metrics) > 1 else "low"
            patterns.append(
                BiasPattern(
                    pattern_type="llm_lenient",
                    affected_metrics=[m.metric_id for m in lenient_metrics],
                    description=f"LLM tends to pass {len(lenient_metrics)} metric(s) more often than humans",
                    severity=severity,
                    sample_size=sum(m.sample_count for m in lenient_metrics),
                )
            )

        # Pattern 2: LLM Strict - LLM fails more than humans
        strict_metrics = [
            m
            for m in metric_alignments
            if m.human_pass_rate > m.llm_pass_rate + bias_threshold
            and m.sample_count >= self.min_samples_per_metric
        ]
        if strict_metrics:
            severity = "high" if len(strict_metrics) > 3 else "medium" if len(strict_metrics) > 1 else "low"
            patterns.append(
                BiasPattern(
                    pattern_type="llm_strict",
                    affected_metrics=[m.metric_id for m in strict_metrics],
                    description=f"LLM tends to fail {len(strict_metrics)} metric(s) more often than humans",
                    severity=severity,
                    sample_size=sum(m.sample_count for m in strict_metrics),
                )
            )

        # Pattern 3: Inconsistent - Low kappa despite similar rates
        inconsistent_metrics = [
            m
            for m in metric_alignments
            if m.cohens_kappa < 0.4
            and abs(m.human_pass_rate - m.llm_pass_rate) < 0.10
            and m.sample_count >= self.min_samples_per_metric
        ]
        if inconsistent_metrics:
            patterns.append(
                BiasPattern(
                    pattern_type="inconsistent",
                    affected_metrics=[m.metric_id for m in inconsistent_metrics],
                    description="Similar pass rates but low item-level agreement - disagreements cancel out",
                    severity="medium",
                    sample_size=sum(m.sample_count for m in inconsistent_metrics),
                )
            )

        return patterns

    def _extract_metric_ids(
        self,
        human_evaluations: List[Dict[str, Any]],
        llm_evaluations: Optional[List[Dict[str, Any]]] = None,
    ) -> Set[str]:
        """Extract all metric IDs from evaluations."""
        metric_ids: Set[str] = set()

        for eval_data in human_evaluations:
            evaluation = eval_data.get("evaluation", {})
            for key in evaluation:
                if not key.endswith("_reasoning") and key != "global_comment":
                    metric_ids.add(key)

        if llm_evaluations:
            for eval_data in llm_evaluations:
                evaluation = eval_data.get("evaluation", {})
                for key in evaluation:
                    if not key.endswith("_reasoning") and key != "global_comment":
                        metric_ids.add(key)

        return metric_ids

    def _group_by_item(
        self, evaluations: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group evaluations by item_id."""
        by_item: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for eval_data in evaluations:
            item_id = eval_data.get("item_id", "unknown")
            by_item[item_id].append(eval_data)
        return dict(by_item)

    def _has_multiple_evaluators(self, evaluations: List[Dict[str, Any]]) -> bool:
        """Check if evaluations come from multiple human evaluators."""
        evaluator_ids = set()
        for eval_data in evaluations:
            evaluator_id = eval_data.get("evaluator_id")
            if evaluator_id:
                evaluator_ids.add(evaluator_id)

        # If no evaluator_ids, check if same item has multiple evaluations
        if not evaluator_ids:
            by_item = self._group_by_item(evaluations)
            return any(len(evals) > 1 for evals in by_item.values())

        return len(evaluator_ids) > 1

    def _calculate_human_agreement(
        self, human_evaluations: List[Dict[str, Any]], metric_ids: Set[str]
    ) -> float:
        """Calculate Fleiss' Kappa for human inter-rater reliability."""
        by_item = self._group_by_item(human_evaluations)

        # Build ratings matrix per metric, then average
        kappas = []
        for metric_id in metric_ids:
            ratings_matrix = []
            for item_id, evals in by_item.items():
                if len(evals) < 2:
                    continue
                row = []
                for eval_data in evals:
                    evaluation = eval_data.get("evaluation", {})
                    value = evaluation.get(metric_id)
                    if isinstance(value, bool):
                        row.append(value)
                if len(row) >= 2:
                    ratings_matrix.append(row)

            if ratings_matrix:
                kappa = self.calculate_fleiss_kappa(ratings_matrix)
                kappas.append(kappa)

        if not kappas:
            return 0.0

        return sum(kappas) / len(kappas)

    def _calculate_per_metric_alignment(
        self,
        human_by_item: Dict[str, List[Dict[str, Any]]],
        llm_by_item: Dict[str, List[Dict[str, Any]]],
        matched_items: Set[str],
        metric_ids: Set[str],
    ) -> List[MetricAlignment]:
        """Calculate alignment statistics for each metric."""
        alignments = []

        for metric_id in metric_ids:
            human_ratings = []
            llm_ratings = []

            for item_id in matched_items:
                human_evals = human_by_item.get(item_id, [])
                llm_evals = llm_by_item.get(item_id, [])

                if not human_evals or not llm_evals:
                    continue

                # Aggregate human ratings (majority vote)
                human_values = []
                for eval_data in human_evals:
                    evaluation = eval_data.get("evaluation", {})
                    value = evaluation.get(metric_id)
                    if isinstance(value, bool):
                        human_values.append(value)

                if not human_values:
                    continue

                human_majority = sum(human_values) > len(human_values) / 2

                # Get LLM rating (use first if multiple)
                llm_value = None
                for eval_data in llm_evals:
                    evaluation = eval_data.get("evaluation", {})
                    value = evaluation.get(metric_id)
                    if isinstance(value, bool):
                        llm_value = value
                        break

                if llm_value is None:
                    continue

                human_ratings.append(human_majority)
                llm_ratings.append(llm_value)

            if not human_ratings:
                continue

            # Calculate statistics
            n = len(human_ratings)
            agreements = sum(1 for h, l in zip(human_ratings, llm_ratings) if h == l)
            agreement_rate = agreements / n if n > 0 else 0.0

            human_pass_rate = sum(human_ratings) / n if n > 0 else 0.0
            llm_pass_rate = sum(llm_ratings) / n if n > 0 else 0.0

            kappa = self.calculate_cohens_kappa(human_ratings, llm_ratings)

            # Determine bias direction
            bias_direction = None
            bias_threshold = 0.15
            if llm_pass_rate > human_pass_rate + bias_threshold:
                bias_direction = "llm_lenient"
            elif human_pass_rate > llm_pass_rate + bias_threshold:
                bias_direction = "llm_strict"

            # Calculate confidence score
            confidence = self._calculate_confidence_score(n)

            alignments.append(
                MetricAlignment(
                    metric_id=metric_id,
                    agreement_rate=agreement_rate,
                    cohens_kappa=kappa,
                    human_pass_rate=human_pass_rate,
                    llm_pass_rate=llm_pass_rate,
                    sample_count=n,
                    bias_direction=bias_direction,
                    confidence_score=confidence,
                )
            )

        return alignments

    def _calculate_overall_kappa(
        self,
        human_by_item: Dict[str, List[Dict[str, Any]]],
        llm_by_item: Dict[str, List[Dict[str, Any]]],
        matched_items: Set[str],
        metric_ids: Set[str],
    ) -> float:
        """Calculate overall Cohen's Kappa across all metrics."""
        all_human = []
        all_llm = []

        for metric_id in metric_ids:
            for item_id in matched_items:
                human_evals = human_by_item.get(item_id, [])
                llm_evals = llm_by_item.get(item_id, [])

                if not human_evals or not llm_evals:
                    continue

                # Aggregate human ratings
                human_values = []
                for eval_data in human_evals:
                    evaluation = eval_data.get("evaluation", {})
                    value = evaluation.get(metric_id)
                    if isinstance(value, bool):
                        human_values.append(value)

                if not human_values:
                    continue

                human_majority = sum(human_values) > len(human_values) / 2

                # Get LLM rating
                llm_value = None
                for eval_data in llm_evals:
                    evaluation = eval_data.get("evaluation", {})
                    value = evaluation.get(metric_id)
                    if isinstance(value, bool):
                        llm_value = value
                        break

                if llm_value is None:
                    continue

                all_human.append(human_majority)
                all_llm.append(llm_value)

        if not all_human:
            return 0.0

        return self.calculate_cohens_kappa(all_human, all_llm)

    def _calculate_confidence_score(self, sample_count: int) -> float:
        """
        Calculate confidence score based on sample size.

        Confidence levels:
        - < 10 samples: 0.0 - 0.3 (low)
        - 10-30 samples: 0.3 - 0.6 (medium)
        - 30-100 samples: 0.6 - 0.9 (good)
        - 100+ samples: 0.9 - 1.0 (high)
        """
        if sample_count < 5:
            return 0.1
        elif sample_count < 10:
            return 0.2 + (sample_count - 5) * 0.02
        elif sample_count < 30:
            return 0.3 + (sample_count - 10) * 0.015
        elif sample_count < 100:
            return 0.6 + (sample_count - 30) * 0.004
        else:
            return min(0.95, 0.88 + (sample_count - 100) * 0.001)

    def _determine_confidence_level(self, report: AlignmentReport) -> str:
        """Determine overall confidence level for the report."""
        if report.total_items < 10:
            return "low"
        elif report.total_items < 30:
            return "medium"
        elif report.total_items < 100:
            return "good"
        else:
            return "high"
