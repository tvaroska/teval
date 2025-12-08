from typing import List
from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationInfo

class MetricDefinition(BaseModel):
    """
    Defines a single Yes/No evaluation metric.

    The 'weight' is implicitly 1.0, meaning the cumulative score is the simple
    count of passed cumulative metrics.
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the metric (e.g., 'M1', 'code_style_pass')")
    rubric: str = Field(..., description="The specific pass/fail criterion, acting as the rubric for this metric.")
    mandatory: bool = Field(default=False, description="If True, this metric must pass for the evaluation to pass.")


class EvaluationRubric(BaseModel):
    """
    The complete evaluation rubric, defining all metrics and the passing threshold.
    """
    model_config = ConfigDict(extra="forbid")

    rubric_id: str = Field(..., description="A unique identifier for this specific rubric.")
    metrics: List[MetricDefinition] = Field(..., description="All evaluation metrics. Use mandatory=True for metrics that must all pass.")
    passing_score_threshold: int = Field(..., ge=0, description="The minimum required COUNT of passed cumulative metrics to pass this component of the evaluation.")

    @property
    def mandatory_metrics(self) -> List[MetricDefinition]:
        """Returns all metrics where mandatory=True."""
        return [m for m in self.metrics if m.mandatory]

    @property
    def cumulative_metrics(self) -> List[MetricDefinition]:
        """Returns all metrics where mandatory=False."""
        return [m for m in self.metrics if not m.mandatory]

    @field_validator('passing_score_threshold')
    @classmethod
    def check_threshold_validity(cls, threshold: int, info: ValidationInfo) -> int:
        """
        Ensures the passing threshold is not greater than the maximum possible score (total metric count).
        """
        metrics = info.data.get('metrics', [])
        # Count only non-mandatory (cumulative) metrics
        cumulative_count = sum(1 for m in metrics if not m.mandatory)

        if threshold > cumulative_count:
            raise ValueError(
                f"Passing threshold (count: {threshold}) cannot exceed the maximum possible cumulative metric count ({cumulative_count})."
            )
        return threshold

    @field_validator('metrics')
    @classmethod
    def check_unique_metric_ids(cls, metrics: List[MetricDefinition]) -> List[MetricDefinition]:
        """
        Ensures all metric IDs are unique.
        """
        ids = [m.id for m in metrics]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate metric IDs found in metrics list.")
        return metrics