# -*- coding: utf-8 -*-

import time
import traceback

import crawler_engine_pro_final
import queue_engine
import agent_engine_pro

INTERVAL = 600  # 10 phút

def log(msg):
    print(msg, flush=True)

def safe_run(name, func):
    log(f"\n===== {name} START =====")
    try:
        func()
        log(f"===== {name} END =====")
    except Exception as e:
        log(f"? ERROR in {name}: {e}")
        traceback.print_exc()

def main():

    log("?? MASTER LOOP (TOOLS 1-2-3) STARTED")

    while True:

        safe_run("TOOL 1 - CRAWLER", crawler_engine_pro_final.main)
        safe_run("TOOL 2 - BUILD QUEUE", queue_engine.build_queue)
        safe_run("TOOL 3 - AGENT SYNC", agent_engine_pro.main)

        log(f"\n? Sleeping {INTERVAL} seconds...\n")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()