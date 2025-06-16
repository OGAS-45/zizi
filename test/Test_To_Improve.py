import time
from pymilvus import connections
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus
import json
import requests
import os
from dotenv import load_dotenv

class QueryAnalyzer:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="./models/bge-large-zh-v1.5")
        connections.connect(host=os.getenv("MILVUS_HOST", "localhost"), port=os.getenv("MILVUS_PORT", "19530"))
        
        self.db = Milvus(
            embedding_function=self.embeddings,
            collection_name="doc_vectors",
            connection_args={
                "host": os.getenv("MILVUS_HOST", "localhost"),
                "port": os.getenv("MILVUS_PORT", "19530"),
                "secure": False
            },
            # 新增：指定文本字段
            text_field="content"
        )
    
    def analyze_query(self, query, top_k=3, temperature=0.7):
        """执行查询并返回详细分析结果"""
        print(f"\n{'='*50}")
        print(f"开始分析查询: '{query}'")
        print(f"参数: top_k={top_k}, temperature={temperature}")
        print('='*50)
        
        # 模型信息
        print("\n[模型信息]")
        print(f"- 嵌入模型: {self.embeddings.model_name}")
        print(f"- 模型参数: {self.embeddings.model_kwargs}")
        print(f"- 编码参数: {self.embeddings.encode_kwargs}")
        
        # 1. 向量搜索阶段
        vector_start = time.time()
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        
        print("\n[向量搜索阶段]")
        # 获取最近和最远文档
        all_docs = self.db.similarity_search_with_score(query, k=top_k, search_params=search_params)
        
        # print(all_docs)

        # 筛选
        if len(all_docs) > 1:
            # 计算前两个文档的平均距离
            avg_top2 = sum(d[1] for d in all_docs[:2]) / 2
            # 设置距离阈值为前两个平均距离的1.5倍
            threshold = avg_top2 * 1.5
            # 筛选文档：距离小于阈值
            docs = [d for d in all_docs if d[1] <= threshold]
            # 如果筛选后文档数超过top_k，取前top_k个
            docs = docs[:top_k] if len(docs) > top_k else docs
        else:
            docs = all_docs[:top_k]

        # 新增：获取最远文档的正确方法
        max_distance_doc = max(docs, key=lambda x: x[1])  # 按距离取最大值
        
        # 打印距离统计
        all_distances = [score for _, score in docs]
        print(f"\n[距离统计] 最小: {min(all_distances):.4f} | 最大: {max(all_distances):.4f} | 平均: {sum(all_distances)/len(all_distances):.4f}")
        print(f"[全库距离范围] 典型范围: 0.4-1.2 (L2距离)")
        vector_time = time.time() - vector_start
        
        # 新增：获取最远距离文档
        max_distance_doc = self.db.similarity_search_with_score(query, k=1, search_params=search_params, reverse=True)[0]
        
        contexts = []
        for i, (doc, score) in enumerate(docs):
            print(f"\n文档 {i+1}:")
            print(f"- 向量距离: {score:.6f}")
            print(f"- 相似度分数: {(1/(1+score)):.4f}")
            print(f"- 内容长度: {len(doc.page_content)} 字符")
            print(f"- 来源文件: {doc.metadata.get('source', '未知')}")
            print("- 内容预览:", doc.page_content)
            contexts.append(doc.page_content)
        

        # 新增：打印距离范围
        min_score = min(score for _, score in docs)
        print(f"\n[距离范围] 最近: {min_score:.4f} | 最远: {max_distance_doc[1]:.4f} | 跨度: {max_distance_doc[1]-min_score:.4f}")
        
        # 2. LLM调用阶段
        print("\n[LLM调用阶段]")
        llm_start = time.time()
        
        try:
            # 准备请求数据
            messages = [
                {
                    "role": "system", 
                    "content": "你是知识库助手JARVIS，请根据上下文专业地回答"
                },
                {
                    "role": "user",
                    "content": f"问题: {query}\n上下文: {' '.join(contexts)}"
                }
            ]
            
            # 网络请求开始时间
            # 添加上下文相关性检查
            relevant_contexts = []
            for doc, score in docs:
                if 1/(1+score) > 0.6:  # 相似度阈值设为0.6
                    relevant_contexts.append(doc.page_content)
            
            if not relevant_contexts:
                answer = "⚠️ 警告：未找到相关上下文，请检查知识库或调整查询"
                usage = {"total_tokens": 0}
            else:
                # 添加网络超时重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        network_start = time.time()
                        response = requests.post(
                            os.getenv("LLM_SERVER_URL", "http://10.55.136.191:7000") + "/v1/chat/completions",
                            json={
                                "model": os.getenv("LLM_MODEL_NAME", "Qwen2.5_7B"),
                                "messages": messages,
                                "temperature": temperature,
                                "max_tokens": 1024
                            },
                            timeout=60
                        )
                        network_time = time.time() - network_start
                        break
                    except requests.exceptions.Timeout:
                        if attempt == max_retries - 1:
                            raise
                        print(f"网络超时，正在重试({attempt + 1}/{max_retries})...")
                        time.sleep(1)
            
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            
            print("\n[LLM详细信息]")
            print(f"- 模型: " + os.getenv("LLM_MODEL_NAME", "Qwen2.5_7B"),)
            print(f"- 温度: {temperature}")
            print(f"- 实际使用token数: {usage.get('total_tokens', 'N/A')}")
            print(f"- 网络请求耗时: {network_time:.4f}秒")
            print("\n[LLM返回内容]")
            print(answer)  # 新增：打印大模型返回的内容
            
            # 新增：打印完整的API响应
            print("\n[完整API响应]")
            print(json.dumps(result, indent=2, ensure_ascii=False))

        except Exception as e:
            answer = f"LLM调用失败: {str(e)}"
            print(f"\n[LLM错误] {str(e)}")
        
        llm_time = time.time() - llm_start
        
        # 解释LLM处理时间
        print("\n[时间分析]")
        print(f"LLM处理时间({llm_time:.4f}秒) = 网络请求时间({network_time:.4f}秒) + 服务器处理时间({llm_time-network_time:.4f}秒)")
        
        # 汇总结果
        print("\n[性能指标]")
        print(f"- 向量搜索耗时: {vector_time:.4f}秒")
        print(f"- LLM处理耗时: {llm_time:.4f}秒 (网络: {network_time:.4f}秒)")
        print(f"- 总耗时: {vector_time + llm_time:.4f}秒")
        
        return {
            "query": query,
            "answer": answer,
            "timings": {
                "vector_search": vector_time,
                "llm_processing": llm_time,
                "network": network_time,
                "total": vector_time + llm_time
            },
            "usage": usage,
            "contexts": [{
                "content": doc.page_content,
                "distance": score,
                "similarity": 1/(1+score),
                "length": len(doc.page_content),
                "source": doc.metadata.get("source")
            } for doc, score in docs]
        }

if __name__ == "__main__":
    # 示例直接测试
    analyzer = QueryAnalyzer()
    llm_10_start = time.time()

    for i in range(50):
        test_result = analyzer.analyze_query(
            "地图未设置线宽，报8039起点邻接边行驶方向限制或线宽不可通行是什么原因?",
            top_k=5,
            temperature=0.3
        )

    llm_10_end = time.time() - llm_10_start

    print(f"10问题LLM处理时间({llm_10_end:.4f}秒)")

