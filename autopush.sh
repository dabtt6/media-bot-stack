#!/bin/bash

cd /docker/media-stack || exit

# Only push if changes exist
if [[ -n $(git status --porcelain) ]]; then
    git add .
    git commit -m "auto update $(date '+%Y-%m-%d %H:%M:%S')"
    git push
fi
