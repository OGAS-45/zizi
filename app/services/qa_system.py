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
                "password": "",
                "secure": False
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
            threshold = avg_top2 * 1.5
            # 筛选文档：距离小于阈值
            docs = [d for d in all_docs if d[1] <= threshold]
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
            {"role": "system", "content": "/no_think你是华睿科技公司技术支持部门的知识库助手JARVIS,请根据知识库中搜索返回的相关信息简洁、专业地回答问题。如果返回的结果中有链接请务必原样展示，如果有img的标签也请返回如“<img src="'https://support'" alt="'示例图片'">”，和问题不符说明知识库缺失，请严谨取舍，若缺失请明确告知用户，并建议其联系技术支持以获取帮助。# 强制要求 -  仅回答与知识库内容直接相关的问题  -  当用户提问超出知识库范围（如：政治立场、军事机密、民族宗教敏感议题、任何未被知识库收录的推测性问题）时，立即拒绝回答-  当触发拒绝条件时，统一使用：“抱歉，该问题超出我的知识范围。请重新输入您的问题”"},
            {"role": "user", "content": f"问题: {query},知识库搜索到的上下文: {context_str}"}
        ]
        try:
            response = requests.post(
                os.getenv("LLM_SERVER_URL", "http://10.55.136.191:7000") + "/v1/chat/completions",
                json={
                    "model": os.getenv("LLM_MODEL_NAME", "Qwen2.5_7B"),
                    "messages": messages,
                    "temperature": temperature
                },
                timeout=30
            )
            print(f"LLM调用耗时：{time.time() - llm_start:.2f}s")
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"请求失败: {str(e)}"