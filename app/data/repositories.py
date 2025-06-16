# 基础引入
import os
import re
import hashlib
from datetime import datetime, timedelta
from typing import List
import shutil
from chardet import detect

# 第三方引入
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pymilvus import utility, connections

# 项目内部引入
from app.data.models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument, User
from . import models

class QARepository:
    def __init__(self, db: Session):
        self.db = db

    def log_interaction(self, qa_data: dict):
        """记录交互，包括答案内容、答案记录、交互记录和查询配置"""
        try:
            with self.db.begin():
                # 存储回答内容
                answer_content = models.AnswerContent(content=qa_data['answer'])
                self.db.add(answer_content)
                self.db.flush()  # 获取answer_content_id

                # 存储回答记录
                answer = models.Answer(
                    answer_time=datetime.now(),
                    response_time=qa_data['response_time'],
                    chunk_ids=qa_data.get('chunk_ids', []),
                    answer_content_id=answer_content.answer_content_id
                )
                self.db.add(answer)
                self.db.flush()

                # 存储交互记录
                interaction = models.QAInteraction(
                    user_id=qa_data['user_id'],
                    question=qa_data['question'],
                    ask_time=datetime.now(),
                    ip_address=qa_data['ip_address'],
                    device_info=qa_data['device_info'],
                    source=qa_data['source'],
                    answer_id=answer.answer_id,
                    feedback=qa_data.get('feedback')
                )
                self.db.add(interaction)

                # 存储查询配置
                config = models.QueryConfig(
                    qa_id=interaction.id,
                    knowledge_base_id=qa_data['knowledge_base_id'],
                    doc_count=qa_data['doc_count'],
                    model_name=qa_data['model_name'],
                    temperature=qa_data['temperature']
                )
                self.db.add(config)
        except SQLAlchemyError as e:
            self.db.rollback()
            print(f"数据库操作错误: {e}")
            return None
        return interaction.id

    def get_recent_interactions(self, limit: int = 5):
        """获取最近的交互记录"""
        try:
            return self.db.query(models.QAInteraction) \
                .join(models.Answer) \
                .order_by(models.QAInteraction.ask_time.desc()) \
                .limit(limit).all()
        except SQLAlchemyError as e:
            print(f"数据库查询错误: {e}")
            return []

    def add_feedback(self, interaction_id: int, feedback: str):
        """添加用户反馈"""
        try:
            interaction = self.db.query(models.QAInteraction).get(interaction_id)
            if interaction:
                interaction.feedback = feedback
                self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            print(f"数据库更新错误: {e}")

    def get_total_interactions_count(self):
        """获取总问题数"""
        try:
            return self.db.query(models.QAInteraction).count()
        except SQLAlchemyError as e:
            print(f"数据库查询错误: {e}")
            return 0

    def get_today_interactions_count(self, date: datetime):
        """获取指定日期的提问数"""
        try:
            return self.db.query(models.QAInteraction).filter(
                models.QAInteraction.ask_time >= date,
                models.QAInteraction.ask_time < date + timedelta(days=1)
            ).count()
        except SQLAlchemyError as e:
            print(f"数据库查询错误: {e}")
            return 0


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_ip(self, ip: str):
        """根据IP地址获取用户"""
        try:
            return self.db.query(User).filter(User.ip_address == ip).first()
        except SQLAlchemyError as e:
            print(f"数据库查询错误: {e}")
            return None

    def update_user_role(self, user_id: int, new_role: str):
        """更新用户角色"""
        try:
            user = self.db.query(User).get(user_id)
            if user:
                user.role = new_role
                self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            print(f"数据库更新错误: {e}")


class KnowledgeBaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_with_collection(self, name: str, identifier: str):
        """创建知识库（关系库）"""
        try:
            # 1. 关系型数据库创建记录
            kb = KnowledgeBase(
                name=name, 
                identifier=identifier,
                status='enabled',
                create_time=datetime.now()
            )
            self.db.add(kb)
            self.db.flush()  # 获取知识库ID
            

            return {"status": "success", "data": kb}
        except Exception as e:
            self.db.rollback()
            raise

    def list_knowledge_bases(self):
        """获取所有知识库列表"""
        return self.db.query(KnowledgeBase).all()

    # 新增：按标识符过滤知识库（供操作员使用）
    def list_knowledge_bases_by_identifier(self, identifier: str):
        """根据操作员标识符获取对应的知识库列表"""
        return self.db.query(KnowledgeBase).filter(
            KnowledgeBase.identifier == identifier  # 假设知识库有`identifier`字段与操作员关联
        ).all()

    def get_by_identifier(self, identifier: str):
        """根据标识符获取知识库"""
        return self.db.query(KnowledgeBase).filter(
            KnowledgeBase.identifier == identifier
        ).first()

    def get_by_id(self, knowledge_base_id: int):
        """根据ID获取知识库"""
        return self.db.query(KnowledgeBase).filter(
            KnowledgeBase.knowledge_base_id == knowledge_base_id
        ).first()

    def delete_knowledge_base(self, kb_id: int):
        """删除知识库（关系"""
        try:
            kb = self.db.query(KnowledgeBase).get(kb_id)
            if not kb:
                raise HTTPException(status_code=404, detail="知识库不存在")
                
            # 1. 删除关系型数据库关联数据
            # 删除关联的Chunk数据
            self.db.query(KnowledgeChunk).filter(
                KnowledgeChunk.document_id.in_(
                    self.db.query(KnowledgeDocument.document_id)
                    .filter(KnowledgeDocument.knowledge_base_id == kb_id)
                )
            ).delete(synchronize_session=False)
            
            # 删除关联的Document记录
            self.db.query(KnowledgeDocument).filter(
                KnowledgeDocument.knowledge_base_id == kb_id
            ).delete()
            
            # 3. 删除知识库主体记录
            self.db.delete(kb)
            self.db.commit()
            return {"status": "success", "message": "知识库及关联数据已删除"}
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"删除失败: {str(e)}"
            ) from e

    def update_kb_status(self, identifier: str, status: str, update_time: datetime):
        """更新知识库状态"""
        kb = self.get_by_identifier(identifier)
        if not kb:
            raise HTTPException(404, "知识库不存在")
        
        kb.status = status
        kb.updated_at = update_time
        self.db.commit()
        return kb

