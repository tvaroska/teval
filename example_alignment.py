"""
Example usage of alignment calculation for comparing evaluation results.

This demonstrates how to compare if two evaluators (e.g., different LLM models,
or human vs LLM) agree on pass/fail outcomes.
"""

from teval import EvaluationRubric, MetricDefinition


def example_single_comparison():
    """Example: Compare single evaluation results."""
    print("=" * 60)
    print("Example 1: Single Result Comparison")
    print("=" * 60)

    # Define a rubric for code review
    rubric = EvaluationRubric(
        rubric_id="code_review_v1",
        metrics=[
            MetricDefinition(id="M1", rubric="Code compiles without errors", mandatory=True),
            MetricDefinition(id="M2", rubric="No security vulnerabilities", mandatory=True),
            MetricDefinition(id="C1", rubric="Follows style guide"),
            MetricDefinition(id="C2", rubric="Has unit tests"),
            MetricDefinition(id="C3", rubric="Well documented"),
        ],
        passing_score_threshold=2,
    )

    # Get the Pydantic model for results
    ResultModel = rubric.to_pydantic_model()

    # Simulate evaluation by gemini-2.5-flash
    flash_result = ResultModel(
        M1=True,  # Compiles
        M2=True,  # No vulnerabilities
        C1=True,  # Follows style
        C2=False, # No tests
        C3=True,  # Documented
    )

    # Simulate evaluation by gemini-2.0-pro
    pro_result = ResultModel(
        M1=True,  # Compiles
        M2=True,  # No vulnerabilities
        C1=True,  # Follows style
        C2=True,  # Has tests (different from flash!)
        C3=False, # Not documented (different from flash!)
    )

    print(f"\nFlash evaluation passes: {flash_result.passes()}")
    print(f"Pro evaluation passes: {pro_result.passes()}")

    # Calculate alignment
    alignment = rubric.calculate_alignment(flash_result, pro_result)
    print(f"\nAlignment: {alignment:.1%}")

    if alignment == 1.0:
        print("✓ Both evaluators agree on pass/fail outcome!")
    else:
        print("✗ Evaluators disagree on pass/fail outcome")

    print()


def example_batch_comparison():
    """Example: Compare batch of evaluation results (common use case)."""
    print("=" * 60)
    print("Example 2: Batch Comparison (100 Samples)")
    print("=" * 60)

    # Define a rubric
    rubric = EvaluationRubric(
        rubric_id="content_quality_v1",
        metrics=[
            MetricDefinition(id="M1", rubric="No offensive content", mandatory=True),
            MetricDefinition(id="C1", rubric="Clear and concise"),
            MetricDefinition(id="C2", rubric="Factually accurate"),
            MetricDefinition(id="C3", rubric="Well structured"),
        ],
        passing_score_threshold=2,
    )

    ResultModel = rubric.to_pydantic_model()

    # Simulate 100 evaluations with gemini-2.5-flash
    print("\nSimulating 100 evaluations with gemini-2.5-flash...")
    flash_results = [
        ResultModel(M1=True, C1=True, C2=True, C3=False),   # Pass
        ResultModel(M1=True, C1=False, C2=True, C3=True),   # Pass
        ResultModel(M1=False, C1=True, C2=True, C3=True),   # Fail (mandatory)
        ResultModel(M1=True, C1=True, C2=False, C3=False),  # Fail (threshold)
        ResultModel(M1=True, C1=True, C2=True, C3=True),    # Pass
        # ... in practice, you'd have 100 samples here
    ]

    # Simulate 100 evaluations with gemini-2.0-pro on SAME samples
    print("Simulating 100 evaluations with gemini-2.0-pro...")
    pro_results = [
        ResultModel(M1=True, C1=True, C2=False, C3=True),   # Pass (aligned - both pass)
        ResultModel(M1=True, C1=True, C2=True, C3=True),    # Pass (aligned - both pass)
        ResultModel(M1=False, C1=False, C2=False, C3=False),# Fail (aligned - both fail)
        ResultModel(M1=True, C1=True, C2=True, C3=True),    # Pass (NOT aligned - flash failed)
        ResultModel(M1=True, C1=False, C2=True, C3=True),   # Pass (aligned - both pass)
        # ... in practice, you'd have 100 samples here
    ]

    # Calculate alignment
    alignment = rubric.calculate_alignment(flash_results, pro_results)

    print(f"\nAlignment: {alignment:.1%}")
    print(f"Aligned samples: {int(alignment * len(flash_results))} out of {len(flash_results)}")

    # Decision making based on alignment
    if alignment >= 0.95:
        print("\n✓ Flash model is 95%+ aligned with Pro!")
        print("  → Safe to use Flash instead of Pro for cost savings")
    elif alignment >= 0.90:
        print("\n⚠ Flash model is 90-95% aligned with Pro")
        print("  → Consider using Flash for non-critical evaluations")
    else:
        print(f"\n✗ Only {alignment:.1%} aligned")
        print("  → Stick with Pro model for better accuracy")

    print()


def example_human_llm_alignment():
    """Example: Compare human evaluations with LLM evaluations."""
    print("=" * 60)
    print("Example 3: Human-LLM Alignment")
    print("=" * 60)

    rubric = EvaluationRubric(
        rubric_id="essay_grading_v1",
        metrics=[
            MetricDefinition(id="M1", rubric="Answers the prompt", mandatory=True),
            MetricDefinition(id="C1", rubric="Strong thesis statement"),
            MetricDefinition(id="C2", rubric="Supporting evidence provided"),
            MetricDefinition(id="C3", rubric="Proper grammar and spelling"),
            MetricDefinition(id="C4", rubric="Logical flow and structure"),
        ],
        passing_score_threshold=3,
    )

    ResultModel = rubric.to_pydantic_model()

    # Human teacher evaluations of 10 essays
    human_results = [
        ResultModel(M1=True, C1=True, C2=True, C3=True, C4=True),    # Pass
        ResultModel(M1=True, C1=False, C2=True, C3=True, C4=True),   # Pass
        ResultModel(M1=True, C1=False, C2=False, C3=True, C4=False), # Fail
        ResultModel(M1=False, C1=True, C2=True, C3=True, C4=True),   # Fail (mandatory)
        ResultModel(M1=True, C1=True, C2=True, C3=False, C4=True),   # Pass
        ResultModel(M1=True, C1=True, C2=False, C3=True, C4=True),   # Pass
        ResultModel(M1=True, C1=False, C2=False, C3=False, C4=False),# Fail
        ResultModel(M1=True, C1=True, C2=True, C3=True, C4=False),   # Pass
        ResultModel(M1=True, C1=True, C2=True, C3=True, C4=True),    # Pass
        ResultModel(M1=True, C1=False, C2=True, C3=True, C4=True),   # Pass
    ]

    # LLM evaluations of same 10 essays
    llm_results = [
        ResultModel(M1=True, C1=True, C2=True, C3=True, C4=True),    # Pass (aligned)
        ResultModel(M1=True, C1=True, C2=True, C3=True, C4=True),    # Pass (aligned)
        ResultModel(M1=True, C1=True, C2=False, C3=True, C4=False),  # Fail (aligned)
        ResultModel(M1=False, C1=False, C2=True, C3=True, C4=True),  # Fail (aligned)
        ResultModel(M1=True, C1=False, C2=True, C3=False, C4=True),  # Pass (aligned)
        ResultModel(M1=True, C1=False, C2=False, C3=True, C4=True),  # Fail (NOT aligned)
        ResultModel(M1=True, C1=False, C2=False, C3=False, C4=True), # Fail (aligned)
        ResultModel(M1=True, C1=True, C2=True, C3=False, C4=True),   # Pass (aligned)
        ResultModel(M1=True, C1=True, C2=True, C3=True, C4=True),    # Pass (aligned)
        ResultModel(M1=True, C1=True, C2=True, C3=True, C4=True),    # Pass (aligned)
    ]

    alignment = rubric.calculate_alignment(human_results, llm_results)

    print(f"\nHuman-LLM Alignment: {alignment:.1%}")
    print(f"Agreement on {int(alignment * len(human_results))} out of {len(human_results)} essays")

    if alignment >= 0.90:
        print("\n✓ High human-LLM alignment!")
        print("  → LLM can be trusted for automated grading")
    else:
        print("\n⚠ Lower human-LLM alignment")
        print("  → Human review recommended for borderline cases")

    print()


if __name__ == "__main__":
    example_single_comparison()
    example_batch_comparison()
    example_human_llm_alignment()

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print("Alignment score interpretation:")
    print("  1.0 (100%)  = Perfect alignment")
    print("  0.95+ (95%) = Excellent alignment - models are interchangeable")
    print("  0.90+ (90%) = Good alignment - consider cost/quality tradeoffs")
    print("  <0.90 (<90%)= Poor alignment - use higher quality model")
    print()
