# Legal AI OS — Backend
# Deployed on Fly.io
FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY . .

# Run via startup wrapper (catches and logs all errors)
EXPOSE 8080
CMD ["python", "start.py"]
