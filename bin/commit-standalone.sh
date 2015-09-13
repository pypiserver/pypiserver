#! /bin/sh

## Requires this script in your PATH:
##   https://github.com/git/git/blob/master/contrib/workdir/git-new-workdir
## Invoke it with any arg to avoid committing into `standalone` branch.

my_dir="$(dirname "$0")"
cd $my_dir/..

gitversion=$(git describe --tags)
rm -rf .standalone
if nwd_dump=$( git-new-workdir . .standalone standalone 2>&1 ); then
    ./bin/gen-standalone.py
    cp -p pypi-server-standalone.py .standalone
    cd .standalone
    if [ $# -lt 1 ]; then
        git add .
        git commit -m "add pypi-server-standalone $gitversion"
    fi
else
    echo "git-new-workdir: failed due to: $nwd_dump"
    exit 1
fi
