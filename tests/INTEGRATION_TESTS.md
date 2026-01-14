# Integration Tests

This directory contains integration tests that verify teval works correctly with real LLM APIs.

## Test Files

- `test_metrics.py` - Unit tests for the core framework (no external dependencies)
- `test_integration_vertex_ai.py` - Integration tests using Google Vertex AI

## Running Unit Tests

Unit tests run without any external dependencies or credentials:

```bash
# Run all unit tests
uv run pytest tests/test_metrics.py -v

# Or exclude integration tests explicitly
uv run pytest -m "not integration" -v
```

## Running Integration Tests

Integration tests require Google Cloud credentials and make real API calls.

### Prerequisites

1. **Install integration test dependencies**:
   ```bash
   uv sync --group integration-tests
   ```

2. **Google Cloud Project**:
   - Create a Google Cloud project or use an existing one
   - Enable the Vertex AI API in your project
   - Note your project ID

3. **Authentication** (choose one method):

   **Option A: Application Default Credentials (recommended for development)**
   ```bash
   gcloud auth application-default login
   ```

   **Option B: Service Account Key**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

4. **Set your project ID**:
   ```bash
   export GOOGLE_CLOUD_PROJECT=your-project-id
   ```

### Running the Tests

```bash
# Run all integration tests
export GOOGLE_CLOUD_PROJECT=your-project-id
uv run pytest tests/test_integration_vertex_ai.py -v

# Run a specific integration test
uv run pytest tests/test_integration_vertex_ai.py::test_vertex_ai_simple_evaluation -v

# Run all tests (unit + integration)
uv run pytest -v
```

### Skipping Integration Tests

If you don't have credentials set up, integration tests will be automatically skipped:

```bash
# Run all tests, skipping integration tests if credentials are missing
uv run pytest -v
```

To explicitly exclude integration tests:

```bash
# Run only unit tests
uv run pytest -m "not integration" -v
```

## Test Coverage

### Unit Tests (`test_metrics.py`)

- ✅ MetricDefinition creation and validation
- ✅ EvaluationRubric creation and validation
- ✅ Mandatory vs cumulative metrics filtering
- ✅ Duplicate ID rejection
- ✅ Threshold validation
- ✅ Prompt text generation
- ✅ JSON schema generation
- ✅ Result validation (dict and JSON string)
- ✅ Error handling for invalid inputs

### Integration Tests (`test_integration_vertex_ai.py`)

- ✅ Simple Q&A evaluation with Vertex AI
- ✅ Code review evaluation with structured output
- ✅ Failing evaluation detection
- ✅ Schema validation compliance
- ✅ Reasoning field population

## Cost Considerations

Integration tests make real API calls to Vertex AI, which may incur costs:

- **Gemini 2.0 Flash**: Very low cost per request (~$0.00001-$0.0001 per request)
- **Estimated test suite cost**: < $0.01 per full run

To minimize costs:
- Run integration tests only when necessary
- Use the skip markers to exclude them during development
- Monitor your Google Cloud billing

## Troubleshooting

### "GOOGLE_CLOUD_PROJECT environment variable not set"

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### "Failed to initialize Vertex AI client"

Ensure you've authenticated:
```bash
gcloud auth application-default login
```

Or set service account credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### "google-genai not installed"

Install integration test dependencies:
```bash
uv sync --group integration-tests
```

### "Vertex AI API is not enabled"

Enable the API in your Google Cloud project:
```bash
gcloud services enable aiplatform.googleapis.com --project=your-project-id
```

Or via the [Cloud Console](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com).

## CI/CD Integration

For continuous integration, you can:

1. **Skip integration tests by default**:
   ```yaml
   # In your CI config
   - run: uv run pytest -m "not integration"
   ```

2. **Run integration tests with secrets**:
   ```yaml
   # GitHub Actions example
   - name: Run integration tests
     env:
       GOOGLE_CLOUD_PROJECT: ${{ secrets.GOOGLE_CLOUD_PROJECT }}
       GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS }}
     run: uv run pytest tests/test_integration_vertex_ai.py
   ```

## Adding New Integration Tests

To add integration tests for other LLM providers:

1. Add the provider's SDK to the `integration-tests` dependency group in `pyproject.toml`
2. Create a new test file: `test_integration_<provider>.py`
3. Use the `@pytest.mark.integration` decorator
4. Add appropriate skip conditions for missing credentials
5. Update this README with setup instructions

Example structure:
```python
import pytest

@pytest.mark.integration
def test_provider_evaluation(provider_client, rubric):
    # Your test here
    pass
```
