import os
import httpx
from ragflow_sdk import RAGFlow
from logger import logger
from dotenv import load_dotenv
from typing import Dict, Any, List
from server import mcp
import time

load_dotenv()

# --- RagFlow API 的配置 ---
RAGFLOW_BASE_URL = os.getenv("RAGFLOW_BASE_URL", "http://localhost:8000")
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "YOUR_API_KEY_HERE")
RAGFLOW_DATASET_ID = os.getenv("RAGFLOW_DATASET_ID", "YOUR_DATASET_ID_HERE")

# 初始化 RAGFlow 客户端
rag_flow = RAGFlow(api_key=RAGFLOW_API_KEY, base_url=RAGFLOW_BASE_URL)

@mcp.tool()
def knowledge_retrieval_tool(query: str, dataset_id: str = RAGFLOW_DATASET_ID) -> Dict[str, Any]:
    """
    根据用户问题，从指定的RagFlow知识库数据集中检索相关文档。

    Args:
        query (str): 要查询的问题或关键词。
        dataset_id (str): 要查询的RagFlow知识库数据集ID。此参数为必需项。

    Returns:
        一个包含检索结果的字典。
    """
    logger.info(f"--- 🛠️ 执行工具: knowledge_retrieval_tool (query='{query}', dataset_id='{dataset_id}') ---")

    # --- 新增：强制检查 dataset_id ---
    if not dataset_id or dataset_id == "YOUR_DATASET_ID_HERE":
        error_msg = "知识库检索失败：调用 knowledge_retrieval_tool 时未提供有效的 'dataset_id'。"
        logger.error(error_msg)
        return {"status": "error", "error_message": error_msg}

    try:
        # 调用 RAGFlow SDK 进行检索
        chunks = rag_flow.retrieve(
            question=query,
            dataset_ids=[dataset_id]
        )
        if chunks:
            processed_chunks = []
            for r in chunks:
                if hasattr(r, 'text'):
                    processed_chunks.append(r.text)
                elif isinstance(r, dict) and 'content' in r:
                    processed_chunks.append(r['content'])
                else:
                    processed_chunks.append(str(r))
            
            result_content = "\n\n".join(processed_chunks)
            logger.info(f"工具输出: {result_content}")
            return {"status": "success", "summary": result_content}
        else:
            logger.info("工具输出: 在知识库中没有找到相关信息。")
            return {"status": "not_found", "summary": "在知识库中没有找到相关信息。"}
    except httpx.RequestError as e:
        logger.error(f"RagFlow知识库检索失败: {e}")
        return {"status": "error", "error_message": f"知识库检索失败，错误信息: {e}"}

@mcp.tool()
async def list_knowledge_bases(page: int = 1, page_size: int = 30, orderby: str = "create_time", desc: bool = True, id: str = "", name: str = "") -> List[dict]:
    """
    Lists all knowledge bases (datasets).

    Args:
        page: Specifies the page on which the datasets will be displayed. Defaults to 1.
        page_size: The number of datasets on each page. Defaults to 30.
        orderby: The field by which datasets should be sorted. Defaults to "create_time".
        desc: Indicates whether the retrieved datasets should be sorted in descending order. Defaults to True.
        id: The ID of the dataset to retrieve. Defaults to an empty string.
        name: The name of the dataset to retrieve. Defaults to an empty string.

    Returns:
        A list of dataset objects.
    """
    id = None if not id else id
    name = None if not name else name

    try:
        datasets = rag_flow.list_datasets(page=page, page_size=page_size, orderby=orderby, desc=desc, id=id, name=name)
        return [
            {
                "id": ds.id,
                "name": ds.name,
                "document_count": ds.document_count,
                "chunk_count": ds.chunk_count,
                "embedding_model": ds.embedding_model,
                "permission": ds.permission,
                "description": ds.description,
                "avatar": ds.avatar,
            }
            for ds in datasets
        ]
    except Exception as e:
        logger.error(f"Error retrieving datasets: {e}")
        return [{"error": str(e)}]

@mcp.tool()
async def list_documents(
    dataset_id: str,
    page: int = 1,
    page_size: int = 30,
    base_url: str = RAGFLOW_BASE_URL
) -> Dict:
    """
    Lists documents within a specific dataset.

    Args:
        dataset_id: The ID of the dataset.
        page: The page number for pagination. Defaults to 1.
        page_size: The number of documents per page. Defaults to 30.
        orderby: The field to order the results by. Defaults to "create_time".
        desc: Whether to sort in descending order. Defaults to True.
        keywords: Keywords to search for in document names. Defaults to None.
        id: The specific ID of the document to retrieve. Defaults to None.
        name: The name of the document to retrieve. Defaults to None.
        base_url: The base URL of the RAGFlow API. Defaults to RAGFLOW_BASE_URL.

    Returns:
        A dictionary containing the list of documents and pagination details.
    """
    try:
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        url = f"{base_url}/api/v1/datasets/{dataset_id}/documents"
        headers = {"Authorization": f"Bearer {RAGFLOW_API_KEY}"}
        params = {
            "page": page,
            "page_size": page_size
        }
        # Filter out None values from params
        params = {k: v for k, v in params.items() if v is not None}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error listing documents: {e.response.text}")
        return {"error": f"HTTP error: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing documents: {e}")
        return {"error": str(e)}

def _trigger_parsing_and_wait(dataset, document_ids: List[str], timeout: int = 20) -> Dict:
    """
    Triggers parsing for given document IDs and waits until all are done.

    Args:
        dataset: The dataset object from RAGFlow.
        document_ids: List of document IDs to parse.
        timeout: Max time to wait in seconds (default 20).

    Returns:
        A dictionary with status and message.
    """
    if not document_ids:
        return {"status": "skipped", "message": "No documents to parse."}

    try:
        dataset.async_parse_documents(document_ids=document_ids)
        logger.info(f"Parsing triggered for documents: {document_ids}")

        for doc_id in document_ids:
            i = 0
            current_doc = dataset.list_documents(id=doc_id)[0]
            while current_doc.run != "DONE":
                logger.info(f"Current parsing status for {doc_id}: {current_doc.run}. Will sleep 1 second.")
                time.sleep(1)
                current_doc = dataset.list_documents(id=doc_id)[0]
                i += 1
                if i >= timeout:
                    error_msg = f"Document parsing exceeded time limit: {timeout} s."
                    logger.error(error_msg)
                    return {"error": error_msg}
                elif current_doc.run == "FAIL":
                    error_msg = f"Document parsing failed for {doc_id}. Final status: {current_doc.run}"
                    logger.error(error_msg)
                    return {"error": error_msg}

            logger.success(f"Parsing completed for {doc_id}. Final status: {current_doc.run}")

        return {
            "status": "success",
            "message": f"Documents parsed successfully: {document_ids}"
        }
    except Exception as e:
        logger.error(f"Error during parsing: {e}")
        return {"error": str(e)}

@mcp.tool()
async def trigger_parsing_and_wait(
    document_ids: List[str],
    timeout: int = 20
) -> Dict:
    """
    Triggers parsing for given document IDs and waits until all are done.

    Args:
        document_ids: List of document IDs to parse.
        timeout: Max time to wait in seconds (default 20).

    Returns:
        A dictionary with status and message.
    """
    if not document_ids:
        return {"status": "skipped", "message": "No documents to parse."}

    try:
        # 2. 获取 dataset 实例
        dataset = rag_flow.list_datasets(id=RAGFLOW_DATASET_ID)[0]
        result = await _trigger_parsing_and_wait(dataset, document_ids, timeout) # TODO wait
        # 3. 调用内部函数处理解析逻辑
        return result

    except Exception as e:
        logger.error(f"Error linking to RAGFlow dataset {RAGFLOW_DATASET_ID}: {e}")
        return {"error": str(e)}