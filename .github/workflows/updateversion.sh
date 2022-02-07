#!/bin/bash

# checks for and updates the version in tokens.xml when a pull request gets
# approved
set -e

# check if update needed
git fetch --depth=1 origin master
if git diff --quiet origin/master tokens.xml; then
  echo "there are no changes to tokens.xml"
  echo "no commit created"
  exit 0
fi

# get date
olddate="$(cat version.txt)"
date="$(date --utc +%Y%m%d)"
echo "it is currently $date"

# check for suffix used when multiple changes happen in a day
suffixrx='[a-z]+'
if [[ $olddate =~ $date ]]; then
  if [[ $olddate =~ $suffixrx ]]; then
    suffix="${BASH_REMATCH[0]}"
    # it's very unlikely we'll ever do 25 updates a day...
    if [[ $suffix == z ]]; then
      echo "SUFFIX OVERFLOW" >&2
      exit 1
    fi
    alphabet="abcdefghijklmnopqrstuvwxyz"
    for (( i=0; i<25; i++ )); do
      if [[ $suffix == "${alphabet:$i:1}" ]]; then
        suffix="${alphabet:$i+1:1}"
        break
      fi
    done
  else
    date="${date}b"
  fi
fi

# edit files
echo "updating version from $olddate to $date"
sed -i "s?<sourceVersion>.*</sourceVersion>?<sourceVersion>$date</sourceVersion>?" tokens.xml
echo "$date" >version.txt

# push changes
git fetch "$REPO" "$BRANCH"
git checkout -b pull_request
git config user.name github-actions
git config user.email github-actions@github.com
git add tokens.xml version.txt
git commit -m "update version to $date"
git push "$REPO" "HEAD:$BRANCH"
commit="$(git rev-parse HEAD)"
echo "pushed commit: $REPO_PAGE/commit/$commit"
