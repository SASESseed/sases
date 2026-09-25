import subprocess, sys, time, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = [sys.executable, "-m", "uvicorn", "app_full:app", "--reload", "--reload-dir", "static", "--port", "8001"]
BAD_ALLOC_THRESHOLD = 5

while True:
    signal = os.path.join(R, "restart_signal.txt")
import os
if os.path.exists('restart_signal.txt'):
    os.remove('restart_signal.txt')
    if os.path.exists(signal):
        try:
            os.remove(signal)
        except Exception:
            pass
        print("[wrapper] signal-restart", flush=True)
        time.sleep(2)
        continue

    print("[wrapper] start", flush=True)
    s = time.time()
    p = subprocess.Popen(C, cwd=R, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", bufsize=1)
    rr = None
    bad_count = 0
    try:
        for l in p.stdout:
            print(l, end="", flush=True)
            if "bad allocation" in l:
                bad_count += 1
                print(f"[wrapper] bad alloc #{bad_count}", flush=True)
                if bad_count >= BAD_ALLOC_THRESHOLD:
                    rr = "bad alloc x5"
                    break
            if time.time() - s > 43200:
                rr = "max hours"
                break
    except KeyboardInterrupt:
        p.terminate()
        sys.exit(0)
    p.terminate()
    try:
        p.wait(10)
    except Exception:
        p.kill()
    print("[wrapper] restart", rr, flush=True)
    time.sleep(5)
