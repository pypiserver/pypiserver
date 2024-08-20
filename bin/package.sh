#! /bin/sh
#
##

my_dir=`dirname "$0"`
cd $my_dir/..

rm -r build/* dist/* || echo "no build/* or dist/* folder is found"
python3 -m build
