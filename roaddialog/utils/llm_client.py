from openai import OpenAI
from core.config import settings
from typing import List, Dict

# 初始化LLM客户端（适配智谱AI/OpenAI）
client = OpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
)

# 构建Prompt（结合知识库/上下文/问题，设计文档要求）
def build_prompt(question: str, knowledge_chunks: List[str], history: List[Dict] = None) -> str:
    history = history or []
    history_prompt = "\n".join([f"用户：{h['user']}\n助手：{h['assistant']}" for h in history])
    knowledge_prompt = "\n".join([f"知识片段{i+1}：{chunk}" for i, chunk in enumerate(knowledge_chunks)])
    prompt = f"""
    你是高速公路知识问答专家，仅基于提供的知识库内容回答问题，答案要结构化、简洁易懂。
    知识库内容：
    {knowledge_prompt}
    历史对话：
    {history_prompt}
    当前问题：{question}
    回答要求：1. 严格基于知识库，不编造信息；2. 分点说明，逻辑清晰；3. 保留核心数据（如限速、收费标准）。
    """
    return prompt.strip()

# 调用LLM生成答案
def call_llm(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # 低温度保证准确性
            max_tokens=1024
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"LLM调用失败：{str(e)}")