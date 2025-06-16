# 基础引入
import os
from datetime import datetime
import shutil
from typing import Dict, List

# 第三方引入
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Request, Body
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session


# 项目内部引入
from app.data.models import User
from app.data.repositories import KnowledgeBaseRepository
from app.database import get_db
from app.utils.vector_db_operations import VectorDB_Operations  # 改为新路径和类名
from app.security import get_current_user, require_admin   # 引入新的安全依赖
import json  # 新增导入

router = APIRouter(prefix="/admin/knowledge", tags=["Knowledge Management"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

security = HTTPBearer()

async def get_current_admin(request: Request):
    if "admin_user" not in request.session:
        raise HTTPException(status_code=403, detail="请先登录")
    return request.session["admin_user"]

# 当前硬编码管理员凭证
ADMIN_CREDENTIALS = {
    "username": "admin",
    "password": "zizi@2025"
}

async def require_confirmation():
    """危险操作确认依赖"""
    # 这里可以添加二次确认逻辑，比如：
    # 1. 弹出确认对话框
    # 2. 要求输入管理员密码
    # 3. 或其他验证方式
    # 当前先简单返回True通过验证
    return True


# 文档处理端点
@router.post("/process-folder")
async def process_folder(
    folder_path: str = Body(..., description="待处理的文件夹路径"),
    knowledge_base: str = Body('robot', description="目标知识库名称"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    try:
        processor = VectorDB_Operations()  # 改为新类实例化
        # 替换旧的分步调用为统一入口方法（方法名调整为process_collection）
        result = processor.process_collection(
            folder_path=folder_path,
            collection_name=knowledge_base  # 参数名调整为collection_name
        )
        
        # 更新知识库状态
        repo = KnowledgeBaseRepository(db)
        repo.update_kb_status(knowledge_base, "processed", datetime.now())
        
        return result  # 直接返回统一方法的结果
    except Exception as e:
        raise HTTPException(500, detail=f"处理失败: {str(e)}")

# 新增登录页面前端模板
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<body>
  <form action="/admin/knowledge/login" method="post">
    用户名: <input type="text" name="username"><br>
    密码: <input type="password" name="password"><br>
    <input type="submit" value="登录">
  </form>
</body>
</html>
"""

# 新增登录验证路由
@router.post("/login")
async def admin_login(
    username: str = Form(...),
    password: str = Form(...),
    request: Request = Request,
    db: Session = Depends(get_db)  # 新增数据库依赖
):
    try:
        # 从数据库查询用户
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return HTMLResponse("用户不存在 <a href='/admin/knowledge/login'>重试</a>")
        
        # 验证密码（假设使用bcrypt哈希，需安装bcrypt）
        # 实际应使用security.py中的密码验证函数
        if not user.password == password:  # 示例代码，实际应比较哈希值
            return HTMLResponse("密码错误 <a href='/admin/knowledge/login'>重试</a>")
        
        # 记录用户信息到session（包含角色和identifier）
        request.session["current_user"] = {
            "username": user.username,
            "role": user.role,
            "identifier": user.identifier
        }
        return RedirectResponse(url="/admin/knowledge/kb_admin", status_code=302)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录验证失败: {str(e)}")


@router.get("/login")
async def login_page():
    return HTMLResponse(LOGIN_TEMPLATE)

@router.get("/logout")
async def admin_logout(request: Request):
    request.session.pop("admin_user", None)
    return RedirectResponse(url="/admin/knowledge/login")


@router.get("/kb_admin")
async def admin_page(request: Request, db: Session = Depends(get_db)):
    # 验证管理员登录   
    if "admin_user" not in request.session:
        return RedirectResponse(url="/admin/knowledge/login")
    
    # 获取当前用户角色（从session中获取）
    current_user = request.session.get("current_user")
    is_admin = current_user.get("role") == "Admin" if current_user else False  # 判断是否为管理员
    
    # 获取知识库列表
    repo = KnowledgeBaseRepository(db)
    kb_list = repo.list_knowledge_bases()
    
    # 返回管理页面（注入用户角色信息）
    with open("app/templates/kb_admin.html", "r", encoding="utf-8") as f:
        content = f.read()
        # 替换知识库列表区域
        content = content.replace('<div class="kb-list">', 
                                f'<div class="kb-list" data-kbs=\'{kb_list}\'>')
        # 注入全局变量标记管理员身份（新增）
        content += f'<script>window.isAdmin = {json.dumps(is_admin)};</script>'
        return HTMLResponse(content)

@router.post("/create-kb")
async def create_knowledge_base(
    name: str = Body(...),
    identifier: str = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    try:
        repo = KnowledgeBaseRepository(db)
        if repo.get_by_identifier(identifier):
            raise HTTPException(400, "知识库标识符已存在")
        
        # 创建文件夹
        base_path = "D:\\401385\\zizi-1.5-5.6\\markdown_files"
        kb_path = os.path.join(base_path, identifier)
        os.makedirs(kb_path, exist_ok=True)
        
        # 创建关系库记录
        result = repo.create_with_collection(name, identifier)
        kb = repo.get_by_identifier(identifier)
        kb.file_path = kb_path
        db.commit()
        
        # 新增：初始化向量库集合（确保与关系库同步）
        vector_processor = VectorDB_Operations()
        vector_processor._setup_milvus_collection(collection_name=identifier)  # 直接调用初始化方法
        
        return result
    except Exception as e:
        print({str(e)})
        raise HTTPException(500, detail=f"创建失败: {str(e)}")

@router.get("/list-kbs")
async def list_knowledge_bases(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  # 使用新的权限依赖
):
    repo = KnowledgeBaseRepository(db)
    if current_user["role"] == "Admin":
        # 管理员查看所有知识库
        kbs = repo.list_knowledge_bases()
    else:
        # 操作员只查看自己identifier对应的知识库
        kbs = repo.list_knowledge_bases_by_identifier(current_user["identifier"])
    
    # 返回更结构化的数据
    return [
        {
            "knowledge_base_id": kb.knowledge_base_id,
            "name": kb.name,
            "identifier": kb.identifier,
            "status": kb.status,
            "create_time": kb.create_time.isoformat() if kb.create_time else None,
            "update_time": kb.update_time.isoformat() if kb.update_time else None,
            "total_chunks": kb.total_chunks or 0
        }
        for kb in kbs
    ]

@router.post("/vectorize-kb")
async def vectorize_knowledge_base(
    knowledge_base: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    try:
        repo = KnowledgeBaseRepository(db)
        kb = repo.get_by_identifier(knowledge_base)
        if not kb:
            raise HTTPException(404, detail="知识库不存在")
        if not kb.file_path:
            raise HTTPException(400, detail="知识库路径未配置")
        print("vectorizeing")
        processor = VectorDB_Operations()
        print("process")
        result = processor.process_collection(
            folder_path=kb.file_path,
            collection_name=knowledge_base
        )
        return result
    except Exception as e:
        raise HTTPException(500, detail=f"向量化失败: {str(e)}")

@router.post("/upload-files")
async def upload_files(
    files: List[UploadFile] = File(...),
    knowledge_base_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  # 使用权限依赖
):
    try:
        kb = KnowledgeBaseRepository(db).get_by_id(knowledge_base_id)
        
        # 操作员必须上传到自己identifier的知识库
        if current_user["role"] == "Operator" and kb.identifier != current_user["identifier"]:
            raise HTTPException(status_code=403, detail="无权限操作该知识库")
        
        # 获取知识库信息
        repo = KnowledgeBaseRepository(db)
        kb = repo.get_by_id(knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 检查知识库路径是否存在
        if not kb.file_path or not os.path.exists(kb.file_path):
            raise HTTPException(status_code=400, detail="知识库路径无效")

        # 新增：清空原有文件夹内容

        shutil.rmtree(kb.file_path)  # 删除原文件夹
        os.makedirs(kb.file_path)     # 重新创建空文件夹

        saved_files = []
        for file in files:
            # 获取前端传递的相对路径（包含目录结构）
            relative_path = file.filename
            # 构建完整保存路径
            save_path = os.path.join(kb.file_path, relative_path)
            # 创建必要的目录
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            # 保存文件
            with open(save_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_files.append(save_path)

        return {
            "status": "success",
            "message": "文件/目录上传成功",
            "saved_files": saved_files,
            "knowledge_base": kb.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/delete")
async def delete_knowledge_base(
    identifier: str = Form(...),   # 保留标识符参数
    password: str = Form(...),  # 新增密码字段
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)  # 强制管理员权限
):
    # 验证最高权限密码（示例使用硬编码，实际应从配置获取）
    if password != ADMIN_CREDENTIALS["password"]:
        raise HTTPException(status_code=401, detail="管理员密码错误")
    
    # 获取知识库信息
    repo = KnowledgeBaseRepository(db)
    kb = repo.get_by_identifier(identifier)
    print(1)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    print(2)
    # 删除向量库
    vector_processor = VectorDB_Operations()
    vec_result = vector_processor.delete_knowledge_base(collection_name=identifier)
    print(3)
    if vec_result["status"] != "success":
        raise HTTPException(status_code=500, detail=f"向量库删除失败: {vec_result['message']}")
    
    print(4)
    # 删除关系库（复用现有方法）
    rel_result = repo.delete_knowledge_base(kb.knowledge_base_id)
    return {"status": "success", "message": "知识库（关系库+向量库）删除完成"}

