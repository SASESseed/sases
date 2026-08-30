import time

import auth
from core import config
from core import knowledge_base
from core import seed_utils
from core import seed_store

MODEL = config.MODEL_NAME

def process_seed(seed):
    desc = seed["description"]
    test_cases = seed.get("test_cases", [])
    seed_user_id = seed.get("user_id", "system")
    print(f"\n处理种子: {desc} (提交者ID: {seed_user_id})")

    try:
        branches_text = seed_utils.call_chat(
            f"任务：{desc}\n请提出两种截然不同的思路，用`思路A：`和`思路B：`标明。",
            temperature=0.7
        )
        branch_a, branch_b = seed_utils.parse_two_branches(branches_text)

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

            # 从主种子池删除已处理种子
            seed_store.delete_main_seed(seed["id"])
            return True
        else:
            print(f"  ✗ 失败：{msg}")
            return False
    except Exception as e:
        print(f"  处理异常：{e}")
        return False

def main():
    seeds = seed_store.list_main_seeds()
    if not seeds:
        print("主种子池为空，无任务可处理。")
        return

    success = 0
    for i, seed in enumerate(seeds):
        print(f"\n[{i+1}/{len(seeds)}]")
        if process_seed(seed):
            success += 1
        time.sleep(0.3)

    print(f"\n处理完成：成功 {success}/{len(seeds)}")

if __name__ == "__main__":
    main()
