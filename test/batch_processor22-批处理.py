import asyncio
import json
import time
from typing import List, Dict
from fastapi import FastAPI, Request, HTTPException
import redis
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fastapi.responses import JSONResponse
from pymilvus import connections
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus
import requests
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# 初始化FastAPI和Redis
app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# 请求和响应模型
class QueryRequest(BaseModel):
    question: str
    top_k: int = 3
    temperature: float = 0.7

class BatchResponse(BaseModel):
    request_id: str
    answer: str
    contexts: List[Dict]
    status: str



# 添加监控端点
# 替换MockQASystem为真实QASystem
# 在RealQASystem类中添加以下方法
class RealQASystem:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="./bge-large-zh-v1.5",
            model_kwargs={'device': 'cuda'},
            encode_kwargs={
                'normalize_embeddings': True,
                'batch_size': 128,
                'convert_to_tensor': True,
                'device': 'cuda'
            }
        )
        connections.connect(host=os.getenv("MILVUS_HOST", "localhost"), port=os.getenv("MILVUS_PORT", "19530"))
        self.db = Milvus(
            embedding_function=self.embeddings,
            collection_name="doc_vectors",
            connection_args={
                "host": os.getenv("MILVUS_HOST", "localhost"),
                "port": os.getenv("MILVUS_PORT", "19530"),
                "secure": False
            },
            index_params=os.getenv("INDEX_PARAMS", {"metric_type": "L2","index_type": "IVF_FLAT","params": {"nlist": 1024}})
        )
        self.batch_history = []
        self.request_count = 0
        self.batch_count = 0
    
    def get_gpu_status(self):
        """获取GPU状态信息"""
        try:
            import torch
            if torch.cuda.is_available():
                return {
                    "gpu_usage": torch.cuda.memory_allocated(0) / torch.cuda.max_memory_allocated(0),
                    "gpu_memory": f"{torch.cuda.memory_allocated(0)/1024**2:.2f}MB / {torch.cuda.max_memory_allocated(0)/1024**2:.2f}MB"
                }
        except:
            return {"error": "GPU信息获取失败"}
        return {"status": "无GPU可用"}

    def process_batch(self, batch: List[QueryRequest]) -> List[Dict]:
        """实际处理批量的问答请求"""
        batch_start = time.time()
        batch_size = len(batch)
        self.request_count += batch_size
        
        print(f"\n{'='*50}")
        print(f"开始处理批次 #{self.batch_count + 1} (共{batch_size}个请求)")
        print(f"累计已处理请求数: {self.request_count}")
        
        # 获取GPU状态
        gpu_status = self.get_gpu_status()
        print(f"GPU状态: {gpu_status}")
        
        batch_results = []
        for req in batch:
            start_time = time.time()
            
            # 1. 向量搜索阶段
            vector_start = time.time()
            context = self.query_local_db(req.question, req.top_k)
            vector_time = time.time() - vector_start
            
            # 2. LLM调用阶段
            llm_start = time.time()
            answer = self.query_llm_server(req.question, context, req.temperature)
            llm_time = time.time() - llm_start
            
            batch_results.append({
                "request_id": req.question[:8] + str(int(time.time())),
                "answer": answer,
                "contexts": context,
                "status": "completed",
                "timings": {
                    "vector_search": vector_time,
                    "llm_processing": llm_time,
                    "total": time.time() - start_time
                }
            })
        batch_time = time.time() - batch_start
        print(f"\n批次 #{self.batch_count + 1} 处理完成")
        print(f"总耗时: {batch_time:.2f}s | 平均每个请求: {batch_time/batch_size:.2f}s")
        print(f"GPU内存使用: {gpu_status.get('gpu_memory', 'N/A')}")
        print('='*50)
        
        self.batch_count += 1  # 确保在最后才增加批次计数
        return batch_results
    
    def query_local_db(self, query, top_k=3):
         # 生成查询向量
        query_vector = self.embeddings.embed_query(query)
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        
        # 执行查询
        all_docs = self.db.similarity_search_with_score(
            query,
            k=top_k,
            search_params=search_params
        )

        if len(all_docs) > 1:
            # 计算前两个文档的平均距离
            avg_top2 = sum(d[1] for d in all_docs[:2]) / 2
            # 设置距离阈值为前两个平均距离的1.5倍
            threshold = avg_top2 * 1.5
            # 筛选文档：距离小于阈值
            docs = [d for d in all_docs if d[1] <= threshold]
            # 动态更新top_k值为筛选后的文档数
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
        
        return results

    
    def query_llm_server(self, query, context, temperature=0.7):
         # 将context中的内容提取为字符串
        context_str = " ".join([item['content'] for item in context]).replace(chr(10), ' ')
        
        messages = [
            {"role": "system", "content": "你是华睿科技公司技术支持部门的知识库助手JARVIS,使用large模型，请根据知识库中搜索返回的相关信息简洁、专业地回答问题。如果返回的结果和问题不符说明知识库缺失，请严谨取舍，若缺失请明确告知用户，并建议其联系技术支持以获取帮助。"},
            {"role": "user", "content": f"问题: {query}知识库搜索到的上下文: {context_str}"}
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
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"请求失败: {str(e)}"


# 替换全局QASystem实例
qa_system = RealQASystem()

# 修改批处理监控端点
@app.get("/batch_monitor")
async def get_batch_monitor():
    """获取带性能指标的批处理监控信息"""
    return {
        "batch_count": qa_system.batch_count,
        "performance_metrics": {
            "avg_vector_time": sum(
                b.get("avg_vector_time", 0) 
                for b in qa_system.batch_history
            ) / len(qa_system.batch_history) if qa_system.batch_history else 0,
            "avg_llm_time": sum(
                b.get("avg_llm_time", 0)
                for b in qa_system.batch_history
            ) / len(qa_system.batch_history) if qa_system.batch_history else 0
        },
        "batch_history": qa_system.batch_history
    }

# 全局变量
BATCH_INTERVAL = 5  # 批处理间隔(秒)
BATCH_SIZE = 5        # 每批处理的最大请求数
executor = ThreadPoolExecutor(max_workers=4)

# 批处理任务
from contextlib import asynccontextmanager

# 替换原有的startup_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    asyncio.create_task(batch_processor())
    yield
    # 关闭时
    executor.shutdown()

app = FastAPI(lifespan=lifespan)  # 修改FastAPI初始化

# 删除原有的startup_event装饰器
# @app.on_event("startup")  # 这行删除
# async def startup_event():
#     asyncio.create_task(batch_processor())

# API端点
@app.post("/ask")
async def ask_question(request: Request):
    """提交问题到批处理队列"""
    try:
        # 获取原始请求体并解析JSON
        body = await request.json()
        
        # 验证请求数据
        query_request = QueryRequest(**body)
        
        # 生成唯一请求ID（包含时间戳和问题哈希）
        request_id = f"req_{int(time.time())}_{hash(query_request.question)}"
        
        # 将请求存入Redis队列（包含request_id）
        redis_client.rpush('request_queue', json.dumps({
            **query_request.model_dump(),  # 修改这里：dict() -> model_dump()
            "request_id": request_id
        }))
        
        return {"request_id": request_id, "status": "queued"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 修改批处理任务
async def batch_processor():
    while True:
        print(f"\n等待新请求... (当前时间: {datetime.now().strftime('%H:%M:%S')})")
        await asyncio.sleep(BATCH_INTERVAL)
        
        # 从Redis获取待处理请求
        pending_requests = []
        while len(pending_requests) < BATCH_SIZE:
            request_data = redis_client.lpop('request_queue')
            if not request_data:
                break
            data = json.loads(request_data)
            pending_requests.append((data["request_id"], QueryRequest(**data)))
        
        if pending_requests:
            print(f"准备处理 {len(pending_requests)} 个请求...")
            # 提取纯请求对象用于处理
            requests_to_process = [req for _, req in pending_requests]
            
            # 使用线程池处理批量请求
            future = executor.submit(qa_system.process_batch, requests_to_process)
            batch_results = await asyncio.wrap_future(future)
            
            # 存储结果到Redis（使用原始request_id）
            for (request_id, _), result in zip(pending_requests, batch_results):
                redis_client.set(request_id, json.dumps({
                    **result,
                    "request_id": request_id  # 确保ID一致
                }))

@app.get("/result/{request_id}")
async def get_result(request_id: str):
    """获取处理结果"""
    result = redis_client.get(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return json.loads(result)

# 修改全局变量
BATCH_INTERVAL = 1.0  # 缩短批处理间隔
BATCH_SIZE = 51       # 将批处理大小改为10
executor = ThreadPoolExecutor(max_workers=4)

# 添加测试端点
@app.post("/test_batch")
async def test_batch():
    """测试批量处理50个请求"""
    test_questions = [
        {"question": f"测试问题{i}", "top_k": 3, "temperature": 0.7}
        for i in range(1, 51)
    ]
    
    start_time = time.time()
    
    # 将测试请求加入队列
    for question in test_questions:
        redis_client.rpush('request_queue', json.dumps({
            **question,
            "request_id": f"test_{int(time.time())}_{hash(question['question'])}"
        }))
    
    # 等待所有请求完成
    while True:
        completed = all(
            redis_client.get(f"test_{int(start_time)}_{hash(f'测试问题{i}')}") 
            for i in range(1, 51)
        )
        if completed:
            break
        await asyncio.sleep(0.5)
    
    total_time = time.time() - start_time
    
    # 收集结果
    results = []
    for i in range(1, 51):
        result = redis_client.get(f"test_{int(start_time)}_{hash(f'测试问题{i}')}")
        results.append(json.loads(result))
    
    return {
        "total_time": total_time,
        "avg_time_per_request": total_time / 50,
        "results": results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)