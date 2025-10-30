# back/Makefile

.PHONY: test test-unit test-integration test-cov test-watch clean-test

# Запуск всех тестов
test:
	pytest

# Только unit тесты (быстрые)
test-unit:
	pytest -m unit

# Только integration тесты
test-integration:
	pytest -m integration

# Smoke тесты (быстрая проверка)
test-smoke:
	pytest -m smoke

# Тесты с покрытием
test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

# Тесты конкретного файла
test-file:
	pytest $(FILE) -v

# Тесты конкретной функции
test-func:
	pytest -k $(FUNC) -v

# Режим watch (перезапуск при изменениях)
test-watch:
	pytest-watch

# Параллельный запуск тестов
test-parallel:
	pytest -n auto

# Только failed тесты
test-failed:
	pytest --lf

# Verbose mode
test-verbose:
	pytest -vv -s

# Очистка кеша и артефактов
clean-test:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Создание тестовой БД
create-test-db:
	docker exec -it postgres_local psql -U app_user -c "DROP DATABASE IF EXISTS test_db;"
	docker exec -it postgres_local psql -U app_user -c "CREATE DATABASE test_db;"

# Запуск тестов в Docker
test-docker:
	docker compose run --rm backend pytest

# Все тесты + coverage + отчет
test-all: clean-test
	pytest --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "Coverage report generated in htmlcov/index.html"

# CI/CD режим (строгий)
test-ci:
	pytest --cov=app --cov-report=term --cov-report=xml --cov-fail-under=70 -v

# Помощь
help:
	@echo "Available targets:"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-smoke      - Run smoke tests"
	@echo "  test-cov        - Run tests with coverage"
	@echo "  test-file FILE=<path> - Test specific file"
	@echo "  test-func FUNC=<name> - Test specific function"
	@echo "  test-watch      - Watch mode (auto-rerun)"
	@echo "  test-parallel   - Run tests in parallel"
	@echo "  test-failed     - Rerun only failed tests"
	@echo "  test-verbose    - Verbose output"
	@echo "  clean-test      - Clean test artifacts"
	@echo "  test-docker     - Run tests in Docker"
	@echo "  test-all        - Full test suite with coverage"
	@echo "  test-ci         - CI/CD mode"