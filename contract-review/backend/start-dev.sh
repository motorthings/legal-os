#!/bin/bash
# Start all services for local development

echo "🚀 Starting Contract Review System (Development)"
echo ""

# Check Redis
if ! redis-cli ping > /dev/null 2>&1; then
  echo "❌ Redis not running. Start with:"
  echo "   brew services start redis  (macOS)"
  echo "   sudo service redis-server start  (Linux)"
  echo "   docker run -d -p 6379:6379 redis:7-alpine  (Docker)"
  exit 1
fi

echo "✅ Redis is running"
echo ""

# Start services in background
echo "📋 Starting FastAPI on http://localhost:8000..."
uvicorn main:app --reload --port 8000 &
API_PID=$!

sleep 2

echo "👷 Starting Celery worker..."
celery -A celery_app worker --loglevel=info --concurrency=3 -Q default,urgent,batch --pool=solo &
WORKER_PID=$!

sleep 2

echo "🌸 Starting Flower monitoring on http://localhost:5555..."
celery -A celery_app flower --port=5555 --basic_auth=admin:admin &
FLOWER_PID=$!

sleep 2

echo ""
echo "✅ All services started!"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Flower: http://localhost:5555 (admin/admin)"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Trap Ctrl+C and kill all processes
trap "echo ''; echo 'Stopping services...'; kill $API_PID $WORKER_PID $FLOWER_PID 2>/dev/null; exit" INT TERM

# Wait for Ctrl+C
wait
