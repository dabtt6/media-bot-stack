#!/bin/bash

cd /docker/media-stack || exit

# Kiểm tra thay đổi
if [[ -n $(git status --porcelain) ]]; then
    echo "Changes detected..."

    git add .
    git commit -m "auto update $(date '+%Y-%m-%d %H:%M:%S')"
    git push

    echo "Pushed to GitHub"
else
    echo "No changes"
fi
