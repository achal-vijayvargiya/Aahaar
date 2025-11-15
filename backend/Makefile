.PHONY: help install run docker-up docker-down docker-logs test clean migrate init-db

help:
	@echo "DrAssistent Backend - Available Commands:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make run          - Run the application locally"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make docker-logs  - View Docker logs"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Clean temporary files"
	@echo "  make migrate      - Create and apply database migration"
	@echo "  make init-db      - Initialize database with sample data"

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker-compose up -d
	@echo "Services started! API available at http://localhost:8000"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

docker-rebuild:
	docker-compose up -d --build

test:
	pytest

test-coverage:
	pytest --cov=app --cov-report=html

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

migrate:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"
	alembic upgrade head

init-db:
	python scripts/init_db.py

shell:
	python -i -c "from app.database import SessionLocal; from app.models import *; db = SessionLocal()"

