from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from core.config import settings

# 密码加密上下文（bcrypt）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = settings.JWT_SECRET_KEY or "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 令牌有效期 60 分钟

# 打印密钥用于调试
print(f"JWT SECRET_KEY: {SECRET_KEY}")
print(f"JWT ALGORITHM: {ALGORITHM}")


# 密码哈希
def get_password_hash(password: str) -> str:
    """
    对密码进行 bcrypt 哈希加密
    """
    return pwd_context.hash(password)


# 密码校验
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


# 创建访问令牌
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    生成 JWT 访问令牌

    Args:
        data: 要编码在令牌中的数据（如 user_id, username, role）
        expires_delta: 令牌过期时间增量，默认使用 ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        生成的 JWT 令牌字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 解码令牌
def decode_token(token: str) -> dict:
    """
    解码并验证 JWT 令牌

    Args:
        token: JWT 令牌字符串

    Returns:
        解码后的 payload 字典

    Raises:
        JWTError: 如果令牌无效或已过期
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(f"令牌解码失败：{str(e)}")
