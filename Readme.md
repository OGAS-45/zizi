



python -m app.main 进行打开和运行

查看数据库：

下载

pip install 

pip install  + 路径

pip download -i https://pypi.tuna.tsinghua.edu.cn/simple langchain==0.2.17 langchain-community==0.2.19 langsmith==0.1.112 -d ./wheels

pip download -i https://pypi.tuna.tsinghua.edu.cn/simple pynuml -d ./wheels

pip freeze > requirements.txt

pip list --format=freeze >requirement.txt



这样调整后文件监控服务将完全独立，可以通过 python -m app.file_monitor.core 单独运行，同时保持与文档处理逻辑的解耦。



帮我把这个引入全部整理一下，去除冗余，重新排序，最后效果类似
# 基础引入
import os
from datetime import datetime


# 第三方引入
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Request, Body


# 项目内部引入
from app.data.repositories import KnowledgeBaseRepository











项目架构：
5.6zizi（文件同步）/
│
├── .env                          # 环境变量配置文件
├── .vscode/                      # VSCode配置目录
├── Dockerfile                    # Docker镜像构建配置
├── Readme.md                     # 项目说明文档（当前为空）
├── VERSION_HISTORY.md            # 版本更新日志
├── requirements.txt              # Python依赖清单
├── sql_app.db                    # SQLite数据库文件（可能存储用户交互记录）
├── logs/                         # 应用日志目录
│   ├── document_processor.log    # 文档处理模块日志
│   ├── feedback.log              # 用户反馈日志
│   └── usage.log                 # 问题使用日志
├── markdown_files/               # 知识库源文件目录（Markdown格式）
│   ├── robot/                    # 机器人知识库
│   ├── mvp/                      # MVP算法平台知识库
│   ├── vision/                   # 机器视觉知识库
│   └── test/                     # 测试用知识库
├── milvus_data/                  # Milvus向量数据库存储目录
│   ├── bin/                      # Milvus可执行文件及依赖库
│   ├── configs/                  # Milvus配置文件
│   ├── data/                     # 向量数据存储目录
│   └── logs/                     # Milvus数据库日志
├── models/                       # 预训练模型目录（如嵌入模型bge-large-zh-v1.5）
├── utils/                        # 通用工具模块
│   ├── milvue_new.py             # Milvus数据库管理工具类
│   └── milvus_get.py             # Milvus数据查询工具
├── test/                         # 测试模块
│   ├── stream_test_界面流式打印.py  # 流式响应测试脚本
│   └── batch_processor22-批处理.py  # 批量请求处理测试脚本
├── app/                          # 核心应用目录
│   ├── __init__.py               # 包初始化文件
│   ├── main.py                   # FastAPI应用入口文件
│   ├── database.py               # 数据库连接配置
│   ├── static/                   # 静态资源目录（CSS/JS/字体）
│   ├── templates/                # HTML模板目录（如首页、管理页）
│   ├── data/                     # 数据模型与存储仓库
│   │   ├── models.py             # SQLAlchemy数据模型（如知识块、文档）
│   │   └── repositories.py       # 数据库操作仓库类
│   ├── services/                 # 核心业务逻辑层
│   │   ├── qa_system.py          # 问答系统核心类（向量搜索+LLM调用）
│   │   └── log_handler.py        # 日志记录与统计服务
│   ├── routes/                   # 路由接口定义
│   │   └── kb_admin_api.py       # 知识库管理接口（创建/上传/删除）
│   ├── utils/                    # 应用级工具模块
│   │   ├── vector_db_operations.py  # 向量数据库操作工具（分块/存储）
│   │   └── test_document_processor.py  # 文档处理测试脚本
│   └── file_monitor/             # 文件监控模块
│       └── core.py               # 文件变更监控服务（基于watchdog）
└── 参考文件/                      # 废弃或备用参考文件（如旧版知识库API）

### 关键目录说明：
- app/ ：项目核心代码目录，包含FastAPI应用入口、路由、服务层、数据模型及工具类，负责实现知识库管理、问答交互等核心功能。
- markdown_files/ ：存储原始知识库文档（Markdown格式），通过 app/utils/vector_db_operations.py 处理后存入Milvus向量数据库。
- milvus_data/ ：Milvus向量数据库的存储目录，用于持久化文本向量数据，支持高效相似性搜索。
- utils/ ：封装通用工具（如Milvus操作、文件监控），供业务逻辑复用。
- test/ ：包含功能测试脚本（如流式响应测试、批量请求处理测试），验证核心功能的正确性。





更新版本：app/static/version/VERSION_HISTORY.md

删除库使用app\routes\delete_database.py，并且设置固定的库名。



启动项目：

python -m app.main

更细

python -m utils.update_version

启动mysql

python -m utils.test_mysql_generation



## 新建知识库流程：

新建知识库流程
http://10.55.136.191:8000/admin/knowledge/login
管理员登陆
http://10.55.136.191:8000/admin/knowledge/kb_admin


1. 在sql_app里的user表里增加用户信息
2. admin登录后台界面新增知识库，标识符要和用户信息一样
3. 拖入测试文档并点击向量化
4. 在前端页面中加入前端知识库选项
5. 在后台qa_system中添加新的知识库信息在选项中。
6. 即可登陆前端运行
