# mcp_server/default_tools/file_analysis_tool.py
import pandas as pd
import os
import io
import asyncio
import uuid
import matplotlib
matplotlib.use('Agg')
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from typing import Dict, Any
from server import mcp  # Import from centralized app
from logger import logger  # 从中央日志记录器导入
from dotenv import load_dotenv
from tabulate import tabulate

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
        agent_executor_kwargs={"handle_parsing_errors": True},
        allow_dangerous_code=True,
        max_iterations=15,
        max_execution_time=120
    )

    logger.warning("--- [CSV内容分析工具 - 安全警告] 即将执行由LLM生成的Python代码进行数据分析。 ---")

    plot_dir = "downloads"
    os.makedirs(plot_dir, exist_ok=True)
    plot_filename = f"plot_{uuid.uuid4()}.png"
    plot_filepath = os.path.join(plot_dir, plot_filename).replace('\\', '/')

    plot_instruction = (
        f"IMPORTANT: If you need to generate a plot, you MUST save it as a file. "
        f"Save the plot to the following path: '{plot_filepath}'. "
        f"After saving, you MUST respond with ONLY the markdown for the image, like this: "
        f"'![Generated Plot]({plot_filepath})'. "
        f"DO NOT use plt.show(). Just save the file and return the markdown path."
        f"\n\nUser's question: "
    )
    full_question = plot_instruction + question

    try:
        # The agent's ainvoke method is asynchronous
        result = await pandas_agent_executor.ainvoke({"input": full_question})
        
        output = result.get("output", "未能获得有效的输出。")
        
        # Check if the agent created a plot by checking if the file exists
        if os.path.exists(plot_filepath):
            logger.info(f"--- [CSV内容分析工具(Gemini)] 分析完成，生成了图表: {plot_filepath} ---")
            return f"![Generated Plot]({plot_filepath})"
        
        # If no plot, return the text output. The agent formats its own output.
        logger.info(f"--- [CSV内容分析工具(Gemini)] 分析完成，结果: {str(output)[:200]}... ---")
        return str(output)
    except Exception as e:
        logger.error(f"--- [CSV内容分析工具(Gemini) ERROR] 执行Pandas代码分析时出错: {e} ---")
        return f"执行Pandas代码分析时出错: {e}"
