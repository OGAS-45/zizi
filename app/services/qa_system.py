from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus
from pymilvus import connections
import requests
from utils.version_info import get_version_info
import os
from dotenv import load_dotenv
import logging
import time

class QASystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 初始化逻辑移到 __init__
        return cls._instance

    def __init__(self): 
        if hasattr(self, 'initialized'):  
            # // 避免重复初始化
            return
        self.initialized = True

        load_dotenv() 
        # // 加载环境变量逻辑保留
        version = get_version_info()
        print(f"\n🔖 JARVIS知识库系统 v{version['version']}")
        print(f"🕒 最后更新: {version['update_date']}\n")

        # 记录模型加载开始时间
        start_time = time.time()
        self.embeddings = HuggingFaceEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL_PATH", "./models/bge-large-zh-v1.5"),
            model_kwargs={'device': 'cuda'},
            encode_kwargs={
                'normalize_embeddings': True,
                'batch_size':128,  # 根据GPU内存调整
                'convert_to_tensor': True,
                'device': 'cuda'
            }
        )
        # 输出加载耗时
        print(f"✨ 嵌入模型加载完成，耗时 {time.time() - start_time:.2f} 秒")

        connections.connect(
            host=os.getenv("MILVUS_HOST", "localhost"),
            port=os.getenv("MILVUS_PORT", "19530")
        )
        
        
        # 定义不同知识库的集合名称和文本字段
        self.collections = {
            'robot': {
                'name': 'robot',
                'text_field': 'content'
            },
            'mvp': {
                'name': 'mvp',
                'text_field': 'content'
            },
            # 未来添加的知识库配置
            'vision': {  # 对应前端value="vision"
                'name': 'vision',  # 实际Milvus集合名称
                'text_field': 'content'  # 文本字段名
            },
            'robotbody': {  # 对应前端value="vision"
                'name': 'robotbody',  # 实际Milvus集合名称
                'text_field': 'content'  # 文本字段名
            }
        }
        
    def query_local_db(self, query, top_k=3, collection_type='robot'):
        start_time = time.time()
        """支持按知识库类型查询"""
        collection_info = self.collections.get(collection_type, self.collections['robot'])
        

        db = Milvus(
            embedding_function=self.embeddings,
            collection_name=collection_info['name'],
            connection_args={
                "host": os.getenv("MILVUS_HOST", "localhost"),
                "port": os.getenv("MILVUS_PORT", "19530"),
                "user": "",
                "password": ""
            },
            # 添加索引参数
            index_params=os.getenv("INDEX_PARAMS", {"metric_type": "L2","index_type": "IVF_FLAT","params": {"nlist": 1024}}),
            # 明确指定文档内容字段
            text_field=collection_info['text_field']
        )
    
        # 生成查询向量
        search_params = {"metric_type": "L2", "params": {"nprobe": 30}}
        
        # 执行查询
        all_docs = db.similarity_search_with_score(
            query,
            k=top_k,
            search_params=search_params
        )

        if len(all_docs) > 1:
            # 计算前两个文档的平均距离
            print(f"原始搜索结果（距离）: {[d[1] for d in all_docs]}")
            avg_top2 = sum(d[1] for d in all_docs[:2]) / 2
            # 设置距离阈值为前两个平均距离的1.5倍
            threshold = avg_top2 * 0.8
            # 筛选文档：距离小于阈值
            docs = [d for d in all_docs if d[1] >= threshold]
            # 动态更新top_k值为筛选后的文档数
            print(f"筛选后结果（距离）: {[d[1] for d in docs]}")
            top_k = min(len(docs), top_k)
            docs = docs[:top_k]
        else:
            docs = all_docs[:top_k]
            top_k = len(docs)
        
        # 处理查询结果
        results = []
        for doc in docs:
            metadata = doc[0].metadata or {}
            content = doc[0].page_content
            
            # 将代码块转换为Markdown格式
            if '<code>' in content:
                content = content.replace('<code>', '```').replace('</code>', '```')
            
            # 将换行符转换为Markdown换行
            content = content.replace('\n', '  \n')
            
            results.append({
                'title': metadata.get('document_title', '未命名文档'),
                'source': metadata.get('source', '未知来源'),
                'content': content
            })
        print(f"向量搜索耗时：{time.time() - start_time:.2f}s")
        return results
    
    def query_llm_server(self, query, context, temperature=0.7):
        llm_start = time.time()
        # 将context中的内容提取为字符串
        # context_str = " ".join([item['content'] for item in context]).replace(chr(10), ' ')
        context_str = " ".join(item['content'] for item in context).replace('\n', ' ')  # 直接遍历生成器
        
        # print(f"传递给LLM的上下文: {context}")
        # print(f"传递给LLM的遍历后的上下文: {context_str}")
        
        messages = [
            {"role": "system", "content": "/no_think你是华睿科技技术支持部门的知识库助手JARVIS，负责根据知识库中返回的信息，提供专业、清晰、简练的回答。回答内容应基于知识库中的具体内容，不添加与文档无关的信息，不提及任何文档中未出现的人名。如果结果中包含链接或图片，如<img src='https://support' alt='示例图片'>，请原样返回。如果问题与知识库无关，或涉及推测、未收录内容，需说明知识库中未找到相关信息。对于涉及政治、军事、民族、宗教等敏感内容的问题，或不在知识库覆盖范围的，统一回复：“抱歉，该问题超出我的知识范围。请重新输入您的问题”。同时，JARVIS应根据问题的性质灵活调整回答结构，例如使用分点说明、步骤化解释、代码示例、逻辑推导等形式，清晰简洁的说明。"},
            {"role": "user", "content": f"问题: {query},知识库搜索到的上下文: {context_str}"}
        ]
        try:
            response = requests.post(
                os.getenv("LLM_SERVER_URL", "http://10.55.136.170:7000") + "/v1/chat/completions",
                json={
                    "model": os.getenv("LLM_MODEL_NAME"),
                    "messages": messages,
                    "temperature": temperature
                },
                timeout=30
            )
            print(f"LLM调用耗时：{time.time() - llm_start:.2f}s")
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"请求失败: {str(e)}"