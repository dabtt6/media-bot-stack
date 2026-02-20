#!/bin/bash

SOURCE="/data/movies"
DEST="/data/broken"
LOG="/data/video_check.log"

apk add --no-cache inotify-tools >/dev/null 2>&1

echo "Realtime video checker started" >> "$LOG"

inotifywait -m -r -e close_write --format '%w%f' "$SOURCE" | while read FILE
do
    case "$FILE" in
        *.mkv|*.mp4|*.avi)
            echo "Checking: $FILE" >> "$LOG"

            ffmpeg -v error -i "$FILE" -f null - 2>> "$LOG"

            if [ $? -ne 0 ]; then
                echo "Broken file detected: $FILE" >> "$LOG"
                mv "$FILE" "$DEST/"
            else
                echo "File OK: $FILE" >> "$LOG"
            fi
        ;;
    esac
done
