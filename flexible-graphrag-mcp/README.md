# Flexible GraphRAG MCP Server

Standalone Model Context Protocol (MCP) server for Flexible GraphRAG system.

## Overview

This is a **standalone FastMCP server** that provides direct access to the Flexible GraphRAG backend through shared Python modules. Unlike the HTTP-based MCP client, this server has no REST overhead and calls the backend directly through Python imports.

## Installation

```bash
cd flexible-graphrag-mcp
uv pip install -r requirements.txt
```

## Usage

**No need to start the REST API backend!** This MCP server uses the shared backend directly.

1. **Install dependencies**:
   ```bash
   cd flexible-graphrag-mcp
   uv pip install -r requirements.txt
   ```

2. **Run the standalone MCP server**:
   ```bash
   uv run fastmcp-server.py
   ```

3. **Configure in Claude Desktop** (add to config):
   ```json
   {
     "mcpServers": {
       "flexible-graphrag": {
         "command": "uv",
         "args": ["run", "python", "/path/to/flexible-graphrag-mcp/fastmcp-server.py"],
         "cwd": "/path/to/flexible-graphrag-mcp"
       }
     }
   }
   ```

## Available Tools

### System Management
- `get_system_status()`: Get current system status and configuration
- `health_check()`: Check if backend is responsive
- `get_python_info()`: Get backend Python environment info

### Document Operations
- `ingest_documents(data_source, paths)`: Ingest documents from various sources
- `test_with_sample()`: Quick test with sample text

### Search & Query
- `search_documents(query, top_k)`: Hybrid search returning ranked results
- `query_documents(query, top_k)`: AI-generated answers to questions

## Configuration

The MCP server uses the same `.env` configuration as the main backend. Make sure your Neo4j and LLM settings are configured in the parent directory's `.env` file.

## Examples

Once configured in Claude Desktop, you can:

```
@flexible-graphrag Please ingest documents from my ~/Documents folder
```

```
@flexible-graphrag Search for "machine learning algorithms" in the documents
```

```
@flexible-graphrag What are the main conclusions from the research papers?
```