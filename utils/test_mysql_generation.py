import requests
import json
import os
import re  # 新增正则表达式模块
import time  # 新增：用于计时
import csv   # 新增：用于结果存储
from datetime import datetime  # 新增：用于记录测试时间
import requests  # 新增：用于HTTP请求
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import mysql.connector
from mysql.connector import Error
from mysql.connector import pooling

connection_pool = None

def init_db_pool():
    """初始化数据库连接池"""
    global connection_pool
    if connection_pool is None:
        try:
            connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="mypool",
                pool_size=32,  # 连接池大小，可根据实际需求调整
                pool_reset_session=True,
                host='localhost',
                port=3306,
                user='root',
                password='170170',
                database='xxyz'
            )
            print("✅ 数据库连接池初始化成功!")
        except Error as e:
            print(f"数据库连接池初始化错误: {str(e)}")

def get_mysql_connection():
    """
    创建MySQL数据库连接
    :return: MySQL连接对象
    """
    global connection_pool
    if connection_pool is None:
        init_db_pool()
    
    try:
        connection = connection_pool.get_connection()
        if connection.is_connected():
            print("✅ 从连接池获取数据库连接成功!")
        return connection
    except Error as e:
        print(f"从连接池获取数据库连接错误: {str(e)}")
        return None


def get_table_columns(db_name: str, table_name: str) -> list:
    """
    连接MySQL数据库并获取指定表的字段信息
    :param db_name: 数据库名称
    :param table_name: 目标表名
    :return: 字段信息列表（包含字段名、类型等）
    """
    start_time = time.time()  # 记录函数开始执行时间
    try:
        conn_start = time.time()
        connection = get_mysql_connection()
        conn_time = time.time() - conn_start
        print(f"数据库连接耗时: {conn_time:.4f}秒")

        if not connection:
            return []
        cursor = connection.cursor()
        
        # 记录SQL执行耗时，使用PRAGMA table_info获取字段信息
        sql_start = time.time()
        cursor.execute(f"""
                    SELECT COLUMN_NAME, DATA_TYPE 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = '{db_name}' AND TABLE_NAME = '{table_name}'
            """)
        sql_exec_time = time.time() - sql_start
        print(f"SQL执行耗时: {sql_exec_time:.4f}秒")

        # 记录结果获取耗时
        fetch_start = time.time()
        columns = cursor.fetchall()  # 结果格式: (cid, name, type, notnull, dflt_value, pk)
        fetch_time = time.time() - fetch_start
        print(f"结果获取耗时: {fetch_time:.4f}秒")
        print(columns)
        # 提取字段名和类型（返回字典列表）
        column_info = [{"name": col[0], "type": col[1]} for col in columns]
        # print(column_info)

        total_time = time.time() - start_time
        print(f"函数总耗时: {total_time:.4f}秒")
        return column_info
        
    
    except Error as e:      
        print(f"数据库错误: {str(e)}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()  # 归还连接到池中

def get_related_tables(db_name: str, main_table: str) -> dict:
    """
    获取与主表关联的其他表及外键关系（通过SQLite的外键约束查询）
    :param db_name: 数据库路径
    :param main_table: 主表名（如 'orders'）
    :return: 关联表信息字典（表名: 外键字段）
    """
    try:
        conn = get_mysql_connection()
        if not conn:
            return {}
        cursor = conn.cursor()
        related_tables = {}
        
        # 查询主表的外键约束
        cursor.execute(f"""
            SELECT TABLE_NAME, COLUMN_NAME 
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE REFERENCED_TABLE_NAME = '{main_table}' 
              AND TABLE_SCHEMA = '{db_name}'
        """)
        foreign_keys = cursor.fetchall() 
        
        for fk in foreign_keys:
            related_table = fk[0]  # 关联表名
            main_field = fk[1]     # 主表外键字段
            related_tables[related_table] = main_field
        
        return related_tables
    except Error as e:
        print(f"获取关联表错误: {str(e)}")
        return {}
    finally:
        if 'conn' in locals() and conn is not None and conn.is_connected():
            cursor.close()
            conn.close()
            

def generate_sql_with_llm(prompt: str,sql_model) -> str:
    """
    调用LLM模型生成SQL语句（复用原有逻辑）
    """
    url = "http://10.55.136.170:7000/v1/chat/completions"
    messages = [
        {"role": "system", "content": "你是一个专业的数据库工程师，请根据用户需求和表结构生成正确的SQL语句"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = requests.post(
            url,
            json={
                "model": sql_model,
                "messages": messages,
                "temperature": 0.7
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    except requests.exceptions.RequestException as e:
        return f"请求失败: {str(e)}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"响应解析错误: {str(e)}"

def execute_sql_query(db_path: str, sql: str) -> list:
    """
    执行SQL查询并返回结果
    :param db_path: SQLite数据库文件路径
    :param sql: 要执行的SQL语句
    :return: 查询结果列表
    """
    try:
        conn = get_mysql_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql)
        results = cursor.fetchall()  # 获取所有查询结果
        
        return results
    
    except Error as e:
        print(f"SQL执行错误: {str(e)}")
        return []
    finally:
        if 'conn' in locals() and conn is not None and conn.is_connected():
            cursor.close()
            conn.close()

def generate_natural_language_result(prompt: str,nl_model) -> str:
    """
    调用LLM将查询结果转换为自然语言描述
    """
    url = ("http://10.55.136.170:7000/v1/chat/completions").rstrip(';')
    messages = [
        {"role": "system", "content": "/no_think你是一个自然语言处理专家，需要将数据库查询结果转换为易懂的自然语言描述"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = requests.post(
            url,
            json={
                "model":  nl_model,
                "messages": messages,
                "temperature": 0.3  # 结果描述需要更稳定，降低温度值
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    except requests.exceptions.RequestException as e:
        return f"请求失败: {str(e)}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"响应解析错误: {str(e)}"

def get_table_sample_data(db_name: str, table_name: str) -> list:
    """
    获取数据库表第一行样本数据
    :param db_name: 数据库名称
    :param table_name: 目标表名
    :return: 第一行数据的字典列表（字段名: 值）
    """
    try:
        conn = get_mysql_connection()
        if not conn or not conn.is_connected():
            return []
        cursor = conn.cursor(dictionary=True)  # 使用字典游标便于字段映射
        
        # 查询第一行数据
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        result = cursor.fetchone()  # 获取单行数据
        
        return [result] if result else []
    
    except Error as e:
        print(f"获取样本数据错误: {str(e)}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def get_target_table_structures(db_name: str) -> dict:
    """
    获取指定表的字段结构及值域信息
    :param db_name: 数据库名称
    :return: 表结构信息字典
    """
    conn = None
    cursor = None
    try:
        target_tables = {}
        # 直接指定需要查询的表名
        conn = get_mysql_connection()
        if not conn:
            return {}
        cursor = conn.cursor()
        
        cursor.execute(f"SHOW TABLES FROM {db_name}")
        tables = cursor.fetchall()  # 结果格式: (table_name,)
        
        
        # 遍历所有表
        for table in tables:
            table_name = table[0]
            
            # 获取表字段信息
            columns = get_table_columns(db_name, table_name)
            if columns:
                # 获取外键关系
                foreign_keys = get_related_tables(db_name, table_name)
                
                # 将字段和外键信息存储
                target_tables[table_name] = {
                    'columns': columns,
                    'foreign_keys': foreign_keys
                }
        return target_tables
    except Error as e:
        print(f"获取表结构错误: {str(e)}")
        return {}
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()  # 确保连接正确归还到池中


# 新增：测试问题集
TEST_QUESTIONS = [
    "2024年王逸飞的总销售数量是多少？",
    "列出化纤行业的所有物料描述",
    "找出销售区域是华东业务部的记录",
    "有哪些产品的销售收入大于5000元？",
    "显示一级标签为算法平台-2D的物料料号",
    "2024年华东业务部销售中，销售收入大于2000元的记录有哪些？",
    "2023年国内销售且销售数量少于5个的产品是哪些？",
    "列出2024年1月到3月的销售记录",
    "找出2023年和2024年都卖出过HR-EK03-A产品的客户",
    "显示华中业务部和华东业务部在2024年卖出的所有产品料号",
    "列出2024年所有算法平台-2D产品的销售额",
    "哪个业务员卖出了深度学习功能软加密狗？",
    "显示化纤行业软件的销售区域分布",
    "找出闸口基础功能产品（如DH-MV-RDEK00-B）的总销售数量",
    "列出液晶行业和铁路行业的销售总金额并比较",
    "2024年最畅销产品的销售数量是多少？",
    "每个区域的平均销售收入是多少？",
    "列出各产品大类的销售总量",
    "哪个业务员的销售总金额最高？",
    "化纤行业软件的平均价格是多少？",
    "比较2023年和2024年化纤行业软件的销售总额",
    "2024年Q1（1-3月）华东业务部的销售收入是多少？",
    "2025年截至目前的总销售数量是多少？",
    "显示每个季度的销售趋势",
    "找出HR-EK03-A产品在2023年和2024年的销售数量变化",
    "列出所有包含‘硬加密狗’的物料描述",
    "哪些产品包含深度学习功能并是软加密狗？",
    "显示产品大类包含‘算法平台’的销售记录",
    "找出客户名称中有‘科技’的销售信息",
    "2024年销售描述中包含‘闸口’的记录",
    "列出2026年的销售数据",
    "显示料号为XYZ123的销售记录",
    "哪个客户买了‘量子计算加密狗’？",
    "找出所有海外客户的海外客户名称",
    "列出2024年华东业务部崔爱强卖出的物料描述",
    "2025年2月同比变化情况？"
]



# if __name__ == "__main__":
    # db_path = r"D:/Workplace/数据库/备份数据库/sql_app.db"
    # # 明确指定模型名称
    # sql_model = "Qwen3_7B"
    # nl_model = os.getenv("LLM_MODEL_NAME"),
    # # 生成带时间戳的结果文件名
    # results_file = sql_model + f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    # # 修改：仅保留用户指定的CSV表头
    # csv_headers = [
    #     "测试序号", "问题描述", "响应时间(秒)",
    #     "生成SQL", "查询结果", "自然语言结果", 
    #     "SQL模型", "自然语言模型", "是否成功"
    # ]
    # test_results = []


    # # 循环处理测试问题集中的每个问题
    # for idx, natural_language in enumerate(TEST_QUESTIONS, 1):
    #     print(f"\n===== 测试 {idx}/{len(TEST_QUESTIONS)}: {natural_language} =====")
    #     # 修改：精简测试结果字典，仅包含需要的字段
    #     test_result = {
    #         "test_id": idx,
    #         "question": natural_language,
    #         "sql_model": sql_model,
    #         "nl_model": nl_model,
    #         "success": False
    #     }

    #     try:
    #         start_timestamp = time.time()

    #         # 构建SQL生成提示词（保持不变）
    #         llm_prompt = f"/no_think 你是SQLite专家，请根据用户问题和提供的表结构生成正确的SQL查询语句。"
    #         llm_prompt += "直接输出SQL语句，无需多余解释。"

    #         filtered_tables = get_target_table_structures(db_path)
    #         for table, table_data in filtered_tables.items():
    #             llm_prompt += f"表名：{table}\n"
    #             for col in table_data['columns']:
    #                 llm_prompt += f"- 字段名：{col['name']}，类型：{col['type']}"
    #                 if col['values']:
    #                     values_str = ', '.join([str(v)[:10] for v in col['values']])
    #                     if len(col['values']) >= 20:
    #                         values_str += f"（仅显示前20个，共{len(col['values'])}个不同值）"
    #                     llm_prompt += f"，可选值：[{values_str}]\n"
    #                 else:
    #                     llm_prompt += "\n"
    #             if table_data['foreign_keys']:
    #                 llm_prompt += f"外键关系：{table_data['foreign_keys']}\n"

    #         llm_prompt += f"问题：{natural_language}"
            
    #         # print(llm_prompt)

    #         # 生成SQL
    #         generated_sql = generate_sql_with_llm(llm_prompt,sql_model) + ";"
            
    #         # print(generated_sql)
    #         test_result["generated_sql"] = generated_sql

    #         # 提取有效SQL
    #         sql_pattern = re.compile(r'SELECT\s+.*?;', re.DOTALL)
    #         match = sql_pattern.search(generated_sql)
    #         if not match:
    #             raise Exception("未检测到有效SELECT语句")
    #         generated_sql = match.group().strip()

    #         # 执行SQL
    #         query_results = execute_sql_query(db_path, generated_sql)
    #         # 修改：确保查询结果格式与示例一致
    #         test_result["query_results"] = json.dumps(query_results, ensure_ascii=False)

    #         # 生成自然语言结果
    #         if query_results:
    #             nl_prompt = f"用户询问问题是：{natural_language}。将以下数据库查询结果转换为简洁易懂的自然语言：{json.dumps(query_results, ensure_ascii=False)}"
    #             natural_language_result = generate_natural_language_result(nl_prompt,nl_model)
    #             test_result["natural_language_result"] = natural_language_result
    #             print("\n查询结果（自然语言）：\n" + "-"*50 + f"\n{natural_language_result}\n" + "-"*50)
    #         else:
    #             test_result["natural_language_result"] = "查询结果为空"

    #         # 记录成功状态和时间
    #         test_result["success"] = True
    #         end_timestamp = time.time()
    #         # 修改：响应时间保留两位小数
    #         test_result["response_time"] = round(end_timestamp - start_timestamp, 2)

    #     except Exception as e:
    #         # 错误处理
    #         error_msg = str(e)
    #         test_result["natural_language_result"] = f"处理失败: {error_msg}"
    #         test_result["query_results"] = f"错误: {error_msg}"
    #         test_result["generated_sql"] = f"错误: {error_msg}"
    #         end_timestamp = time.time()
    #         test_result["response_time"] = round(end_timestamp - start_timestamp, 2)

    #     # 添加到结果列表
    #     test_results.append(test_result)
    #     print(f"测试 {idx} 完成，耗时 {test_result['response_time']}秒，状态: {'成功' if test_result['success'] else '失败'}")

    # # 写入CSV文件
    # with open(results_file, 'w', newline='', encoding='utf-8') as f:
    #     writer = csv.DictWriter(f, fieldnames=csv_headers,delimiter="|")
    #     writer.writeheader()
    #     for result in test_results:
    #         writer.writerow({
    #             "测试序号": result["test_id"],
    #             "问题描述": result["question"],
    #             "响应时间(秒)": result["response_time"],
    #             "生成SQL": result["generated_sql"].replace('\n', ' ').replace('  ', ' ').strip(),
    #             "查询结果": result["query_results"].replace('\n', ' ').replace('  ', ' ').strip(),
    #             "自然语言结果": result["natural_language_result"].replace('\n', ' ').replace('  ', ' ').strip(),
    #             "SQL模型": result["sql_model"],
    #             "自然语言模型": result["nl_model"],
    #             "是否成功": "是" if result["success"] else "否"
    #         })


    # print(f"\n所有测试完成！结果已保存至: {os.path.abspath(results_file)}")


# // ... 注释掉原有的TEST_QUESTIONS测试代码块 ...

if __name__ == "__main__":
    db_name = "xxyz"  # MySQL数据库名称
    # 明确指定模型名称
    sql_model = "sql_Qwen_8B"
    nl_model = "sql_Qwen_4B"
    # 创建FastAPI应用
    app = FastAPI(title="SQL查询助手")

    # 配置模板目录app\templates\sql.html
    templates = Jinja2Templates(directory="D:/Workplace/zizi-5.19/app/templates")
    
    # 配置静态文件目录
    # app.mount("/static", StaticFiles(directory="../app/static"), name="static")
    
    # 请求模型
    class QueryRequest(BaseModel):
        question: str
    
    # 主页路由
    @app.get("/")
    async def read_root(request: Request):
        return templates.TemplateResponse("sql.html", {"request": request})
    
    # API路由
    @app.post("/api/query")
    async def process_query(request: QueryRequest):
        try:
            # 提取问题
            natural_language = request.question
            
            # 构建SQL生成提示词
            llm_prompt = f"/no_think 你是MySQL专家，请根据用户问题和提供的表结构生成正确的SQL查询语句。务必遵循MySQL语法，并且让输出尽量少，不要输出多余信息。直接输出SQL语句，无需多余解释。\n\n"
            
            filtered_tables = get_target_table_structures(db_name)
            for table, table_data in filtered_tables.items():
                llm_prompt += f"表名：{table}\n"
                llm_prompt += f"字段：{', '.join([col['name'] + '(' + col['type'] + ')' for col in table_data['columns']])}\n"
                if table_data['foreign_keys']:
                    fk_str = ', '.join([f"{k}->{v}" for k, v in table_data['foreign_keys'].items()])
                    llm_prompt += f"外键：{fk_str}\n"
                # 新增：获取并添加第一行样本数据
                sample_data = get_table_sample_data('xxyz', table)
                if sample_data:
                    # 格式化样本数据为紧凑格式：字段=值|字段=值
                    formatted_sample = "| ".join([f"{k}={str(v)[:20]}" for k, v in sample_data[0].items()])
                    llm_prompt += f"示例数据：{formatted_sample}\n"
                
                llm_prompt += "\n"

            llm_prompt += f"问题：{natural_language}"
            
            print(llm_prompt)
            print("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
            # print(llm_prompt[:30000])
            
            
            # 生成SQL
            generated_sql = generate_sql_with_llm(llm_prompt, sql_model) 
            
            # 提取有效SQL
            sql_pattern = re.compile(r'SELECT\s+.*?;', re.DOTALL)
            match = sql_pattern.search(generated_sql)
            if not match:
                raise Exception("未检测到有效SELECT语句")
            generated_sql = match.group().strip()
            
            # 执行SQL
            query_results = execute_sql_query(db_name, generated_sql)
            
            print(generated_sql)
            
            
            # 生成自然语言结果
            if query_results:
                nl_prompt = f"用户询问问题是：{natural_language}。将以下数据库查询结果转换为简洁易懂的自然语言：{json.dumps(query_results, ensure_ascii=False)}"
                natural_language_result = generate_natural_language_result(nl_prompt, nl_model)
            else:
                natural_language_result = "查询结果为空"
            
            # // 添加SQL字段
            return {
                "success": True,
                "result": natural_language_result,
                "sql": generated_sql  
            }
            # # // 错误时也返回SQL
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sql": generated_sql if 'generated_sql' in locals() else ""  
                
            }
    
    # 启动服务器
    uvicorn.run(app, host="10.55.136.170", port=8005)