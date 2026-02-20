import requests
import time

QBIT_URL = "http://qbittorrent:8080"
QBIT_USER = "admin"
QBIT_PASS = "111111"

MAX_ACTIVE = 3
MIN_SPEED = 50 * 1024
CHECK_INTERVAL = 20
MIN_ACTIVE_TIME = 60


def login():
    s = requests.Session()
    r = s.post(
        f"{QBIT_URL}/api/v2/auth/login",
        data={"username": QBIT_USER, "password": QBIT_PASS}
    )
    if r.text == "Ok.":
        print("Connected to qBit")
        return s
    print("Login failed")
    return None


def manage():
    s = login()
    if not s:
        return

    torrents = s.get(f"{QBIT_URL}/api/v2/torrents/info").json()

    downloading = [
        t for t in torrents if t["state"] == "downloading"
    ]

    queued = [
        t for t in torrents if t["state"] == "queuedDL"
    ]

    print("Downloading:", len(downloading), "| Queued:", len(queued))

    # Pause slow torrents
    for t in downloading:
        if (
            t["dlspeed"] < MIN_SPEED
            and t["time_active"] > MIN_ACTIVE_TIME
        ):
            print("Pause slow:", t["name"], "Speed:", t["dlspeed"])
            s.post(
                f"{QBIT_URL}/api/v2/torrents/pause",
                data={"hashes": t["hash"]}
            )

    # Refresh list
    torrents = s.get(f"{QBIT_URL}/api/v2/torrents/info").json()
    downloading = [
        t for t in torrents if t["state"] == "downloading"
    ]
    queued = [
        t for t in torrents if t["state"] == "queuedDL"
    ]

    # Resume if slot available
    while len(downloading) < MAX_ACTIVE and queued:
        t = queued.pop(0)
        print("Resume:", t["name"])
        s.post(
            f"{QBIT_URL}/api/v2/torrents/resume",
            data={"hashes": t["hash"]}
        )
        downloading.append(t)


if __name__ == "__main__":
    print("qBit Manager started")

    while True:
        try:
            manage()
        except Exception as e:
            print("Error:", e)

        print("Sleep...\n")
        time.sleep(CHECK_INTERVAL)
