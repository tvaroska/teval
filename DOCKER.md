# Docker Image Build and Push Guide

This guide explains the two-layer architecture for testing: a cached Docker image for infrastructure and dynamic code injection at runtime.

## Architecture Overview

This project separates **infrastructure** from **code**:

1. **Docker Image (ghcr.io/tvaroska/teval:latest)**: Contains Python 3.10-3.14, uv, and tox (NO code)
2. **Repository Code**: Injected at Cloud Build runtime from `/workspace`

**Benefits**:
- Faster CI builds (no image rebuild on code changes)
- Clear separation of concerns
- Efficient caching of heavy Python installations

## What Gets Tested

Every Cloud Build run tests your code against:

- **Python versions**: 3.10, 3.11, 3.12, 3.13, 3.14
- **Pydantic versions**: 2.8.0 (minimum) and latest (<3.0.0)
- **Total test environments**: 10 (5 Python × 2 Pydantic)

This matrix is defined in tox.ini:4 and automatically executed by the Docker image.

## Prerequisites

### 1. Docker Installation

Ensure Docker is installed and running:

```bash
docker --version
```

### 2. GitHub Container Registry Authentication

Create a GitHub Personal Access Token (PAT):

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "teval-docker-push")
4. Select scopes:
   - `write:packages`
   - `read:packages`
   - `delete:packages` (optional)
5. Click "Generate token" and copy it

Login to GitHub Container Registry:

```bash
# Replace YOUR_GITHUB_TOKEN with your actual token
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u tvaroska --password-stdin
```

Alternatively, set it as an environment variable for repeated use:

```bash
export GITHUB_TOKEN=YOUR_GITHUB_TOKEN
echo $GITHUB_TOKEN | docker login ghcr.io -u tvaroska --password-stdin
```

## Building and Pushing the Image

### Option 1: Build and Push Latest (Recommended)

Build and push the image tagged as `latest`:

```bash
# Build the image
docker build -t ghcr.io/tvaroska/teval:latest .

# Push to GitHub Container Registry
docker push ghcr.io/tvaroska/teval:latest
```

### Option 2: Build with Version Tag

Tag with a specific version:

```bash
VERSION=0.1.1

# Build with multiple tags
docker build \
  -t ghcr.io/tvaroska/teval:latest \
  -t ghcr.io/tvaroska/teval:v${VERSION} \
  .

# Push both tags
docker push ghcr.io/tvaroska/teval:latest
docker push ghcr.io/tvaroska/teval:v${VERSION}
```

### Option 3: Build with Git Commit SHA

Tag with the current git commit SHA:

```bash
# Get current commit SHA
GIT_SHA=$(git rev-parse --short HEAD)

# Build with multiple tags
docker build \
  -t ghcr.io/tvaroska/teval:latest \
  -t ghcr.io/tvaroska/teval:${GIT_SHA} \
  .

# Push both tags
docker push ghcr.io/tvaroska/teval:latest
docker push ghcr.io/tvaroska/teval:${GIT_SHA}
```

### Combined Script

Here's a complete script to build and push:

```bash
#!/bin/bash
set -e

# Configuration
IMAGE_NAME="ghcr.io/tvaroska/teval"
VERSION=$(grep '^version' pyproject.toml | cut -d'"' -f2)
GIT_SHA=$(git rev-parse --short HEAD)

echo "Building Docker image..."
echo "  Image: ${IMAGE_NAME}"
echo "  Version: ${VERSION}"
echo "  Commit: ${GIT_SHA}"

# Build with multiple tags
docker build \
  -t ${IMAGE_NAME}:latest \
  -t ${IMAGE_NAME}:v${VERSION} \
  -t ${IMAGE_NAME}:${GIT_SHA} \
  .

echo "Pushing to GitHub Container Registry..."
docker push ${IMAGE_NAME}:latest
docker push ${IMAGE_NAME}:v${VERSION}
docker push ${IMAGE_NAME}:${GIT_SHA}

echo "Done! Image pushed successfully."
echo "  ${IMAGE_NAME}:latest"
echo "  ${IMAGE_NAME}:v${VERSION}"
echo "  ${IMAGE_NAME}:${GIT_SHA}"
```

## Testing Locally

### Option 1: Using uv Directly (Fastest)

```bash
# Run full test matrix
uv run tox

# Run specific Python/Pydantic combination
uv run tox -e py310-pydanticlowest
```

### Option 2: Using Docker Image (Matches CI Exactly)

Mount your code into the container:

```bash
# Run full test matrix with current code
docker run --rm -v $(pwd):/home/teval_user/app ghcr.io/tvaroska/teval:latest

# Run specific environment
docker run --rm -v $(pwd):/home/teval_user/app ghcr.io/tvaroska/teval:latest \
  tox -e py312-pydanticlatest

# Interactive debugging
docker run --rm -it -v $(pwd):/home/teval_user/app \
  --entrypoint /bin/bash ghcr.io/tvaroska/teval:latest
```

**Note**: The `-v` flag mounts your local code into the container, exactly like Cloud Build does.

## Running Tests on Google Cloud Build

Cloud Build uses the cached image and injects your repository code at runtime:

```bash
# Submit build (no Docker rebuild needed!)
gcloud builds submit --config cloudbuild.yaml .
```

**What happens**:
1. Cloud Build clones your repository to `/workspace`
2. Pulls `ghcr.io/tvaroska/teval:latest` (cached image with Python versions)
3. Copies code from `/workspace` into the container
4. Runs `tox` to test all Python 3.10-3.14 × Pydantic versions

**Important**: You only need to rebuild the Docker image when Python versions or tools change, NOT on every code commit!

## Image Visibility

By default, GitHub Container Registry packages are private. To make the image public:

1. Go to https://github.com/tvaroska?tab=packages
2. Click on the `teval` package
3. Click "Package settings" (right side)
4. Scroll down to "Danger Zone"
5. Click "Change visibility" → "Public"

This allows Cloud Build and others to pull the image without authentication.

## Troubleshooting

### "denied: permission_denied: write_package"

Your GitHub token doesn't have the required permissions. Create a new token with `write:packages` scope.

### "no basic auth credentials"

You haven't logged in to ghcr.io. Run:

```bash
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u tvaroska --password-stdin
```

### "failed to solve: python:3.12-slim-bookworm: failed to resolve source metadata"

Docker can't pull the base image. Check your internet connection and Docker daemon status.

### "failed to install Python 3.14"

Python 3.14 might not be available yet in uv. Either:
- Wait for uv to support Python 3.14
- Remove Python 3.14 from Dockerfile and tox.ini temporarily

### Cloud Build can't pull the image

If the package is private, you need to configure Cloud Build authentication:

```bash
# Grant Cloud Build access to pull from ghcr.io
# This requires storing your GitHub token in Secret Manager
# See cloudbuild.yaml for details
```

Alternatively, make the package public (see "Image Visibility" above).

## Workflow Summary

### Normal Development (Code Changes)

```
┌─────────────────────────────────────────────────────────────┐
│ Local Development                                           │
│                                                             │
│  1. Make code changes to src/teval/*.py or tests/          │
│  2. Test locally: uv run tox                                │
│  3. Commit and push to GitHub                               │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Google Cloud Build                                          │
│                                                             │
│  1. gcloud builds submit --config cloudbuild.yaml .        │
│  2. Pulls cached image: ghcr.io/tvaroska/teval:latest      │
│  3. Injects code from /workspace into container             │
│  4. Runs tox (5 Python versions × 2 Pydantic versions)     │
│  5. Reports SUCCESS or FAILURE                             │
└─────────────────────────────────────────────────────────────┘
```

### Rare: Infrastructure Changes (Python/Tool Updates)

```
┌─────────────────────────────────────────────────────────────┐
│ Update Dockerfile (Python versions, uv, tox)               │
│                                                             │
│  1. docker build -t ghcr.io/tvaroska/teval:latest .        │
│  2. docker push ghcr.io/tvaroska/teval:latest              │
│  3. Now Cloud Build will use the updated image              │
└─────────────────────────────────────────────────────────────┘
```

## Best Practices

### For Code Changes (99% of commits)
1. **Test locally first**: Run `uv run tox` before pushing
2. **No Docker rebuild needed**: Just commit and push your code
3. **Cloud Build automatically**: Uses cached image + your fresh code

### For Infrastructure Changes (Rare)
1. **Test the image**: Run `docker run --rm -v $(pwd):/home/teval_user/app ghcr.io/tvaroska/teval:latest`
2. **Use semantic versioning**: Tag releases with version numbers (v0.1.0, v0.1.1, etc.)
3. **Keep latest updated**: Always tag and push `:latest` for Cloud Build
4. **Make it public**: Simplifies Cloud Build access (no auth needed)

### When to Rebuild the Docker Image
- Adding/removing Python versions (Dockerfile:15)
- Updating base image (Dockerfile:2)
- Updating uv, tox, or system dependencies
- **NOT** when changing application code or tests!
