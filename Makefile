##
# pypiserver
#
# this makefile is used to help with building resources needed for testing
#
# @file
# @version 0.1

SHELL = /bin/sh

MYPKG_SRC = fixtures/mypkg/setup.py $(shell find fixtures/mypkg/mypkg -type f -name '*.py')

# Build the test fixture package.
mypkg: fixtures/mypkg/dist/pypiserver_mypkg-1.0.0.tar.gz
mypkg: fixtures/mypkg/dist/pypiserver_mypkg-1.0.0-py2.py3-none-any.whl
fixtures/mypkg/dist/pypiserver_mypkg-1.0.0.tar.gz: $(MYPKG_SRC)
	cd fixtures/mypkg; python setup.py sdist

fixtures/mypkg/dist/pypiserver_mypkg-1.0.0-py2.py3-none-any.whl: $(MYPKG_SRC)
	cd fixtures/mypkg; python setup.py bdist_wheel


# end
