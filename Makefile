##
# pypiserver
#
# this makefile is used to help with building resources needed for testing
#
# @file
# @version 0.1

MYPKG_DIST = $(shell find fixtures/mypkg/dist -type f)
MYPKG_SRC = fixtures/mypkg/setup.py $(shell find fixtures/mypkg/mypkg -type f -name '*.py')

# Build the test fixture package.
mypkg: $(MYPKG_DIST)
$(MYPKG_DIST) &: $(MYPKG_SRC)
	cd fixtures/mypkg; \
	python setup.py sdist && \
	python setup.py bdist_wheel


# end
