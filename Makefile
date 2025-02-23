##
# pypiserver
#
# this makefile is used to help with building resources needed for testing
#
# @file
# @version 0.1

SHELL = /bin/sh

MYPKG_DIR := fixtures/mypkg
MYPKG_HEAVY_DIR := fixtures/mypkg_heavy
MYPKG_HEAVY_PLACEHOLDER_PATH := $(MYPKG_HEAVY_DIR)/mypkg_heavy/generated_placeholder.py
MYPKG_SRC = $(MYPKG_DIR)/setup.py $(shell find $(MYPKG_DIR)/ -type f -name '*.py')
MYPKG_HEAVY_SRC = $(MYPKG_HEAVY_DIR)/setup.py $(shell find $(MYPKG_HEAVY_DIR)/ -type f -name '*.py')

fixtures: mypkg mypkg_heavy

# Build the test fixture package.
mypkg: $(MYPKG_DIR)/dist/pypiserver_mypkg-1.0.0.tar.gz
mypkg: $(MYPKG_DIR)/dist/pypiserver_mypkg-1.0.0-py2.py3-none-any.whl

$(MYPKG_DIR)/dist/pypiserver_mypkg-1.0.0.tar.gz: $(MYPKG_SRC)
	cd $(MYPKG_DIR); python setup.py sdist
$(MYPKG_DIR)/dist/pypiserver_mypkg-1.0.0-py2.py3-none-any.whl: $(MYPKG_SRC)
	cd $(MYPKG_DIR); python setup.py bdist_wheel

# end

# Build the heavy test fixture package.
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
	dd if=/dev/urandom bs=1048576 count=1 | base64 >> $(MYPKG_HEAVY_PLACEHOLDER_PATH)
	echo '"""' >> $(MYPKG_HEAVY_PLACEHOLDER_PATH)

# end
