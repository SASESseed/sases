import os
import json
import time
import uuid
import datetime

import auth
from core import config
from core import knowledge_base
from core import seed_utils

SEED_FILE = config.MAIN_SEED_FILE
MODEL = config.MODEL_NAME

def process_seed(task):
    desc = task["description"]
    test_cases = task.get("test_cases", [])
    seed_user_id = task.get("user_id", "system")
    print(f"\n处理种子: {desc} (提交者ID: {seed_user_id})")

    try:
        # 发芽：生成两个分支
        branches_text = seed_utils.call_chat(
            f"任务：{desc}\n请提出两种截然不同的思路，用`思路A：`和`思路B：`标明。",
            temperature=0.7
        )
        branch_a, branch_b = seed_utils.parse_two_branches(branches_text)

        # 生长 + 申诉
        synthesis = ""
        syntax_error = ""
        for attempt in range(2):
            if attempt == 0:
                prompt = f"任务：{desc}\n思路A：{branch_a}\n思路B：{branch_b}\n请**只输出纯Python函数定义**，不要包含函数调用或`if __name__ == '__main__'`。"
            else:
                prompt = f"之前代码有语法错误：{syntax_error}\n请修正并重新输出纯函数。"
            synthesis = seed_utils.clean_code(seed_utils.call_chat(prompt, temperature=0.2))
            ok, err = seed_utils.check_syntax(synthesis)
            if ok:
                break
            syntax_error = err
        else:
            print("  申诉失败，跳过。")
            return False

        # 沙箱验证
        passed, msg, _ = seed_utils.safe_run_tests(synthesis, test_cases)
        if passed:
            print("  ✓ 通过，入库。")
            knowledge_base.add_to_kb(
                task=desc,
                branch_a=branch_a,
                branch_b=branch_b,
                synthesis=synthesis,
                model_id=MODEL,
                user_id=seed_user_id,
                test_cases=test_cases
            )

            # 发放积分：仅对真实用户
            if seed_user_id != "system":
                try:
                    uid = int(seed_user_id)
                    auth.add_credits(uid, config.EXTERNAL_SEED_REWARD, "外部种子被采纳")
                    auth.add_system_message(
                        uid,
                        f"感谢你的贡献！你提交的种子已成功处理并加入知识库，获得 {config.EXTERNAL_SEED_REWARD} 积分。任务：{desc[:100]}...",
                        "SASES助手"
                    )
                    print(f"  已为用户 {uid} 发放 {config.EXTERNAL_SEED_REWARD} 积分。")
                except Exception as e:
                    print(f"  发放积分失败: {e}")

            return True
        else:
            print(f"  ✗ 失败：{msg}")
            return False
    except Exception as e:
        print(f"  处理异常：{e}")
        return False

def main():
    if not os.path.exists(SEED_FILE):
        print(f"种子文件 {SEED_FILE} 不存在。")
        return

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    if not tasks:
        print("种子池为空，无任务可处理。")
        return

    success = 0
    for i, task in enumerate(tasks):
        print(f"\n[{i+1}/{len(tasks)}]")
        if process_seed(task):
            success += 1
        time.sleep(0.3)

    print(f"\n处理完成：成功 {success}/{len(tasks)}")

    # 处理完成后清空种子池
    with open(SEED_FILE, "w", encoding="utf-8") as f:
        pass
    print(f"种子池 {SEED_FILE} 已清空，避免重复处理。")

if __name__ == "__main__":
    main()
