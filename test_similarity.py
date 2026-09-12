# test_similarity.py
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.db import init_db
from core.services import knowledge_service as ks


TEST_PAIRS = [
    ("排序函数", "排列方法", True),
    ("排序函数", "搜索算法", False),
    ("删除数据", "移除数据", True),
    ("删除数据", "添加数据", False),
    ("计算最大公约数", "求两个数的最大公因数", True),
    ("计算最大公约数", "计算最小公倍数", False),
    ("修复API版本问题", "解决接口过时问题", True),
    ("修复API版本问题", "优化数据库性能", False),
]


def main():
    init_db()
    print("=" * 60)
    print("混合模式相似度测试")
    print("=" * 60)

    correct = 0
    api_calls = 0

    for a, b, should_match in TEST_PAIRS:
        r = ks._compute_similarities(a, [b])
        sim = r["sims"][0]
        method = r["method"]
        used_api = r["used_api"]
        if used_api:
            api_calls += 1

        thresholds = ks._get_thresholds_for_method(method)
        threshold = thresholds["duplicate"]
        predicted = sim >= threshold
        ok = (predicted == should_match)
        if ok:
            correct += 1

        status = "✅" if ok else "❌"
        print(f"{status} [{method}] 「{a}」 vs 「{b}」: 相似度={sim:.3f}, 预测={'相似' if predicted else '不同'}, 期望={'相似' if should_match else '不同'}, 阈值={threshold}")

    print(f"\n准确率: {correct}/{len(TEST_PAIRS)} = {correct/len(TEST_PAIRS):.1%}")
    print(f"API 调用次数: {api_calls}/{len(TEST_PAIRS)}")


if __name__ == "__main__":
    main()
