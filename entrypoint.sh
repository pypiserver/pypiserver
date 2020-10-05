#!/bin/ash

set -euo pipefail

chown -R pypiserver:pypiserver /data

if [ "$@" = "" ]; then
    # default CMD
    echo "Set default option '/data/packages'"
    set -- " /data/packages"
else
    # 
    echo "Using custom CMD: $@"
fi
exec gosu pypiserver pypi-server -p "$PORT" $@
