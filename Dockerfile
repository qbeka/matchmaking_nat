# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set work directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry: Don't create virtual environment, install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Default command (can be overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 