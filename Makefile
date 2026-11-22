.PHONY: install lint types test check run docker

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

types:
	mypy

test:
	pytest

check: lint types test

run:
	pr-sentinel serve

docker:
	docker build -t pr-sentinel:local .