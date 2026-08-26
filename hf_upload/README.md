---
license: mit
task_categories:
- text-generation
language:
- zh
- en
---

# SASES Fine-tune Dataset

SASES 种子架构自动迭代产生的成功轨迹数据集。

## 数据量
600 条成功记录

## 格式
每行一个 JSON 对象，包含 `messages` 字段（指令微调格式）。

## 用途
用于微调代码生成模型，使模型学习 SASES 的生成-验证-回溯工作范式。
