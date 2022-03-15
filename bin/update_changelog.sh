#!/bin/bash

# Script to create a new RC entry
#
# Actions:
# 1. find latest published version
# 2. find the TBD planned big version
# 3. create new RC version entry
# 4. add change log entries

# TODO: provide that as parameters?

CHANGE_FILE='CHANGES.rst'
RC_DATE=$(date +'%m-%d-%Y')
TMP_CHANGE_LOG="./rc-${RC_DATE}.txt"


############
# CLEANUPS #
############

rm -rf $TMP_CHANGE_LOG


##################
# INITIALIZATION #
##################

echo "Updating $CHANGE_FILE:"

LAST_VERSION=$(grep -m1 -E ' \([0-9]+-[0-9]+-[0-9]+\)$' $CHANGE_FILE | awk '{ print $1 }')

echo "Detected last release version: $LAST_VERSION"


###################
# VERSION BUMPING #
###################

echo "Bumping patch version..."
MAJOR_COLUMN=1
MINOR_COLUMN=2
PATCH_COLUMN=3

BUMPED_VERSION=$(echo $LAST_VERSION | awk -F. -v K=$PATCH_COLUMN '{$K+=1; print $0}' OFS='.')

echo "Bumped to new candidate version: $BUMPED_VERSION"

RC_VERSION=${BUMPED_VERSION}rc${RC_DATE}

echo "Final RC version: $RC_VERSION"


###################
# CHANGELOG ENTRY #
###################

CHANGE_DIFF_TARGETS="v${LAST_VERSION}..HEAD"
VERSION_TITLE="${RC_VERSION} (__rc__)"
TITLE_LINE=$(awk -v LL=${#VERSION_TITLE} 'BEGIN{for(c=0;c<LL;c++) printf "-"}')
VERSION_HEADER="$VERSION_TITLE\n${TITLE_LINE}"

# VERSION HEADER:
echo -e "$VERSION_HEADER\n" >> $TMP_CHANGE_LOG

# COLLECT ALL COMMITS:
git log --pretty=oneline --abbrev-commit $CHANGE_DIFF_TARGETS | sed 's/^/- /' >> $TMP_CHANGE_LOG

# CHECK FINAL CONTENT
cat $TMP_CHANGE_LOG

# APPEND INFO TO CHANGE FILE:
#   1. Finds the first (tbd) release
#   2. Populates space between (tbd) release with RC changes
sed -i '' "/^[0-9]\.0\.0.*\(tbd\)/{N;G;r\
\
$TMP_CHANGE_LOG
\
}" $CHANGE_FILE

# CHANGE_LOG_CONTENTS=$(cat $TMP_CHANGE_LOG)
