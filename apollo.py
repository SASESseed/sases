import random, time, os, json
from datetime import datetime

# ---------- 配置 ----------
MAX_CONSECUTIVE_FAILS = 5
EXIT_NIGHT_SUCCESSES = 3
SUNNY_MAX_BONUS = 3
SUNNY_RANDOM_CHANCE = 0.10
BASE_DAY_SPEED = 0.60
BASE_OVERCAST_SPEED = 0.40
BASE_NIGHT_SPEED = 0.30
SUNNY_SPEED = 1.0

# ---------- 状态 ----------
consecutive_successes = 0
consecutive_failures = 0
sunny_bonus_count = 0
current_weather = "Day"
log_file = "apollo_weather.log"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[阿波罗] {msg}")

def get_base_weather():
    hour = datetime.now().hour
    if hour < 8 or hour >= 20:
        return "Overcast"
    else:
        return "Overcast" if random.random() < 0.2 else "Day"

def get_current_weather():
    global current_weather, sunny_bonus_count
    base = get_base_weather()

    if consecutive_failures >= MAX_CONSECUTIVE_FAILS:
        if current_weather != "Night":
            log("进入黑夜状态（连续失败）")
        current_weather = "Night"
        return ("Night", BASE_NIGHT_SPEED)

    current_weather = base
    speed = BASE_DAY_SPEED if base == "Day" else BASE_OVERCAST_SPEED

    if current_weather == "Day" and random.random() < SUNNY_RANDOM_CHANCE:
        current_weather = "Sunny"
        speed = SUNNY_SPEED
        log("随机太阳出现！")

    return (current_weather, speed)

def report_result(success: bool):
    global consecutive_successes, consecutive_failures, sunny_bonus_count, current_weather

    if success:
        consecutive_successes += 1
        consecutive_failures = 0

        # 黑夜退出并奖励太阳
        if current_weather == "Night":
            if consecutive_successes >= EXIT_NIGHT_SUCCESSES:
                log(f"连续成功{consecutive_successes}次，黑夜破晓！")
                current_weather = "Sunny"
                sunny_bonus_count = 1
                consecutive_successes = 0
            return

        # 白天/阴天太阳奖励
        if current_weather == "Day" and sunny_bonus_count < SUNNY_MAX_BONUS:
            current_weather = "Sunny"
            sunny_bonus_count += 1
            log(f"奖励太阳！(已连续奖励{sunny_bonus_count}次)")
        elif current_weather == "Overcast" and sunny_bonus_count < 1:
            current_weather = "Sunny"
            sunny_bonus_count += 1
            log("阴天短暂太阳奖励。")
    else:
        consecutive_failures += 1
        consecutive_successes = 0
        sunny_bonus_count = 0
        if current_weather == "Sunny":
            current_weather = get_base_weather()
