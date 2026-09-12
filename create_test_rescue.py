# create_test_rescue.py
# 创建测试用的解救任务数据
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import init_db
from core.services import quality_service, rescue_service


def main():
    init_db()

    print("正在创建测试质量问题...")

    # 创建几条不同严重程度的质量问题
    test_issues = [
        ("知识库条目包含过时API", "某条知识库记录使用的API已在最新版本中废弃", "low"),
        ("代码存在逻辑错误", "排序函数在边界条件下输出错误结果", "medium"),
        ("检测到不安全的代码模式", "方案中包含未经验证的外部调用，存在安全隐患", "high"),
        ("文档描述与实际不符", "参数说明与函数实现不一致", "low"),
        ("性能问题", "算法时间复杂度过高，大数据集下超时", "medium"),
    ]

    created_issues = []
    for title, detail, severity in test_issues:
        issue_id = quality_service.submit_debug_issue(
            title=title,
            detail=detail,
            severity=severity,
            source_id=f"test-{len(created_issues)+1}"
        )
        created_issues.append(issue_id)
        print(f"  ✅ 创建问题 #{issue_id}: {title} ({severity})")

    print(f"\n共创建 {len(created_issues)} 个质量问题")

    # 生成解救任务
    print("\n正在生成解救任务...")
    result = rescue_service.generate_rescue_tasks_from_issues(limit=20)
    print(f"  ✅ 生成 {result['created_count']} 个解救任务")

    # 列出可接取任务
    tasks = rescue_service.list_available_tasks(limit=20)
    print(f"\n当前可接取任务: {len(tasks)} 个")
    for t in tasks:
        print(f"  - task_id={t['id']}, 标题={t['title']}, 难度={t['difficulty']}, 宠物等级={t['pet_level']}")

    print("\n完成！现在可以在智维空间 → 解救任务中看到任务了。")


if __name__ == "__main__":
    main()
