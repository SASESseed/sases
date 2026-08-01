# 种子任务规范

请生成一个 JSONL 文件 `seed_tasks.jsonl`，每行一个 JSON 对象，包含以下字段：

- task_id: 字符串，格式 "SEED-{类别}-{4位序号}"
- category: 类别，从以下随机轮选：code_generation, math_proof, logic_reasoning, security_judgment, text_summarization, data_analysis
- difficulty: 难度，随机选 easy, medium, hard
- description: 中文任务描述，清晰具体，例如："写一个Python函数，判断一个数是否为质数"
- test_cases: 测试用例列表，每个用例包含 input 和 expected_output。代码类任务至少有2个用例
- reference_answer: 一个高质量的参考解答（代码或文本）

共生成 100 个不同的种子任务，覆盖所有类别，难度分布均匀。