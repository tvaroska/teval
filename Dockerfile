# Use a lightweight base image
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

# 3. Add the user's local bin and uv python bin to PATH so we can run 'tox' directly and find Python versions
ENV PATH="/home/$CI_USER/.local/bin:${PATH}" \
    UV_PYTHON_INSTALL_DIR="/home/$CI_USER/.local/share/uv/python"

# Note: Code is NOT copied into the image - it will be mounted at runtime
# This allows the image to be cached and reused across builds

# Default command: run tox
CMD ["tox"]
