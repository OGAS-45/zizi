
**项目名称**: [ZIZI(JARVIS)，公司文档库RAG助手]

**项目负责人**: [OGAS-45]

**项目开始日期**:[2025.2.22]

**项目状态**: [进行中]


---

## 1. 项目概述

**项目背景**:  
[简要描述项目的背景、目标和重要性。]

**项目目的**：
[简要描述项目的目标和重要性。]

---



## 2. 项目OKR

**目标 (Objective)**:  
[在此填写项目的核心目标。]

**关键结果 (Key Results)**:  
- [KR1: 描述第一个关键结果及其衡量标准。]
- [KR2: 描述第二个关键结果及其衡量标准。]
- [KR3: 描述第三个关键结果及其衡量标准。]

**链接**: [OKR文档链接]

---

## 3. 项目日记

**每日进度记录**:  
[在此简要描述每日的进展、遇到的问题和解决方案。]

**链接**: [日记文档链接]

---

## 4. 项目收录

**相关资料**:  
[列出项目过程中收集到的有用资料、文献、工具等。]

**链接**: [收录文档链接]

---

## 5. 项目笔记

**经验总结**:  

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
基础引入
import os
from datetime import datetime

第三方引入
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Request, Body

项目内部引入
from app.data.repositories import KnowledgeBaseRepository


重启机子后启动项目的方式：
打开docker，导航到standalone.bat，powershell管理员.\standalone.bat start 启动milvus
使用anaconda里3.9.21的python环境启动项目，输入python -m app.main

更新版本：app/static/version/VERSION_HISTORY.md
删除库使用app\routes\delete_database.py，并且设置固定的库名。


启动项目：
python -m app.main
更细
python -m utils.update_version
启动mysql
python -m utils.test_mysql_generation

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



重启环境：
conda环境 activate D:\Workplace\conda-zizi_198
项目环境D:\Workplace\zizi-5.19
docker开启
打开milvus数据库（start在D:\Workplace\docker）
    PS C:\Windows\system32> cd D:\Workplace\docker
    PS D:\Workplace\docker> .\standalone.bat start
启动LMstudio，嵌入模型加载要交
cmd打开移动到项目路径输入python -m app.main



**链接**: [笔记文档链接]

---

## 6. 项目时间线

**里程碑**:  
- [里程碑: 完成被邀请至其他部门的大模型研讨会并培训指导-2025.4.11]
- [里程碑2: 描述第二个里程碑及其完成日期。]
- [里程碑3: 描述第三个里程碑及其完成日期。]

**时间线图**:  
[在此插入项目时间线图或甘特图。]
    
---

## 7. 项目团队

**团队成员**:  
- [成员1: 角色和职责。]
- [成员2: 角色和职责。]
- [成员3: 角色和职责。]

**联系方式**:  
[列出团队成员的联系方式。]

---

## 8. 项目风险与应对措施

**风险1**:  
- **描述**: [描述第一个风险。]
- **应对措施**: [列出应对措施。]

**风险2**:  
- **描述**: [描述第二个风险。]
- **应对措施**: [列出应对措施。]

---

## 9. 项目资源

**工具与软件**:  
[列出项目中使用的主要工具和软件。]

**预算**:  
[简要描述项目的预算情况。]

---

## 10. 项目反馈与改进

**反馈**:  
[收集项目相关方的反馈意见。]

**改进措施**:  
[根据反馈提出的改进措施。]

---

## 11. 项目总结

**项目成果**:  
[总结项目的最终成果和达成情况。]

**经验教训**:  
[总结项目中的经验教训和未来改进方向。]

---

**最后更新日期**: [YYYY-MM-DD]

---

### 使用说明

1. **项目概述**: 提供项目的整体背景和目标，帮助读者快速了解项目。
2. **项目OKR**: 链接到OKR文档，确保目标清晰且可衡量。
3. **项目日记**: 链接到日记文档，记录每日进展。
4. **项目收录**: 链接到收录文档，整理相关资料。
5. **项目笔记**: 链接到笔记文档，记录经验和反思。
6. **项目时间线**: 提供项目的时间线和里程碑，帮助跟踪进度。
7. **项目团队**: 列出团队成员及其职责，确保责任明确。
8. **项目风险与应对措施**: 识别潜在风险并制定应对策略。
9. **项目资源**: 列出项目所需的资源和预算。
10. **项目反馈与改进**: 收集反馈并制定改进措施。
11. **项目总结**: 在项目结束时进行总结，记录成果和经验教训。
