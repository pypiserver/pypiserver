# pypi-server Makefile
# ********************
# 
# This Makefile contains various developer-oriented scripts

# Dev utilities
# =============

# Cleanups
# --------

.PHONY: clean-cache
clean-cache:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -exec rm -f {} +
	find . -type f -name "*.pyo" -exec rm -f {} +

.PHONY: clean-build
clean-build:
	@echo ">>> 🧹 Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info .pytest_cache .config.cache
	uv cache clean

# Code style
# ----------

.PHONY: format
format: pyproject.toml ./pypiserver
	@echo ">>> 🎗️ Cleaning and formatting the source code"
	uv run isort $(CHECK) pypiserver
	uv run black $(CHECK) $(DIFF) pypiserver

.PHONY: check-types
check-types: pyproject.toml ./pypiserver ./docker ./tests
	@echo ">>> 📋 Checking the Python types"
	uv run mypy pypiserver tests docker || echo "--- 🫣 Fixing type errors is still in progress"
	uv run mypy docker/test_docker.py tests/test_init.py --follow-imports="skip"

.PHONY: format-readme
format-readme: pyproject.toml README.md
	@echo ">>> 📜 Formatting README.md"
	uv run mdformat $(CHECK) README.md

.PHONY: format-readme-diff
format-readme-diff: pyproject.toml README.md
	@echo ">>> 📜 Checking README.md format differences"
	@echo ">>> -- copy readme to /tmp/pypiserver"
	@mkdir -p /tmp/pypiserver
	@cp README.md /tmp/pypiserver
	@$(MAKE) format-readme
	diff -u README.md /tmp/pypiserver/README.md
	@rm -rf /tmp/pypiserver/README.md

# Testing
# -------

# Standard test run
# :::::::::::::::::

.PHONY: test
test test-3.x: pyproject.toml ./tests ./pypiserver
	@echo ">>> 🧪 Running tests for Current Python ..."
	uv run --isolated --group test pytest tests

# Tests On Multiple Python Versions
# :::::::::::::::::::::::::::::::::
PY_VERSIONS := 3.10 3.11 3.12 3.13 3.14 pypy3

.PHONY: test-all-python-versions
test-all-python-versions test-px: $(addprefix test-,$(PY_VERSIONS))

.PHONY: test-%
test-%: pyproject.toml ./tests ./pypiserver
	@$(MAKE) clean-build
	@echo ">>> 🧪 Running tests for Python $* ..."
	uv run --isolated --python $* --group test pytest tests

# ~~~~~~~~~~~~~~~~~~~~~~

# Docker test run
# :::::::::::::::

.PHONY: test-docker
test-docker: pyproject.toml ./docker/test_docker.py ./pypiserver
	uv run --isolated --group test pytest docker/test_docker.py

# DOCKER TESTING FIXTURES
# =======================
# These scripts are used to help with
# building resources needed for testing

SHELL = /bin/sh

MYPKG_DIR := fixtures/mypkg
MYPKG_HEAVY_DIR := fixtures/mypkg_heavy
MYPKG_HEAVY_PLACEHOLDER_PATH := $(MYPKG_HEAVY_DIR)/mypkg_heavy/generated_placeholder.py
MYPKG_SRC = $(MYPKG_DIR)/setup.py $(shell find $(MYPKG_DIR)/ -type f -name '*.py')
MYPKG_HEAVY_SRC = $(MYPKG_HEAVY_DIR)/setup.py $(shell find $(MYPKG_HEAVY_DIR)/ -type f -name '*.py')

fixtures: mypkg mypkg_heavy

# Basic Test Fixture
# ------------------
# Build the test fixture package

mypkg: $(MYPKG_DIR)/dist/pypiserver_mypkg-1.0.0.tar.gz
mypkg: $(MYPKG_DIR)/dist/pypiserver_mypkg-1.0.0-py2.py3-none-any.whl

$(MYPKG_DIR)/dist/pypiserver_mypkg-1.0.0.tar.gz: $(MYPKG_SRC)
	cd $(MYPKG_DIR); python setup.py sdist
$(MYPKG_DIR)/dist/pypiserver_mypkg-1.0.0-py2.py3-none-any.whl: $(MYPKG_SRC)
	cd $(MYPKG_DIR); python setup.py bdist_wheel

# Heavy Test Fixture
# ------------------
# Build the heavy test fixture package

mypkg_heavy: $(MYPKG_HEAVY_DIR)/dist/pypiserver_mypkg_heavy-1.0.0.tar.gz
mypkg_heavy: $(MYPKG_HEAVY_DIR)/dist/pypiserver_mypkg_heavy-1.0.0-py2.py3-none-any.whl

$(MYPKG_HEAVY_DIR)/dist/pypiserver_mypkg_heavy-1.0.0.tar.gz: $(MYPKG_HEAVY_PLACEHOLDER_PATH)
$(MYPKG_HEAVY_DIR)/dist/pypiserver_mypkg_heavy-1.0.0.tar.gz: $(MYPKG_SRC)
	cd $(MYPKG_HEAVY_DIR); python setup.py sdist
$(MYPKG_HEAVY_DIR)/dist/pypiserver_mypkg_heavy-1.0.0-py2.py3-none-any.whl: $(MYPKG_HEAVY_PLACEHOLDER_PATH)
$(MYPKG_HEAVY_DIR)/dist/pypiserver_mypkg_heavy-1.0.0-py2.py3-none-any.whl: $(MYPKG_SRC)
	cd $(MYPKG_HEAVY_DIR); python setup.py bdist_wheel

$(MYPKG_HEAVY_PLACEHOLDER_PATH): $(MYPKG_HEAVY_DIR)
	echo '"""' > $(MYPKG_HEAVY_PLACEHOLDER_PATH)
	dd if=/dev/urandom bs=150M count=1 | base64 >> $(MYPKG_HEAVY_PLACEHOLDER_PATH)
	echo '"""' >> $(MYPKG_HEAVY_PLACEHOLDER_PATH)
