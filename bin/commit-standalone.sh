#! /bin/sh
#
## Create an executable file and add it into `standalone` branch
#
#  Invoke it directly on the commmit "tagged" for a release.
#  Invoke it with any arg to avoid committing into `standalone` branch.

set -x

my_dir="$(dirname "$0")"
cd $my_dir/..

git_wdir="./bin/git-new-workdir"
git_wdir_url="https://raw.githubusercontent.com/git/git/master/contrib/workdir/git-new-workdir"

if [ ! -x "$git_wdir" ]; then
    wget "$git_wdir_url" -O "$git_wdir"
    chmod a+x "$git_wdir"
fi

## Ensure `standalone` branch exists (fails in travis).
git fetch pypiserver standalone:pypiserver/standalone -f && \
        git branch --track standalone pypiserver/standalone

set -o errexit

gitversion=$(git describe --tags)
rm -rf .standalone
if nwd_dump=$( "$git_wdir" . .standalone standalone 2>&1 ); then
     ./bin/gen-standalone.sh
    mkdir -p .standalone
    cp -p pypi-server-standalone.py .standalone
    cd .standalone
    if [ $# -lt 1 ]; then
        git add .
        git commit -m "Add pypi-server-standalone $gitversion"
    fi
else
    echo "git-new-workdir: failed due to: $nwd_dump"
    exit 1
fi
