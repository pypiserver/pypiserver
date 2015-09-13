#! /bin/sh

my_dir="$(dirname "$0")"
cd $my_dir/..

./bin/commit-standalone.sh no_commit
./pypi-server-standalone.py  &
server_pid=$!
sleep 2
kill $server_pid  # Killing will fail if server had failed to start.
