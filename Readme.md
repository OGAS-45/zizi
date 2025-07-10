

# ZIZI 智能知识库问答系统

## 项目简介
ZIZI 是一个基于向量数据库和大语言模型的智能知识库问答系统，能够帮助用户高效管理和查询各类技术文档。系统支持自然语言查询、多知识库管理、自动SQL生成等功能，适用于企业内部知识管理、技术支持和智能问答场景。

## ✨ 核心功能

- **智能问答**：结合向量搜索和LLM技术，提供精准的自然语言回答
- **多知识库管理**：支持创建、删除和切换多个独立知识库
- **权限控制**：基于角色的访问控制(RBAC)，区分管理员和操作员权限
- **SQL自动生成**：将自然语言查询转换为SQL语句，直接查询数据库
- **批量处理**：支持大批量文档导入和向量化处理
- **实时监控**：文件系统监控，自动同步新增文档
- **Web界面**：直观的管理界面，方便非技术人员操作

## 🚀 技术栈

- **后端框架**：FastAPI
- **向量数据库**：Milvus
- **嵌入模型**：HuggingFace BGE-Large-zh
- **前端技术**：HTML, CSS, JavaScript
- **数据库**：SQLite, MySQL
- **部署**：Uvicorn

## 🔧 安装步骤

### 前提条件
- Python 3.8+ 
- Milvus 2.2.0+ 
- MySQL (可选)

### 安装方法

1. 克隆仓库
```bash
git clone https://github.com/yourusername/jarvis-knowledge-base.git
cd jarvis-knowledge-base
```

2. 创建虚拟环境并激活
```bash
python -m venv venv
# Windows
env\Scripts\activate
# Linux/MacOS
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
创建`.env`文件，配置以下参数：
```
MILVUS_HOST=localhost
MILVUS_PORT=19530
LLM_SERVER_URL=http://10.55.136.170:7000
LLM_MODEL_NAME=your_model_name
KB_PATH=./markdown_files
EMBEDDING_MODEL_PATH=./models/bge-large-zh-v1.5
```

5. 启动服务
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

6. 访问系统
打开浏览器访问: http://localhost:8000

## 📖 使用指南

### 知识库管理
1. 登录系统（默认管理员账号: admin/zizi@2025）
2. 点击"创建知识库"，输入名称和标识符
3. 上传Markdown文档或指定文档文件夹路径
4. 点击"向量化"按钮处理文档

### 智能查询
1. 在首页输入框中输入问题
2. 选择目标知识库
3. 点击"提问"获取答案
4. 查看相关文档来源和相似度评分

### SQL生成（高级功能）
1. 访问SQL查询页面
2. 输入自然语言问题
3. 系统自动生成并执行SQL查询
4. 获取格式化的查询结果

## 📁 项目结构

```
├── app/                  # 主应用目录
│   ├── data/             # 数据模型和存储
│   ├── routes/           # API路由
│   ├── services/         # 业务逻辑
│   ├── static/           # 静态资源
│   ├── templates/        # HTML模板
│   └── utils/            # 工具函数
├── logs/                 # 日志文件
├── milvus_data/          # Milvus数据目录
├── test/                 # 测试文件
└── utils/                # 通用工具
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开Pull Request

## 📄 许可证
本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式
- 项目维护者: [OGAS-45](https://github.com/OGAS-45)
- 项目地址: https://github.com/OGAS-45/zizi

---
如果觉得这个项目对你有帮助，请给它一个 ⭐️ 支持一下！
        
