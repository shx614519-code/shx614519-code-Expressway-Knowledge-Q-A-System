import re
from typing import List

# 文本清洗：去除冗余格式/特殊字符
def clean_text(text: str) -> str:
    text = re.sub(r'\n+', '\n', text)  # 合并多行
    text = re.sub(r'\s+', ' ', text)   # 合并空格
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\n，。？！：；""''()（）【】]', '', text)  # 保留核心字符
    return text.strip()

# 语义分段：按500字左右分段，避免切断语义
def split_text_by_semantic(text: str, chunk_size: int = 500) -> List[str]:
    clean_content = clean_text(text)
    chunks = []
    start = 0
    while start < len(clean_content):
        end = start + chunk_size
        # 找到最近的分隔符，避免切断句子
        if end < len(clean_content):
            end = clean_content.rfind('\n', start, end) or clean_content.rfind('。', start, end) or end
            end += 1 if end != len(clean_content) else end
        chunk = clean_content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks