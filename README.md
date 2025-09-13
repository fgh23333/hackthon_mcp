# Hackathon MCP Server

这是一个基于 FastMCP 框架的 MCP (Model Context Protocol) 服务器。它提供了一系列工具，用于与 RAGFlow 知识库和 MySQL 数据库进行交互。

## 功能

- **动态工具加载**: 服务器会自动从 `tools/` 目录加载所有 Python 工具模块。
- **RAGFlow 集成**:
    - 从指定的 RAGFlow 数据集检索知识。
    - 列出所有可用的知识库。
    - 列出特定知识库中的文档。
- **数据库交互**:
    - 连接到 MySQL 数据库。
    - 列出所有数据库。
    - 获取数据库的表结构 (Schema)。
    - 执行只读的 SQL 查询。

## 安装与配置

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/fgh23333/hackthon_mcp.git
    cd hackthon_mcp
    ```

2.  **创建并激活虚拟环境**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```

3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **配置环境变量**:
    复制 `.env.example` 文件为 `.env`：
    ```bash
    # Windows
    copy .env.example .env
    # macOS/Linux
    cp .env.example .env
    ```
    然后，编辑 `.env` 文件，填入你的 RAGFlow 和数据库的配置信息：
    ```env
    # RAGFlow Configuration
    RAGFLOW_BASE_URL=http://your-ragflow-host:8000
    RAGFLOW_API_KEY=YOUR_RAGFLOW_API_KEY
    RAGFLOW_DATASET_ID=YOUR_DEFAULT_DATASET_ID

    # Database Configuration
    DB_HOST=your-database-host
    DB_PORT=3306
    DB_USER=your-database-user
    DB_PASSWORD=your-database-password
    ```

## 运行服务器

配置完成后，运行以下命令启动 MCP 服务器：

```bash
python server.py
```

服务器将在 `http://0.0.0.0:8080` 上启动。

## 可用工具

### RAG 工具 (`tools/rag_tool.py`)

- `knowledge_retrieval_tool(query: str, dataset_id: str)`: 从指定的知识库中检索信息。
- `list_knowledge_bases(...)`: 列出所有可用的知识库。
- `list_documents(dataset_id: str, ...)`: 列出指定知识库中的所有文档。

### 数据库工具 (`tools/database_tools.py`)

- `list_databases()`: 列出所有数据库名称。
- `get_schema_of_database(db_name: str)`: 获取指定数据库的完整表结构。
- `run_readonly_query_in_database(db_name: str, query: str)`: 执行只读的 SQL 查询。
- `list_tables_in_database(db_name: str)`: (后备工具) 列出数据库中的所有表。
- `describe_table_in_database(db_name: str, table_name: str)`: (后备工具) 获取单个表的结构。
