"""
Example demonstrating Pydantic model usage with teval.

This shows how to use the dynamically created Pydantic model for:
1. Type-safe result creation
2. JSON parsing with validation
3. Integration with the evaluation rubric
"""

from teval import EvaluationRubric, MetricDefinition

# Create a simple rubric
rubric = EvaluationRubric(
    rubric_id="code_quality_v1",
    metrics=[
        MetricDefinition(id="M1", rubric="Code runs without errors", mandatory=True),
        MetricDefinition(id="C1", rubric="Code is well-formatted"),
        MetricDefinition(id="C2", rubric="Code has good naming"),
    ],
    passing_score_threshold=1
)

# Generate the Pydantic model
ResultModel = rubric.to_pydantic_model()

print("=" * 80)
print("PYDANTIC MODEL DEMONSTRATION")
print("=" * 80)
print()

# Example 1: Create instance directly
print("1. Creating a result instance with type safety:")
print("-" * 80)
result1 = ResultModel(
    M1=True,
    M1_reasoning="Code executes successfully",
    C1=True,
    C1_reasoning="Follows PEP 8",
    C2=False,
    C2_reasoning="Some variable names are unclear"
)

print(f"M1 (mandatory): {result1.M1}")
print(f"C1 (cumulative): {result1.C1}")
print(f"C2 (cumulative): {result1.C2}")
print(f"M1 reasoning: {result1.M1_reasoning}")
print()

# Example 2: Parse from JSON string
print("2. Parsing from JSON string (e.g., LLM response):")
print("-" * 80)
llm_json_response = """{
    "M1": true,
    "M1_reasoning": "All tests pass",
    "C1": false,
    "C1_reasoning": "Inconsistent formatting",
    "C2": true,
    "C2_reasoning": "Variable names are descriptive"
}"""

result2 = ResultModel.model_validate_json(llm_json_response)
print(f"Parsed result: M1={result2.M1}, C1={result2.C1}, C2={result2.C2}")
print()

# Example 3: Export to dictionary
print("3. Exporting to dictionary:")
print("-" * 80)
result_dict = result1.model_dump()
print(f"Full dict: {result_dict}")
print()

# Exclude None values
result_dict_no_none = result1.model_dump(exclude_none=True)
print(f"Dict (excluding None): {result_dict_no_none}")
print()

# Example 4: Validate against rubric
print("4. Validating results against rubric:")
print("-" * 80)

# Result 1: Should pass (M1=True, and 1 cumulative metric passes)
passes_1 = rubric.validate_result(result1.model_dump())
print(f"Result 1 passes: {passes_1} (M1=True, C1=True, C2=False)")

# Result 2: Should pass (M1=True, and 1 cumulative metric passes)
passes_2 = rubric.validate_result(result2.model_dump())
print(f"Result 2 passes: {passes_2} (M1=True, C1=False, C2=True)")

# Create a failing result
result3 = ResultModel(M1=False, C1=True, C2=True)
passes_3 = rubric.validate_result(result3.model_dump())
print(f"Result 3 passes: {passes_3} (M1=False - mandatory fails)")
print()

# Example 5: Validation errors
print("5. Pydantic automatic validation:")
print("-" * 80)

try:
    # Missing required field
    invalid_result = ResultModel(M1=True, C1=True)  # Missing C2
except Exception as e:
    print(f"✗ Error (missing C2): {type(e).__name__}")

try:
    # Wrong type
    invalid_result = ResultModel(M1="yes", C1=True, C2=False)
except Exception as e:
    print(f"✗ Error (wrong type): {type(e).__name__}")

try:
    # Extra field not allowed
    invalid_result = ResultModel(M1=True, C1=True, C2=False, extra="field")
except Exception as e:
    print(f"✗ Error (extra field): {type(e).__name__}")

print()

# Example 6: JSON Schema from Pydantic model
print("6. Generating JSON Schema from Pydantic model:")
print("-" * 80)
pydantic_schema = ResultModel.model_json_schema()
print(f"Schema title: {pydantic_schema.get('title')}")
print(f"Required fields: {pydantic_schema.get('required')}")
print(f"Number of properties: {len(pydantic_schema.get('properties', {}))}")
print()

# Example 7: Type hints and IDE support
print("7. Type hints benefit:")
print("-" * 80)
print("With Pydantic models, you get:")
print("  - IDE autocomplete for field names")
print("  - Type checking with mypy/pyright")
print("  - Automatic validation on instantiation")
print("  - JSON serialization/deserialization")
print("  - Schema generation")
print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print("The Pydantic model approach provides:")
print("  ✓ Type safety and IDE support")
print("  ✓ Automatic validation")
print("  ✓ Easy JSON parsing and serialization")
print("  ✓ Integration with tools like instructor, FastAPI, etc.")
print("  ✓ Better developer experience than raw dictionaries")
print()
print("Use rubric.to_pydantic_model() when you want strong typing")
print("Use rubric.to_json_schema() when you need a plain JSON schema")
print()
