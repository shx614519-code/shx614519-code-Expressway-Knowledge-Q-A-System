from sentence_transformers import SentenceTransformer
from core.config import settings
from typing import List
import numpy as np

# 加载预训练模型（单例）
model = SentenceTransformer(settings.EMBEDDING_MODEL)

# 生成文本向量
def generate_embedding(text: str) -> List[float]:
    embedding = model.encode(text, convert_to_numpy=True)
    embedding = embedding / np.linalg.norm(embedding)  # 归一化
    return embedding.tolist()

# 批量生成向量
def generate_batch_embeddings(texts: List[str]) -> List[List[float]]:
    embeddings = model.encode(texts, convert_to_numpy=True)
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings.tolist()