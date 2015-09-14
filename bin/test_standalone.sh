#! /bin/sh

my_dir="$(dirname "$0")"
cd $my_dir/..

git fetch origin standalone:origin/standalone 
git branch --track standalone origin/standalone
./bin/commit-standalone.sh no_commit

./pypi-server-standalone.py . &
server_pid=$!
sleep 2

kill $server_pid  # Killing fails if server failed starting-up.
