# -*- coding: utf-8 -*-
"""为现有 safety_memory 表补 embedding 和 content_hash"""
import sys
from core.services import memory_service

total = 0
while True:
    count = memory_service.backfill_embeddings(batch_size=50)
    if count == 0:
        break
    total += count
    print(f"已处理 {total} 条...")

print(f"\n✅ 完成，共补生成 {total} 条 embedding")
