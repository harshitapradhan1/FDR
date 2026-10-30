.PHONY: up down migrate seed data test demo run-backend run-frontend clean help

help:
	@echo "DepoSafe - AICTE Regulation Bureau FDR Intelligence Portal"
	@echo "=========================================================="
	@echo "Commands:"
	@echo "  make up            - Launch all services via docker-compose"
	@echo "  make down          - Stop all docker services"
	@echo "  make migrate       - Apply Alembic migrations"
	@echo "  make data          - Generate synthetic dataset (80 institutions, 164 FDRs) and seed DB"
	@echo "  make seed          - Seed database from synthetic dataset"
	@echo "  make test          - Run complete unit, forensic and E2E test suites"
	@echo "  make demo          - Run 90-second automated demo sequence in terminal"
	@echo "  make run-backend   - Run FastAPI backend locally (port 8000)"
	@echo "  make run-frontend  - Run Next.js frontend locally (port 3000)"
	@echo "  make clean         - Clean temporary files, caches, and database"

up:
	docker-compose up -d --build

down:
	docker-compose down

migrate:
	PYTHONPATH=. backend/venv/bin/alembic -c backend/alembic.ini upgrade head

data:
	PYTHONPATH=. backend/venv/bin/python3 data/generator.py
	PYTHONPATH=. backend/venv/bin/python3 data/seed_loader.py

seed:
	PYTHONPATH=. backend/venv/bin/python3 data/seed_loader.py

test:
	PYTHONPATH=. backend/venv/bin/pytest backend/tests/ -v

demo:
	PYTHONPATH=. backend/venv/bin/python3 scripts/demo_runner.py

run-backend:
	PYTHONPATH=. backend/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd frontend && npm run dev

clean:
	rm -f deposafe.db
	rm -rf backend/.pytest_cache frontend/.next

