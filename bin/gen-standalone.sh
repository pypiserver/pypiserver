#! /bin/sh
##
## Create an executable zip file.

exec_zip="./pypi-server-standalone.py"

my_dir="$(dirname "$0")"
cd $my_dir/..

rm -rf ./build/* ./dist/*
python setup.py bdist_wheel
wheel="./dist/pypiserver-*.whl"


## Modify `wheel` archive with `__main__.py` at root,
#   prepend it with a python-flashbang, and
#   add header-comments >= 10-lines so that
#   ``head pypiserver*.py`` behaves politely.
#
gitversion=$(git describe --tags)
unzip -jo $wheel pypiserver/__main__.py -d ./dist
zip -d $wheel pypiserver/__main__.py
zip -mj $wheel ./dist/__main__.py
cat  - $wheel > "$exec_zip" << EOF
#!/usr/bin/env python
##
## Standalone pypiserver-$gitversion
##
## Execute it like that:
##      $exec_zip <packages_dir>
## To get more help, type:
##      $exec_zip --help
##
## BINARY CONTENT FOLLOWS
EOF
chmod a+xr "$exec_zip"
