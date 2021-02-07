#!/usr/bin/env bash

set -euo pipefail

function run() {
    # we're not root. Run as who we are.
    if [[ "$EUID" -ne 0 ]]; then
        eval "$@"
    else
        gosu pypiserver "$@"
    fi
}

if [[ "$EUID" -ne 0 && "$EUID" -ne $(id -u pypiserver) ]]; then
    USER_ID="$EUID"
    WARN=(
        "The pypiserver container was run as a non-root, non-pypiserver user."
        "Pypiserver will be run as this user if possible, but this is not"
        "officially supported."
    )
    echo "" 1>&2
    echo "${WARN[@]}" 1>&2
    echo "" 1>&2
else
    USER_ID=$(id -u pypiserver)
fi


function print_permissions_help() {
    MSG1=(
        "If you are mounting a volume at /data or /data/packages and are running the"
        "container on a linux system, you may need to add add a pypiserver"
        "group to the host and give it permission to access the directories."
        "Please see https://github.com/pypiserver/pypiserver/issues/256 for more"
        "details."
    )
    MSG2=(
        "Please see https://github.com/pypiserver/pypiserver/issues/256 for more"
        "details."
    )
    echo "" 1>&2
    echo "${MSG1[@]}" 1>&2
    echo "" 1>&2
    echo "${MSG2[@]}" 1>&2
}


# the user must have read and execute access to the /data directory
# (execute to be able to cd into directory and list content metadata)
if ! run test -r /data -a -x /data; then

    chown -R "$USER_ID:pypiserver" /data || true

    if ! run test -r /data -a -x /data; then
        FAIL_MSG=(
            "Cannot start pypiserver:"
            "pypiserver user (UID $USER_ID)"
            "or pypiserver group (GID $(id -g pypiserver))"
            "must have read/execute access to /data"
        )
        echo "${FAIL_MSG[@]}" 1>&2
        echo "" 1>&2
        print_permissions_help
        exit 1
    fi

fi

# The /data/packages directory must exist
# It not existing is very unlikely, possibly impossible, because the VOLUME
# specification in the Dockerfile leads to its being created even if someone is
# mounting a volume at /data that does not contain a /packages subdirectory
if [[ ! -d "/data/packages" ]]; then
    if ! run test -w /data; then
        FAIL_MSG=(
            "Cannot start pypiserver:"
            "/data/packages does not exist and"
            "pypiserver user (UID $USER_ID)"
            "or pypiserver group (GID $(id -g pypiserver))"
            "does not have write access to /data to create it"
        )
        echo "" 1>&2
        echo "${FAIL_MSG[@]}" 1>&2
        print_permissions_help
        exit 1
    fi
    run mkdir /data/packages
fi

# The pypiserver user needs read/write/execute access to the packages directory
if ! run \
    test -w /data/packages \
    -a -r /data/packages \
    -a -x /data/packages; then

    # We'll try to chown as a last resort.
    # Don't complain if it fails, since we'll bomb on the next check anyway.
    chown -R "$USER_ID:pypiserver" /data/packages || true

    if ! run \
        test -w /data/packages \
        -a -r /data/packages \
        -a -x /data/packages; then
        FAIL_MSG=(
            "Cannot start pypiserver:"
            "pypiserver user (UID $USER_ID)"
            "or pypiserver group (GID $(id -g pypiserver))"
            "must have read/write/execute access to /data/packages"
        )
        echo "" 1>&2
        echo "${FAIL_MSG[@]}" 1>&2
        print_permissions_help
        exit 1
    fi

fi


if [[ "$*" == "" ]]; then
    # Use the gunicorn server by default, since it's more performant than
    # bottle's default server
    CMD=("run" "-p" "${PYPISERVER_PORT:-$PORT}" "--server" "gunicorn")
else
    # this reassigns the array to the CMD variable
    CMD=( "${@}" )
fi

if [[ "$EUID" -ne 0 ]]; then
    exec pypi-server "${CMD[@]}"
else
    exec gosu pypiserver pypi-server "${CMD[@]}"
fi
