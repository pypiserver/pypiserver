#! /bin/sh

## Requires this script in your PATH:
##   https://github.com/git/git/blob/master/contrib/workdir/git-new-workdir
## Invoke it with any arg to avoid committing into `standalone` branch.

my_dir="$(dirname "$0")"
cd $my_dir/..

git_wdir="./bin/git-new-workdir"
git_wdir_url="https://raw.githubusercontent.com/git/git/master/contrib/workdir/git-new-workdir"

if [ ! -x "$git_wdir" ]; then
    wget "$git_wdir_url" -O "$git_wdir"
    chmod a+x "$git_wdir"
fi

gitversion=$(git describe --tags)
rm -rf .standalone
if nwd_dump=$( "$git_wdir" . .standalone standalone 2>&1 ); then
    ./bin/gen-standalone.py
    chmod a+xr ./pypi-server-standalone.py
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
