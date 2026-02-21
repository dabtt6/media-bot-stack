# -*- coding: utf-8 -*-

import time
import subprocess

INTERVAL = 300  # 5 phút ch?y 1 l?n


def run_javinizer():
    print("TOOL6 | Running Javinizer -Recurse")

    subprocess.run([
        "docker", "exec", "javinizer",
        "pwsh", "-Command",
        "Import-Module Javinizer; "
        "Javinizer -Path '/data' "
        "-DestinationPath '/data' "
        "-Recurse -Update -Move -WriteNfo -DownloadImages"
    ])


def main():
    print("TOOL6 | Recurse Mode Started")

    while True:
        try:
            run_javinizer()
        except Exception as e:
            print("TOOL6 ERROR:", e)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()