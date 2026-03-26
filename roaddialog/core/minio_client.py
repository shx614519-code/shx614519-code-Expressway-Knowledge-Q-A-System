# pyright: ignore[reportMissingImports]
from minio import Minio
from core.config import settings

# 初始化 MinIO 客户端
minio_client = Minio(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False  # HTTP（如果是本地开发）；生产环境建议 True（HTTPS）
)

# 确保存储桶存在
def ensure_bucket_exists():
    try:
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
            print(f"创建 MinIO 存储桶：{settings.MINIO_BUCKET}")
    except Exception as e:
        print(f"检查/创建 MinIO 存储桶失败：{e}")

# 启动时检查存储桶
ensure_bucket_exists()
