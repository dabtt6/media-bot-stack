# -*- coding: utf-8 -*-

import requests
import time
import os
from logger_core import log

QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")

SESSION = requests.Session()

CHECK_INTERVAL = 300      # 5 minutes
EVAL_DELAY = 10           # wait 10 seconds after resume-all
MIN_SPEED = 200 * 1024    # 200 KB/s
MAX_ACTIVE = 3

progress_map = {}


# ================= LOGIN =================
def login():
    try:
        r = SESSION.post(
            f"{QBIT_URL}/api/v2/auth/login",
            data={"username": QBIT_USER, "password": QBIT_PASS},
            timeout=10
        )
        return r.text == "Ok."
    except Exception as e:
        log("TOOL5", "ERROR", f"Login error: {str(e)}")
        return False


# ================= GET TORRENTS =================
def get_torrents():
    try:
        r = SESSION.get(
            f"{QBIT_URL}/api/v2/torrents/info",
            timeout=10
        )
        return r.json()
    except Exception as e:
        log("TOOL5", "ERROR", f"Fetch torrents error: {str(e)}")
        return []


# ================= CONTROL =================
def pause(hash_value):
    try:
        SESSION.post(
            f"{QBIT_URL}/api/v2/torrents/pause",
            data={"hashes": hash_value}
        )
    except:
        pass


def resume(hash_value):
    try:
        SESSION.post(
            f"{QBIT_URL}/api/v2/torrents/resume",
            data={"hashes": hash_value}
        )
    except:
        pass


# ================= SELECT LOGIC =================
def select_torrents(torrents):

    # only incomplete torrents
    candidates = [t for t in torrents if t["progress"] < 1]

    if not candidates:
        return []

    # sort by download speed descending
    candidates.sort(key=lambda x: x["dlspeed"], reverse=True)

    # torrents that meet speed requirement
    good = [t for t in candidates if t["dlspeed"] >= MIN_SPEED]

    if len(good) >= MAX_ACTIVE:
        log("TOOL5", "MODE", "Using 3 good torrents")
        return good[:MAX_ACTIVE]

    if good:
        remaining = MAX_ACTIVE - len(good)
        others = [t for t in candidates if t not in good]
        log("TOOL5", "MODE", "Mixed good + fastest others")
        return good + others[:remaining]

    log("TOOL5", "MODE", "All fail - using fastest 3")
    return candidates[:MAX_ACTIVE]


# ================= MAIN LOOP =================
def main():

    log("TOOL5", "START", "Optimizer started")

    while True:

        if not login():
            time.sleep(10)
            continue

        torrents = get_torrents()

        # STEP 1: Resume all incomplete torrents for evaluation
        for t in torrents:
            if t["progress"] < 1:
                resume(t["hash"])

        log("TOOL5", "CHECK", "Resume all for evaluation")

        # STEP 2: wait for speed update
        time.sleep(EVAL_DELAY)

        torrents = get_torrents()

        selected = select_torrents(torrents)

        if not selected:
            log("TOOL5", "IDLE", "No active torrents")
            time.sleep(CHECK_INTERVAL)
            continue

        selected_hashes = {t["hash"] for t in selected}

        # STEP 3: Pause non-selected torrents
        for t in torrents:
            if t["progress"] < 1 and t["hash"] not in selected_hashes:
                pause(t["hash"])

        # STEP 4: Record progress baseline
        for t in selected:
            progress_map[t["hash"]] = t["progress"]
            speed_kb = round(t["dlspeed"] / 1024, 1)
            log("TOOL5", "RUN", f"{t['name']} {speed_kb} KB/s")

        log("TOOL5", "SLEEP", "Monitoring 5 minutes")
        time.sleep(CHECK_INTERVAL)

        # STEP 5: Check for stuck torrents
        torrents = get_torrents()

        for t in torrents:

            if t["hash"] in selected_hashes:

                old_progress = progress_map.get(t["hash"], 0)
                new_progress = t["progress"]

                if new_progress <= old_progress:
                    log("TOOL5", "SWAP",
                        f"{t['name']} no progress - swapping")
                    pause(t["hash"])

        log("TOOL5", "CYCLE", "Re-evaluating")


if __name__ == "__main__":
    main()