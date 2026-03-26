from core.mongo import knowledge_col
from utils.embedding import generate_embedding
import numpy as np
from fastapi import HTTPException
from typing import List


# 替代MongoDB向量索引的检索函数（适配所有MongoDB版本）
def search_similar_knowledge(question: str, top_k: int = 5) -> list:
    try:
        # 1. 生成问题的向量（和原逻辑一致，用all-MiniLM-L6-v2模型）
        query_embedding = np.array(generate_embedding(question))

        # 2. 先用文本索引筛选相关知识片段（缩小计算范围）
        # 文本索引检索：匹配问题中的关键词
        candidate_docs = list(
            knowledge_col.find(
                {"$text": {"$search": question}},  # 文本模糊检索
                {"content": 1, "doc_id": 1, "embedding": 1}  # 只取需要的字段
            ).limit(20)  # 先取20条候选，减少本地计算量
        )

        # 3. 本地计算余弦相似度（替代MongoDB的向量索引）
        for doc in candidate_docs:
            # 跳过无向量的文档
            if not doc.get("embedding") or len(doc["embedding"]) == 0:
                doc["score"] = 0.0
                continue
            # 余弦相似度公式：cosθ = (A·B) / (||A|| × ||B||)
            doc_embedding = np.array(doc["embedding"])
            # 计算点积
            dot_product = np.dot(query_embedding, doc_embedding)
            # 计算向量模长
            query_norm = np.linalg.norm(query_embedding)
            doc_norm = np.linalg.norm(doc_embedding)
            # 避免除以0
            if query_norm == 0 or doc_norm == 0:
                doc["score"] = 0.0
            else:
                doc["score"] = float(dot_product / (query_norm * doc_norm))

        # 4. 按相似度排序，取Top-K结果
        candidate_docs.sort(key=lambda x: x["score"], reverse=True)
        # 只返回top_k条
        final_results = candidate_docs[:top_k]

        return final_results

    except Exception as e:
        # 捕获并抛出明确的错误信息
        raise HTTPException(status_code=500, detail=f"知识检索失败：{str(e)}")


# 知识更新函数（原逻辑不变，仅适配无向量索引）
def update_knowledge(doc_id: str, user_id: str):
    # 1. 校验文档存在
    from core.mongo import documents_col
    doc = documents_col.find_one({"_id": doc_id, "status": {"$ne": "deleted"}})
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 2. 删除旧知识片段
    knowledge_col.delete_many({"doc_id": doc_id})
    # 3. 记录日志
    from core.mongo import system_logs_col
    from datetime import datetime
    system_logs_col.insert_one({
        "module": "knowledge",
        "operation": "update",
        "user_id": user_id,
        "content": f"用户{user_id}更新文档{doc_id}的知识片段，已删除旧数据",
        "create_time": datetime.now(),
        "level": "info"
    })
    return {"status": "success", "msg": "旧知识片段已删除，请重新解析文档生成新向量"}


# 知识片段检索函数（原逻辑不变）
def get_knowledge(filters: dict = None):
    filters = filters or {}
    return list(knowledge_col.find(filters, {"content": 1, "doc_id": 1, "chunk_index": 1}))