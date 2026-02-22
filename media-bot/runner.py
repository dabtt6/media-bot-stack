# -*- coding: utf-8 -*-

import subprocess
import threading
import time
import traceback
import logging

CRAWL_INTERVAL = 86400  # 24h

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | MASTER | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("MASTER")


# =========================
# SAFE PROCESS RUNNER
# =========================
def run_process(name, script):

    while True:
        try:
            logger.info(f"{name} STARTED")

            process = subprocess.Popen(
                ["python", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in process.stdout:
                print(line.rstrip())

            process.wait()

            logger.error(f"{name} STOPPED - restarting in 5s")

        except Exception as e:
            logger.error(f"{name} CRASH: {e}")
            traceback.print_exc()

        time.sleep(5)


# =========================
# CRAWLER LOOP (FIX HERE)
# =========================
# =========================
# CRAWLER LOOP
# =========================
def crawl_loop():

    while True:
        try:
            # ?? 1?? Agent scan tru?c
            logger.info("AGENT SCAN START")
            subprocess.run(["python", "agent.py", "once"])
            logger.info("AGENT SCAN DONE")

            # ?? 2?? Sau dó crawl
            logger.info("CRAWLER START")
            subprocess.run(["python", "crawler_engine_pro_final.py"])
            logger.info("CRAWLER DONE")

        except Exception as e:
            logger.error(f"CRAWLER ERROR: {e}")
            traceback.print_exc()

        logger.info(f"Sleeping {CRAWL_INTERVAL} seconds")
        time.sleep(CRAWL_INTERVAL)


# =========================
# MAIN
# =========================
def main():

    logger.info("MASTER SYSTEM STARTED")

    threading.Thread(target=crawl_loop, daemon=True).start()

    threading.Thread(
        target=run_process,
        args=("QUEUE WORKER", "queue_worker.py"),
        daemon=True
    ).start()

    threading.Thread(
        target=run_process,
        args=("QBIT OPTIMIZER", "qbit_optimizer.py"),
        daemon=True
    ).start()

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()