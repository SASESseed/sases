import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"  # 强制使用镜像

import json
from huggingface_hub import HfApi, create_repo, upload_folder

KB_FILE = "success_kb.json"
EXPORT_FILE = "finetune_data.jsonl"
REPO_NAME = "sases-finetune-data"

def export_data():
    with open(KB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(EXPORT_FILE, "w", encoding="utf-8") as out:
        for item in data:
            task = item.get("task", "")
            solution = item.get("solution", "")
            record = {
                "messages": [
                    {"role": "user", "content": f"任务：{task}\n请写出一个完整可运行的Python函数。只需输出代码。"},
                    {"role": "assistant", "content": solution}
                ]
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"已导出 {len(data)} 条数据")
    return len(data)

def upload():
    count = export_data()
    os.makedirs("hf_upload", exist_ok=True)
    if os.path.exists(f"hf_upload/{EXPORT_FILE}"):
        os.remove(f"hf_upload/{EXPORT_FILE}")
    os.replace(EXPORT_FILE, f"hf_upload/{EXPORT_FILE}")

    with open("hf_upload/README.md", "w", encoding="utf-8") as f:
        f.write(f"""---
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
{count} 条成功记录

## 格式
每行一个 JSON 对象，包含 `messages` 字段（指令微调格式）。

## 用途
用于微调代码生成模型，使模型学习 SASES 的生成-验证-回溯工作范式。
""")

    api = HfApi()
    user = api.whoami()["name"]
    repo_id = f"{user}/{REPO_NAME}"

    try:
        create_repo(repo_id, repo_type="dataset", exist_ok=True)
        print(f"仓库已就绪: {repo_id}")
    except Exception as e:
        print(f"创建仓库失败: {e}")
        return

    upload_folder(
        folder_path="hf_upload",
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Update dataset: {count} records"
    )

    print(f"上传完成: https://huggingface.co/datasets/{repo_id}")

if __name__ == "__main__":
    upload()
