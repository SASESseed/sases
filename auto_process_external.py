import time
import subprocess
import sys

from core import seed_store

CHECK_INTERVAL = 60  # 秒

def main():
    print("启动外部种子自动处理监控...")
    while True:
        # 检查外部种子池是否有记录
        external_seeds = seed_store.list_external_seeds()
        if external_seeds:
            print(f"检测到 {len(external_seeds)} 条外部种子，开始合并...")
            subprocess.run([sys.executable, "merge_external_seeds.py"], check=False)
            print("合并完成，启动主循环...")
            subprocess.run([sys.executable, "process_seeds.py"], check=False)
            print("主循环执行完毕。")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
