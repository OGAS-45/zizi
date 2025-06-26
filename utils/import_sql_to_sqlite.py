import sqlite3
import os

def import_sql_to_db(sql_file_path: str, db_file_path: str):
    """
    读取SQL文件并导入到SQLite数据库
    :param sql_file_path: 输入的SQL文件路径（如："data/input.sql"）
    :param db_file_path: 输出的数据库文件路径（如："output.db"）
    """
    try:
        # 连接/创建数据库（Windows路径使用反斜杠或双反斜杠）
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()

        # 检查SQL文件是否存在
        if not os.path.exists(sql_file_path):
            raise FileNotFoundError(f"SQL文件不存在: {sql_file_path}")

        # 读取SQL文件内容（使用utf-8编码）
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # 执行SQL脚本（支持多语句，如CREATE TABLE、INSERT等）
        cursor.executescript(sql_script)
        conn.commit()
        print(f"成功执行SQL脚本，数据库已保存至: {db_file_path}")

    except sqlite3.Error as e:
        print(f"SQL执行错误: {str(e)}")
    except Exception as e:
        print(f"其他错误: {str(e)}")
    finally:
        # 确保关闭连接
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # 示例配置（根据实际路径修改）
    INPUT_SQL_PATH = "D:/Workplace/数据库/consumption_details.sql"  # 替换为你的SQL文件路径
    OUTPUT_DB_PATH = "consumption_details6565.db"  # 替换为目标数据库路径

    # 执行导入
    import_sql_to_db(INPUT_SQL_PATH, OUTPUT_DB_PATH)