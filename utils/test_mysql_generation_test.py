import requests
import json
import os
import sqlite3  # 新增sqlite3模块
import re  # 新增正则表达式模块
import time  # 新增：用于计时
import csv   # 新增：用于结果存储
from datetime import datetime  # 新增：用于记录测试时间
import requests
import json
import os
import sqlite3
import re
import time
import csv
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

def get_table_columns(db_path: str, table_name: str) -> list:
    """
    连接SQLite数据库并获取指定表的字段信息
    :param db_path: SQLite数据库文件路径
    :param table_name: 目标表名
    :return: 字段信息列表（包含字段名、类型等）
    """
    print(2)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 使用PRAGMA table_info获取字段信息
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()  # 结果格式: (cid, name, type, notnull, dflt_value, pk)
        
        # 提取字段名和类型（返回字典列表）
        column_info = [{"name": col[1], "type": col[2]} for col in columns]
        print(column_info)
        return column_info
        
    
    except sqlite3.Error as e:
        print(f"数据库错误: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_related_tables(db_path: str, main_table: str) -> dict:
    """
    获取与主表关联的其他表及外键关系（通过SQLite的外键约束查询）
    :param db_path: 数据库路径
    :param main_table: 主表名（如 'orders'）
    :return: 关联表信息字典（表名: 外键字段）
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        related_tables = {}
        
        # 查询主表的外键约束
        cursor.execute(f"PRAGMA foreign_key_list({main_table})" )
        foreign_keys = cursor.fetchall()  # 结果格式: (id, seq, table, from, to, on_update, on_delete, match)
        
        for fk in foreign_keys:
            related_table = fk[2]  # 关联表名
            main_field = fk[3]     # 主表外键字段
            related_tables[related_table] = main_field
        
        return related_tables
    except sqlite3.Error as e:
        print(f"获取关联表错误: {str(e)}")
        return {}
    finally:
        if 'conn' in locals():
            conn.close()

def generate_sql_with_llm(prompt: str,sql_model) -> str:
    """
    调用LLM模型生成SQL语句（复用原有逻辑）
    """
    url = os.getenv("LLM_SERVER_URL", "http://10.55.136.191:7000") + "/v1/chat/completions"
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
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()  # 获取所有查询结果
        
        # 获取列名（用于构造带字段名的结果）
        column_names = [description[0] for description in cursor.description]
        formatted_results = [dict(zip(column_names, row)) for row in results]
        return formatted_results
    
    except sqlite3.Error as e:
        print(f"SQL执行错误: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def generate_natural_language_result(prompt: str,nl_model) -> str:
    """
    调用LLM将查询结果转换为自然语言描述
    """
    url = os.getenv("LLM_SERVER_URL", "http://10.55.136.191:7000") + "/v1/chat/completions"
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

def get_table_sample_data(db_path: str, table_name: str) -> list:
    """
    获取数据库表前5行样本数据（包含所有字段）
    :param db_path: SQLite数据库文件路径
    :param table_name: 目标表名
    :return: 前5行数据的字典列表（字段名: 值）
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询前5行数据
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        results = cursor.fetchall()
        
        # 获取列名并格式化为字典列表
        column_names = [description[0] for description in cursor.description]
        sample_data = [dict(zip(column_names, row)) for row in results]
        return sample_data
    
    except sqlite3.Error as e:
        print(f"获取样本数据错误: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_target_table_structures(db_path: str) -> dict:
    """
    获取指定的Fruits、Orders、Customers三张表的字段结构及值域信息
    :param db_path: SQLite数据库文件路径
    :return: 表结构信息字典（包含字段值域和外键关系）
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        target_tables = {}
        print(1)
        # 直接指定需要查询的表名
        for table in ["sales_data", "material_description"]:
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone():
                columns = get_table_columns(db_path, table)
                if columns:
                    # 为每个字段添加值域信息
                    for col in columns:
                        col["values"] = get_field_value_summary(db_path, table, col["name"])
                    # 获取外键关系
                    foreign_keys = get_related_tables(db_path, table)
                    # 将字段和外键信息嵌套存储在表名下
                    target_tables[table] = {
                        'columns': columns,
                        'foreign_keys': foreign_keys
                    }
        return target_tables
    except sqlite3.Error as e:
        print(f"获取表结构错误: {str(e)}")
        return {}
    finally:
        if 'conn' in locals():
            conn.close()


# 修改validate_sql_logic函数定义及逻辑
def validate_sql_logic(sql: str, need_multi_table: bool, has_aggregation: bool) -> bool:
    # 检查多表关联（根据问题判断是否需要）
    if need_multi_table and not re.search(r'JOIN\s+\w+\s+ON', sql, re.IGNORECASE):
        print("警告：检测到需要多表关联但未使用JOIN语法")
        return False
    # 检查聚合逻辑（优化后：仅当明确需要聚合时验证）
    if has_aggregation:
        if not re.search(r'(SUM|COUNT|AVG|MAX|MIN)\(', sql, re.IGNORECASE):  # 匹配聚合函数
            print("警告：需要聚合统计但未使用SUM/COUNT/AVG/MAX/MIN函数")
            return False
        if not re.search(r'GROUP\s+BY', sql, re.IGNORECASE):
            print("警告：需要聚合统计但未使用GROUP BY")
            return False
    return True


# 新增：验证SQL是否包含必要的多表连接或聚合逻辑
def validate_sql_logic(sql: str, related_tables: dict, has_aggregation: bool) -> bool:
    """
    验证SQL是否符合多表关联或聚合要求
    :param sql: 生成的SQL语句
    :param related_tables: 关联表信息（来自get_related_tables）
    :param has_aggregation: 是否需要聚合（根据用户问题判断）
    :return: 验证结果
    """
    # 检查多表关联
    if related_tables and not re.search(r'JOIN\s+\w+\s+ON', sql, re.IGNORECASE):
        print("警告：检测到关联表但未使用JOIN语法")
        return False
    
    # 检查聚合逻辑
    if has_aggregation and not re.search(r'GROUP\s+BY', sql, re.IGNORECASE):
        print("警告：需要聚合统计但未使用GROUP BY")
        return False
    
    return True


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



def get_field_value_summary(db_path: str, table_name: str, column_name: str) -> list:
    """
    获取指定字段的可选值集合（最多前20个distinct值）
    :param db_path: 数据库路径
    :param table_name: 表名
    :param column_name: 字段名
    :return: 字段可选值列表
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 查询去重后的值，最多返回20个
        cursor.execute(f"SELECT DISTINCT {column_name} FROM {table_name} LIMIT 20")
        values = [row[0] for row in cursor.fetchall() if row[0] is not None]
        # print(values)
        return values
    except sqlite3.Error as e:
        print(f"获取字段'{column_name}'可选值错误: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    db_path = r"D:/401385/数据库/备份数据库/sql_app.db" 
        # 明确指定模型名称
    sql_model = "sqlcoder7bq5"
    nl_model = "Qwen3_4B"
    # 生成带时间戳的结果文件名
    results_file = sql_model + f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    # 修改：仅保留用户指定的CSV表头
    csv_headers = [
        "测试序号", "问题描述", "响应时间(秒)",
        "生成SQL", "查询结果", "自然语言结果", 
        "SQL模型", "自然语言模型", "是否成功"
    ]
    test_results = []


    # 循环处理测试问题集中的每个问题
    for idx, natural_language in enumerate(TEST_QUESTIONS, 1):
        print(f"\n===== 测试 {idx}/{len(TEST_QUESTIONS)}: {natural_language} =====")
        # 修改：精简测试结果字典，仅包含需要的字段
        test_result = {
            "test_id": idx,
            "question": natural_language,
            "sql_model": sql_model,
            "nl_model": nl_model,
            "success": False
        }

        try:
            start_timestamp = time.time()

            # 构建SQL生成提示词（保持不变）
            llm_prompt = f"/no_think 你是SQLite专家，请根据用户问题和提供的表结构生成正确的SQL查询语句。"
            llm_prompt += "直接输出SQL语句，无需多余解释。"

            filtered_tables = get_target_table_structures(db_path)
            for table, table_data in filtered_tables.items():
                llm_prompt += f"表名：{table}\n"
                for col in table_data['columns']:
                    llm_prompt += f"- 字段名：{col['name']}，类型：{col['type']}"
                    if col['values']:
                        values_str = ', '.join([str(v)[:10] for v in col['values']])
                        if len(col['values']) >= 20:
                            values_str += f"（仅显示前20个，共{len(col['values'])}个不同值）"
                        llm_prompt += f"，可选值：[{values_str}]\n"
                    else:
                        llm_prompt += "\n"
                if table_data['foreign_keys']:
                    llm_prompt += f"外键关系：{table_data['foreign_keys']}\n"

            llm_prompt += f"问题：{natural_language}"
            
            # print(llm_prompt)

            # 生成SQL
            generated_sql = generate_sql_with_llm(llm_prompt,sql_model) + ";"
            
            # print(generated_sql)
            test_result["generated_sql"] = generated_sql

            # 提取有效SQL
            sql_pattern = re.compile(r'SELECT\s+.*?;', re.DOTALL)
            match = sql_pattern.search(generated_sql)
            if not match:
                raise Exception("未检测到有效SELECT语句")
            generated_sql = match.group().strip()

            # 执行SQL
            query_results = execute_sql_query(db_path, generated_sql)
            # 修改：确保查询结果格式与示例一致
            test_result["query_results"] = json.dumps(query_results, ensure_ascii=False)

            # 生成自然语言结果
            if query_results:
                nl_prompt = f"用户询问问题是：{natural_language}。将以下数据库查询结果转换为简洁易懂的自然语言：{json.dumps(query_results, ensure_ascii=False)}"
                natural_language_result = generate_natural_language_result(nl_prompt,nl_model)
                test_result["natural_language_result"] = natural_language_result
                print("\n查询结果（自然语言）：\n" + "-"*50 + f"\n{natural_language_result}\n" + "-"*50)
            else:
                test_result["natural_language_result"] = "查询结果为空"

            # 记录成功状态和时间
            test_result["success"] = True
            end_timestamp = time.time()
            # 修改：响应时间保留两位小数
            test_result["response_time"] = round(end_timestamp - start_timestamp, 2)

        except Exception as e:
            # 错误处理
            error_msg = str(e)
            test_result["natural_language_result"] = f"处理失败: {error_msg}"
            test_result["query_results"] = f"错误: {error_msg}"
            test_result["generated_sql"] = f"错误: {error_msg}"
            end_timestamp = time.time()
            test_result["response_time"] = round(end_timestamp - start_timestamp, 2)

        # 添加到结果列表
        test_results.append(test_result)
        print(f"测试 {idx} 完成，耗时 {test_result['response_time']}秒，状态: {'成功' if test_result['success'] else '失败'}")

    # 写入CSV文件
    with open(results_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers,delimiter="|")
        writer.writeheader()
        for result in test_results:
            writer.writerow({
                "测试序号": result["test_id"],
                "问题描述": result["question"],
                "响应时间(秒)": result["response_time"],
                "生成SQL": result["generated_sql"].replace('\n', ' ').replace('  ', ' ').strip(),
                "查询结果": result["query_results"].replace('\n', ' ').replace('  ', ' ').strip(),
                "自然语言结果": result["natural_language_result"].replace('\n', ' ').replace('  ', ' ').strip(),
                "SQL模型": result["sql_model"],
                "自然语言模型": result["nl_model"],
                "是否成功": "是" if result["success"] else "否"
            })


    print(f"\n所有测试完成！结果已保存至: {os.path.abspath(results_file)}")


# // ... 注释掉原有的TEST_QUESTIONS测试代码块 ...