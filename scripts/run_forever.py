import subprocess, sys, time, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = [sys.executable, "-m", "uvicorn", "app_full:app", "--port", "8001"]
BAD_ALLOC_THRESHOLD = 5

while True:
    signal = os.path.join(R, "restart_signal.txt")
    # restart signal handled
    if os.path.exists(signal):
        try:
            os.remove(signal)
        except Exception:
            pass
        print("[wrapper] signal-restart", flush=True)
        time.sleep(2)
        continue

    # 启动前清理 8001 端口占用（防止孤儿进程卡住）
    try:
        import subprocess as _sp
        _r = _sp.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
        for _line in _r.stdout.splitlines():
            if ":8001" in _line and "LISTENING" in _line:
                _pid = _line.strip().split()[-1]
                _sp.run(["taskkill", "/F", "/PID", _pid], capture_output=True, timeout=5)
                print(f"[wrapper] killed orphan pid={_pid} on :8001", flush=True)
    except Exception as _e:
        print(f"[wrapper] port cleanup failed: {_e}", flush=True)

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
    # 杀进程树（防止 uvicorn 子进程变孤儿）
    try:
        import subprocess as _sp
        _sp.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, timeout=10)
    except Exception:
        try:
            p.terminate()
            p.wait(5)
        except Exception:
            p.kill()
    print("[wrapper] restart", rr, flush=True)
    time.sleep(5)
