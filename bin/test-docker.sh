#!/usr/bin/env sh

# Perform some simple validation to make sure the Docker image works
# Should be run from the repo root.

set -xe  # exit on any error, show debug output

DIR="$( cd "$( dirname "$0" )" >/dev/null 2>&1 && pwd )"

docker build . -t pypiserver:test

docker run pypiserver:test --help > /dev/null

# Mount our htpasswd file, which contains a test user with a bcrypt-encrypted
# "test" password
CONTAINER_ID=$(docker run \
    -d \
    -v "${DIR}/test.htpasswd:/data/.htpasswd" \
    -p 8080:8080 \
    -e PORT=8080 \
    pypiserver:test -a "list,update,download" -P /data/.htpasswd packages)

trap "docker container stop $CONTAINER_ID" EXIT

sleep 15  # give the container some time to get going

# Ensure we can authenticate locally
RET=$(curl localhost:8080)
echo $RET
echo $RET | grep -q "pypiserver"

RET=$(curl localhost:8080/packages/)
echo $RET
echo $RET | grep -q "401"


RET=$(curl test:test@localhost:8080/packages/)
echo $RET
echo $RET | grep -q "Index of packages"

twine upload \
    -u test \
    -p test \
    --repository-url http://localhost:8080 \
    "${DIR}/pypiserver-1.2.6-py2.py3-none-any.whl"

RET=$(curl test:test@localhost:8080/packages/)
echo $RET
echo $RET | grep -q "pypiserver-1.2.6"
