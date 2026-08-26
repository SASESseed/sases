import json
import time
import os

KB_FILE = "success_kb.json"
TARGET = 600
CHECK_INTERVAL = 60  # 每60秒检查一次

def count_records():
    if not os.path.exists(KB_FILE):
        return 0
    with open(KB_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return len(data)
        except:
            return 0

def main():
    print(f"开始监控 {KB_FILE}，目标 {TARGET} 条记录。")
    while True:
        count = count_records()
        print(f"[{time.strftime('%H:%M:%S')}] 当前记录数: {count}")
        if count >= TARGET:
            print(f"\n✅ 已达到目标 {TARGET} 条记录！可以停止主循环并进行微调。")
            break
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
