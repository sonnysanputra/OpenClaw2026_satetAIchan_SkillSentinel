# SkillSentinel — common dev tasks.
# Use `make help` to list targets.

.DEFAULT_GOAL := help
PY ?= python3
UV ?= uv

help:  ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?##"}; {printf "  %-20s %s\n", $$1, $$2}'

install:  ## Install project + dev deps.
	$(UV) sync --all-extras

build-info:  ## Regenerate __about__.py from git.
	$(PY) scripts/build_info.py

lint:  ## Run ruff lint + format check.
	ruff check .
	ruff format --check .

format:  ## Auto-fix lint and format.
	ruff check --fix .
	ruff format .

typecheck:  ## Run mypy.
	mypy src tests

test:  ## Run pytest.
	pytest

ci:  ## Run everything CI runs.
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

scan:  ## Run a smoke scan on an example bundle (override BUNDLE=path).
	BUNDLE?=tests/fixtures/empty
	$(PY) -m skillsentinel scan $(BUNDLE) --no-dynamic

clean:  ## Remove build artifacts and caches.
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +

.PHONY: help install build-info lint format typecheck test ci scan clean
