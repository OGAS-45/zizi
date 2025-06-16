from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from app.data.repositories import KnowledgeBaseRepository
from app.data.models import KnowledgeBase
from sqlalchemy.exc import IntegrityError
from app.utils.vector_db_operations import VectorDB_Operations  # 改为新路径和类名

class KnowledgeService:
    def __init__(self, db: Session):
        self.repo = KnowledgeBaseRepository(db)

    def create_knowledge_base(self, name: str, identifier: str):
        # 增强字段验证
        if not identifier.isalnum():
            return {"status": "error", "message": "标识符 只能包含字母数字"}
        
        try:
            # 唯一性检查
            if self.repo.get_by_identifier(identifier):
                raise HTTPException(
                    status_code=409,
                    detail="知识库标识已存在"
                )
                
            return self.repo.create_with_collection(name, identifier)
            
        except IntegrityError as e:
            raise HTTPException(
                status_code=500,
                detail="数据库操作失败"
            ) from e

    # 新增安全验证方法
    @staticmethod
    def verify_admin(request: Request):
        if "admin_user" not in request.session:
            raise HTTPException(
                status_code=403,
                detail="需要管理员权限"
            )

    def process_upload(self, files, knowledge_base_id=None):
        # 添加权限验证
        self.verify_admin(current_user)  # 需要传入当前用户上下文
        # 实现文件处理逻辑
        processed_files = []
        for file in files:
            # 文件存储路径处理
            file_path = self._store_file(file)
            # 调用文档处理器
            processed = self._process_document(file_path)
            processed_files.append(processed)
        
        # 数据库事务管理
        try:
            return self.repo.bulk_insert(processed_files, knowledge_base_id)
        except Exception as e:
            self.repo.rollback()
            raise e

    def vectorize_knowledge_base(self, knowledge_base_id: int):
        """向量化知识库内容"""
        kb = self.repo.get_by_id(knowledge_base_id)
        if not kb:
            raise HTTPException(404, detail="知识库不存在")
        
        if not kb.file_path:
            raise HTTPException(400, detail="知识库路径未配置")
        
        try:
            processor = VectorDB_Operations()  # 改为新类实例化
            return processor.process_collection(  # 方法名调整
                folder_path=kb.file_path,
                collection_name=kb.identifier  # 参数名调整
            )
        except Exception as e:
            raise HTTPException(500, detail=f"向量化失败: {str(e)}")