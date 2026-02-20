# -*- coding: utf-8 -*-

import time
import traceback

import crawler_engine_pro_final
import queue_engine

INTERVAL = 600

def log(msg):
    print(msg, flush=True)

def safe_run(name, func):
    log(f"\n===== {name} START =====")
    try:
        func()
        log(f"===== {name} END =====")
    except Exception as e:
        log(f"ERROR in {name}: {e}")
        traceback.print_exc()

def main():
    log("MASTER LOOP STARTED")

    while True:
        safe_run("TOOL 1 - CRAWLER", crawler_engine_pro_final.main)
        safe_run("TOOL 2 - BUILD QUEUE", queue_engine.build_queue)

        log(f"Sleeping {INTERVAL} seconds...\n")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()