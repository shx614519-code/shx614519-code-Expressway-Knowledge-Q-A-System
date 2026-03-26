from fastapi import HTTPException
from core.mongo import system_logs_col
from datetime import datetime


# 获取系统日志
def get_system_logs():
    """
    获取系统日志（从 MongoDB 的系统日志集合中获取）
    """
    try:

        # 获取最近的日志，按时间倒序排列
        logs = list(system_logs_col.find().sort("timestamp", -1).limit(100))

        # ... existing code ...
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统日志失败：{str(e)}")


# 可选：添加记录系统日志的函数
def log_system_action(action: str, user_id: str, details: dict = None):
    """
    记录系统操作日志
    """
    try:

        log_entry = {
            "action": action,
            "user_id": user_id,
            "details": details or {},
            "timestamp": datetime.utcnow()
        }

        system_logs_col.insert_one(log_entry)
        return True
    except Exception as e:
        print(f"记录系统日志失败：{e}")
        return False
