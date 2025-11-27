# Dockerfile for Python Dependency Management Environment
#
# This image provides an isolated environment for managing Python project dependencies
# using Poetry, PDM, uv, and pipx, without requiring any tools to be installed on the host.
# - Installs Python, pipx, Poetry, PDM, and uv
# - Creates a non-root user to match host UID/GID for correct file permissions
# - Designed to be used with docker-compose and a /workspace volume mount
# - Intended for interactive use and automation

# Build argument for Python version (defaults to 3.13 if not provided)
ARG PYTHON_VERSION=3.13-slim
FROM python:${PYTHON_VERSION}

# Install system dependencies, including bash for interactive shells
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to match host UID/GID for file permissions
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN addgroup --gid $GROUP_ID devuser && \
    adduser --disabled-password --gecos '' --uid $USER_ID --gid $GROUP_ID devuser

# Switch to devuser for pipx installation
USER devuser

# Set up pipx environment variables
ENV PIPX_HOME=/home/devuser/.local/pipx
ENV PIPX_BIN_DIR=/home/devuser/.local/bin
ENV PATH=/home/devuser/.local/bin:$PATH

# Install pipx as the devuser
RUN pip install --user pipx && pipx ensurepath

# Install Poetry, PDM, and uv globally using pipx
RUN pipx install poetry && pipx install pdm && pipx install uv

# Configure PDM to use uv as backend by default (can be overridden by config)
RUN pdm config use_uv true

WORKDIR /workspace

# Default to bash for interactive use
CMD ["/bin/bash"] 