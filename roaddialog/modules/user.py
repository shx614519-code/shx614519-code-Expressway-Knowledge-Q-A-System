from core.mongo import users_col, system_logs_col
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from core.jwt import create_access_token, verify_password, get_password_hash
from datetime import datetime
from bson import ObjectId

# 权限认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login")

# 用户注册
def register_user(username: str, password: str, role: str = "user"):
    # 校验角色
    if role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="角色仅支持admin/user")
    # 校验用户名是否存在
    if users_col.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="用户名已存在")
    # 密码加密（bcrypt，设计文档要求）
    hashed_pw = get_password_hash(password)
    # 插入用户
    user_id = str(ObjectId())
    users_col.insert_one({
        "_id": user_id,
        "username": username,
        "password": hashed_pw,
        "role": role,
        "create_time": datetime.now(),
        "last_login_time": None,
        "status": "active"
    })
    # 记录日志
    system_logs_col.insert_one({
        "module": "user",
        "operation": "register",
        "user_id": user_id,
        "content": f"用户{user_id}注册，用户名：{username}，角色：{role}",
        "create_time": datetime.now(),
        "level": "info"
    })
    return {"user_id": user_id, "username": username, "role": role}

# 用户登录
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    # 校验用户
    user = users_col.find_one({"username": form_data.username, "status": "active"})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    # 更新最后登录时间
    users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login_time": datetime.now()}}
    )
    # 生成JWT令牌
    access_token = create_access_token(
        data={"user_id": str(user["_id"]), "username": user["username"], "role": user["role"]}
    )
    # 记录日志
    system_logs_col.insert_one({
        "module": "user",
        "operation": "login",
        "user_id": str(user["_id"]),
        "content": f"用户{str(user['_id'])}（{user['username']}）登录成功",
        "create_time": datetime.now(),
        "level": "info"
    })
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user["_id"]),
        "username": user["username"],
        "role": user["role"]
    }

# 获取用户信息（权限校验）
# 获取用户信息（权限校验）
# def get_current_user(token: str = Depends(oauth2_scheme)):
#     from core.jwt import decode_token
#     from jose import JWTError
#
#     try:
#         payload = decode_token(token)
#         print(f"Token 解码成功 - Payload: {payload}")
#         user_id = payload.get("user_id")
#         if not user_id:
#             raise HTTPException(
#                 status_code=401,
#                 detail="令牌中缺少 user_id",
#                 headers={"WWW-Authenticate": "Bearer"}
#             )
#         user = users_col.find_one({"_id": ObjectId(user_id), "status": "active"})
#         if not user:
#             raise HTTPException(
#                 status_code=401,
#                 detail="令牌无效或用户已注销",
#                 headers={"WWW-Authenticate": "Bearer"}
#             )
#         return {
#             "user_id": str(user["_id"]),
#             "username": user["username"],
#             "role": user["role"]
#         }
#     except JWTError as e:
#         print(f"JWT 解码错误：{str(e)}")
#         raise HTTPException(
#             status_code=401,
#             detail=f"令牌解码失败：{str(e)}",
#             headers={"WWW-Authenticate": "Bearer"}
#         )

def get_current_user(token: str = Depends(oauth2_scheme)):
    from core.jwt import decode_token
    from jose import JWTError

    print(f"=== 开始验证 token ===")
    print(f"接收到的 token: {token[:50]}...")

    try:
        payload = decode_token(token)
        print(f"Token 解码成功 - Payload: {payload}")
        user_id = payload.get("user_id")
        if not user_id:
            print(f"错误：token 中缺少 user_id")
            raise HTTPException(
                status_code=401,
                detail="令牌中缺少 user_id",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 尝试使用 ObjectId 查询，如果失败则使用字符串查询
        # try:
        #     user = users_col.find_one({"_id": ObjectId(user_id), "status": "active"})
        # except:
        #     # 如果 ObjectId 转换失败，尝试直接使用字符串查询
        #     user = users_col.find_one({"_id": user_id, "status": "active"})

            # 直接使用字符串形式的 user_id 查询用户
        user = users_col.find_one({"_id": user_id, "status": "active"})

        if not user:
            print(f"错误：用户不存在或已注销，user_id: {user_id}")
            # 调试：查询所有用户看看
            all_users = list(users_col.find())
            print(f"数据库中所有用户：{[(str(u['_id']), u['username']) for u in all_users]}")
            raise HTTPException(
                status_code=401,
                detail="令牌无效或用户已注销",
                headers={"WWW-Authenticate": "Bearer"}
            )
        print(f"用户验证成功：{user['username']}")
        return {
            "user_id": str(user["_id"]),
            "username": user["username"],
            "role": user["role"]
        }
    except JWTError as e:
        print(f"JWT 解码错误：{str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"令牌解码失败：{str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


# ... existing code ...

# 管理员校验
def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="无管理员权限")
    return current_user