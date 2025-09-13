import os
from tavily import TavilyClient
from dotenv import load_dotenv
from server import mcp

# 加载环境变量
load_dotenv()

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
def find_and_download_paper(query: str, download_dir: str = "downloads"):
    """
    【论文查找与下载工具】此工具根据查询词在arXiv.org上搜索学术论文，下载其PDF源文件，并以Base64编码返回文件内容。

    Args:
        query (str): 要搜索的论文标题或关键词。
        download_dir (str): 用于存放下载文件的目录。

    Returns:
        dict: 包含下载状态、文件名和Base64编码文件内容的字典。
    """
    import httpx
    import base64
    from typing import Dict

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

        # 2. 查找并下载PDF链接
        for result in results:
            url = result.get('url')
            # 优先寻找arXiv和常见论文网站的PDF链接
            if url and ('arxiv.org/pdf' in url or url.endswith('.pdf')):
                try:
                    with httpx.stream("GET", url, follow_redirects=True, timeout=30) as r:
                        r.raise_for_status()
                        
                        # 从URL中提取文件名
                        file_name = url.split('/')[-1]
                        if not file_name.endswith('.pdf'):
                            file_name += '.pdf'
                        
                        file_path = os.path.join(download_dir, file_name)
                        
                        # 确保下载目录存在
                        os.makedirs(download_dir, exist_ok=True)

                        # 将文件内容读入内存
                        pdf_content = r.read()

                        # 保存文件到本地
                        with open(file_path, 'wb') as f:
                            f.write(pdf_content)
                        
                        # Base64编码文件内容
                        content_base64 = base64.b64encode(pdf_content).decode('utf-8')
                        
                        return {
                            "status": "success",
                            "filename": file_name,
                            "saved_path": file_path,
                            "content_base64": content_base64
                        }
                except Exception as e:
                    continue # 如果下载失败，尝试下一个结果

        return {"status": "not_found", "message": "找到了相关论文，但未能找到可直接下载的PDF源文件。"}

    except Exception as e:
        return {"status": "error", "message": f"在查找或下载论文时发生错误: {e}"}
