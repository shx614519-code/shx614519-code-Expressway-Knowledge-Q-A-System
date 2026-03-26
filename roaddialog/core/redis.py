import redis
from core.config import settings

# Redis连接（用于会话缓存/ Celery）
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

def close_redis_connection():
    redis_client.close()