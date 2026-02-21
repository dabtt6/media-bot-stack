# -*- coding: utf-8 -*-

import requests
import time
import os
from logger_core import log

QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")

SESSION = requests.Session()

CHECK_INTERVAL = 300
MIN_SPEED = 200 * 1024
MAX_ACTIVE = 3


# ================= LOGIN =================
def login():
    try:
        r = SESSION.post(
            f"{QBIT_URL}/api/v2/auth/login",
            data={"username": QBIT_USER, "password": QBIT_PASS},
            timeout=10
        )

        if r.status_code == 200 and "Ok" in r.text:
            log("TOOL5", "INFO", "qBit connected")
            return True

        log("TOOL5", "WARNING", f"Login failed: {r.text}")
        return False

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
    SESSION.post(
        f"{QBIT_URL}/api/v2/torrents/pause",
        data={"hashes": hash_value}
    )


def resume(hash_value):
    SESSION.post(
        f"{QBIT_URL}/api/v2/torrents/resume",
        data={"hashes": hash_value}
    )


# ================= SMART SELECT =================
def select_best(torrents):

    candidates = [
        t for t in torrents
        if t["progress"] < 1
    ]

    if not candidates:
        return []

    # Uu tiên:
    # 1. Download speed cao
    # 2. Progress th?p (d? tránh stuck 99%)
    candidates.sort(
        key=lambda t: (
            t["dlspeed"],
            -t["progress"]
        ),
        reverse=True
    )

    return candidates[:MAX_ACTIVE]


# ================= MAIN =================
def main():

    log("TOOL5", "START", "Optimizer started")

    while True:

        if not login():
            time.sleep(10)
            continue

        torrents = get_torrents()

        if not torrents:
            time.sleep(CHECK_INTERVAL)
            continue

        active = [
            t for t in torrents
            if t["state"] == "downloading"
        ]

        selected = select_best(torrents)

        selected_hashes = {t["hash"] for t in selected}

        # Pause torrents không n?m trong top
        for t in active:
            if t["hash"] not in selected_hashes:
                pause(t["hash"])
                log("TOOL5", "PAUSE", t["name"])

        # Resume torrents du?c ch?n
        for t in selected:
            if t["state"] != "downloading":
                resume(t["hash"])
                log("TOOL5", "RESUME", t["name"])

        # Log tr?ng thái
        for t in selected:
            speed_kb = round(t["dlspeed"] / 1024, 1)
            log("TOOL5", "RUN",
                f"{t['name']} {speed_kb} KB/s")

        log("TOOL5", "SLEEP",
            f"Monitoring {CHECK_INTERVAL//60} minutes")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()