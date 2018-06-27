#!/usr/bin/env sh

# Perform some simple validation to make sure the Docker image works
# Should be run from the repo root.

set -xe  # exit on any error, show debug output

docker build . -t pypiserver:test

docker run pypiserver:test --help

CONTAINER_ID=$(docker run -d -p 8080:8080 pypiserver:test)

sleep 5  # give the contaienr some time to get going

# Ensure our home page is returning something
curl localhost:8080 | grep -q "pypiserver"

docker container stop "$CONTAINER_ID"
