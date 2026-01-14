"""
Evaluation metrics framework for LLM output assessment.

This module provides a flexible framework for defining and validating evaluation
rubrics for Large Language Model (LLM) outputs. It supports two types of metrics:
mandatory (must-pass) and cumulative (scored), allowing for nuanced evaluation
criteria.

The framework is designed to integrate with any LLM provider through JSON Schema
or Pydantic model generation, enabling structured output validation and
human-LLM alignment measurement.

Classes
-------
MetricDefinition
    Defines a single Yes/No evaluation metric with optional mandatory flag.
EvaluationRubric
    Complete evaluation rubric containing metrics and passing thresholds.

Examples
--------
Basic usage with mandatory and cumulative metrics:

>>> from teval import EvaluationRubric, MetricDefinition
>>>
>>> rubric = EvaluationRubric(
...     rubric_id="code_review_v1",
...     metrics=[
...         MetricDefinition(
...             id="M1",
...             rubric="Code compiles without errors",
...             mandatory=True
...         ),
...         MetricDefinition(
...             id="C1",
...             rubric="Code follows style guidelines"
...         ),
...         MetricDefinition(
...             id="C2",
...             rubric="Code includes appropriate comments"
...         )
...     ],
...     passing_score_threshold=1
... )
>>>
>>> # Validate an evaluation result
>>> result = {"M1": True, "C1": True, "C2": False}
>>> rubric.validate_result(result)
True

Integration with LLM providers:

>>> # Generate JSON Schema for structured output
>>> schema = rubric.to_json_schema()
>>>
>>> # Or create a Pydantic model for validation
>>> ResultModel = rubric.to_pydantic_model()
>>> evaluation = ResultModel(M1=True, C1=True, C2=False)
>>> evaluation.passes()
True

Notes
-----
The framework uses a simple scoring system where each cumulative metric
has an implicit weight of 1.0, and the score is the count of passed metrics.
This design prioritizes simplicity and interpretability over complex
weighted scoring systems.
"""

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
        """
        Return metrics marked as mandatory.

        Filters the metrics list to return only those with mandatory=True.
        These metrics must all pass for the overall evaluation to pass.

        Returns
        -------
        List[MetricDefinition]
            List of MetricDefinition instances where mandatory=True.
            Empty list if no mandatory metrics are defined.

        Examples
        --------
        >>> rubric = EvaluationRubric(
        ...     rubric_id="test",
        ...     metrics=[
        ...         MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        ...         MetricDefinition(id="C1", rubric="Optional")
        ...     ],
        ...     passing_score_threshold=0
        ... )
        >>> len(rubric.mandatory_metrics)
        1
        >>> rubric.mandatory_metrics[0].id
        'M1'
        """
        return [m for m in self.metrics if m.mandatory]

    @property
    def cumulative_metrics(self) -> List[MetricDefinition]:
        """
        Return metrics that contribute to the cumulative score.

        Filters the metrics list to return only those with mandatory=False.
        These metrics are scored, and a minimum number must pass based on
        the passing_score_threshold.

        Returns
        -------
        List[MetricDefinition]
            List of MetricDefinition instances where mandatory=False.
            Empty list if no cumulative metrics are defined.

        Examples
        --------
        >>> rubric = EvaluationRubric(
        ...     rubric_id="test",
        ...     metrics=[
        ...         MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        ...         MetricDefinition(id="C1", rubric="Optional 1"),
        ...         MetricDefinition(id="C2", rubric="Optional 2")
        ...     ],
        ...     passing_score_threshold=1
        ... )
        >>> len(rubric.cumulative_metrics)
        2
        >>> [m.id for m in rubric.cumulative_metrics]
        ['C1', 'C2']
        """
        return [m for m in self.metrics if not m.mandatory]

    @field_validator('passing_score_threshold')
    @classmethod
    def check_threshold_validity(cls, threshold: int, info: ValidationInfo) -> int:
        """
        Validate that the passing threshold is achievable.

        Ensures the passing_score_threshold does not exceed the number of
        cumulative metrics available, as this would make passing impossible.

        Parameters
        ----------
        threshold : int
            The proposed passing score threshold.
        info : ValidationInfo
            Pydantic validation context containing other field values.

        Returns
        -------
        int
            The validated threshold value.

        Raises
        ------
        ValueError
            If threshold exceeds the number of cumulative metrics.

        Notes
        -----
        This is a Pydantic field validator that runs during model instantiation.
        It ensures logical consistency of the rubric configuration.
        """
        metrics = info.data.get('metrics', [])
        # Count mandatory and cumulative metrics
        mandatory_count = sum(1 for m in metrics if m.mandatory)
        cumulative_count = sum(1 for m in metrics if not m.mandatory)

        if threshold > cumulative_count:
            raise ValueError(
                f"Passing threshold ({threshold}) cannot exceed the number of cumulative metrics ({cumulative_count}). "
                f"You have {mandatory_count} mandatory metric(s) and {cumulative_count} cumulative metric(s)."
            )
        return threshold

    @field_validator('metrics')
    @classmethod
    def check_unique_metric_ids(cls, metrics: List[MetricDefinition]) -> List[MetricDefinition]:
        """
        Validate that all metric IDs are unique.

        Checks for duplicate metric IDs across the entire metrics list
        to prevent ambiguity in evaluation results.

        Parameters
        ----------
        metrics : List[MetricDefinition]
            The list of metric definitions to validate.

        Returns
        -------
        List[MetricDefinition]
            The validated metrics list.

        Raises
        ------
        ValueError
            If duplicate metric IDs are found.

        Notes
        -----
        This is a Pydantic field validator that runs during model instantiation.
        Unique IDs are required for unambiguous result mapping.
        """
        ids = [m.id for m in metrics]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate metric IDs found in metrics list.")
        return metrics

    def to_prompt_text(self) -> str:
        """
        Generate formatted text for inclusion in LLM prompts.

        Creates a human-readable markdown representation of the evaluation
        rubric, clearly separating mandatory and cumulative criteria with
        instructions for evaluation.

        Returns
        -------
        str
            Formatted markdown text containing:
            - Rubric title and ID
            - Mandatory criteria section (if any)
            - Cumulative criteria section with threshold (if any)
            - Clear evaluation instructions

        Examples
        --------
        >>> rubric = EvaluationRubric(
        ...     rubric_id="code_review",
        ...     metrics=[
        ...         MetricDefinition(id="M1", rubric="No syntax errors", mandatory=True),
        ...         MetricDefinition(id="C1", rubric="Good variable names")
        ...     ],
        ...     passing_score_threshold=1
        ... )
        >>> prompt = rubric.to_prompt_text()
        >>> print(prompt.split('\\n')[0])
        # Evaluation Rubric: code_review

        Notes
        -----
        The generated text is designed to be prepended to LLM prompts
        to provide clear evaluation criteria. The format emphasizes the
        distinction between mandatory and cumulative metrics.
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
        Generate a JSON Schema for structured LLM output.

        Creates a JSON Schema that defines the expected structure for
        evaluation results. Compatible with OpenAI's response_format,
        Gemini's response_schema, and other structured output APIs.

        Returns
        -------
        Dict[str, Any]
            JSON Schema dictionary with:
            - type: "object"
            - properties: Boolean field for each metric ID, optional reasoning fields
            - required: List of all metric IDs
            - additionalProperties: False (strict validation)

        Examples
        --------
        >>> rubric = EvaluationRubric(
        ...     rubric_id="test",
        ...     metrics=[
        ...         MetricDefinition(id="M1", rubric="Must pass", mandatory=True)
        ...     ],
        ...     passing_score_threshold=0
        ... )
        >>> schema = rubric.to_json_schema()
        >>> schema['properties']['M1']['type']
        'boolean'
        >>> 'M1_reasoning' in schema['properties']
        True

        Notes
        -----
        The schema includes optional reasoning fields (metric_id + "_reasoning")
        to capture LLM explanations. This is useful for debugging and
        understanding evaluation decisions.

        See Also
        --------
        to_pydantic_model : For type-safe validation with Pydantic models.
        validate_result : To validate results against this schema.
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
        Create a dynamic Pydantic model for type-safe validation.

        Generates a Pydantic BaseModel class tailored to this rubric's metrics.
        The model provides validation, serialization, and helper methods for
        working with evaluation results.

        Returns
        -------
        Type[BaseModel]
            A dynamically generated Pydantic model class with:
            - Required boolean field for each metric ID
            - Optional string reasoning field for each metric
            - Helper methods: passes(), get_failed_metrics(),
              get_passed_metrics(), to_report()

        Examples
        --------
        >>> rubric = EvaluationRubric(
        ...     rubric_id="test",
        ...     metrics=[
        ...         MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        ...         MetricDefinition(id="C1", rubric="Optional")
        ...     ],
        ...     passing_score_threshold=0
        ... )
        >>> ResultModel = rubric.to_pydantic_model()
        >>> result = ResultModel(M1=True, C1=False, M1_reasoning="Well structured")
        >>> result.M1
        True
        >>> result.passes()
        True
        >>> result.get_failed_metrics()
        ['C1']

        Notes
        -----
        The generated model class is cached internally for reuse. The model
        name follows the pattern: EvaluationResult_{rubric_id}.

        Helper methods on the generated model:
        - passes(): Check if evaluation meets all requirements
        - get_failed_metrics(): List metric IDs that failed
        - get_passed_metrics(): List metric IDs that passed
        - to_report(title): Generate formatted text report

        See Also
        --------
        to_json_schema : For JSON Schema generation.
        validate_result : For simple validation without model instantiation.
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

        def to_report(model_self, title: Optional[str] = None) -> str:
            """Generates a consolidated text report of the evaluation results."""
            result_dict = {metric.id: getattr(model_self, metric.id) for metric in rubric_ref.metrics}
            reasoning_dict = {metric.id: getattr(model_self, f"{metric.id}_reasoning", None)
                            for metric in rubric_ref.metrics}
            return rubric_ref.generate_report(result_dict, reasoning_dict, title)

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
        Validate an LLM-generated evaluation result against this rubric.

        Checks that all mandatory metrics pass and the cumulative score meets
        the required threshold. Accepts either a JSON string or dictionary.

        Parameters
        ----------
        result : str or dict
            Evaluation results as either:
            - JSON string containing boolean values for each metric ID
            - Dictionary mapping metric IDs to boolean values

        Returns
        -------
        bool
            True if the evaluation passes (all mandatory metrics pass AND
            cumulative threshold is met), False otherwise.

        Raises
        ------
        ValueError
            If result is missing required metric IDs, contains non-boolean
            values, or if JSON string is malformed.

        Examples
        --------
        >>> rubric = EvaluationRubric(
        ...     rubric_id="test",
        ...     metrics=[
        ...         MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        ...         MetricDefinition(id="C1", rubric="Optional")
        ...     ],
        ...     passing_score_threshold=0
        ... )
        >>> rubric.validate_result({"M1": True, "C1": False})
        True
        >>> rubric.validate_result('{"M1": false, "C1": true}')
        False

        Notes
        -----
        This method performs strict validation - all metric IDs must be present
        and have boolean values. Additional fields in the result are ignored.

        See Also
        --------
        to_pydantic_model : For creating a validating model class.
        generate_report : To create a formatted report of results.
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

    def generate_report(self, result: Dict[str, Any], reasoning: Optional[Dict[str, Optional[str]]] = None, title: Optional[str] = None) -> str:
        """
        Generate a formatted text report of evaluation results.

        Creates a comprehensive markdown report showing the overall pass/fail
        status, individual metric results, and requirements for passing.

        Parameters
        ----------
        result : dict
            Dictionary mapping metric IDs to boolean pass/fail values.
        reasoning : dict, optional
            Dictionary mapping metric IDs to explanation strings.
            If not provided, no reasoning is included in the report.
        title : str, optional
            Custom title for the report. If not provided,
            defaults to "Evaluation Report: {rubric_id}".

        Returns
        -------
        str
            Formatted markdown report containing:
            - Overall pass/fail status
            - Mandatory criteria results (if any)
            - Cumulative criteria results with score (if any)
            - Reasoning for each metric (if provided)
            - Summary of requirements for passing

        Examples
        --------
        >>> rubric = EvaluationRubric(
        ...     rubric_id="review",
        ...     metrics=[
        ...         MetricDefinition(id="M1", rubric="No errors", mandatory=True),
        ...         MetricDefinition(id="C1", rubric="Good style")
        ...     ],
        ...     passing_score_threshold=1
        ... )
        >>> result = {"M1": True, "C1": False}
        >>> reasoning = {"M1": "Code compiles", "C1": "Poor naming"}
        >>> report = rubric.generate_report(result, reasoning, "Code Review")
        >>> print(report.split('\\n')[0])
        # Code Review

        Notes
        -----
        The report uses Unicode symbols for visual clarity:
        - ✓ for passed metrics
        - ✗ for failed metrics
        - ⚠️ for warnings about failed requirements

        Each metric appears as a separate paragraph for readability.
        Reasoning, when provided, is indented under the corresponding metric.

        See Also
        --------
        validate_result : To check if results pass without generating a report.
        to_pydantic_model : Model's to_report() method provides similar functionality.
        """
        if reasoning is None:
            reasoning = {}

        lines = []
        report_title = title if title else f"Evaluation Report: {self.rubric_id}"
        lines.append(f"# {report_title}")
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

                # Add blank line after each metric to create separate paragraphs
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

                # Add blank line after each metric to create separate paragraphs
                lines.append("")

            if cumulative_passed < self.passing_score_threshold:
                needed = self.passing_score_threshold - cumulative_passed
                lines.append(f"⚠️  **Need {needed} more cumulative metric(s) to pass**")
                lines.append("")

        # Summary
        lines.append("## Requirements for Passing")
        lines.append("")

        if self.mandatory_metrics:
            lines.append("**Mandatory criteria (ALL must pass):**")
            for metric in self.mandatory_metrics:
                passed = result.get(metric.id, False)
                status = "✓" if passed else "✗"
                lines.append(f"  {status} {metric.id}")
            lines.append("")

        if self.cumulative_metrics:
            cumulative_passed = sum(1 for m in self.cumulative_metrics if result.get(m.id, False))
            lines.append(f"**Cumulative criteria:**")
            lines.append(f"  - Need at least {self.passing_score_threshold} of {len(self.cumulative_metrics)} to pass")
            lines.append(f"  - Currently passed: {cumulative_passed}")
            if cumulative_passed < self.passing_score_threshold:
                needed = self.passing_score_threshold - cumulative_passed
                lines.append(f"  - Still need: {needed} more")

        return "\n".join(lines)

    def calculate_alignment(
        self,
        results_a: Union[BaseModel, List[BaseModel]],
        results_b: Union[BaseModel, List[BaseModel]]
    ) -> float:
        """
        Calculate alignment between two sets of evaluation results.

        Compares whether evaluation results agree on the overall pass/fail
        outcome. This is useful for measuring human-LLM alignment or
        comparing different model evaluations.

        Parameters
        ----------
        results_a : BaseModel or List[BaseModel]
            Single result or list of results from to_pydantic_model().
            Must be instances of the model generated for this rubric.
        results_b : BaseModel or List[BaseModel]
            Single result or list of results to compare against.
            Must match the type (single/list) of results_a.

        Returns
        -------
        float
            Alignment score between 0.0 and 1.0:
            - 1.0: Perfect alignment (all pass/fail decisions match)
            - 0.0: No alignment (all decisions disagree)
            - For lists: Fraction of aligned pairs (e.g., 0.85 = 85% agreement)

        Raises
        ------
        TypeError
            If inputs are not Pydantic BaseModel instances or if
            results_a and results_b have mismatched types (single vs list).
        ValueError
            If list inputs have different lengths.

        Examples
        --------
        Single result comparison:

        >>> rubric = EvaluationRubric(
        ...     rubric_id="test",
        ...     metrics=[
        ...         MetricDefinition(id="M1", rubric="Must pass", mandatory=True),
        ...         MetricDefinition(id="C1", rubric="Optional")
        ...     ],
        ...     passing_score_threshold=1
        ... )
        >>> ResultModel = rubric.to_pydantic_model()
        >>> human = ResultModel(M1=True, C1=True)
        >>> llm = ResultModel(M1=True, C1=False)
        >>> alignment = rubric.calculate_alignment(human, llm)
        >>> print(f"Human-LLM alignment: {alignment:.0%}")
        Human-LLM alignment: 100%

        Batch comparison:

        >>> humans = [ResultModel(M1=True, C1=True), ResultModel(M1=False, C1=False)]
        >>> llms = [ResultModel(M1=True, C1=False), ResultModel(M1=False, C1=True)]
        >>> alignment = rubric.calculate_alignment(humans, llms)
        >>> print(f"Batch alignment: {alignment:.0%}")
        Batch alignment: 50%

        Notes
        -----
        Alignment is calculated at the overall pass/fail level, not at
        individual metric level. Two results align if they both pass or
        both fail, regardless of which specific metrics differ.

        This metric is particularly useful for:
        - Validating cheaper models against expensive ones
        - Measuring inter-rater reliability in human evaluations
        - Tracking consistency across model versions

        See Also
        --------
        to_pydantic_model : To create the result models for comparison.
        validate_result : For simple pass/fail checking.
        """
        # Normalize inputs to lists
        is_single_a = isinstance(results_a, BaseModel)
        is_single_b = isinstance(results_b, BaseModel)

        if is_single_a != is_single_b:
            raise TypeError("Both results_a and results_b must be either single instances or lists")

        # Convert to lists for uniform processing
        if is_single_a:
            results_a = [results_a]
            results_b = [results_b]
        else:
            # Validate they are lists
            if not isinstance(results_a, list) or not isinstance(results_b, list):
                raise TypeError("results_a and results_b must be BaseModel instances or lists of BaseModel instances")

        # Validate list lengths match
        if len(results_a) != len(results_b):
            raise ValueError(
                f"Results lists must have the same length. "
                f"Got {len(results_a)} for results_a and {len(results_b)} for results_b"
            )

        # Validate all items are BaseModel instances
        for i, (item_a, item_b) in enumerate(zip(results_a, results_b)):
            if not isinstance(item_a, BaseModel):
                raise TypeError(f"results_a[{i}] is not a BaseModel instance")
            if not isinstance(item_b, BaseModel):
                raise TypeError(f"results_b[{i}] is not a BaseModel instance")

        # Handle empty lists
        if len(results_a) == 0:
            return 1.0

        # Calculate alignment
        aligned_count = 0
        for item_a, item_b in zip(results_a, results_b):
            # Check if both have passes() method
            if not hasattr(item_a, 'passes') or not hasattr(item_b, 'passes'):
                raise TypeError("Results must be instances from to_pydantic_model() with passes() method")

            if item_a.passes() == item_b.passes():
                aligned_count += 1

        return aligned_count / len(results_a)