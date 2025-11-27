# Use the official Python base image
# Build argument for Python version (defaults to 3.13 if not provided)
ARG PYTHON_VERSION=3.13-slim
FROM python:${PYTHON_VERSION}

# Bake Image tag into the image.
ARG IMAGE_TAG=local_docker
ENV IMAGE_TAG=$IMAGE_TAG

# Set the working directory in the container
WORKDIR /app

# Install database client tools for backup/restore
RUN apt-get update && apt-get install -y \
    postgresql-client \
    mariadb-client \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for better build caching
COPY pyproject.toml pdm.lock ./

# Install PDM and project dependencies (creates a fresh .venv)
RUN pip install pdm && pdm install --prod

# Copy application code directly to /app
COPY app/ ./

# Copy Alembic migration files
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Add app directory to PYTHONPATH so imports work correctly
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose the port that the FastAPI application will run on
EXPOSE 8000

# Use 'pdm run' to execute uvicorn from within the project's virtual environment.
ENTRYPOINT ["pdm", "run"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

