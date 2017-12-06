#! /bin/sh
#
## Builds the test pypiserver plugins package

set -e

my_dir=`dirname "$0"`
cd $my_dir/../tests/plugins

rm -rf build/* dist/*
python setup.py bdist_wheel
