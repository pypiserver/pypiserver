#!/usr/bin/env bash

set -euo pipefail

# chown the VOLUME mount set in the dockerfile
# If you're using an alternative directory for packages,
# you'll need to ensure that pypiserver has read and
# write access to that directory
chown -R pypiserver:pypiserver /data/packages

exec gosu pypiserver pypi-server -p "$PORT" $@
