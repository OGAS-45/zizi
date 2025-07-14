# 基础引入
import os
import re
import hashlib
from datetime import datetime
from typing import List
import shutil
from chardet import detect
import logging  # 新增
from logging.handlers import RotatingFileHandler 

# 第三方引入
from fastapi import HTTPException
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus
from langchain_core.documents import Document
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, connections, utility
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 项目内部引入
from ..data.models import KnowledgeChunk, KnowledgeDocument
from ..database import SessionLocal
from ..file_monitor.core import FileWatcher

# 日志配置(新增)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 设置最低日志级别

# 日志格式:时间-级别-模块:函数:行号-消息
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s')

# 控制台输出(仅输出INFO及以上)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# 文件输出(带轮转，最大5MB，保留3个备份)
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../logs"))
os.makedirs(log_dir, exist_ok=True)
file_handler = RotatingFileHandler(
    filename=os.path.join(log_dir, "document_processor.log"),
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=3,
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)  # 文件记录更详细的DEBUG日志
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)




class VectorDB_Operations:
    def __init__(self, model_path="./models/bge-large-zh-v1.5", split_size=1500, chunk_overlap=200):
        self._connect_milvus()
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_path,
            model_kwargs={'device': 'cuda'},
            encode_kwargs={
                'normalize_embeddings': True,
                'batch_size': 128,
                'convert_to_tensor': True,
                'device': 'cuda'
            }
        )
        self.embeddings.client._first_forward = True
        self.index_params = os.getenv("INDEX_PARAMS", {"metric_type": "L2","index_type": "IVF_FLAT","params": {"nlist": 1024}})
        self.markdown_splitter = self._create_markdown_splitter()  # 提取拆分器创建逻辑
        self.split_size = split_size
        self.chunk_overlap = chunk_overlap
        self.folder_path = None  # 新增：初始化folder_path为None
        
        logger.info(f"VectorDBOperations初始化完成 | 模型路径: {model_path} | 分块大小: {split_size} | 重叠大小: {chunk_overlap}")
        
        
    def _connect_milvus(self):
        """统一管理Milvus连接（原__init__中的连接逻辑）"""
        self.connection_args = {
            "host": os.getenv("MILVUS_HOST", "localhost"),
            "port": os.getenv("MILVUS_PORT", "19530"),
            "user": "",
            "password": "",
            "secure": False
        }
        try:
            connections.connect(**self.connection_args)
            logger.info(f"Milvus连接成功 | 地址: {self.connection_args['host']}:{self.connection_args['port']}")
        except Exception as e:
            logger.error(f"Milvus连接失败 | 参数: {self.connection_args} | 错误: {str(e)}", exc_info=True)
            raise
        
    def _create_markdown_splitter(self):
        """独立拆分器创建方法（原batch_process_markdown中的嵌套类）"""
        print("Creating markdown splitter")
        headers_to_split_on = [("#", "Header_1"), ("##", "Header_2"), ("###", "Header_3")]
        code_block_pattern = re.compile(r'```(?:[^`]|`[^`]|``[^`])*```', re.DOTALL)
        link_pattern = re.compile(r'\$[^\$]*\$\$[^\$]*\$')  # 更精确的数学公式匹配（避免贪婪）

        class EnhancedMarkdownSplitter(MarkdownHeaderTextSplitter):
            def split_text(self, text: str) -> List[Document]:
                # 合并连续空白行，减少因空行导致的过度拆分
                text = re.sub(r'\n{2,}', '\n\n', text.strip())
                
                # 提取代码块并替换为占位符
                code_blocks = code_block_pattern.findall(text)
                # text = code_block_pattern.sub("__CODE_BLOCK__", text)
                placeholder_map = {f"__CODE_BLOCK_{i}__": block for i, block in enumerate(code_blocks)}
                for placeholder, block in placeholder_map.items():
                    text = text.replace(block, placeholder, 1)
                
                # 调用父类方法进行标题拆分
                docs = super().split_text(text)
                
                # 修改标题与内容的组合方式
                processed_docs = []
                for doc in docs:
                    content = doc.page_content
                    # 还原代码块占位符
                    for placeholder, block in placeholder_map.items():
                        content = content.replace(placeholder, block, 1)
                    # 收集标题路径（最多到 H5）
                    full_title = []
                    for level in ['Header_1', 'Header_2', 'Header_3', 'Header_4', 'Header_5']:
                        header = doc.metadata.get(level)
                        if header:
                            full_title.append(header)
                    
                    
                    # 确保内容不为空时才添加标题
                    # if full_title and content.strip():
                    #     doc.page_content = " > ".join(full_title) + "\n\n" + content
                    # elif content.strip():
                    #     doc.page_content = content
                    # else:
                    #     continue  # 跳过空内容文档
                    if not content.strip():
                        continue  # 跳过无内容的文档
                    
                    if full_title and isinstance(full_title, (list, tuple)):
                        # 确保标题和内容正确分隔
                        title_part = " > ".join(full_title)
                        # 避免内容仅包含标题
                        if content.strip() != title_part:
                            doc.page_content = f"{title_part}\n{content}"
                        else:
                            doc.page_content = content  # 仅保留内容，避免重复
                    else:
                        doc.page_content = content
                    
                    doc.page_content = link_pattern.sub(r'<link>\g<0></link>', doc.page_content)
                    processed_docs.append(doc)
                return processed_docs
        
        return EnhancedMarkdownSplitter(headers_to_split_on=headers_to_split_on, return_each_line=False)
        
        
    """知识库处理统一入口(简化原逻辑)
    - 前提条件 :
        - folder_path 为存在的文件夹(函数内部已检查，否则抛 FileNotFoundError )。
        - collection_name 对应Milvus集合未被占用(或允许覆盖，因 _setup_milvus_collection 会删除同名集合)。
    - 后续条件 :
        - 返回 {"status": "success", "processed_files": N} ，其中 N 为处理的Markdown文件数。"""
    def process_collection(self, folder_path: str, collection_name: str):
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"文件夹路径不存在: {folder_path}")

        self.folder_path = folder_path  # 新增：将传入的folder_path赋值给实例变量

        # 启动监控（保持原逻辑）
        watcher = self.start_monitoring(folder_path)
        
        # 处理文件 -> 生成向量库（流程清晰化）
        chunks = self._batch_process_files(folder_path)
        self._create_vector_db(chunks, collection_name)
        
        return {"status": "success", "processed_files": len(chunks)}
        
    """批量处理文件夹内所有Markdown文件(原batch_ssprocess_markdown核心逻辑)
    - 前提条件 :
        - folder_path 存在且包含至少一个 .md 文件(否则 md_files 为空)。
    - 后续条件 :
        - 返回 List[Document] ，每个 Document 包含 chunk_id 、 processing_time 等元数据。
    """
    def _batch_process_files(self, folder_path: str) -> List[Document]:
        """批量处理文件夹内所有Markdown文件（原batch_process_markdown核心逻辑）"""
        md_files = [os.path.join(root, f) for root, _, files in os.walk(folder_path) 
                    for f in files if f.endswith(".md")]
        
        logger.info(f"发现 {len(md_files)} 个Markdown文件待处理")
        all_chunks = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self._process_single_file, path): path for path in md_files}
            with tqdm(total=len(futures), desc="处理文件中", unit="file") as pbar:
                for future in as_completed(futures):
                    file_path = futures[future]
                    try:
                        chunks = future.result()
                        all_chunks.extend(chunks)
                    except Exception as e:
                        logger.error(f"文件处理异常: {file_path}\n{str(e)}")
                    finally:
                        pbar.update(1)
            
        for idx, chunk in enumerate(all_chunks):
            chunk.metadata.update({
                "chunk_id": idx + 1,
                "processing_time": datetime.now().isoformat(),
                "vector_dim": 1024  # 与Milvus维度一致
            })
        
        logger.info(f"文件批量处理完成 | 总块数: {len(all_chunks)}")
        
        print(f"\n共生成 {len(all_chunks)} 个文本块")

        return all_chunks
    
    """处理单个文件核心逻辑(原process_single_file简化版)
    - 前提条件 :
        - file_path 为有效 .md 文件路径，且可读(否则 open 会抛异常)。
    - 后续条件 :
        - 返回拆分后的文本块列表，若原块过长(>1000字符)或含代码块( <code> )，会进一步拆分为子块。
    """
    
    def _process_single_file(self, file_path: str) -> List[Document]:
        # 处理单个文件核心逻辑（原process_single_file简化版）
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding = detect(raw_data)['encoding'] or 'utf-8'
            if encoding != 'utf-8':
                logger.warning(f"文件 {file_path} 编码检测为 {encoding}，可能存在乱码风险")
            md_content = raw_data.decode(encoding)
        
        # 计算文件哈希值
        # file_hash = hashlib.sha256(raw_data).hexdigest()
        filename = os.path.basename(file_path)

        # 删除基于文件路径的title变量
        # title = (os.path.dirname(file_path) + '\' + os.path.basename(file_path).replace('.md', ''))[:50]
        
        # 生成基础分块（保留原Markdown拆分逻辑）
        # 计算相对于知识库根目录的路径
        relative_path = os.path.relpath(file_path, self.folder_path)
        
        # 修改分块生成逻辑，从metadata提取标题
        chunks = []
        for doc in self.markdown_splitter.split_text(md_content):
            # 从metadata中提取标题路径
            full_title = []
            for level in ['Header_1', 'Header_2', 'Header_3', 'Header_4', 'Header_5']:
                header = doc.metadata.get(level)
                if header:
                    full_title.append(header)
            # 使用文档层级标题作为document_title
            document_title = " > ".join(full_title) if full_title else filename.replace('.md', '')
            # source仅保留文件名
            chunks.append(Document(
                page_content=doc.page_content,
                metadata={
                    **doc.metadata,
                    "document_title": document_title,
                    "source": filename  # 仅保留文件名
                }
            ))
        
        # 进一步拆分过大或含代码块的分块
        processed_chunks = [] 
        for chunk in chunks: 
            # 新增：过滤纯标题块（只包含标题路径而无实际内容）
            cleaned_content = chunk.page_content.strip()
            title = chunk.metadata.get("document_title", "")
            
            # 统一过滤无效分块
            if not cleaned_content:
                logger.warning(f"过滤空内容分块 | 文件: {file_path}")
                continue
            if cleaned_content == title:
                logger.warning(f"过滤纯标题分块: {cleaned_content[:100]}... | 文件: {file_path}")
                continue
            
            # 原有分块逻辑
            if len(chunk.page_content) > 1000 or '<code>' in chunk.page_content: 
                split_size = 1500 if '<code>' in chunk.page_content else 1000 
                sub_chunks = RecursiveCharacterTextSplitter( 
                    chunk_size=split_size, 
                    chunk_overlap=200, 
                    # 优先按段落(双换行)和中文句末标点分割，最后才按单换行分割
                    separators=["\n\n"] 
                ).split_text(chunk.page_content) 
                processed_chunks.extend(Document(page_content=sc, metadata=chunk.metadata) for sc in sub_chunks) 
            else: 
                processed_chunks.append(chunk)
        
        return processed_chunks

    
    # def _split_markdown(self, content: str) -> List[Document]:
    #     """Markdown内容拆分专用方法（原嵌套类逻辑提取）"""
    #     return self.markdown_splitter.split_text(content)

    """Milvus集合初始化(合并原clear_existing_collection和create_collection)
    - 前提条件 :
        - Milvus连接已建立(通过 _connect_milvus )。
    - 后续条件 :   
        - 创建/覆盖集合，字段包括 id (主键)、 vector (1024维向量)、 document_title (≤256字符)、 source (≤256字符)、 content (≤65535字符)。"""

    
    def _setup_milvus_collection(self, collection_name: str):
        """Milvus集合初始化（合并原clear_existing_collection和create_collection）"""
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
        
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
            FieldSchema(name="document_title", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535)  # 简化字段名（根据实际需求调整）
        ]
        
        schema = CollectionSchema(fields, "Document collection schema")
        collection = Collection(collection_name, schema)
        collection.create_index("vector", self.index_params)
        logger.info(f"成功初始化集合: {collection_name}")
    
    """向量数据库生成专用方法(原create_vector_db简化版)
    - 前提条件 :
        - chunks 为有效的 Document 列表(否则抛 ValueError )。
        - _setup_milvus_collection 已调用，集合已初始化。
    - 后续条件 :
        - 将 chunks 插入Milvus集合，生成向量数据库。
    """
    def _create_vector_db(self, chunks: List[Document], collection_name: str):
        """向量数据库生成专用方法（原create_vector_db简化版）"""
        self._setup_milvus_collection(collection_name)
        
        batch_size = 100
        with tqdm(total=len(chunks), desc="生成向量数据库", unit="chunk") as pbar:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i+batch_size]
                try:
                    # 新增：打印入库的文档块信息
                    for idx, chunk in enumerate(batch):
                        logger.info(f"入库文档块 {i+idx+1}/{len(chunks)} | 标题: {chunk.metadata.get('document_title', '无标题')} | 内容预览: {chunk.page_content}")
                        # print(f"入库文档块 {i+idx+1}/{len(chunks)} | 内容: {chunk.page_content[:200]}...")
                    
                    # 确保每个文档包含所有字段
                    for chunk in batch:
                        chunk.metadata.setdefault('document_title', '无标题')
                        chunk.metadata.setdefault('source', '未知来源')
                        chunk.metadata.setdefault('content', chunk.page_content)
                    
                    # 截断元数据字段长度
                    for chunk in batch:
                        if 'document_title' in chunk.metadata and len(chunk.metadata['document_title']) > 256:
                            logger.warning(f"元数据截断 | 文档标题: {chunk.metadata['document_title']}")
                            chunk.metadata['document_title'] = chunk.metadata['document_title'][:256]
                    
                    vector_db = Milvus.from_documents(
                        documents=batch,
                        embedding=self.embeddings,
                        connection_args=self.connection_args,
                        collection_name=collection_name,
                        index_params=self.index_params
                    )
                    logger.debug(f"向量库初始化 | 批次: {i//batch_size+1} | 文档数: {len(batch)}")
                    pbar.update(len(batch))
                except Exception as e:
                    logger.error(f"向量库批次处理失败 | 批次: {i//batch_size+1} | 错误: {str(e)}", exc_info=True)
                    raise
        
        print("向量数据库创建成功")
        logger.info(f"向量库创建完成 | 集合: {collection_name} | 总块数: {len(chunks)}")
        
    def delete_knowledge_base(self, collection_name: str):
        """删除指定知识库（集合）
        - 与关系型数据库删除操作对应
        """
        if not utility.has_collection(collection_name):
            logger.warning(f"集合 {collection_name} 不存在，无需删除")
            return {"status": "skipped", "message": "集合不存在"}
        
        try:
            utility.drop_collection(collection_name)
            logger.info(f"成功删除集合: {collection_name}")
            return {"status": "success", "message": "集合删除完成"}
        except Exception as e:
            logger.error(f"集合删除失败 | 集合名: {collection_name} | 错误: {str(e)}", exc_info=True)
            raise

    def start_monitoring(self, folder_path: str):
        """文件监控启动（保持原逻辑）"""
        watcher = FileWatcher(self, folder_path)
        watcher.start()
        return watcher
