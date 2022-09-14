#!/bin/bash

set -eo pipefail
last="Zombie Wizard Token"
startrx=" -->"
namerx="<name>([^<]*)</name>"
endrx="</card>"
declare -A list # associative array
{
while IFS= read -r line; do
  echo "$line"
  if [[ $line =~ $startrx ]]; then # eat first comment
    break
  fi
done
while
  while
    IFS= read -r line || exit 2
    card+="$line
"
    [[ ! $line =~ $namerx ]]
  do :; done
  name="${BASH_REMATCH[1]}"
  while
    IFS= read -r line || exit 3
    card+="$line
"
    [[ ! $line =~ $endrx ]]
  do :; done
  list[ "$name"]="$card"
  keys+="
$name"
  card=""
  [[ $name != "$last" ]]
do :; done
<<<"${keys:1}" LC_ALL=C sort --ignore-case | while IFS= read -r key; do
  echo -n "${list[ $key]}"
done
cat
} <tokens.xml | sponge tokens.xml
