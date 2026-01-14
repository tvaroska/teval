"""
Example usage of teval for LLM evaluations.

This demonstrates how to:
1. Create an evaluation rubric
2. Generate prompt text for LLM evaluators
3. Get JSON schema for structured LLM responses
4. Validate LLM responses against the rubric
"""

import json
from teval import EvaluationRubric, MetricDefinition

# Create an evaluation rubric for code review
rubric = EvaluationRubric(
    rubric_id="code_review_v1",
    metrics=[
        # Mandatory metrics (ALL must pass)
        MetricDefinition(
            id="M1",
            rubric="Code compiles without errors",
            mandatory=True
        ),
        MetricDefinition(
            id="M2",
            rubric="No security vulnerabilities present",
            mandatory=True
        ),
        # Cumulative metrics (must meet threshold)
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
            rubric="Well documented with docstrings"
        ),
    ],
    passing_score_threshold=2  # Must pass 2 out of 3 cumulative metrics
)

# 1. Generate prompt text to include in your LLM evaluation prompt
print("=" * 80)
print("PROMPT TEXT (add this to your LLM evaluation prompt):")
print("=" * 80)
prompt_text = rubric.to_prompt_text()
print(prompt_text)
print()

# 2. Get JSON schema for structured output
print("=" * 80)
print("JSON SCHEMA (use this for structured output generation):")
print("=" * 80)
schema = rubric.to_json_schema()
print(json.dumps(schema, indent=2))
print()

# 2b. Or get a Pydantic model for type-safe validation
print("=" * 80)
print("PYDANTIC MODEL (for type-safe validation):")
print("=" * 80)
ResultModel = rubric.to_pydantic_model()
print(f"Model class: {ResultModel.__name__}")
print(f"Fields: {', '.join(ResultModel.model_fields.keys())}")
print()
print("Example usage:")
print("  result = ResultModel(M1=True, M2=True, C1=True, C2=False, C3=False)")
print("  result.M1  # True")
print("  result.model_dump()  # {'M1': True, 'M2': True, ...}")
print("  ResultModel.model_validate_json(json_string)  # Parse JSON directly")
print()

# 3. Example: Validate an LLM response (accepts both dict and JSON string)
print("=" * 80)
print("VALIDATION EXAMPLES:")
print("=" * 80)

# Example 1: Passing evaluation (using dictionary)
llm_response_pass = {
    "M1": True,
    "M1_reasoning": "Code compiles successfully with no errors",
    "M2": True,
    "M2_reasoning": "No security issues found in scan",
    "C1": True,
    "C1_reasoning": "Follows PEP 8 style guide",
    "C2": True,
    "C2_reasoning": "Has 95% test coverage",
    "C3": False,
    "C3_reasoning": "Some functions lack docstrings",
}

result = rubric.validate_result(llm_response_pass)
print(f"Example 1 (dict - should pass): {result}")
print(f"  - All mandatory metrics passed: ✓")
print(f"  - Cumulative metrics: 2/3 passed (threshold: 2)")
print()

# Example 2: Failing due to mandatory metric (using JSON string)
llm_response_fail_mandatory = """{
    "M1": false,
    "M2": true,
    "C1": true,
    "C2": true,
    "C3": true
}"""

result = rubric.validate_result(llm_response_fail_mandatory)
print(f"Example 2 (JSON string - should fail - mandatory): {result}")
print(f"  - Mandatory metric M1 failed: ✗")
print()

# Example 3: Failing due to cumulative threshold (using JSON string)
llm_response_fail_cumulative = """{
    "M1": true,
    "M2": true,
    "C1": true,
    "C2": false,
    "C3": false
}"""

result = rubric.validate_result(llm_response_fail_cumulative)
print(f"Example 3 (JSON string - should fail - cumulative): {result}")
print(f"  - All mandatory metrics passed: ✓")
print(f"  - Cumulative metrics: 1/3 passed (threshold: 2) ✗")
print()

print("=" * 80)
print("INTEGRATION GUIDE:")
print("=" * 80)
print("""
To use with LLMs like Gemini or OpenAI:

1. Add the prompt text to your evaluation prompt:
   prompt = f\"""
   Evaluate the following code submission:

   {rubric.to_prompt_text()}

   Code to evaluate:
   {code_to_evaluate}
   \"""

2. For structured output, you have two options:

   Option A: Use JSON Schema
   schema = rubric.to_json_schema()

   # Gemini example:
   response = model.generate_content(
       prompt,
       generation_config=genai.GenerationConfig(
           response_mime_type="application/json",
           response_schema=schema
       )
   )

   # OpenAI example with JSON schema:
   response = client.chat.completions.create(
       model="gpt-4",
       messages=[{"role": "user", "content": prompt}],
       response_format={"type": "json_schema", "json_schema": schema}
   )

   Option B: Use Pydantic Model (recommended for type safety)
   ResultModel = rubric.to_pydantic_model()

   # OpenAI with Pydantic (using instructor library):
   import instructor
   client = instructor.from_openai(OpenAI())

   result = client.chat.completions.create(
       model="gpt-4",
       messages=[{"role": "user", "content": prompt}],
       response_model=ResultModel
   )
   # result is now a validated Pydantic model instance
   print(result.M1)  # Type-safe access

3. Validate the LLM response (accepts both JSON string and dict):
   # Option A: Pass the JSON string directly
   passes = rubric.validate_result(response.text)

   # Option B: Parse first, then pass dict
   llm_result = json.loads(response.text)
   passes = rubric.validate_result(llm_result)

   if passes:
       print("Evaluation passed!")
   else:
       print("Evaluation failed.")
""")
