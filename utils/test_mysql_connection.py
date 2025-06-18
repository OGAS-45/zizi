import mysql.connector


def test_mysql_connection():
    try:
        connection = None  # 初始化连接变量
        cursor = None      # 初始化游标变量
        # 使用用户提供的连接参数
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='0000',
            database='xyz_test'
        )

        if connection.is_connected():           
            print("✅ MySQL数据库连接成功!")
            cursor = connection.cursor()

            # 获取数据库中所有表
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_count = len(tables)
            print(f"📊 数据库中共有 {table_count} 张表:")

            # 遍历并打印每个表的基本信息
            for idx, table in enumerate(tables, 1):
                table_name = table[0]
                print(f"--- 表 {idx}: {table_name} ---")

                # 获取表结构
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                print("字段信息:")
                for col in columns:
                    print(f"  {col[0]} ({col[1]}) - {col[2]}")

                # 获取表内容预览(前5行)
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                print(f"内容预览 (前5行):")
                for row in rows:
                    print(f"  {row}")

    finally:
        # 确保连接关闭
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 MySQL连接已关闭")


if __name__ == "__main__":
    test_mysql_connection()