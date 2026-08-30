import json
import os
from core.db import init_db
from core import seed_store

init_db()

# 迁移外部种子池
if os.path.exists("seed_tasks_external.jsonl"):
    with open("seed_tasks_external.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            try:
                seed = json.loads(line)
                seed_store.add_external_seed(
                    description=seed.get("description", ""),
                    test_cases=seed.get("test_cases", []),
                    user_id=str(seed.get("user_id", "system")),
                    source=seed.get("source", "external_api")
                )
            except:
                pass

# 迁移主种子池
if os.path.exists("seed_tasks_new.jsonl"):
    with open("seed_tasks_new.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            try:
                seed = json.loads(line)
                seed_store.add_main_seed(
                    description=seed.get("description", ""),
                    test_cases=seed.get("test_cases", []),
                    user_id=str(seed.get("user_id", "system")),
                    source=seed.get("source", "external_api")
                )
            except:
                pass

print("种子池迁移完成")
