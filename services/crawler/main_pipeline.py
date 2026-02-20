import time
import subprocess
from datetime import datetime

CYCLE_SLEEP = 600   # 10 phút 1 cycle

def run(script):
    print(f"\n🟢 Running: {script}")
    try:
        subprocess.run(["python3", script], check=True)
    except Exception as e:
        print(f"❌ Error in {script}:", e)

def main():
    print("🚀 PRODUCTION PIPELINE STARTED")

    while True:
        print("\n====================================")
        print("🔁 NEW CYCLE:", datetime.now())
        print("====================================")

        run("crawler_engine_pro_final.py")   # Tool 1
        run("queue_engine.py")               # Tool 2
        run("agent_engine_pro.py")           # Tool 3
        run("qbit_engine_daemon.py")         # Tool 4

        print(f"\n⏳ Sleep {CYCLE_SLEEP} seconds...")
        time.sleep(CYCLE_SLEEP)

if __name__ == "__main__":
    main()
