#!/bin/bash

TORRENT_DIR="/data/movies"
LOG_FILE="/data/cleaner.log"

echo "===== $(date) =====" >> "$LOG_FILE"
echo "Đang quét: $TORRENT_DIR" >> "$LOG_FILE"

KEYWORDS=(
"18+"
"996gg"
"七龍珠"
"三國志"
"三國群淫"
"H版"
)

for keyword in "${KEYWORDS[@]}"; do
    find "$TORRENT_DIR" -type f -iname "*$keyword*" | while read FILE; do
        echo "Xoá file: $FILE" >> "$LOG_FILE"
        rm -f "$FILE"
    done
done

# Xoá folder rỗng
find "$TORRENT_DIR" -type d -empty -delete

echo "Hoàn tất dọn spam." >> "$LOG_FILE"
