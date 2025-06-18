from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
import os
from dotenv import load_dotenv

def create_collection(collection_name):
    connections.connect(host="localhost", port=os.getenv("MILVUS_PORT", "19530"))
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535)
    ]
    
    schema = CollectionSchema(fields, description=f"{collection_name} collection")
    collection = Collection(name=collection_name, schema=schema)
    
    index_params = os.getenv("INDEX_PARAMS", {"metric_type": "L2","index_type": "IVF_FLAT","params": {"nlist": 1024}})
    collection.create_index("vector", index_params)

if __name__ == "__main__":
    create_collection("robot_knowledge")
    create_collection("mvp_knowledge")