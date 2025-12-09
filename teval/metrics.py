import json
from typing import List, Dict, Any, Union, Optional, Type
from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationInfo, create_model

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

    def to_prompt_text(self) -> str:
        """
        Generates formatted text to include in LLM prompts describing the evaluation rubric.

        Returns:
            A formatted string describing all metrics and evaluation criteria.
        """
        lines = [f"# Evaluation Rubric: {self.rubric_id}", ""]

        # Mandatory metrics section
        if self.mandatory_metrics:
            lines.append("## Mandatory Criteria (ALL must pass)")
            lines.append("")
            for metric in self.mandatory_metrics:
                lines.append(f"- **{metric.id}**: {metric.rubric}")
            lines.append("")

        # Cumulative metrics section
        if self.cumulative_metrics:
            lines.append("## Cumulative Criteria")
            lines.append(f"(Must pass at least {self.passing_score_threshold} of {len(self.cumulative_metrics)})")
            lines.append("")
            for metric in self.cumulative_metrics:
                lines.append(f"- **{metric.id}**: {metric.rubric}")
            lines.append("")

        # Evaluation instructions
        lines.append("## Instructions")
        lines.append("For each criterion above, evaluate whether it passes (Yes) or fails (No).")

        if self.mandatory_metrics:
            lines.append(f"- All {len(self.mandatory_metrics)} mandatory criteria must pass.")

        if self.cumulative_metrics:
            lines.append(f"- At least {self.passing_score_threshold} cumulative criteria must pass.")

        return "\n".join(lines)

    def to_json_schema(self) -> Dict[str, Any]:
        """
        Generates a JSON Schema for structured LLM output generation (e.g., for Gemini, OpenAI).

        The schema defines an object with:
        - A boolean field for each metric ID
        - An optional 'reasoning' field for each metric

        Returns:
            A JSON Schema dictionary compatible with OpenAPI/Swagger specifications.
        """
        properties = {}
        required = []

        # Add a field for each metric
        for metric in self.metrics:
            # Boolean field for the evaluation result
            properties[metric.id] = {
                "type": "boolean",
                "description": f"Does this pass the criterion: {metric.rubric}"
            }
            required.append(metric.id)

            # Optional reasoning field
            properties[f"{metric.id}_reasoning"] = {
                "type": "string",
                "description": f"Explanation for the {metric.id} evaluation"
            }

        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
            "description": f"Evaluation results for rubric: {self.rubric_id}"
        }

        return schema

    def to_pydantic_model(self) -> Type[BaseModel]:
        """
        Dynamically creates a Pydantic model class for validation of evaluation results.

        The generated model includes:
        - A required boolean field for each metric
        - An optional string field for reasoning (metric_id + "_reasoning")
        - Helper methods: passes(), get_failed_metrics(), get_passed_metrics(), to_report()

        Returns:
            A Pydantic BaseModel class that can be used for validation and type hints.

        Example:
            >>> rubric = EvaluationRubric(...)
            >>> ResultModel = rubric.to_pydantic_model()
            >>> result = ResultModel(M1=True, C1=False, M1_reasoning="Looks good")
            >>> result.M1
            True
            >>> result.passes()
            False
            >>> result.to_report()
            'Evaluation Result: FAIL...'
        """
        # Build field definitions for create_model
        field_definitions = {}

        for metric in self.metrics:
            # Required boolean field for the metric evaluation
            field_definitions[metric.id] = (
                bool,
                Field(..., description=f"Does this pass the criterion: {metric.rubric}")
            )

            # Optional reasoning field
            field_definitions[f"{metric.id}_reasoning"] = (
                Optional[str],
                Field(None, description=f"Explanation for the {metric.id} evaluation")
            )

        # Store reference to rubric for use in methods
        rubric_ref = self

        # Define helper methods
        def passes(model_self) -> bool:
            """Returns True if the evaluation passes all requirements."""
            result_dict = {metric.id: getattr(model_self, metric.id) for metric in rubric_ref.metrics}
            return rubric_ref.validate_result(result_dict)

        def get_failed_metrics(model_self) -> List[str]:
            """Returns list of metric IDs that failed (returned False)."""
            return [metric.id for metric in rubric_ref.metrics if not getattr(model_self, metric.id)]

        def get_passed_metrics(model_self) -> List[str]:
            """Returns list of metric IDs that passed (returned True)."""
            return [metric.id for metric in rubric_ref.metrics if getattr(model_self, metric.id)]

        def to_report(model_self) -> str:
            """Generates a consolidated text report of the evaluation results."""
            result_dict = {metric.id: getattr(model_self, metric.id) for metric in rubric_ref.metrics}
            reasoning_dict = {metric.id: getattr(model_self, f"{metric.id}_reasoning", None)
                            for metric in rubric_ref.metrics}
            return rubric_ref.generate_report(result_dict, reasoning_dict)

        # Create the model class dynamically
        model_name = f"EvaluationResult_{self.rubric_id}"
        model = create_model(
            model_name,
            __config__=ConfigDict(extra="forbid"),
            **field_definitions
        )

        # Add helper methods to the model class
        model.passes = passes
        model.get_failed_metrics = get_failed_metrics
        model.get_passed_metrics = get_passed_metrics
        model.to_report = to_report

        return model

    def validate_result(self, result: Union[str, Dict[str, Any]]) -> bool:
        """
        Validates an LLM-generated evaluation result against this rubric.

        Args:
            result: JSON string or dictionary containing boolean values for each metric ID

        Returns:
            True if the evaluation passes (all mandatory metrics pass AND
            cumulative threshold is met), False otherwise.

        Raises:
            ValueError: If result is missing required metric IDs, contains invalid values,
                       or if JSON string is malformed
        """
        # Parse JSON string if provided
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string: {e}")

        if not isinstance(result, dict):
            raise ValueError(f"Result must be a JSON string or dictionary, got {type(result).__name__}")

        # Check all metric IDs are present
        missing_metrics = []
        for metric in self.metrics:
            if metric.id not in result:
                missing_metrics.append(metric.id)

        if missing_metrics:
            raise ValueError(f"Missing metric results for: {', '.join(missing_metrics)}")

        # Validate all values are boolean
        for metric in self.metrics:
            value = result[metric.id]
            if not isinstance(value, bool):
                raise ValueError(f"Metric {metric.id} must be boolean, got {type(value).__name__}")

        # Check mandatory metrics
        for metric in self.mandatory_metrics:
            if not result[metric.id]:
                return False

        # Check cumulative metrics
        cumulative_passed = sum(1 for m in self.cumulative_metrics if result[m.id])
        if cumulative_passed < self.passing_score_threshold:
            return False

        return True

    def generate_report(self, result: Dict[str, Any], reasoning: Optional[Dict[str, Optional[str]]] = None) -> str:
        """
        Generates a consolidated text report of evaluation results.

        Args:
            result: Dictionary mapping metric IDs to boolean pass/fail values
            reasoning: Optional dictionary mapping metric IDs to reasoning strings

        Returns:
            A formatted text report showing:
            - Overall pass/fail status
            - All metrics with their pass/fail status
            - Reasoning for each metric (if provided)
            - What is required for passing

        Example:
            >>> rubric = EvaluationRubric(...)
            >>> result = {"M1": True, "C1": False, "C2": True}
            >>> reasoning = {"M1": "Code follows style guide", "C1": "Missing tests"}
            >>> print(rubric.generate_report(result, reasoning))
        """
        if reasoning is None:
            reasoning = {}

        lines = []
        lines.append(f"# Evaluation Report: {self.rubric_id}")
        lines.append("")

        # Determine overall pass/fail
        overall_pass = self.validate_result(result)
        status = "PASS" if overall_pass else "FAIL"
        lines.append(f"**Overall Result: {status}**")
        lines.append("")

        # Mandatory metrics section
        if self.mandatory_metrics:
            lines.append("## Mandatory Criteria (ALL must pass)")
            lines.append("")
            mandatory_failed = []
            for metric in self.mandatory_metrics:
                passed = result.get(metric.id, False)
                status_symbol = "✓" if passed else "✗"
                status_text = "PASS" if passed else "FAIL"
                lines.append(f"{status_symbol} **{metric.id}** [{status_text}]: {metric.rubric}")

                if not passed:
                    mandatory_failed.append(metric.id)

                # Add reasoning if available
                metric_reasoning = reasoning.get(metric.id)
                if metric_reasoning:
                    lines.append(f"  → {metric_reasoning}")
            lines.append("")

            if mandatory_failed:
                lines.append(f"⚠️  **{len(mandatory_failed)} mandatory metric(s) failed:** {', '.join(mandatory_failed)}")
                lines.append("")

        # Cumulative metrics section
        if self.cumulative_metrics:
            cumulative_passed = sum(1 for m in self.cumulative_metrics if result.get(m.id, False))
            cumulative_total = len(self.cumulative_metrics)

            lines.append("## Cumulative Criteria")
            lines.append(f"**Score: {cumulative_passed}/{cumulative_total}** (Required: {self.passing_score_threshold})")
            lines.append("")

            for metric in self.cumulative_metrics:
                passed = result.get(metric.id, False)
                status_symbol = "✓" if passed else "✗"
                status_text = "PASS" if passed else "FAIL"
                lines.append(f"{status_symbol} **{metric.id}** [{status_text}]: {metric.rubric}")

                # Add reasoning if available
                metric_reasoning = reasoning.get(metric.id)
                if metric_reasoning:
                    lines.append(f"  → {metric_reasoning}")
            lines.append("")

            if cumulative_passed < self.passing_score_threshold:
                needed = self.passing_score_threshold - cumulative_passed
                lines.append(f"⚠️  **Need {needed} more cumulative metric(s) to pass**")
                lines.append("")

        # Summary
        lines.append("## Requirements for Passing")
        requirements = []

        if self.mandatory_metrics:
            requirements.append(f"- ALL {len(self.mandatory_metrics)} mandatory criteria must pass")

        if self.cumulative_metrics:
            requirements.append(f"- At least {self.passing_score_threshold} of {len(self.cumulative_metrics)} cumulative criteria must pass")

        lines.extend(requirements)

        return "\n".join(lines)