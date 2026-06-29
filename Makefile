.PHONY: help install lint fmt test cov package clean

PY ?= python3
FUNCS := ingestor transformer feature_extractor loader insights

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Install dev dependencies
	$(PY) -m pip install -r requirements-dev.txt

lint:  ## Run ruff lint checks
	ruff check lambdas tests

fmt:  ## Auto-format / autofix with ruff
	ruff check --fix lambdas tests
	ruff format lambdas tests

test:  ## Run the test suite
	$(PY) -m pytest

cov:  ## Run tests with coverage report
	$(PY) -m pytest --cov --cov-report=term-missing

package:  ## Build deployment zips for every Lambda into build/
	@mkdir -p build
	@for fn in $(FUNCS); do \
		echo "Packaging $$fn ..."; \
		rm -rf build/$$fn && mkdir -p build/$$fn; \
		cp lambdas/$$fn/handler.py build/$$fn/; \
		cp -r lambdas/common build/$$fn/common; \
		if [ -f lambdas/$$fn/requirements.txt ]; then \
			$(PY) -m pip install -q -r lambdas/$$fn/requirements.txt -t build/$$fn/ ; \
		fi; \
		(cd build/$$fn && zip -qr ../$$fn.zip .); \
	done
	@echo "Zips written to build/"

clean:  ## Remove build artifacts and caches
	rm -rf build .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
