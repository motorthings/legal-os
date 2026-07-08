# Legal AI OS — Development Commands

.PHONY: install dev test worker migrate lint clean

# Install dependencies
install:
	cd backend && pip install -r requirements.txt --break-system-packages

# Run dev server
dev:
	cd backend && uvicorn app.main:app --reload --port 8080

# Run Celery worker (separate terminal)
worker:
	cd backend && celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# Run tests
test:
	cd backend && python -m pytest tests/ -v

# Run migrations (apply SQL files against Supabase)
migrate:
	cd backend && python -m app.migrate

# Lint
lint:
	cd backend && ruff check app/

# Deploy to Fly.io
deploy:
	cd backend && fly deploy

# Open app
open:
	open https://legal-os.fly.dev/health
