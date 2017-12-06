#! /bin/sh
## Test setuptools entry-point plugins.
#
# Requires pypiserver to be pip-installed.

set -xe

my_dir="$(dirname "$0")"
tmp="${TMP:-/tmp}"  # Travis has not this variable.

loadable_fpath="$tmp/loadable.txt"
installable_fpath="$tmp/installable.txt"

python -c "import sys; print(sys.version)"

pip uninstall -y pypiserver-test-plugins || \
    echo "Test-plugins were not installed, as expected." >&2

## Test plugin-code does not run if entry-points not installed.
#
rm -f "$loadable_fpath" "$installable_fpath"
python -c "import pypiserver"
[ ! -f "$loadable_fpath" ]
[ ! -f "$installable_fpath" ]


## Test plugin-code runs when entry-points installed.
#
cd "$my_dir/../tests/plugins"
pip install -e .
python -c "import pypiserver"
[ -f "$loadable_fpath" ] && echo "Loadable OK" >&2
[ -f "$installable_fpath" ] && echo "Installable OK" >&2
