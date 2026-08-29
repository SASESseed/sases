import openai, ast, re, uuid, time, random, json, os, subprocess, tempfile, inspect, datetime
from collections import defaultdict

import auth
from core import config
from core import knowledge_base
from core import seed_utils
from core import seed_generator

# ========== 配置 ==========
client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=120,
    max_retries=2
)
MODEL = config.MODEL_NAME
KB_FILE = config.KB_FILE
TARGET_SUCCESS = 700  # 你可以随时调整这个目标
SEEDS_PER_ROUND = 10

# ========== 知识库 ==========
knowledge_base.KB_FILE = KB_FILE   # 确保知识库模块使用相同路径

# ========== 工具函数 ==========
def is_python_code(text):
    return seed_utils.is_python_code(text)

def clean_code(text):
    return seed_utils.clean_code(text)

def check_syntax(code):
    return seed_utils.check_syntax(code)

def safe_run_tests(code, test_cases, timeout=5):
    return seed_utils.safe_run_tests(code, test_cases, timeout)

def parse_two_branches(text):
    return seed_utils.parse_two_branches(text)

def call_chat(prompt, max_retries=2, temperature=0.7):
    return seed_utils.call_chat(prompt, max_retries, temperature, model=MODEL)

def add_to_kb(task, branch_a, branch_b, synthesis, model_id=MODEL, user_id="system", backtrack_count=0, test_cases=None):
    knowledge_base.add_to_kb(
        task=task,
        branch_a=branch_a,
        branch_b=branch_b,
        synthesis=synthesis,
        model_id=model_id,
        user_id=user_id,
        backtrack_count=backtrack_count,
        test_cases=test_cases
    )

# ========== 种子处理（自动迭代） ==========
def process_seed_task(task):
    """处理单个种子任务，成功后入库"""
    desc = task["description"]
    test_cases = task.get("test_cases", [])
    print(f"\n处理种子: {desc}")

    try:
        branches_text = call_chat(
            f"任务：{desc}\n请提出两种截然不同的思路，用`思路A：`和`思路B：`标明。",
            temperature=0.7
        )
        branch_a, branch_b = parse_two_branches(branches_text)

        synthesis = ""
        syntax_error = ""
        for attempt in range(2):
            if attempt == 0:
                prompt = f"任务：{desc}\n思路A：{branch_a}\n思路B：{branch_b}\n请**只输出纯Python函数定义**，不要包含函数调用或`if __name__ == '__main__'`。"
            else:
                prompt = f"之前代码有语法错误：{syntax_error}\n请修正并重新输出纯函数。"
            synthesis = clean_code(call_chat(prompt, temperature=0.2))
            ok, err = check_syntax(synthesis)
            if ok:
                break
            syntax_error = err
        else:
            print("  申诉失败，跳过。")
            return False

        passed, msg, _ = safe_run_tests(synthesis, test_cases)
        if passed:
            print("  ✓ 通过，入库。")
            add_to_kb(desc, branch_a, branch_b, synthesis, test_cases=test_cases)
            return True
        else:
            print(f"  ✗ 失败：{msg}")
            return False
    except Exception as e:
        print(f"  处理异常：{e}")
        return False

# ========== 主循环 ==========
def main():
    # 初始时，知识库可能有历史数据，加载现有描述用于去重
    existing_descs = seed_generator.load_all_existing_descriptions()
    print(f"现有描述数量: {len(existing_descs)}")

    round_num = 1
    while len(knowledge_base.load_kb()) < TARGET_SUCCESS:
        # 生成一批新种子（内部包含语义相似去重和领域轮转）
        print(f"\n===== 第 {round_num} 轮：生成 {SEEDS_PER_ROUND} 个新种子 =====")
        seeds = seed_generator.generate_new_seeds(SEEDS_PER_ROUND)
        if not seeds:
            print("种子生成失败，可能API问题，等待 5 分钟后重试...")
            time.sleep(300)
            continue

        # 处理这批种子
        for i, seed in enumerate(seeds):
            if len(knowledge_base.load_kb()) >= TARGET_SUCCESS:
                break
            print(f"\n[{i+1}/{len(seeds)}] 开始处理...")
            process_seed_task(seed)
            time.sleep(0.3)

        round_num += 1

    print(f"\n🎉 达到目标！当前知识库记录数：{len(knowledge_base.load_kb())}")

if __name__ == "__main__":
    main()
