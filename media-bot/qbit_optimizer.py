# -*- coding: utf-8 -*-

import requests
import time
import os
from logger_core import log

QBIT_URL = os.getenv("QBIT_URL")
QBIT_USER = os.getenv("QBIT_USER")
QBIT_PASS = os.getenv("QBIT_PASS")

SESSION = requests.Session()

CHECK_INTERVAL = 10
MAX_ACTIVE = 3
MIN_SEED_KEEP = 2  # Không pause n?u seed v?n >= m?c này

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


# ================= BLOCK SEEDING =================
def block_seeding(torrents):
    for t in torrents:
        if t["progress"] == 1 and t["state"] in ("uploading", "stalledUP"):
            pause(t["hash"])
            log("TOOL5", "SEED-BLOCK", f"Paused seeding {t['name']}")


# ================= SCORE CALC =================
def calculate_score(t):
    seeds = t.get("num_seeds", 0)
    speed = t.get("dlspeed", 0)
    progress = t.get("progress", 0)

    # Uu tiên:
    # Seed quan tr?ng nh?t
    # Speed quan tr?ng th? hai
    # Tr? di?m n?u g?n xong (d? tránh gi? slot)
    return (seeds * 3) + (speed / 100000) - (progress * 5)


# ================= SMART SELECT =================
def select_best(torrents):

    candidates = [
        t for t in torrents
        if t["progress"] < 1
        and t["state"] in ("downloading", "pausedDL", "stalledDL")
    ]

    if not candidates:
        return []

    for t in candidates:
        t["_score"] = calculate_score(t)

    candidates.sort(key=lambda x: x["_score"], reverse=True)

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

        # 1?? Ch?n seeding
        block_seeding(torrents)

        # 2?? L?y torrent dang download
        active = [
            t for t in torrents
            if t["state"] in ("downloading", "stalledDL")
        ]

        # 3?? Ch?n top torrent theo score
        selected = select_best(torrents)
        selected_hashes = {t["hash"] for t in selected}

        # 4?? Pause torrent y?u (anti-flapping)
        for t in active:
            if (
                t["hash"] not in selected_hashes
                and t.get("num_seeds", 0) < MIN_SEED_KEEP
            ):
                pause(t["hash"])
                log("TOOL5", "PAUSE", t["name"])

        # 5?? Resume torrent du?c ch?n
        for t in selected:
            if t["state"] not in ("downloading", "stalledDL"):
                resume(t["hash"])
                log("TOOL5", "RESUME", t["name"])

        # 6?? Log tr?ng thái
        for t in selected:
            speed_kb = round(t["dlspeed"] / 1024, 1)
            log(
                "TOOL5",
                "RUN",
                f"{t['name']} | Seeds:{t['num_seeds']} | {speed_kb} KB/s"
            )

        log("TOOL5", "SLEEP", f"{CHECK_INTERVAL}s")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()