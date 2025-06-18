from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Index  # 添加Index
from app.database import Base
from sqlalchemy import CheckConstraint


class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)  # 新增用户名唯一约束
    password = Column(String(100), nullable=False)  # 存储哈希值
    role = Column(String(20))  # 修改为字符串类型存储枚举值
    identifier = Column(String(50))  # 新增操作员标识符字段
    ip_address = Column(String(45))  # 新增字段
    permissions = Column(JSON)  # 新增权限字段
    __table_args__ = (
        Index('ix_user_ip', 'ip_address'),
        CheckConstraint("role IN ('Admin','Operator')", name='check_valid_roles')  # 修改角色枚举值
    )

class KnowledgeBase(Base):
    __tablename__ = 'knowledge_bases'
    knowledge_base_id = Column(Integer, primary_key=True)
    identifier = Column(String(50), unique=True)  # 新增专属标识字段
    name = Column(String(100))
    create_time = Column(DateTime)
    update_time = Column(DateTime)
    status = Column(String(20), default='pending')
    last_processed = Column(DateTime)
    access_level = Column(String(20))
    total_chunks = Column(Integer)
    file_path = Column(String(500))  # 新增文件路径字段
    __table_args__ = (
        CheckConstraint(
            "status IN ('enabled','disabled','review')", 
            name='check_valid_status'
        ),
        CheckConstraint(
            "access_level IN ('public','internal','private')", 
            name='check_valid_access_level'
        )
    )

class KnowledgeDocument(Base):
    __tablename__ = 'knowledge_documents'
    document_id = Column(Integer, primary_key=True)
    knowledge_base_id = Column(Integer, ForeignKey('knowledge_bases.knowledge_base_id'))
    document_name = Column(String(100))
    source = Column(String(50))
    upload_time = Column(DateTime)
    word_count = Column(Integer)
    update_time = Column(DateTime)

class KnowledgeChunk(Base):
    __tablename__ = 'knowledge_chunks'
    chunk_id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('knowledge_documents.document_id'))
    content = Column(Text)
    vector_data = Column(Text)
    keywords = Column(Text)
    chunk_type = Column(String(20))
    __table_args__ = (
        CheckConstraint(
            "chunk_type IN ('text','code','definition','example','principle')",
            name='check_valid_chunk_types'
        ),
    )

class AnswerContent(Base):
    __tablename__ = 'answer_contents'
    answer_content_id = Column(Integer, primary_key=True)
    content = Column(Text)

class Answer(Base):
    __tablename__ = 'answers'
    answer_id = Column(Integer, primary_key=True)
    answer_time = Column(DateTime)
    response_time = Column(Float)
    chunk_ids = Column(JSON)
    answer_content_id = Column(Integer, ForeignKey('answer_contents.answer_content_id'))
    __table_args__ = (
        CheckConstraint('response_time >= 0', name='check_response_time_positive'),
    )

class QAInteraction(Base):
    __tablename__ = 'qa_interactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    question = Column(Text)
    ask_time = Column(DateTime)
    ip_address = Column(String(45))
    device_info = Column(String(100))
    source = Column(String(20))
    answer_id = Column(Integer, ForeignKey('answers.answer_id'))
    feedback = Column(String(100))
    __table_args__ = (
        Index('ix_qa_user_time', 'user_id', 'ask_time'),
        Index('ix_qa_source', 'source'),
    )

class QueryConfig(Base):
    __tablename__ = 'query_configs'
    config_id = Column(Integer, primary_key=True)
    qa_id = Column(Integer, ForeignKey('qa_interactions.id'))
    knowledge_base_id = Column(Integer, ForeignKey('knowledge_bases.knowledge_base_id'))
    doc_count = Column(Integer)
    model_name = Column(String(50))
    temperature = Column(Float)


# 新增操作日志表
class OperationLog(Base):
    __tablename__ = 'operation_logs'
    log_id = Column(Integer, primary_key=True)
    operator = Column(String(50))
    operation_type = Column(String(50))
    timestamp = Column(DateTime)
    details = Column(Text)