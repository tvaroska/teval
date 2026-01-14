#!/usr/bin/env python3
"""
Example demonstrating the new report generation and Pydantic model helper methods.

This example shows:
1. Creating an evaluation rubric
2. Using the Pydantic model with helper methods (passes, get_failed_metrics, etc.)
3. Generating consolidated reports
"""

from teval import EvaluationRubric, MetricDefinition

# Create a code review rubric
rubric = EvaluationRubric(
    rubric_id="code_review_v1",
    metrics=[
        MetricDefinition(
            id="M1",
            rubric="Code compiles without errors",
            mandatory=True
        ),
        MetricDefinition(
            id="M2",
            rubric="No security vulnerabilities detected",
            mandatory=True
        ),
        MetricDefinition(
            id="C1",
            rubric="Follows project style guide"
        ),
        MetricDefinition(
            id="C2",
            rubric="Has comprehensive unit tests"
        ),
        MetricDefinition(
            id="C3",
            rubric="Code is well documented"
        ),
        MetricDefinition(
            id="C4",
            rubric="Performance is acceptable"
        ),
    ],
    passing_score_threshold=3
)

print("=" * 70)
print("EXAMPLE 1: Using Pydantic Model Helper Methods")
print("=" * 70)

# Create a Pydantic model for type-safe evaluation results
ResultModel = rubric.to_pydantic_model()

# Create a sample evaluation result
result = ResultModel(
    M1=True,
    M1_reasoning="Code compiles successfully with no errors",
    M2=True,
    M2_reasoning="Security scan passed",
    C1=False,
    C1_reasoning="Some style guide violations found",
    C2=True,
    C2_reasoning="80% test coverage achieved",
    C3=True,
    C3_reasoning="All public APIs documented",
    C4=True,
    C4_reasoning="Response time under 100ms"
)

# Use helper methods
print(f"\nEvaluation passes: {result.passes()}")
print(f"Passed metrics: {result.get_passed_metrics()}")
print(f"Failed metrics: {result.get_failed_metrics()}")

print("\n" + "=" * 70)
print("EXAMPLE 2: Consolidated Report from Pydantic Model")
print("=" * 70)
print()
print(result.to_report())

print("\n" + "=" * 70)
print("EXAMPLE 3: Consolidated Report from EvaluationRubric")
print("=" * 70)

# You can also generate a report directly from the rubric
result_dict = {
    "M1": False,
    "M2": True,
    "C1": True,
    "C2": False,
    "C3": False,
    "C4": True,
}

reasoning_dict = {
    "M1": "Compilation failed with 3 errors",
    "M2": "No security issues detected",
    "C1": "Code follows style guide perfectly",
    "C2": "Only 40% test coverage",
    "C3": "Missing documentation for 5 functions",
    "C4": "Performance within acceptable limits",
}

print()
print(rubric.generate_report(result_dict, reasoning_dict))

print("\n" + "=" * 70)
print("EXAMPLE 4: Report for Passing Evaluation")
print("=" * 70)

passing_result = ResultModel(
    M1=True,
    M1_reasoning="Clean compilation",
    M2=True,
    M2_reasoning="Security audit passed",
    C1=True,
    C1_reasoning="Style guide compliance verified",
    C2=True,
    C2_reasoning="90% test coverage",
    C3=True,
    C3_reasoning="Comprehensive documentation",
    C4=False,
    C4_reasoning="Some queries are slow"
)

print()
print(passing_result.to_report())
