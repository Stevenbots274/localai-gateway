.PHONY: install test run migrate deploy

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

run:
	./scripts/start.sh

migrate:
	alembic upgrade head

makemigrations:
	alembic revision --autogenerate -m "$(msg)"

deploy:
	./scripts/deploy.sh

format:
	black app/ tests/
	isort app/ tests/

lint:
	flake8 app/ tests/
	mypy app/
