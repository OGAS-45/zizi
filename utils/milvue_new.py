import time
from pymilvus import connections, utility, FieldSchema, CollectionSchema, Collection, DataType
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus
import json
import requests
import os
from dotenv import load_dotenv
from pymilvus import MilvusClient
from dotenv import load_dotenv
import os



# client = MilvusClient(
#     uri="http://" + os.getenv("MILVUS_HOST", os.getenv("MILVUS_HOST", "localhost"))  + ":" + os.getenv("MILVUS_PORT", "19530"),
#     token="root:Milvus"
# )

class MilvusManager:
    def __init__(self,connection_args, knowledge_bases):
        self.connection_args = connection_args
        self.knowledge_bases = knowledge_bases
        
    def create_collection(self, collection_name,text_field="content"):
        """创建新的集合"""
        try:
            connections.connect(**self.connection_args)
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
            
            self.knowledge_bases[collection_name] = {
                "text_field": text_field
            }
            
            self.fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
                FieldSchema(name="document_title", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name=self.knowledge_bases[os.path.splitext(collection_name)[0]]['text_field'], dtype=DataType.VARCHAR, max_length=65535)
            ]
            
            schema = CollectionSchema(self.fields, "Document collection schema")
            collection = Collection(collection_name, schema)
            
            index_params = os.getenv("INDEX_PARAMS", {"metric_type": "L2","index_type": "IVF_FLAT","params": {"nlist": 1024}})
            collection.create_index("vector", index_params)
            print(f"成功创建集合: {collection_name}")
        except Exception as e:
            print(f"创建集合失败: {str(e)}")
            raise
        
# 测试脚本
if __name__ == "__main__":
    # 定义连接参数
    connection_args = {
        "host": "localhost",
        "port": "19530"
    }
    
    # 定义知识库
    knowledge_bases = {
        "test": {
            "text_field": "content"
        },
        "testppp": {
            "text_field": "content"
        }
    }
    
    
    
    # 建立连接（新增代码）
    connections.connect(**connection_args)
    
    # 创建 MilvusManager 实例
    client = MilvusManager(connection_args, knowledge_bases)
    

    
    # 打印创建前的集合列表
    print("创建前的集合列表:")
    res = utility.list_collections()
    print(res)

    # 创建集合
    collection_name = "yyyyyy"
    client.create_collection(collection_name)
    
    # 打印创建后的集合列表
    print("创建后的集合列表:")
    res = utility.list_collections()
    print(res)