#!/bin/bash

DB="/docker/media-stack/data/crawler/crawler_master_full.db"

echo "🧹 RESET DB (KEEP ACTORS)"

sqlite3 $DB <<SQL
DELETE FROM crawl;
DELETE FROM queuedqbit;
DELETE FROM agent;
VACUUM;
SQL

echo "✅ Reset done"

echo ""
echo "🚀 RUN TOOL 1 – CRAWL"
python3 crawler_master_full.py

echo ""
echo "🚀 RUN TOOL 2 – BUILD QUEUE"
python3 queue_engine.py

echo ""
echo "🚀 RUN TOOL 3 – SYNC AGENT + COMPARE"
python3 agent_engine_pro.py

echo ""
echo "🚀 RUN TOOL 4 – ADD QB"
python3 qbit_engine_pro_safe.py

echo ""
echo "✅ FULL CYCLE DONE"
