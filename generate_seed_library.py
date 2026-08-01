import openai
import json
import time
import os

# ========== 配置 ==========
API_KEY = "sk-88208784f9d14eb2a422f992d044bca8"          # 替换成你自己的
BASE_URL = "https://api.deepseek.com/v1"
MODEL = "deepseek-v4-flash"              # 或 deepseek-v4-pro

TOTAL_SEEDS = 100
SUCCESS_TRAJECTORIES = 100
FAILURE_CASES = 50

# 类别池
CATEGORIES = [
    "code_generation",
    "math_proof",
    "logic_reasoning",
    "security_judgment",
    "text_summarization",
    "data_analysis"
]

DIFFICULTIES = ["easy", "medium", "hard"]

# 初始化客户端
client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ========== 工具函数 ==========
def call_api(prompt, max_tokens=4096, temperature=0.7):
    """封装API调用，带重试"""
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"user", "content":prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"API调用失败 (尝试{attempt+1}/3): {e}")
            time.sleep(2)
    raise Exception("API调用最终失败")

def clean_json(text):
    """清理模型可能返回的markdown包裹"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split('\n')
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = '\n'.join(lines)
    return text

# ========== 主流程 ==========
def main():
    # 1. 生成种子任务
    print("正在生成种子任务...")
    seed_prompt = f"""请生成{TOTAL_SEEDS}个AI训练种子任务，输出为JSONL格式，每行一个JSON对象。
每个对象字段：
- task_id: "SEED-{{类别缩写}}-{{4位序号}}"
- category: 从{json.dumps(CATEGORIES)}中均匀选择
- difficulty: 从{json.dumps(DIFFICULTIES)}中随机，尽量分布均匀
- description: 清晰的中文任务描述，长度适中
- test_cases: 测试用例列表，每个用例有input和expected_output。代码类任务至少2个用例。
- reference_answer: 一个高质量的参考解答

类别缩写对照：code_generation->CODE, math_proof->MATH, logic_reasoning->LOGIC, security_judgment->SEC, text_summarization->TEXT, data_analysis->DATA

直接输出纯JSONL，不要任何额外文字。"""
    
    raw = call_api(seed_prompt, max_tokens=8192, temperature=0.8)
    # 一次可能生成不了100个，需要分多次调用
    seeds_text = clean_json(raw)
    seeds_lines = [line for line in seeds_text.split('\n') if line.strip()]
    
    # 如果不够100个，继续追加生成
    while len(seeds_lines) < TOTAL_SEEDS:
        remaining = TOTAL_SEEDS - len(seeds_lines)
        extra_prompt = f"继续生成{remaining}个种子任务，格式同前，只输出JSONL。"
        extra_raw = call_api(extra_prompt, max_tokens=4096, temperature=0.8)
        extra_text = clean_json(extra_raw)
        extra_lines = [line for line in extra_text.split('\n') if line.strip()]
        seeds_lines.extend(extra_lines)
        print(f"  已生成 {len(seeds_lines)}/{TOTAL_SEEDS} 个种子")
        time.sleep(1)  # 避免限流
    
    seeds_lines = seeds_lines[:TOTAL_SEEDS]
    
    # 验证每行是否为合法JSON
    valid_seeds = []
    for i, line in enumerate(seeds_lines):
        try:
            obj = json.loads(line)
            if "task_id" not in obj:
                obj["task_id"] = f"SEED-GEN-{i+1:04d}"
            valid_seeds.append(obj)
        except json.JSONDecodeError:
            print(f"  警告：第{i+1}行不是合法JSON，已跳过")
    
    with open("seed_tasks.jsonl", "w", encoding="utf-8") as f:
        for seed in valid_seeds:
            f.write(json.dumps(seed, ensure_ascii=False) + "\n")
    
    print(f"✅ 种子任务生成完成，共{len(valid_seeds)}个，保存至 seed_tasks.jsonl")
    
    # 2. 生成成功轨迹
    print("\n正在生成成功轨迹...")
    trajectory_prompt = f"""基于以下种子任务列表（前10个示例，其余请类似处理）：
{json.dumps(valid_seeds[:10], ensure_ascii=False, indent=2)}

请为每个种子任务生成一个成功轨迹，输出JSONL格式，每行一个JSON对象：
{{
  "task_id": "原种子task_id",
  "task": "原任务描述",
  "branch_a": "一种截然不同的解决思路A（简短描述）",
  "branch_b": "另一种与A对立的思路B（简短描述）",
  "synthesis": "综合A和B后的完整可运行代码或答案，需保证正确",
  "verified": true,
  "metacognition": "一句成功原因总结"
}}

共需生成{SUCCESS_TRAJECTORIES}个轨迹，直接输出JSONL，不要额外文字。"""
    
    traj_lines = []
    for batch_start in range(0, len(valid_seeds), 20):
        batch = valid_seeds[batch_start:batch_start+20]
        batch_prompt = f"""为以下{len(batch)}个种子生成成功轨迹，格式同前：
{json.dumps(batch, ensure_ascii=False, indent=2)}

直接输出JSONL。"""
        raw = call_api(batch_prompt, max_tokens=8192, temperature=0.7)
        text = clean_json(raw)
        batch_lines = [line for line in text.split('\n') if line.strip()]
        traj_lines.extend(batch_lines)
        print(f"  已生成轨迹 {min(batch_start+20, len(valid_seeds))}/{len(valid_seeds)}")
        time.sleep(1)
    
    valid_traj = []
    for i, line in enumerate(traj_lines):
        try:
            obj = json.loads(line)
            valid_traj.append(obj)
        except json.JSONDecodeError:
            print(f"  警告：轨迹第{i+1}行非法JSON，跳过")
    
    with open("success_trajectories.jsonl", "w", encoding="utf-8") as f:
        for t in valid_traj:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"✅ 成功轨迹生成完成，共{len(valid_traj)}个")
    
    # 3. 生成失败案例
    print("\n正在生成失败案例...")
    failure_prompt = f"""基于已生成的种子任务，请创建{FAILURE_CASES}个失败案例，输出JSONL格式：
{{
  "task_id": "对应种子task_id",
  "task": "任务描述",
  "failed_synthesis": "一个看起来合理但有隐藏错误的方案",
  "error_type": "syntax_error|logic_error|security_violation",
  "error_description": "具体错误说明",
  "correction_path": "如何修正错误的指引",
  "verified_false": true
}}

请均匀覆盖不同错误类型，直接输出JSONL。"""
    
    raw = call_api(failure_prompt, max_tokens=8192, temperature=0.7)
    fail_text = clean_json(raw)
    fail_lines = [line for line in fail_text.split('\n') if line.strip()]
    
    # 补足50个
    while len(fail_lines) < FAILURE_CASES:
        remaining = FAILURE_CASES - len(fail_lines)
        extra_prompt = f"继续生成{remaining}个失败案例，格式同前，只输出JSONL。"
        extra_raw = call_api(extra_prompt, max_tokens=4096, temperature=0.7)
        extra_text = clean_json(extra_raw)
        extra_lines = [line for line in extra_text.split('\n') if line.strip()]
        fail_lines.extend(extra_lines)
        print(f"  已生成失败案例 {len(fail_lines)}/{FAILURE_CASES}")
        time.sleep(1)
    
    fail_lines = fail_lines[:FAILURE_CASES]
    valid_fail = []
    for i, line in enumerate(fail_lines):
        try:
            obj = json.loads(line)
            valid_fail.append(obj)
        except json.JSONDecodeError:
            print(f"  警告：失败案例第{i+1}行非法JSON，跳过")
    
    with open("failure_trajectories.jsonl", "w", encoding="utf-8") as f:
        for fcase in valid_fail:
            f.write(json.dumps(fcase, ensure_ascii=False) + "\n")
    print(f"✅ 失败案例生成完成，共{len(valid_fail)}个")
    
    print("\n🎉 全部完成！生成文件：")
    print("  - seed_tasks.jsonl")
    print("  - success_trajectories.jsonl")
    print("  - failure_trajectories.jsonl")

if __name__ == "__main__":
    main()
