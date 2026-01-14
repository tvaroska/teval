Running teval Tests on Google Cloud Build

This guide details how to run the teval test suite (spanning Python 3.10 - 3.14) using Google Cloud Build.

**Workflow**: Build Docker image locally → Push to GitHub Container Registry → Cloud Build pulls and runs tests

See DOCKER.md for detailed instructions on building and pushing the Docker image locally.

Part 1: Configuration FilesThe following files are in the root of the repository (teval/).1. DockerfileThis file defines the test environment. It uses uv to install specific Python versions and tox so they are pre-baked into the image.# Use a lightweight base image
FROM python:3.12-slim-bookworm

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

# Define the non-root user
ARG CI_USER=teval_user
# Install Python versions required for testing (3.10 to 3.14)
ARG PYTHON_VERSIONS="3.10 3.11 3.12 3.13 3.14"

# Create a non-root user
RUN useradd -m -s /bin/bash $CI_USER

# Switch to the non-root user
USER $CI_USER
WORKDIR /home/$CI_USER/app

# 1. Install the requested Python versions using uv.
RUN uv python install $PYTHON_VERSIONS

# 2. Install tox and the tox-uv plugin.
RUN uv tool install tox --with tox-uv

# 3. Add the user's local bin to PATH so we can run 'tox' directly
ENV PATH="/home/$CI_USER/.local/bin:${PATH}"

# 4. Copy the application code
COPY --chown=$CI_USER:$CI_USER . .

# Default command: run tox
CMD ["tox"]
2. tox.iniThis file configures tox to use uv for virtual environment creation and defines the test matrix.

The configuration tests all combinations of:
- Python versions: 3.10, 3.11, 3.12, 3.13, 3.14
- Pydantic versions: lowest supported (2.7.4) and latest (2.x)

This creates 10 test environments total (5 Python versions × 2 Pydantic versions).

[tox]
# Define the test environments - matrix of Python versions (3.10-3.14) × Pydantic versions (lowest + latest)
env_list =
    py{310,311,312,313,314}-pydantic{lowest,latest}
# Require the tox-uv plugin
requires = tox-uv
# Isolate the build
isolated_build = True

[testenv]
# Use the tox-uv runner for faster virtualenv creation
runner = uv-venv-runner
# Use uv's managed Python versions instead of system Python
uv_python_preference = managed
description = Run unit tests with pytest
# Install test dependencies with different Pydantic versions
deps =
    pytest>=8.0.0
    pytest-cov>=7.0.0
    pydanticlowest: pydantic==2.7.4
    pydanticlatest: pydantic>=2.7.4,<3.0.0
# Pass Google Cloud credentials if present (for future integration tests)
pass_env =
    GOOGLE_CLOUD_PROJECT
    GOOGLE_APPLICATION_CREDENTIALS
commands =
    pytest tests/test_metrics.py -v

# Convenience environment to run all tests with coverage on Python 3.12 with latest Pydantic
[testenv:coverage]
basepython = python3.12
deps =
    pytest>=8.0.0
    pytest-cov>=7.0.0
    pydantic>=2.7.4,<3.0.0
commands =
    pytest --cov=teval --cov-report=term-missing --cov-report=html -v

# Run tests across all Python versions with latest Pydantic only (faster CI)
[testenv:py{310,311,312,313,314}]
deps =
    pytest>=8.0.0
    pydantic>=2.7.4,<3.0.0
commands =
    pytest tests/test_metrics.py -v

**Local Usage Examples:**

```bash
# Run all test combinations (10 environments: 5 Python × 2 Pydantic versions)
uv run tox

# Test a specific Python version with both Pydantic versions
uv run tox -e py312-pydanticlowest,py312-pydanticlatest

# Test all Python versions with lowest Pydantic
uv run tox -e py{310,311,312,313,314}-pydanticlowest

# Test all Python versions with latest Pydantic (faster for CI)
uv run tox -e py{310,311,312,313,314}-pydanticlatest

# Or use the shorthand
uv run tox -e py{310,311,312,313,314}

# Run tests with coverage report
uv run tox -e coverage

# List all available environments
uv run tox -l
```
3. cloudbuild.yamlThis is the build configuration file. It tells Cloud Build to pull the pre-built Docker image from GitHub Container Registry and run tests.

**Note**: The Docker image must be built locally and pushed to ghcr.io first. See DOCKER.md for instructions.

steps:
  # Step 1: Pull the latest image from GitHub Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'pull'
      - 'ghcr.io/tvaroska/teval:latest'

  # Step 2: Run the tests
  # Use the image from GitHub Container Registry. If 'tox' returns non-zero (fails), this step fails.
  - name: 'ghcr.io/tvaroska/teval:latest'
    env:
      - 'GOOGLE_CLOUD_PROJECT=$PROJECT_ID'
    # The default entrypoint is "tox", so we don't need to specify args unless overriding.

options:
  logging: CLOUD_LOGGING_ONLY
Part 2: Setup & Execution Guide

Prerequisites:
- Google Cloud Project with billing enabled
- gcloud CLI installed and authenticated
- Cloud Build API enabled
- Docker image built and pushed to ghcr.io/tvaroska/teval:latest (see DOCKER.md)

1. Initial Setup

Run these commands once to enable the Cloud Build API:

# Enable API
gcloud services enable cloudbuild.googleapis.com

Note: We no longer need Artifact Registry since we're using GitHub Container Registry (ghcr.io).

2. Build and Push Docker Image Locally

Before running tests on Cloud Build, build and push the Docker image locally:

# Build the image
docker build -t ghcr.io/tvaroska/teval:latest .

# Login to GitHub Container Registry (one-time setup)
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u tvaroska --password-stdin

# Push to GitHub Container Registry
docker push ghcr.io/tvaroska/teval:latest

See DOCKER.md for detailed instructions and authentication setup.

3. Run the Tests on Cloud Build

To run the tests, submit the build. Cloud Build will pull the image from ghcr.io and run tox.

gcloud builds submit --config cloudbuild.yaml .

4. (Optional) Configure Permissions for Vertex AI

If you later want to run integration tests with Vertex AI on Cloud Build, grant the service account permissions:

export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/aiplatform.user"

Note: The Cloud Build service account email format is [PROJECT_NUMBER]@cloudbuild.gserviceaccount.com
5. Viewing Results

Terminal: The logs will stream directly to your terminal. You will see the docker pull output followed by the tox output.
Success: If all tests pass, the command finishes with SUCCESS.
Failure: If any tox environment fails (e.g., py310 fails), the Cloud Build step will fail, and the command will exit with FAILURE.

Workflow Summary:

1. Local: docker build -t ghcr.io/tvaroska/teval:latest . && docker push ghcr.io/tvaroska/teval:latest
2. Cloud Build: gcloud builds submit --config cloudbuild.yaml .
3. Cloud Build pulls the image and runs tests across Python 3.10-3.14
