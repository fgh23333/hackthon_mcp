import os
from tavily import TavilyClient
from dotenv import load_dotenv
from server import mcp
from logger import logger
from ragflow_sdk import RAGFlow
import httpx
from typing import List, Dict
import tempfile

# 加载环境变量
load_dotenv()
RAGFLOW_DATASET_ID = os.getenv("RAGFLOW_DATASET_ID")

@mcp.tool()
def tavily_search(query: str, max_results: int = 5, topic: str = "general"):
    """
    【Tavily搜索工具】此工具使用Tavily API执行网络搜索。

    Args:
        query (str): 要搜索的问题或关键词。
        max_results (int): 返回的最大结果数。
        topic (str): 搜索主题，可以是 'general' (常规) 或 'news' (新闻)。

    Returns:
        list: 搜索结果列表，或在出错时返回错误信息字符串。
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY 环境变量未设置。")
    
    client = TavilyClient(api_key=api_key)
    try:
        response = client.search(query=query, topic=topic, max_results=max_results)
        return response['results']
    except Exception as e:
        return f"Tavily搜索时发生错误: {e}"

@mcp.tool()
def find_paper_url(query: str) -> Dict[str, str]:
    """
    【论文URL查找工具】此工具根据查询词在arXiv.org上搜索学术论文，并返回其PDF的URL。

    Args:
        query (str): 要搜索的论文标题或关键词。

    Returns:
        dict: 包含查找状态和PDF URL的字典。
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY 环境变量未设置。")

    client = TavilyClient(api_key=api_key)
    
    try:
        # 1. 优化查询，优先搜索arXiv
        search_query = f'{query} site:arxiv.org'
        response = client.search(query=search_query, max_results=5)
        results = response.get('results', [])

        if not results:
            return {"status": "not_found", "message": "未找到相关论文。"}

        # 2. 查找PDF链接
        for result in results:
            url = result.get('url')
            # 优先寻找arXiv和常见论文网站的PDF链接
            if url and ('arxiv.org/pdf' in url or url.endswith('.pdf')):
                return {
                    "status": "success",
                    "url": url
                }

        return {"status": "not_found", "message": "找到了相关论文，但未能找到可直接下载的PDF源文件。"}

    except Exception as e:
        return {"status": "error", "message": f"在查找论文时发生错误: {e}"}

def download_and_upload(url: str) -> dict:
    """
    工具一：从URL下载文件，并将其上传到指定的RagFlow知识库。
    
    Args:
        url: 要下载的文件的公开URL。

    Returns:
        一个包含操作结果的字典。成功时包含 'doc_id'，失败时包含 'error'。
    """
    print(f"  [Action] 正在从URL下载文件: {url}")
    try:
        # CHANGED: 使用 httpx 进行同步流式下载
        with httpx.stream("GET", url, follow_redirects=True, timeout=30.0) as response_download:
            response_download.raise_for_status()  # 检查下载是否成功

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                for chunk in response_download.iter_bytes(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_file_path = tmp_file.name
        
        print(f"  [Action] 文件已下载到临时路径: {tmp_file_path}")
        print(f"  [Action] 正在上传到知识库 '{RAGFLOW_DATASET_ID}'...")
        
        # 使用 ragflow-sdk 上传文档
        result = RAGFlow.upload_document(tmp_file_path, RAGFLOW_DATASET_ID)
        
        os.remove(tmp_file_path) # 清理临时文件
        
        # SDK返回的结果通常是一个字典，我们提取关键信息
        if "doc_id" in result:
            return {"status": "success", "doc_id": result["doc_id"]}
        else:
            return {"status": "error", "message": f"SDK上传失败，返回信息: {result}"}

    except Exception as e:
        return {"status": "error", "message": f"下载或上传过程中发生错误: {e}"}
