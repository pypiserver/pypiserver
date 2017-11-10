#! /bin/sh
#
## Create an executable zip file.
#  Invoked by `commit-standalone.sh`.

set -x

set -o errexit

exec_zip="./pypi-server-standalone.py"

my_dir="$(dirname "$0")"
cd $my_dir/..

rm -rf ./build/* ./dist/*
python setup.py bdist_wheel
wheel="./dist/pypiserver-*.whl"


## Modify `wheel` archive with `__main__.py` at root,
#   add dependencies, and
#   prepend it with a python-flashbang + some header-comments >= 10-lines
#   so that ``head pypiserver*.py``behaves politely.
#
sudo update-ca-certificates || echo "Failed updating certs (run on travis container?)"
unzip -jo $wheel pypiserver/__main__.py -d ./dist
zip -d $wheel pypiserver/__main__.py
zip -mj $wheel ./dist/__main__.py
wget https://pypi.python.org/packages/2.7/p/passlib/passlib-1.6.5-py2.py3-none-any.whl#md5=03de8f28697eaa67835758a60386c9fa \
        -O ./dist/passlib-1.6.5-py2.py3-none-any.whl
zip -mj $wheel ./dist/passlib-*.whl
gitversion=$(git describe --tags)
cat  - $wheel > "$exec_zip" << EOF
#!/usr/bin/env python
##
## Standalone pypiserver-$gitversion $(date -R)
##
## Execute it like that:
##      $exec_zip <packages_dir>
## To get more help, type:
##      $exec_zip --help
##
## BINARY CONTENT FOLLOWS
EOF
chmod a+xr "$exec_zip"
