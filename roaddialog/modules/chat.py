from core.mongo import conversations_col, messages_col, system_logs_col
from core.redis import redis_client
from modules.knowledge import search_similar_knowledge
from utils.llm_client import build_prompt, call_llm
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException
from typing import List, Dict

# 初始化会话（首次提问）
def init_conversation(user_id: str) -> str:
    conv_id = str(ObjectId())
    conversations_col.insert_one({
        "_id": conv_id,
        "user_id": user_id,
        "create_time": datetime.now(),
        "last_update_time": datetime.now(),
        "status": "active"
    })
    # Redis缓存会话（过期时间24h）
    redis_client.set(f"conv_{conv_id}", user_id, ex=86400)
    return conv_id

# 获取会话上下文（Redis+MongoDB，设计文档要求）
def get_conversation_context(conv_id: str, limit: int = 5) -> List[Dict]:
    # 从MongoDB获取历史消息
    messages = list(
        messages_col.find({"conversation_id": conv_id})
        .sort("create_time", -1)
        .limit(limit)
    )
    # 反转顺序，按时间正序
    messages.reverse()
    # 构建上下文
    context = [
        {
            "user": msg["content"] if msg["role"] == "user" else "",
            "assistant": msg["content"] if msg["role"] == "assistant" else ""
        }
        for msg in messages
        if msg["role"] in ["user", "assistant"]
    ]
    return context

# 多轮问答核心流程（设计文档完整流程）
def chat(question: str, user_id: str, conv_id: str = None) -> Dict:
    # 1. 初始化/校验会话
    if not conv_id:
        conv_id = init_conversation(user_id)
    else:
        conv = conversations_col.find_one({"_id": conv_id, "user_id": user_id, "status": "active"})
        if not conv:
            raise HTTPException(status_code=404, detail="会话不存在或已关闭")
    # 2. 向量检索相似知识片段
    similar_knowledge = search_similar_knowledge(question)
    knowledge_chunks = [k["content"] for k in similar_knowledge]
    source_docs = [str(k["_id"]) for k in similar_knowledge]
    # 3. 获取会话上下文
    context = get_conversation_context(conv_id)
    # 4. 构建Prompt并调用LLM
    prompt = build_prompt(question, knowledge_chunks, context)
    answer = call_llm(prompt)
    # 5. 存储消息记录（设计文档messages集合）
    user_msg_id = str(ObjectId())
    assistant_msg_id = str(ObjectId())
    messages_col.insert_many([
        {
            "_id": user_msg_id,
            "conversation_id": conv_id,
            "content": question,
            "role": "user",
            "create_time": datetime.now(),
            "source_docs": []
        },
        {
            "_id": assistant_msg_id,
            "conversation_id": conv_id,
            "content": answer,
            "role": "assistant",
            "create_time": datetime.now(),
            "source_docs": source_docs
        }
    ])
    # 6. 更新会话最后更新时间
    conversations_col.update_one(
        {"_id": conv_id},
        {"$set": {"last_update_time": datetime.now()}}
    )
    # 7. 记录日志
    system_logs_col.insert_one({
        "module": "chat",
        "operation": "query",
        "user_id": user_id,
        "content": f"用户{user_id}在会话{conv_id}提问：{question[:20]}...",
        "create_time": datetime.now(),
        "level": "info"
    })
    # 8. 返回结果
    return {
        "conv_id": conv_id,
        "question": question,
        "answer": answer,
        "source_count": len(source_docs),
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# 查看/导出/删除对话记录（设计文档要求）
def get_chat_records(user_id: str, conv_id: str = None):
    filters = {"user_id": user_id}
    if conv_id:
        filters["_id"] = conv_id
    conversations = list(
        conversations_col.find(filters)
        .sort("last_update_time", -1)
    )
    # 拼接每条会话的消息
    for conv in conversations:
        conv["messages"] = list(
            messages_col.find({"conversation_id": conv["_id"]})
            .sort("create_time", 1)
        )
        conv["_id"] = str(conv["_id"])
    return conversations

def delete_chat_record(conv_id: str, user_id: str):
    # 关闭会话+删除消息
    conversations_col.update_one(
        {"_id": conv_id, "user_id": user_id},
        {"$set": {"status": "closed", "last_update_time": datetime.now()}}
    )
    messages_col.delete_many({"conversation_id": conv_id})
    # 删除Redis缓存
    redis_client.delete(f"conv_{conv_id}")
    return {"status": "success", "conv_id": conv_id}