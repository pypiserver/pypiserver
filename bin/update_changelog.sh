#!/usr/bin/env bash

# Script to create a new RC entry
#
# Actions:
# 1. find latest published version
# 2. find the TBD planned big version
# 3. create new RC version entry
# 4. add change log entries

set -e # exit on errors

# TODO: provide that as parameters?

CHANGE_FILE='CHANGES.rst'
RC_DATE=$(date +'%m-%d-%Y')
WORKSPACE_DIR="${GITHUB_WORKSPACE:-.}/rc"
TMP_CHANGE_LOG="${WORKSPACE_DIR}/rc-${RC_DATE}.txt"


############
# CLEANUPS #
############

rm -rf $TMP_CHANGE_LOG
mkdir -p $WORKSPACE_DIR


##################
# INITIALIZATION #
##################

echo "Updating $CHANGE_FILE:"

# TODO(tech-debt): get `LAST_VERSION` with a separate bash script
LAST_VERSION=$(grep -m1 -E ' \([0-9]+-[0-9]+-[0-9]+\)$' $CHANGE_FILE | awk '{ print $1 }')

echo "Detected last release version: $LAST_VERSION"


###################
# VERSION BUMPING #
###################


echo "Bumping patch version..."
MAJOR_COLUMN=1
MINOR_COLUMN=2
PATCH_COLUMN=3

# `awk` is used to bump the PATCH version since the last public release.
#   -F - gives a separator for splitting the original release into columns.
#   -v - provides a value for variable to be used in the `awk` command.
#   -v K=$PATCH_COLUMN - provides value for `K` - the version column to bump.
# This attempts to preserve the a standard syntax for GNU Awk.
# More can be found here: https://www.gnu.org/software/gawk/manual/gawk.html
BUMPED_VERSION=$(echo $LAST_VERSION | awk -F. -v K=$PATCH_COLUMN '{$K+=1; print $0}' OFS='.')

echo "Bumped to new candidate version: $BUMPED_VERSION"

RC_VERSION=${BUMPED_VERSION}rc${RC_DATE}

echo "Final RC version: $RC_VERSION"


###################
# CHANGELOG ENTRY #
###################


CHANGE_DIFF_TARGETS="v${LAST_VERSION}..HEAD"
VERSION_TITLE="${RC_VERSION} (__rc__)"
# Using GNU Awk syntax: -v LL specifies the title pattern variable.
TITLE_LINE=$(awk -v LL=${#VERSION_TITLE} 'BEGIN{for(c=0;c<LL;c++) printf "-"}')
VERSION_HEADER="$VERSION_TITLE\n${TITLE_LINE}"

# DEBUG INFO
echo -e "Comparing versions between: $CHANGE_DIFF_TARGETS\n"

# VERSION HEADER:
echo -e "$VERSION_HEADER\n" >> $TMP_CHANGE_LOG

# COLLECT ALL COMMITS:
git log --pretty=oneline --abbrev-commit $CHANGE_DIFF_TARGETS | sed 's/^/- /' >> $TMP_CHANGE_LOG
# DEBUG:
git log --pretty=oneline --abbrev-commit $CHANGE_DIFF_TARGETS | sed 's/^/- /'

# CHECK FINAL CONTENT
echo -e "\nCollected info:"
ls $WORKSPACE_DIR
cat $TMP_CHANGE_LOG

# APPEND INFO TO CHANGE FILE:
#   1. Finds the first (tbd) release
#   2. Populates space between (tbd) release and the latest one with RC changes
# NB: supporting macos and linux interoperability
#     see https://stackoverflow.com/questions/43171648/sed-gives-sed-cant-read-no-such-file-or-directory
if [[ "$OSTYPE" == "darwin"* ]]; then
# begin: mac os support
sed -i '' "/^[0-9]\.0\.0.*\(tbd\)/{N;G;r\
\
$TMP_CHANGE_LOG
\
}" $CHANGE_FILE
# end;
else
# begin: linux support
sed -i "/^[0-9]\.0\.0.*\(tbd\)/{N;G;r\
\
$TMP_CHANGE_LOG
\
}" $CHANGE_FILE
# end;
fi

# CHANGE_LOG_CONTENTS=$(cat $TMP_CHANGE_LOG)
