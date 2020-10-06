#!/usr/bin/env sh

set -euo pipefail

# chown the VOLUME mount set in the dockerfile
# If you're using an alternative directory for packages,
# you'll need to ensure that pypiserver has read and
# write access to that directory
chown -R pypiserver:pypiserver /data/packages

if [ "$@" = "" ]; then
    # No arguments were provided, use the default.
    echo "Set default option '/data/packages'"
    set -- " /data/packages"
else
    # Use whatever was provided
    echo "Using custom CMD: $@"
fi
exec gosu pypiserver pypi-server -p "$PORT" $@
