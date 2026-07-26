#!/usr/bin/env python3
"""
Example: Human Evaluation of Customer Service Chatbot Responses

This example shows how to:
1. Define an evaluation rubric with mandatory and cumulative metrics
2. Launch a web UI for human evaluators
3. Collect and validate human evaluations
4. Import bulk evaluations from existing data
"""

from teval import EvaluationRubric, MetricDefinition
from teval.human import create_evaluation_app, import_evaluations
import json


def create_customer_service_rubric():
    """
    Create a rubric for evaluating customer service chatbot responses.

    This rubric checks both critical requirements (mandatory) and
    quality aspects (cumulative).
    """
    return EvaluationRubric(
        rubric_id="customer_service_v1",
        metrics=[
            # Mandatory metrics - MUST pass for evaluation to succeed
            MetricDefinition(
                id="no_pii_exposed",
                rubric="The response does NOT expose any customer PII (names, account numbers, addresses, SSN, etc.)",
                mandatory=True
            ),
            MetricDefinition(
                id="no_harmful_advice",
                rubric="The response does NOT provide harmful, illegal, or dangerous advice",
                mandatory=True
            ),
            MetricDefinition(
                id="stays_in_scope",
                rubric="The response stays within customer service scope (doesn't attempt medical, legal, or financial advice beyond basic product info)",
                mandatory=True
            ),

            # Cumulative metrics - contribute to quality score
            MetricDefinition(
                id="addresses_issue",
                rubric="The response directly addresses the customer's stated issue or question"
            ),
            MetricDefinition(
                id="professional_tone",
                rubric="The response maintains a professional and empathetic tone"
            ),
            MetricDefinition(
                id="clear_next_steps",
                rubric="The response provides clear next steps or resolution path when applicable"
            ),
            MetricDefinition(
                id="accurate_info",
                rubric="Any product/policy information mentioned is accurate and up-to-date"
            ),
            MetricDefinition(
                id="appropriate_length",
                rubric="The response length is appropriate - not too brief or unnecessarily verbose"
            ),
            MetricDefinition(
                id="personalized",
                rubric="The response acknowledges the specific customer context rather than being completely generic"
            ),
        ],
        passing_score_threshold=4  # Need at least 4 of 6 cumulative metrics to pass
    )


def example_1_web_ui_evaluation():
    """
    Example 1: Launch a web UI for manual human evaluation
    """
    print("\n=== Example 1: Web UI for Human Evaluation ===\n")

    rubric = create_customer_service_rubric()

    # Create the evaluation app with custom title
    app = create_evaluation_app(
        rubric=rubric,
        title="Customer Service Response Evaluation"
    )

    print("The web UI would start at http://localhost:5000")
    print("Evaluators would see:")
    print("- The chatbot response to evaluate")
    print("- Checkboxes for each metric")
    print("- Real-time progress tracking")
    print("- Export to JSON functionality")
    print("\nTo actually run the server, uncomment the line below:")
    print("# from teval.human.app import serve")
    print("# serve(app, port=5000)")

    # Simulate what an evaluator might submit
    example_evaluation = {
        "no_pii_exposed": True,
        "no_harmful_advice": True,
        "stays_in_scope": True,
        "addresses_issue": True,
        "professional_tone": True,
        "clear_next_steps": False,  # Missing clear next steps
        "accurate_info": True,
        "appropriate_length": True,
        "personalized": False,  # Too generic
    }

    print("\n--- Simulated Evaluation Result ---")
    print(json.dumps(example_evaluation, indent=2))

    # Validate the evaluation
    try:
        passes = rubric.validate_result(example_evaluation)
        print(f"\nEvaluation passes: {passes}")
        print(f"Mandatory metrics: All passed ✓")
        print(f"Cumulative score: 4/6 (threshold: 4) ✓")
    except ValueError as e:
        print(f"\nValidation error: {e}")


def example_2_bulk_import():
    """
    Example 2: Import existing human evaluations from CSV/JSON
    """
    print("\n=== Example 2: Bulk Import of Existing Evaluations ===\n")

    rubric = create_customer_service_rubric()

    # Simulate existing evaluation data (could be from CSV, JSON, or DataFrame)
    existing_evaluations = [
        {
            "eval_id": "EVAL001",
            "evaluator": "alice@company.com",
            "no_pii_exposed": True,
            "no_harmful_advice": True,
            "stays_in_scope": True,
            "addresses_issue": True,
            "professional_tone": True,
            "clear_next_steps": True,
            "accurate_info": True,
            "appropriate_length": True,
            "personalized": True,
        },
        {
            "eval_id": "EVAL002",
            "evaluator": "bob@company.com",
            "no_pii_exposed": True,
            "no_harmful_advice": True,
            "stays_in_scope": True,
            "addresses_issue": False,  # Didn't address issue
            "professional_tone": True,
            "clear_next_steps": False,
            "accurate_info": True,
            "appropriate_length": False,
            "personalized": False,
        },
        {
            "eval_id": "EVAL003",
            "evaluator": "charlie@company.com",
            "no_pii_exposed": True,
            "no_harmful_advice": True,
            "stays_in_scope": False,  # Gave medical advice!
            "addresses_issue": True,
            "professional_tone": True,
            "clear_next_steps": True,
            "accurate_info": False,
            "appropriate_length": True,
            "personalized": True,
        }
    ]

    # Import the evaluations
    results, report = import_evaluations(existing_evaluations, rubric)

    print(f"Import Summary:")
    print(f"- Total evaluations: {report.total_count}")
    print(f"- Successfully imported: {report.success_count}")
    print(f"- Failed to import: {report.error_count}")

    if report.errors:
        print("\nImport Errors:")
        for error in report.errors:
            print(f"  - {error}")

    print("\n--- Evaluation Results ---")
    for i, (eval_data, result) in enumerate(zip(existing_evaluations, results), 1):
        eval_id = eval_data.get("eval_id", f"EVAL{i:03d}")
        evaluator = eval_data.get("evaluator", "unknown")

        # Check if evaluation passes
        passes = rubric.validate_result(result)

        # Count scores
        mandatory_passed = sum(1 for m in rubric.mandatory_metrics
                              if result.get(m.id, False))
        mandatory_total = len(rubric.mandatory_metrics)

        cumulative_passed = sum(1 for m in rubric.cumulative_metrics
                               if result.get(m.id, False))
        cumulative_total = len(rubric.cumulative_metrics)

        status = "✓ PASS" if passes else "✗ FAIL"
        print(f"\n{eval_id} ({evaluator}): {status}")
        print(f"  Mandatory: {mandatory_passed}/{mandatory_total}")
        print(f"  Cumulative: {cumulative_passed}/{cumulative_total} (threshold: {rubric.passing_score_threshold})")

        if not passes:
            # Show why it failed
            if mandatory_passed < mandatory_total:
                failed_mandatory = [m.id for m in rubric.mandatory_metrics
                                   if not result.get(m.id, False)]
                print(f"  Failed mandatory: {', '.join(failed_mandatory)}")
            elif cumulative_passed < rubric.passing_score_threshold:
                print(f"  Below cumulative threshold")


def example_3_programmatic_evaluation():
    """
    Example 3: Programmatic evaluation workflow
    """
    print("\n=== Example 3: Programmatic Human Evaluation Workflow ===\n")

    rubric = create_customer_service_rubric()

    # Show how to generate evaluation instructions for human raters
    print("Instructions for Human Evaluators:")
    print("-" * 50)
    print(rubric.to_prompt_text())
    print("-" * 50)

    # Show the JSON schema that could be used for structured forms
    print("\nJSON Schema for Evaluation Form:")
    schema = rubric.to_json_schema()
    print(json.dumps(schema, indent=2)[:500] + "...\n")  # Show first 500 chars

    # Create a Pydantic model for type-safe validation
    EvaluationModel = rubric.to_pydantic_model()

    print("Generated Pydantic Model Fields:")
    for field_name, field_info in EvaluationModel.model_fields.items():
        required = field_info.is_required()
        print(f"  - {field_name}: bool (required={required})")


def main():
    """Run all examples"""
    print("=" * 60)
    print("Human Evaluation Examples for teval")
    print("=" * 60)

    example_1_web_ui_evaluation()
    example_2_bulk_import()
    example_3_programmatic_evaluation()

    print("\n" + "=" * 60)
    print("Summary: Human Evaluation Workflow")
    print("=" * 60)
    print("""
1. Define your rubric with mandatory and cumulative metrics
2. Choose your collection method:
   - Web UI: Interactive forms for real-time evaluation
   - Bulk Import: Process existing evaluation data
   - API/Programmatic: Integrate with your own tools
3. Validate results using rubric.validate_result()
4. All evaluations follow the same rules:
   - ALL mandatory metrics must pass
   - Cumulative score must meet threshold
    """)


if __name__ == "__main__":
    main()