# Legal AI OS — Development Commands

.PHONY: install dev test worker migrate lint clean deploy deploy-backend deploy-frontend

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

# Deploy backend + frontend, then health-check both
deploy:
	@./scripts/deploy.sh

deploy-backend:
	cd backend && fly deploy
	@curl -s -o /dev/null -w "  backend health: %{http_code}\n" https://legal-os-api.fly.dev/health

deploy-frontend:
	cd frontend && vercel --prod --yes
	@curl -s -o /dev/null -w "  frontend health: %{http_code}\n" https://legal.sickofancy.ai

# Open app
open:
	open https://legal-os.fly.dev/health
