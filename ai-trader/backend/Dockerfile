# Multi-stage Dockerfile for Backend Services
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports
EXPOSE 8000 8001 8002 8003 8004

# Default command (will be overridden in docker-compose)
CMD ["uvicorn", "webhook.app:app", "--host", "0.0.0.0", "--port", "8000"]
