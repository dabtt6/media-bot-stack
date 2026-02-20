import os
import threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "data", "system.log")

lock = threading.Lock()

def log(tool, status, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {tool:<6} | {status:<8} | {message}"

    # Console (Docker logs)
    print(line, flush=True)

    # File log
    try:
        with lock:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except:
        pass