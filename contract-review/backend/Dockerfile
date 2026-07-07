# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including bash and coreutils
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    bash \
    coreutils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway sets PORT env var dynamically)
EXPOSE 8000

# Start command using PORT environment variable (defaults to 8000)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
