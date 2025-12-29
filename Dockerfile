# Use a lightweight base image
FROM python:3.12-slim-bookworm

# Install build tools and dependencies
# These are required for compiling native extensions like pydantic-core
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

# Install Python versions required for testing (3.10 to 3.13)
ARG PYTHON_VERSIONS="3.10 3.11 3.12 3.13"

# Set working directory
WORKDIR /workspace

# Install the requested Python versions using uv (as root for CI)
RUN uv python install $PYTHON_VERSIONS

# Install tox and the tox-uv plugin
RUN uv tool install tox --with tox-uv

# Add uv tools to PATH so we can run 'tox' directly and find Python versions
ENV PATH="/root/.local/bin:${PATH}" \
    UV_PYTHON_INSTALL_DIR="/root/.local/share/uv/python"

# Note: Code is NOT copied into the image - it will be mounted at runtime
# This allows the image to be cached and reused across builds

# Default command: run tox
CMD ["tox"]
