from logger_core import log
import crawler_engine_pro_final
import queue_engine

def safe_run(name, func):
    try:
        log("SYSTEM", "RUNNING", f"Starting {name}")
        func()
        log("SYSTEM", "FINISH", f"{name} completed")
    except Exception as e:
        log("SYSTEM", "ERROR", f"{name} crashed: {str(e)}")

def main():
    safe_run("TOOL1", crawler_engine_pro_final.main)
    safe_run("TOOL2", queue_engine.build_queue)

if __name__ == "__main__":
    main()