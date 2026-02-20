#!/bin/bash

FILE="$1"
DIR=$(dirname "$FILE")

echo "Javinizer triggered for: $DIR" >> /data/jav_trigger.log

docker exec javinizer /bin/sh -c "
pwsh -Command '
Import-Module Javinizer;
Invoke-JVSort -Path \"$DIR\" -DestinationPath \"$DIR\" -Update;
'
"
