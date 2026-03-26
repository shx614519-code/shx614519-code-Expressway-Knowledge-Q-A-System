from pymongo import MongoClient
from core.config import settings

# 单例模式创建MongoDB客户端
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

# 导出核心集合（与设计文档一致）
documents_col = db["documents"]
knowledge_col = db["highway_knowledge"]
users_col = db["users"]
conversations_col = db["conversations"]
messages_col = db["messages"]
system_logs_col = db["system_logs"]

def close_mongo_connection():
    client.close()