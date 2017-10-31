#! /bin/sh
#
##

my_dir=`dirname "$0"`
cd $my_dir/..

rm -r build/* dist/*
python setup.py bdist_wheel sdist
