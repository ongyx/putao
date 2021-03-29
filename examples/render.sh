#!/bin/bash

if [[ "$#" -ne 1 ]]; then
  echo "Usage: ./render.sh (mml file to render)"
  exit
fi

JSON_FILE="$1.json"

if [[ ! -f $JSON_FILE ]]; then
  putao new "$1"
fi

putao import "$1.mml" "$1.json"
putao render "$1.json"
