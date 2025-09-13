import os
import glob
import importlib.util
import time
from logger import logger  # 导入配置好的 logger

from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器实例
mcp = FastMCP("Demo", port=8080, host="0.0.0.0")

# 定义工具目录
TOOLS_DIR = "tools"     

def load_tools_from_dir(dir_path: str):
    """
    从指定目录加载工具模块。
    这个函数会在服务器启动时和热重载时被调用。
    """
    full_dir = os.path.join(os.path.dirname(__file__), dir_path)
    if not os.path.isdir(full_dir):
        logger.warning(f"工具目录未找到: {full_dir}")
        return

    logger.info(f"正在从以下目录加载工具: {full_dir}")
    for path in glob.glob(os.path.join(full_dir, "*.py")):
        name = os.path.splitext(os.path.basename(path))[0]
        if name.startswith("_"):
            continue  # 忽略私有文件 (例如 __init__.py)
        try:
            # 创建一个唯一的模块名来避免重载时的冲突
            # 这对于 Python 的导入系统识别变化至关重要
            module_name = f"{dir_path}.{name}.{time.time_ns()}" 
            spec = importlib.util.spec_from_file_location(module_name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            logger.success(f"成功加载工具模块: {dir_path}/{name}.py")
        except Exception as e:
            logger.error(f"加载 {dir_path}/{name}.py 失败: {e}")

# --- 初始加载工具 ---
logger.info("--- 正在进行初始工具加载... ---")
load_tools_from_dir(TOOLS_DIR)
logger.info("--- 初始工具加载完成。 ---")

# --- 运行 MCP 服务器 ---
logger.info("--- 正在启动 MCP 服务器... ---")
mcp.run(transport="streamable-http")
