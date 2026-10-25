.PHONY: install lint format test validate check sample-data build clean

install:
	pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

test:
	pytest --cov

validate:
	python scripts/validate_configs.py

check: lint test validate

sample-data:
	python scripts/generate_sample_data.py

build:
	python -m build --wheel

clean:
	rm -rf build dist .pytest_cache .ruff_cache .coverage coverage.xml spark-warehouse metastore_db
