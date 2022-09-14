#!/bin/bash

set -eo pipefail
mapfile -t sets < <(LC_ALL=C curl -L 'https://mtgjson.com/api/v5/SetList.json' | jq -r '.data[]|.releaseDate,.code' | sed 'N;s/\n/ /' | sort -r | sed 's/.* //')
setrx="<set[^>]*>([^<]+)</set>"
list=()
while IFS= read -r line; do
  if [[ $line =~ $setrx ]]; then
    code="${BASH_REMATCH[1]}"
    list+=("$code" "$line")
  elif [[ $code ]]; then
    for set_ in "${sets[@]}"; do
      for (( i=0; i<${#list[@]}; i+=2 )); do
        code="${list[$i]}"
        if [[ $set_ == "$code" ]]; then
          echo "${list[$i+1]}"
        fi
      done
    done
    code=""
    list=()
    echo "$line"
  else
    echo "$line"
  fi
done <tokens.xml | sponge tokens.xml
