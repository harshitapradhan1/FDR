.PHONY: up down seed test demo run-backend run-frontend clean help

help:
	@echo "DepoSafe - AICTE Regulation Bureau FDR Intelligence Portal"
	@echo "=========================================================="
	@echo "Commands:"
	@echo "  make up            - Launch all services via docker-compose"
	@echo "  make down          - Stop all docker services"
	@echo "  make seed          - Initialize and seed database with synthetic FDRs"
	@echo "  make test          - Run complete unit, forensic and E2E test suites"
	@echo "  make demo          - Run 90-second automated demo sequence in terminal"
	@echo "  make run-backend   - Run FastAPI backend locally (port 8000)"
	@echo "  make run-frontend  - Run Next.js frontend locally (port 3000)"
	@echo "  make clean         - Clean temporary files, caches, and database"

up:
	docker-compose up -d --build

down:
	docker-compose down

seed:
	PYTHONPATH=. backend/venv/bin/python3 -c "from backend.app.core.database import SessionLocal; from backend.app.services.seed_service import seed_database_if_empty; db = SessionLocal(); seed_database_if_empty(db); print('Database seeded successfully with authentic synthetic FDRs!')"

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

