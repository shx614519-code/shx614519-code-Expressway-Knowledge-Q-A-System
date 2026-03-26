from fastapi import FastAPI, Depends, UploadFile, File, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from core.config import settings
from core.mongo import close_mongo_connection
from core.redis import close_redis_connection
from modules import document, knowledge, chat, user, system
from modules.user import get_current_user, get_admin_user
from celery_worker import process_document_task
import uvicorn

# 使用新的 lifespan 事件处理器（替代 on_event）
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时的操作
    print("应用启动成功")
    yield
    # 关闭时的操作
    close_mongo_connection()
    close_redis_connection()
    print("连接已关闭")

# 初始化FastAPI
app = FastAPI(
    title="高速公路知识问答系统",
    description="基于大语言模型的高速公路知识智能问答系统（设计文档实现版）",
    version="1.0.0",
    lifespan=lifespan
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"],
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册接口路由
## 1. 用户模块
# @app.post("/api/user/register", summary="用户注册")
# def register(username: str, password: str, role: str = "user"):
#     return user.register_user(username, password, role)
@app.post("/api/user/register", summary="用户注册")
def register(
    username: str = Body(..., description="用户名"),
    password: str = Body(..., description="密码"),
    role: str = Body(default="user", description="角色")
):
    return user.register_user(username, password, role)

@app.post("/api/user/login", summary="用户登录")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return user.login_user(form_data)

@app.get("/api/user/info", summary="获取当前用户信息")
def get_user_info(current_user: dict = Depends(get_current_user)):
    return current_user

## 2. 文档模块（仅管理员）
@app.post("/api/document/upload", summary="文档上传（管理员）")
async def upload_doc(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_admin_user)
):
    # 上传文档
    res = await document.upload_document(file, current_user["user_id"])
    # 异步处理文档解析+向量入库
    process_document_task.delay(
        doc_id=res["doc_id"],
        file_path=f"{settings.MINIO_BUCKET}/{res['doc_id']}.{file.filename.split('.')[-1].lower()}",
        file_type=file.filename.split(".")[-1].lower()
    )
    return res

@app.get("/api/document/list", summary="文档检索（管理员）")
def get_doc_list(
    name: str = Query(None),
    type: str = Query(None),
    status: str = Query(None),
    current_user: dict = Depends(get_admin_user)
):
    filters = {}
    if name: filters["name"] = {"$regex": name}
    if type: filters["type"] = type
    if status: filters["status"] = status
    return document.get_documents(filters)

@app.delete("/api/document/delete/{doc_id}", summary="文档删除（管理员）")
def del_doc(doc_id: str, current_user: dict = Depends(get_admin_user)):
    return document.delete_document(doc_id, current_user["user_id"])

## 3. 知识库模块（仅管理员）
@app.get("/api/knowledge/search", summary="知识片段检索（管理员）")
def search_knowledge(
    doc_id: str = Query(None),
    current_user: dict = Depends(get_admin_user)
):
    filters = {}
    if doc_id: filters["doc_id"] = doc_id
    return knowledge.get_knowledge(filters)

@app.put("/api/knowledge/update/{doc_id}", summary="知识更新（管理员）")
def update_knowledge(doc_id: str, current_user: dict = Depends(get_admin_user)):
    return knowledge.update_knowledge(doc_id, current_user["user_id"])

## 4. 对话模块（所有用户）
# @app.post("/api/chat", summary="多轮问答（核心）")
# def chat(
#     question: str,
#     conv_id: str = Query(None),
#     current_user: dict = Depends(get_current_user)
# ):
#     return chat.chat(question, current_user["user_id"], conv_id)
@app.post("/api/chat", summary="多轮问答（核心）")
def chat_handler(
    question: str =Query(..., description="问题内容"),
    conv_id: str = Query(None, description="对话 ID"),
    current_user: dict = Depends(get_current_user)
):
    return chat.chat(question, current_user["user_id"], conv_id)


@app.get("/api/chat/records", summary="查看对话记录")
def get_chat_records(
    conv_id: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    return chat.get_chat_records(current_user["user_id"], conv_id)

@app.delete("/api/chat/delete/{conv_id}", summary="删除对话记录")
def del_chat_record(conv_id: str, current_user: dict = Depends(get_current_user)):
    return chat.delete_chat_record(conv_id, current_user["user_id"])

## 5. 系统模块（仅管理员）
@app.get("/api/system/logs", summary="查看系统日志（管理员）")
def get_system_logs(current_user: dict = Depends(get_admin_user)):
    return system.get_system_logs()

# 关闭连接
# @app.on_event("shutdown")
# def shutdown_event():
#     close_mongo_connection()
#     close_redis_connection()

# 启动服务
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )