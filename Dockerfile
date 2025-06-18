
# 设置Python版本（需与servercore镜像兼容）
# 原第3行修改
FROM python:3.9-windowsservercore-ltsc2019 

# 设置工作目录
WORKDIR /

# 复制依赖文件（离线环境需提前准备requirements.txt及wheel包到项目根目录/wheels）
COPY requirements.txt .
COPY wheels/ ./wheels

# 安装依赖（离线模式使用本地wheel包）
RUN pip install --no-index --find-links=./wheels -r requirements.txt

# 复制项目代码（根据实际结构调整）
COPY app/ ./app
COPY models/ ./models  
# 假设模型文件在models目录下
COPY markdown_files/ ./markdown_files  
# 假设知识库文件在markdown_files目录下

# 配置环境变量（根据实际需要调整）
ENV MILVUS_HOST=localhost
ENV MILVUS_PORT=19530
ENV LLM_SERVER_URL=http://localhost:7000
ENV PYTHONPATH "${PYTHONPATH}:/app"

# 暴露应用端口（与uvicorn配置一致）
EXPOSE 8000

# 启动命令（使用uvicorn运行FastAPI应用）
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]