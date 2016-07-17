#! /bin/sh
## Test standalone generation & execution.
##

set -x

my_dir="$(dirname "$0")"
cd $my_dir/..

git fetch origin standalone:origin/standalone
git branch --track standalone origin/standalone
./bin/commit-standalone.sh no_commit

./pypi-server-standalone.py . &
server_pid=$!
sleep 2

kill $server_pid  && echo "Server killed nicely." # Kill fails if server failed.
