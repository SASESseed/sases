import time, os, subprocess, sys

EXTERNAL_FILE = "seed_tasks_external.jsonl"
CHECK_INTERVAL = 60  # 秒

def main():
    print("启动外部种子自动处理监控...")
    while True:
        if os.path.exists(EXTERNAL_FILE) and os.path.getsize(EXTERNAL_FILE) > 0:
            print("检测到外部种子，开始合并...")
            subprocess.run([sys.executable, "merge_external_seeds.py"], check=False)
            print("合并完成，启动主循环...")
            # 启动主循环（如果已经在运行，会自行处理新种子；这里我们直接运行一次）
            subprocess.run([sys.executable, "main.py"], check=False)
            print("主循环执行完毕（可能因目标达到而提前结束）。")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
