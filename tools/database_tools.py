import os
import re
import json
import pymysql
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, List

load_dotenv()

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")

def get_db_connection(db_name=None):
    try:
        return pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return None

def list_databases() -> str:
    """连接到MySQL服务器并列出所有数据库的名称。当不确定有哪些数据库可用时调用。"""
    logger.info("--- 🛠️ 执行工具: list_databases ---")
    conn = get_db_connection()
    if conn is None:
        return "无法连接到数据库，请检查配置。"
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES")
            databases = [db['Database'] for db in cursor.fetchall()]
            user_databases = [db for db in databases if db not in ['information_schema', 'mysql', 'performance_schema', 'sys']]
            result = json.dumps(user_databases, ensure_ascii=False, indent=2)
            logger.info(f"工具输出: {result}")
            return result
    except Exception as e:
        logger.error(f"列出数据库失败: {e}")
        return f"列出数据库失败，错误信息: {e}"
    finally:
        conn.close()

def get_schema_of_database(db_name: str) -> str:
    """
    获取指定数据库的完整表结构（包括表名、字段名、字段类型、主键、是否可空、默认值和注释）。
    这是理解数据库结构的关键工具，在构建SQL查询前必须调用。
    """
    logger.info(f"--- 🛠️ 执行工具: get_schema_of_database (db_name='{db_name}') ---")
    if not re.match(r'^[a-zA-Z0-9_-]+$', db_name):
        return "无效的数据库名称。"
    conn = get_db_connection(db_name)
    if conn is None:
        return "无法连接到数据库，请检查配置或数据库名称是否正确。"
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [table[f'Tables_in_{db_name}'] for table in cursor.fetchall()]
            schema_info = {}
            for table_name in tables:
                cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
                columns = cursor.fetchall()
                table_comment_query = f"SELECT TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{db_name}' AND TABLE_NAME = '{table_name}'"
                cursor.execute(table_comment_query)
                table_comment_result = cursor.fetchone()
                table_comment = table_comment_result['TABLE_COMMENT'] if table_comment_result else ""
                schema_info[table_name] = {
                    "columns": [{"field": col['Field'], "type": col['Type'], "null": col['Null'], "key": col['Key'], "default": col['Default'], "extra": col['Extra'], "comment": col['Comment']} for col in columns],
                    "table_comment": table_comment
                }
            result = json.dumps(schema_info, ensure_ascii=False, indent=2)
            logger.info(f"工具输出: {result}")
            return result
    except Exception as e:
        logger.error(f"获取数据库 '{db_name}' 结构失败: {e}")
        return f"获取数据库 '{db_name}' 结构失败，错误信息: {e}"
    finally:
        conn.close()

def run_readonly_query_in_database(db_name: str, query: str) -> str:
    """
    在指定的数据库中执行只读SQL查询。
    允许的查询类型包括 'SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN'。
    禁止执行任何可能修改数据库状态的写操作（如 INSERT, UPDATE, DELETE, CREATE, DROP, ALTER）。
    返回查询结果的JSON字符串。
    """
    logger.info(f"--- 🛠️ 执行工具: run_readonly_query_in_database (db_name='{db_name}', query='{query}') ---")
    if not re.match(r'^[a-zA-Z0-9_-]+$', db_name):
        return "无效的数据库名称。"
    query_upper = query.strip().upper()
    disallowed_keywords = ["INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER", "TRUNCATE", "GRANT", "REVOKE", "LOCK", "UNLOCK"]
    if any(re.search(r'\b' + keyword + r'\b', query_upper) for keyword in disallowed_keywords):
        return "检测到潜在的写操作，已禁止执行。只允许执行不修改数据库的查询。"
    conn = get_db_connection(db_name)
    if conn is None:
        return "无法连接到数据库，请检查配置或数据库名称是否正确。"
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            logger.info(f"工具输出: {result_json}")
            return result_json
    except Exception as e:
        logger.error(f"执行查询失败: {e}")
        return f"执行查询失败，错误信息: {e}"
    finally:
        conn.close()

def list_tables_in_database(db_name: str) -> str:
    """
    【后备工具】当get_schema_of_database工具失败时，用于列出指定数据库中的所有表名。
    """
    logger.info(f"--- 🛠️ 执行后备工具: list_tables_in_database (db_name='{db_name}') ---")
    if not re.match(r'^[a-zA-Z0-9_-]+$', db_name):
        return "无效的数据库名称。"
    conn = get_db_connection(db_name)
    if conn is None:
        return "无法连接到数据库，请检查配置或数据库名称是否正确。"
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"USE `{db_name}`")
            cursor.execute("SHOW TABLES")
            tables = [table[f'Tables_in_{db_name}'] for table in cursor.fetchall()]
            result = json.dumps(tables, ensure_ascii=False, indent=2)
            logger.info(f"工具输出: {result}")
            return result
    except Exception as e:
        logger.error(f"列出数据库 '{db_name}' 中的表失败: {e}")
        return f"列出数据库 '{db_name}' 中的表失败，错误信息: {e}"
    finally:
        conn.close()

def describe_table_in_database(db_name: str, table_name: str) -> str:
    """
    【后备工具】当get_schema_of_database工具失败时，用于获取指定数据库中单个表的详细结构。
    """
    logger.info(f"--- 🛠️ 执行后备工具: describe_table_in_database (db_name='{db_name}', table_name='{table_name}') ---")
    if not re.match(r'^[a-zA-Z0-9_-]+$', db_name) or not re.match(r'^[a-zA-Z0-9_-]+$', table_name):
        return "无效的数据库或表名称。"
    conn = get_db_connection(db_name)
    if conn is None:
        return "无法连接到数据库，请检查配置或数据库名称是否正确。"
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"USE `{db_name}`")
            cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
            columns = cursor.fetchall()
            table_comment_query = f"SELECT TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{db_name}' AND TABLE_NAME = '{table_name}'"
            cursor.execute(table_comment_query)
            table_comment_result = cursor.fetchone()
            table_comment = table_comment_result['TABLE_COMMENT'] if table_comment_result else ""
            table_info = {
                "table_name": table_name,
                "table_comment": table_comment,
                "columns": [{"field": col['Field'], "type": col['Type'], "null": col['Null'], "key": col['Key'], "default": col['Default'], "extra": col['Extra'], "comment": col['Comment']} for col in columns]
            }
            result = json.dumps(table_info, ensure_ascii=False, indent=2)
            logger.info(f"工具输出: {result}")
            return result
    except Exception as e:
        logger.error(f"获取表 '{table_name}' 结构失败: {e}")
        return f"获取表 '{table_name}' 结构失败，错误信息: {e}"
    finally:
        conn.close()