.PHONY: help install install-dev test test-unit test-integration lint format type-check clean coverage

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/ -v -m "not integration"

test-integration: ## Run integration tests only
	pytest tests/ -v -m "integration"

lint: ## Run ruff linter
	ruff check .

format: ## Format code with black and ruff
	black .
	ruff format .

type-check: ## Run mypy type checking
	mypy app/

quality: lint type-check ## Run all code quality checks

coverage: ## Run tests with coverage report
	pytest --cov=app --cov-report=html --cov-report=term-missing

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .mypy_cache
	rm -rf .ruff_cache

# Development workflow
dev-setup: install-dev ## Set up development environment
	@echo "Development environment set up complete!"

pre-commit: format lint type-check ## Run all checks before committing
	@echo "All quality checks passed!"

# Docker commands
docker-build: ## Build Docker image
	docker build -t ai-mortgage-chatbot .

docker-run: ## Run with Docker Compose
	docker-compose up --build

docker-stop: ## Stop Docker Compose services
	docker-compose down

# API commands
run-api: ## Run the FastAPI backend
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend: ## Run the Streamlit frontend
	streamlit run streamlit_app.py --server.port 8501

run-all: ## Run both backend and frontend (in background)
	@echo "Starting backend..."
	@uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting frontend..."
	@streamlit run streamlit_app.py --server.port 8501 &
	@echo "Services started! Backend: http://localhost:8000, Frontend: http://localhost:8501"
	@echo "Use 'make stop-all' to stop both services"

stop-all: ## Stop all running services
	@pkill -f "uvicorn app.main:app" || true
	@pkill -f "streamlit run streamlit_app.py" || true
	@echo "All services stopped" 