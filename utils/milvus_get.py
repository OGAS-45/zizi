from pymilvus import MilvusClient
from dotenv import load_dotenv
import os
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, connections, utility

client = MilvusClient(
    uri="http://" + os.getenv("MILVUS_HOST", os.getenv("MILVUS_HOST", "localhost"))  + ":" + os.getenv("MILVUS_PORT", "19530"),
    token="root:Milvus"
)

# 查找某一个collection的字段
# res = client.query(
#     collection_name="doc_vectors",
#     filter = "",
#     output_fields=["content"],
#     limit = 100
# )

# 查看所有collection
res = client.list_collections()
print(res)

# 删除特定数据库
# res = client.drop_collection('yyyyyy')

# 增加特定数据库
# _________________________________________

# # 3.1. Create schema
# schema = MilvusClient.create_schema(
#     auto_id=False,
#     enable_dynamic_field=True,
# )

# # 3.2. Add fields to schema
# schema.add_field(field_name="my_id", datatype=DataType.INT64, is_primary=True)
# schema.add_field(field_name="my_vector", datatype=DataType.FLOAT_VECTOR, dim=5)
# schema.add_field(field_name="my_varchar", datatype=DataType.VARCHAR, max_length=512)

# # 3.3. Prepare index parameters
# index_params = client.prepare_index_params()

# # 3.4. Add indexes
# index_params.add_index(
#     field_name="my_id",
#     index_type="AUTOINDEX"
# )

# index_params.add_index(
#     field_name="my_vector", 
#     index_type="AUTOINDEX",
#     metric_type="COSINE"
# )

# res  = client.create_collection(
#     collection_name="dsa89",
#     schema=schema,
#     index_params=index_params
# )

# _________________________________________


res = client.list_collections()


# 查找某一个collection下的所有东西
# res = client.get(
#     collection_name="test_collection",
#     ids=[0,1,2,3],
# )

# 查找某一个collection的字段
# res = client.get(
#     collection_name="test_collection",
#     ids=[0,1,2,3],
#     output_fields=["text"]
# )



print(res)
