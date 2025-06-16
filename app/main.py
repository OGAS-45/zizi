# 基础引入
import os

# 第三方引入
from fastapi import (
    Depends,
    HTTPException,
    Form,
    Request,
    FastAPI,
    Query
)
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import time
from sqlalchemy.orm import Session

# 项目内部引入
from app.database import Base, engine, get_db
from app.services.qa_system import QASystem
from app.services.log_handler import calculate_stats
from app.data.repositories import QARepository, User
from app.routes import kb_admin_api
from utils.version_info import get_version_info
from app.utils.logger_config import setup_logger
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时逻辑
    yield
    # 关闭时逻辑
    from app.utils.vector_db_operations import connections
    if connections.has_connection("default"):
        connections.disconnect("default")
    print("所有资源已释放")

app = FastAPI(lifespan = lifespan,middleware=[
    Middleware(SessionMiddleware, secret_key="zizi", session_cookie="session_cookie")
])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 按需调整允许的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加这行代码来包含所有路由
# app.include_router(api.router)
app.include_router(kb_admin_api.router)
# app.include_router(knowledge_api.router)
qa_system = QASystem() 
templates = Jinja2Templates(directory="app/templates")

@app.get("/version-history")
async def changelog():
    try:
        with open("app/static/version/VERSION_HISTORY.md", "r", encoding="utf-8") as f:
            content = f.read()
        return PlainTextResponse(content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="更新日志未找到")

# 从api.py迁移过来的特有路由
@app.get("/api/version")
async def get_version():
    from utils.version_info import VERSION, UPDATE_DATE
    return {
        "version": VERSION,
        "update_date": UPDATE_DATE
    }

# 维护模式中间件
@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    MAINTENANCE_MODE = False  # 通过修改这个变量切换模式
    
    # 维护模式特殊处理
    if MAINTENANCE_MODE:
        if request.url.path == "/":
            return RedirectResponse(url="/maintenance")
        
        # 开发者路径白名单
        if request.url.path.startswith("/chat"):
            return await call_next(request)
            
    else:
        if request.url.path == "/":
            return RedirectResponse(url="/chat")
    
    # 维护页面处理
    if request.url.path == "/maintenance":
        with open("app/templates/maintenance.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read(), status_code=503)
    
    return await call_next(request)

# API路由
@app.get("/chat/changelog")
async def changelog():
    try:
        with open("VERSION_HISTORY.md", "r", encoding="utf-8") as f:
            return PlainTextResponse(f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="更新日志未找到")

@app.post("/chat/feedback")
async def submit_feedback(
    feedback_data: dict, 
    db: Session = Depends(get_db)
):
    QARepository(db).add_feedback(
        interaction_id=feedback_data.get('interaction_id'),
        feedback=feedback_data.get('feedback')
    )
    return {"status": "success"}

@app.get("/chat/stats")
async def get_stats(db: Session = Depends(get_db)):
    try:
        return calculate_stats(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/api/history")
async def get_qa_history(
    limit: int = Query(5, gt=0, le=20),
    db: Session = Depends(get_db)
):
    try:
        history = QARepository(db).get_recent_interactions(limit)
        return [{
            "question": item.question,
            "answer": item.answer.content if hasattr(item, 'answer') else "暂无答案",
            "ask_time": item.ask_time.isoformat()
        } for item in history]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    version_info = get_version_info()
    stats = calculate_stats(db)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "version": version_info["version"],
        "update_date": version_info["update_date"],
        "stats": stats
    })

@app.post("/chat/ask")
async def ask_question(
    request: Request,
    question: str = Form(...),
    top_k: int = Form(3),
    temperature: float = Form(0.7),
    collection_type: str = Form('robot'),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    context = qa_system.query_local_db(question, top_k, collection_type)
    answer = qa_system.query_llm_server(question, context, temperature)
    
    interaction_id = QARepository(db).log_interaction({
        'user_id': request.session.get('user_id', 0),
        'question': question,
        'answer': answer,
        'response_time': time.time() - start_time,
        'ip_address': request.client.host,
        'device_info': request.headers.get("user-agent"),
        'source': 'web',
        'knowledge_base_id': 1 if collection_type == 'robot' else 2,
        'doc_count': top_k,
        'model_name': os.getenv("LLM_MODEL_NAME", "Qwen2.5_7B"),
        'temperature': temperature,
        'chunk_ids': [c.get('chunk_id') for c in context if 'chunk_id' in c]
    })
    
    return JSONResponse({
        "interaction_id": interaction_id,
        "question": question,
        "answer": answer,
        "context": context,
        "processing_time": f"{time.time() - start_time:.2f}s"
    })

@app.post("/chat/login")
async def user_login(request: Request, db: Session = Depends(get_db)):
    user = db.query().filter(User.ip_address == request.client.host).first()
    if not user:
        user = User(role='guest', ip_address=request.client.host)
        db.add(user)
        db.commit()
    return {"user_id": user.user_id, "role": user.role}

# 初始化数据库和静态文件
Base.metadata.create_all(bind=engine)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

def run_server():
    logger = setup_logger()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        reload=True,  
        limit_concurrency=100,
        timeout_keep_alive=30
    )



# 启动命令建议添加优雅关闭参数
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 30 --graceful-timeout 5

if __name__ == "__main__":
    run_server()




