from datetime import datetime
import os
import tempfile
from pymilvus import utility, connections
import sys
from langchain_core.documents import Document
from pymilvus import Collection  # 补充导入

# 获取项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

# 现在可以使用相对导入
from app.utils.vector_db_operations import VectorDB_Operations  # 改为新类导入


def test_milvus_connection():
    """测试Milvus连接功能"""
    print("\n=== 测试 Milvus 连接功能 ===")
    processor = VectorDB_Operations()  # 改为新类实例化
    
    # 调用前检查连接状态
    before_connections = connections.list_connections()
    print(f"连接前已存在的连接: {before_connections}")
    
    # 触发连接（通过初始化自动调用 _connect_milvus）
    after_connections = connections.list_connections()
    print(f"连接后已存在的连接: {after_connections}")
    
    assert any("default" in conn for conn in after_connections), "Milvus连接失败"

# def test_markdown_splitter():
#     """测试Markdown拆分器功能"""
#     print("\n=== 测试 Markdown 拆分器功能 ===")
#     processor = DocumentProcessor()
#     test_md = """
# # 测试标题1
# ## 测试子标题1-1
# 这是一段普通文本
# """

#     print("测试代码块")

#     # 执行拆分
#     chunks = processor.markdown_splitter.split_text(test_md)
#     print(f"原始内容长度: {len(test_md)}")
#     print(f"拆分后得到块数: {len(chunks)}")
#     print("首块内容示例（前200字）:")
#     print(chunks[0].page_content[:200])

#     # 断言验证拆分结果（至少拆分为2块）
#     assert len(chunks) >= 2, "Markdown拆分器未正确工作"

def test_single_file_processing():
    """测试单个文件处理功能"""
    print("\n=== 测试 单个文件处理功能 ===")
    # 创建临时Markdown文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""
    # 测试文件
    ## 测试章节
    这是需要拆分的长文本内容，长度超过1000字。这里需要填充足够多的文字来测试分块逻辑：
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充...（约1500字）
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充...（约1500字）
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充...（约1500字）
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充...（约1500字）
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充\n
    
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充...（约1500字）
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充\n
    
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充...（约1500字）
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充\n
    
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充...（约1500字）
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充\n
    
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充...（约1500字）
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充\n
    
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充...（约1500字）
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充 重复文字填充重复文字填充重复文字填充
    """)
    temp_path = f.name
    processor = VectorDB_Operations()
    chunks = processor._process_single_file(temp_path)  # 改为新类实例化

    # 打印关键信息
    print(f"原始文件路径: {temp_path}")
    print(f"处理后得到块数: {len(chunks)}")
    print("首块元数据示例:")
    print(chunks[0].metadata)
    print("1块元数据示例:")
    print(chunks[1].metadata)
    print("2块元数据示例:")
    print(chunks[2].metadata)

    # 清理临时文件
    os.unlink(temp_path)
    assert len(chunks) >= 1, "单文件处理未生成有效分块"

def test_milvus_collection_setup():
    """测试Milvus集合初始化功能"""
    print("\n=== 测试 Milvus 集合初始化功能 ===")
    processor = VectorDB_Operations()  # 改为新类实例化
    test_collection = "test_collection_" + datetime.now().strftime("%Y%m%d%H%M%S")  # 唯一集合名
    # 初始化前检查集合状态
    before_exist = utility.has_collection(test_collection)
    print(f"集合 {test_collection} 初始化前存在状态: {before_exist}")

    # 触发集合初始化
    processor._setup_milvus_collection(test_collection)

    # 初始化后检查集合状态（通过Collection对象获取信息）
    collection = Collection(test_collection)
    after_exist = utility.has_collection(test_collection)
    after_info = collection.describe()  # 使用describe()替代get_collection_info
    print(f"集合 {test_collection} 初始化后存在状态: {after_exist}")
    print(f"集合字段数量: {len(after_info['fields'])}")  # 调整字段访问方式

    # 清理测试集合
    utility.drop_collection(test_collection)
    assert after_exist and len(after_info['fields']) == 5, "集合初始化失败"

def test_full_workflow():
    """测试完整知识库处理流程"""
    print("\n=== 测试 完整知识库处理流程 ===")
    # 使用项目中的实际测试文件夹（需确保该路径存在且包含Markdown文件）
    test_folder = os.path.join(project_root, "markdown_files", "test")  # 假设项目根目录已正确设置
    
    # 检查测试文件夹是否存在
    if not os.path.exists(test_folder):
        raise FileNotFoundError(f"测试文件夹不存在: {test_folder}，请先准备测试Markdown文件")

    processor = VectorDB_Operations()  # 改为新类实例化
    result = processor.process_collection(test_folder, "test_dududuj")  # 方法名调整

    # 打印执行结果
    print("完整流程执行结果:")
    print(result)
    print("最终Milvus集合列表（部分）:")
    print(utility.list_collections()[:])  # 显示前5个集合避免信息过长

    # 断言验证流程成功
    assert result["status"] == "success" and result["processed_files"] >= 1, "完整流程执行失败"
    
if __name__ == "__main__":
    # 按顺序执行所有测试
    test_milvus_connection()
    # test_markdown_splitter()
    test_single_file_processing()
    test_milvus_collection_setup()
    test_full_workflow()
    print("\n所有测试完成！")



# ### 脚本说明：
# 1. **功能覆盖**：从基础连接测试开始，逐步验证拆分器、单文件处理、集合操作到完整流程，符合“从简单到复杂”的测试要求。
# 2. **状态打印**：每个测试用例包含关键步骤的前后状态输出（如连接状态、集合存在性、分块数量等）。
# 3. **环境隔离**：使用临时文件/目录和唯一集合名（时间戳后缀），避免影响生产数据。
# 4. **断言验证**：每个测试用例包含关键逻辑的断言检查，确保功能正确性。

# ### 使用说明：
# 1. 确保已安装依赖：`pymilvus`, `langchain`, `chardet`, `tqdm`, `watchdog`。
# 2. 启动Milvus服务（默认localhost:19530）。
# 3. 执行脚本：
#    ```bash
#    python d:\Workplace\python\5.6zizi（文件同步）\app\utils\test_document_processor.py