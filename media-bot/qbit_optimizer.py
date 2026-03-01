# -*- coding: utf-8 -*-

import requests
import time
import os
from logger_core import log

QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")

SESSION = requests.Session()

CHECK_INTERVAL = 60        # chu k? full loop
BURST_WAIT = 15            # ch? do t?c
MAX_ACTIVE = 5             # ch?n top 5


# ================= LOGIN =================
def login():
    try:
        r = SESSION.post(
            f"{QBIT_URL}/api/v2/auth/login",
            data={"username": QBIT_USER, "password": QBIT_PASS},
            timeout=10
        )
        return r.status_code == 200 and "Ok" in r.text
    except:
        return False


# ================= GET TORRENTS =================
def get_torrents():
    try:
        r = SESSION.get(
            f"{QBIT_URL}/api/v2/torrents/info",
            timeout=10
        )
        return r.json()
    except:
        return []


# ================= CONTROL =================
def pause(hash_value):
    SESSION.post(
        f"{QBIT_URL}/api/v2/torrents/pause",
        data={"hashes": hash_value}
    )


def resume(hash_value):
    SESSION.post(
        f"{QBIT_URL}/api/v2/torrents/resume",
        data={"hashes": hash_value}
    )


# ================= MAIN =================
def main():

    log("TOOL5", "START", "Burst Optimizer Started")

    while True:

        if not login():
            log("TOOL5", "ERROR", "Login failed")
            time.sleep(5)
            continue

        torrents = get_torrents()

        # L?c torrent chua hoàn thành
        candidates = [
            t for t in torrents
            if t["progress"] < 1
        ]

        if not candidates:
            time.sleep(CHECK_INTERVAL)
            continue

        log("TOOL5", "BURST", "Resuming all candidates")

        # 1?? Resume t?t c?
        for t in candidates:
            resume(t["hash"])

        # 2?? Ð?i ?n d?nh t?c d?
        time.sleep(BURST_WAIT)

        # 3?? L?y snapshot m?i
        torrents = get_torrents()

        active = [
            t for t in torrents
            if t["progress"] < 1
        ]

        # 4?? Sort theo t?c d? th?c t?
        active.sort(
            key=lambda x: x.get("dlspeed", 0),
            reverse=True
        )

        selected = active[:MAX_ACTIVE]
        selected_hash = {t["hash"] for t in selected}

        # 5?? Pause ph?n còn l?i
        for t in active:
            if t["hash"] not in selected_hash:
                pause(t["hash"])

        # Log top
        for t in selected:
            speed = round(t["dlspeed"] / 1024, 1)
            log("TOOL5", "RUN", f"{t['name']} {speed} KB/s")

        log("TOOL5", "SLEEP", f"Next cycle in {CHECK_INTERVAL}s")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()