from celery import Celery
from core.config import settings
from core.mongo import documents_col, knowledge_col
from utils.text_process import split_text_by_semantic
from utils.embedding import generate_batch_embeddings
from modules.document import parse_file
import traceback

# 初始化Celery
celery = Celery(
    "highway_qa_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# 异步任务：文档解析+向量入库
@celery.task(bind=True, max_retries=3)  # 设计文档要求重试3次
def process_document_task(self, doc_id: str, file_path: str, file_type: str):
    try:
        # 1. 解析文件提取文本
        raw_text = parse_file(file_path, file_type)
        # 2. 语义分段
        text_chunks = split_text_by_semantic(raw_text)
        # 3. 批量生成向量
        embeddings = generate_batch_embeddings(text_chunks)
        # 4. 批量插入知识库集合（设计文档highway_knowledge）
        knowledge_docs = [
            {
                "content": chunk,
                "doc_id": doc_id,
                "embedding": embeddings[i],
                "chunk_index": i,
                "create_time": None,
                "update_time": None
            }
            for i, chunk in enumerate(text_chunks)
        ]
        if knowledge_docs:
            knowledge_col.insert_many(knowledge_docs)
        # 5. 更新文档状态为processed
        documents_col.update_one(
            {"_id": doc_id},
            {"$set": {"status": "processed", "parse_log": "解析成功，向量入库完成"}}
        )
        return {"status": "success", "chunk_count": len(text_chunks)}
    except Exception as e:
        # 重试机制
        self.retry(exc=e, countdown=5)
        # 记录错误日志
        documents_col.update_one(
            {"_id": doc_id},
            {"$set": {"status": "failed", "parse_log": f"解析失败：{str(e)}\n{traceback.format_exc()}"}}
        )
        raise Exception(f"文档处理失败：{str(e)}")