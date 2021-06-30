#!/bin/bash

if [[ "$#" -ne 1 ]]; then
  echo "Usage: ./render.sh (mml file to render)"
  exit
fi

JSON_FILE="$1.project.gz"

if [[ ! -f $JSON_FILE ]]; then
  putao new "$1"
fi

putao import "$1.mml" "$1.project.gz"
putao render "$1.project.gz"
