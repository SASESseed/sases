import subprocess,sys,time,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C=[sys.executable,"-m","uvicorn","app_full:app","--port","8001"]
while True:
 print("[wrapper] start",flush=True)
 s=time.time()
 p=subprocess.Popen(C,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",bufsize=1)
 rr=None
 try:
  for l in p.stdout:
   print(l,end="",flush=True)
   if "bad allocation" in l: rr="bad alloc";break
   if time.time()-s>43200: rr="max hours";break
 except KeyboardInterrupt:
  p.terminate();sys.exit(0)
 p.terminate()
 try: p.wait(10)
 except: p.kill()
 print("[wrapper] restart",rr,flush=True)
 time.sleep(5)