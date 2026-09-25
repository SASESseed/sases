"""SASES auto restart + auto recover supervisor.

Usage:
    python scripts/auto_restart.py
"""
import os
import sys
import time
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(ROOT, "server.py")
MAX_RESTARTS = 20
BASE_DELAY = 2


def run_once():
    return subprocess.call([sys.executable, ENTRY], cwd=ROOT)


def main():
    restarts = 0
    while restarts < MAX_RESTARTS:
        code = run_once()
        if code == 0:
            print("[auto_restart] clean exit")
            break
        restarts += 1
        delay = min(BASE_DELAY * restarts, 60)
        print("[auto_restart] exited code=%s, retry in %ss (%s/%s)" % (code, delay, restarts, MAX_RESTARTS))
        time.sleep(delay)
    else:
        print("[auto_restart] max restarts reached")


if __name__ == "__main__":
    main()
