# mcp_server/default_tools/file_analysis_tool.py
import pandas as pd
import os
import io
import asyncio
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from typing import Dict, Any
from server import mcp  # Import from centralized app
from logger import logger  # 从中央日志记录器导入
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取环境变量
API_KEY = os.getenv("OPENAI_API_KEY")
ENDPOINT = os.getenv("OPENAI_API_BASE")

@mcp.tool()
async def analyze_csv_content(csv_content: str, question: str) -> str:
    """
    【CSV内容分析工具】此工具用于从给定的CSV文本内容中加载数据，并回答关于该数据的问题。
    它使用LangChain的Pandas DataFrame Agent来执行数据分析。

    Args:
        csv_content (str): 需要被分析的CSV文件的文本内容。
        question (str): 关于该CSV文件内容的自然语言问题。

    Returns:
        str: 数据分析的结果，或错误信息。
    """
    logger.info(f"--- [CSV内容分析工具(Gemini) - 默认工具] 正在分析CSV内容，问题: '{question}' ---")

    try:
        # Use io.StringIO to treat the string content as a file
        df = await asyncio.to_thread(pd.read_csv, io.StringIO(csv_content))
    except Exception as e:
        logger.error(f"--- [CSV内容分析工具(Gemini) ERROR] 解析CSV内容时出错: {e} ---")
        return f"错误: 解析CSV内容时出错: {e}"

    llm = ChatOpenAI(
        model="google/gemini-2.5-pro",  # 使用最新的Gemini 2.5 Pro 模型
        temperature=0.1,
        api_key=API_KEY,
        base_url=ENDPOINT
    )
    
    # 创建Pandas DataFrame Agent
    pandas_agent_executor = create_pandas_dataframe_agent(
        llm=llm,
        df=df,
        verbose=False, # 设置为True可以在控制台查看LLM生成的Python代码
        agent_executor_kwargs={"handle_parsing_errors": True}
    )

    logger.warning("--- [CSV内容分析工具 - 安全警告] 即将执行由LLM生成的Python代码进行数据分析。 ---")
    try:
        # The agent's ainvoke method is asynchronous
        result = await pandas_agent_executor.ainvoke({"input": question})
        
        # Pandas DataFrame Agent 的结果通常在 "output" 键中
        output = result.get("output", "未能获得有效的输出。")
        logger.info(f"--- [CSV内容分析工具(Gemini)] 分析完成，结果: {output[:200]}... ---") # 截断部分结果日志
        return output
    except Exception as e:
        logger.error(f"--- [CSV内容分析工具(Gemini) ERROR] 执行Pandas代码分析时出错: {e} ---")
        return f"执行Pandas代码分析时出错: {e}"
