import os
import json
import pytest

try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False

from teval import EvaluationRubric, MetricDefinition


# Skip all tests in this module if google-genai is not installed
pytestmark = pytest.mark.skipif(
    not GOOGLE_GENAI_AVAILABLE,
    reason="google-genai not installed. Install with: uv sync --group integration-tests"
)


@pytest.fixture
def client():
    """
    Create a Vertex AI client.

    Requires GOOGLE_CLOUD_PROJECT environment variable.
    """
    try:
        client = genai.Client(vertexai=True, location="global")
        return client
    except Exception as e:
        pytest.skip(f"Failed to initialize Vertex AI client: {e}")


@pytest.fixture
def simple_rubric():
    """Create a simple evaluation rubric for testing."""
    return EvaluationRubric(
        rubric_id="test_simple_v1",
        metrics=[
            MetricDefinition(
                id="CP",
                rubric="Sentences begin with a capital letter and end with correct punctuation (. ? !).",
                mandatory=True
            ),
            MetricDefinition(
                id="CS",
                rubric="All sentences are complete thoughts and do not run on (e.g., I like my dog.)."
            ),
            MetricDefinition(
                id="G",
                rubric="Correct use of verb tenses (e.g., he runs, I played) and plural/singular forms."
            ),
            MetricDefinition(
                id="CT",
                rubric="The paragraph stays focused on one main topic (e.g., your dog)."
            ),
        ],
        passing_score_threshold=3
    )

@pytest.mark.integration
def test_simple_evaluation(client, simple_rubric):
    """Test a simple evaluation using Vertex AI with structured output."""

    # Content to evaluate
    content_to_evaluate = """My dog is big. He run fast. I like to play with him in park. We go everyday. My dog name is Spot. He haves a tail."""

    # Create the evaluation prompt
    prompt = f"""
You are an expert evaluator. Evaluate the following Q&A response.

{simple_rubric.to_prompt_text()}

Content to evaluate:
{content_to_evaluate}

Provide your evaluation as a JSON object with boolean values for each metric.
Include a reasoning field for each metric (metric_id + "_reasoning").
"""

    # Get JSON schema from rubric
    schema = simple_rubric.to_json_schema()

    # Convert to Vertex AI schema format
    response_schema = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema
    )

    # Call Vertex AI
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=response_schema
    )

    # Extract the response text
    response_text = response.text

    # Validate using our framework (accepts JSON string)
    passes = simple_rubric.validate_result(response_text)

    # Parse to check the structure
    result = json.loads(response_text)

    # Assertions
    assert "CP" in result
    assert "CS" in result
    assert "G" in result
    assert isinstance(result["CP"], bool)
    assert isinstance(result["CS"], bool)
    assert isinstance(result["G"], bool)

    # This should pass since capital letters and punctuation are correct
    assert result["CP"] is True
    assert passes is True

    print(f"\nEvaluation result: {'PASS' if passes else 'FAIL'}")
    print(f"Response: {json.dumps(result, indent=2)}")
