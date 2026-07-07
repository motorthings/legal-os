#!/bin/bash
# Start Flower monitoring UI

echo "🌸 Starting Flower monitoring on http://localhost:5555"

celery -A celery_app flower \
  --port=5555 \
  --basic_auth=admin:admin
