# Flexible GraphRAG Backend

This is the Python FastAPI backend for the Flexible GraphRAG system. It provides REST API endpoints for processing documents from CMIS repositories and querying knowledge graphs using GraphRAG.

## Features

- **CMIS Integration**: Connect to CMIS-compliant repositories (Alfresco, Nuxeo, etc.)
- **Knowledge Graph Building**: Uses Neo4j's GraphRAG library to build knowledge graphs
- **Vector Search**: Supports vector-based document search and retrieval
- **LLM Integration**: Works with both OpenAI and Ollama models
- **REST API**: FastAPI-based endpoints for processing and querying

## About CMIS

[CMIS (Content Management Interoperability Services)](https://en.wikipedia.org/wiki/Content_Management_Interoperability_Services) is a standard that allows different content management systems to inter-operate over the Internet.

For more information: [Libraries Supporting KG building and GraphRAG](https://github.com/stevereiner/cmis-graphrag/blob/main/Libraries%20Supporting%20KG%20building%20and%20GraphRAG.md)

## LLM Models Supported

- **OpenAI**: GPT-4.1-mini and other OpenAI models
- **Ollama**: llama3.1:8b and other local models

## Prerequisites

### Python
- Python 3.10+ (supports 3.10, 3.11, 3.12, 3.13)
- UV package manager

### CMIS Repository Requirements
Your CMIS server needs to support CMIS 1.0 or CMIS 1.1:
- **Alfresco** (CMIS 1.1)
- **Nuxeo** (CMIS 1.1)  
- **OpenText Documentum, OpenText Content Management, OpenText eDocs** (CMIS 1.1)
- **SAP Hana, SAP Extended ECM, SAP Mobile** (CMIS 1.1)
- **IBM FileNet Content Manager, IBM Content Manager** (full CMIS 1.0, partial CMIS 1.1)
- **Microsoft SharePoint Server** (CMIS 1.0, on premises only)

### Neo4j Database Requirements

**Neo4j Server Versions Supported:**
- Neo4j >= 2025.01
- Neo4j >= 5.18.1

**You can use:**
- Neo4j Enterprise Edition (Self Hosted)
- Neo4j Community Edition (Free, Self hosted)
- Neo4j Desktop (Free, Windows, Mac, Linux)
- Neo4j AuraDB (free, professional, mission critical tiers) + Graph Analytics Serverless
- Neo4j AuraDS

**APOC Core is Required:**
- **Neo4j Desktop**: Install APOC core plugin (expand side panel), restart
- **Neo4j Enterprise**: Copy APOC core jar from /product to /plugins dir, restart
- **Neo4j Community**: Download APOC core and copy to /plugins dir, restart
- **Neo4j AuraDB/AuraDS**: Have subset of APOC core with required features

**GDS (Graph Data Science) is Required:**
- **Neo4j Desktop**: Install GDS plugin (expand side panel), restart
- **Neo4j Enterprise**: Copy GDS jar from /labs to /plugins dir, restart
- **Neo4j Community**: Download GDS jar and copy to /plugins dir, restart
- **Neo4j AuraDB**: Requires Neo4j Graph Analytics Serverless or Neo4j AuraDS
- **Neo4j AuraDS**: Includes GDS

### LLM Requirements
- **OpenAI API key** OR **Ollama installation**
- For Ollama: Pull required models (e.g., `ollama pull llama3.1:8b`, `ollama pull mxbai-embed-large`)

## Installation

1. Create and activate a virtual environment using UV:
   ```bash
   # From project root directory
   uv venv
   .\.venv\Scripts\Activate  # On Windows (works in both Command Prompt and PowerShell)
   # or
   source .venv/bin/activate  # on macOS/Linux
   ```

2. Install dependencies:
   ```bash
   # Navigate to flexible-graphrag directory and install requirements
   cd flexible-graphrag
   uv pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration:
   ```env
   # CMIS Configuration
   CMIS_URL=http://your-cmis-server/alfresco/api/-default-/public/cmis/versions/1.1/atom
   CMIS_USERNAME=your-username
   CMIS_PASSWORD=your-password
   
   # Neo4j Configuration
   NEO4J_URI=neo4j://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-neo4j-password
   
   # LLM Configuration
   USE_OPENAI=true  # Set to false to use Ollama
   OPENAI_API_KEY=your-openai-api-key  # If using OpenAI
   OPENAI_MODEL=gpt-4.1-mini  # If using OpenAI
   OLLAMA_MODEL=llama3.1:8b  # If using Ollama
   ```

## Running the Server

Start the FastAPI development server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### Health Check
- `GET /api/health` - Check if the API is running

### Document Processing
- `POST /api/process-folder` - Process documents from a CMIS folder
  ```json
  {
    "folder_path": "/Shared/GraphRAG"
  }
  ```

### Querying
- `POST /api/query` - Query the knowledge graph
  ```json
  {
    "question": "What are the main topics in the documents?"
  }
  ```

### Graph Data
- `GET /api/graph` - Get graph data (nodes and relationships)

### Testing
- `POST /api/test-sample` - Process sample text for testing

### System Info
- `GET /api/python-info` - Get Python environment information

## File Structure

- `main.py` - FastAPI application and API endpoints
- `cmis_util.py` - CMIS repository interaction utilities
- `neo4j_util.py` - Neo4j database and GraphRAG utilities
- `requirements.txt` - Python dependencies
- `.env` - Environment configuration (create from dot-env-sample.txt)

## Development

The server runs in development mode with auto-reload enabled. Any changes to the Python files will automatically restart the server.

For debugging, you can use the VS Code launch configurations provided in the project root.

## Notes

- Only PDF documents are currently supported
- The system builds knowledge graphs using Neo4j's GraphRAG library
- Both vector search and graph-based search are supported
- For production use, configure proper security and authentication

## Neo4j Console Commands

### Viewing Data
```cypher
// View limited nodes
MATCH (n) RETURN n LIMIT 25

// View all nodes
MATCH (n) RETURN n

// Show all indexes
SHOW INDEXES
```

### Cleanup Commands (for testing)
**⚠️ Warning: These commands will delete data. Use only on test databases.**

```cypher
// Delete all nodes and relationships
MATCH (n) DETACH DELETE n

// Verify deletion
MATCH (n) RETURN n

// Drop specific indexes (don't touch other indexes)
DROP INDEX __entity__id IF EXISTS
DROP INDEX vector_index_openai IF EXISTS
DROP INDEX vector_index_ollama IF EXISTS

// Show remaining indexes
SHOW INDEXES
```

## CMIS Library Information

- **Package**: cmislib 0.7.0
- **PyPI**: [cmislib 0.7.0](https://pypi.org/project/cmislib/)
- **Summary**: Apache Chemistry CMIS client library for Python
- **Info**: [Apache Chemistry](http://chemistry.apache.org/)
- **Note**: cmislib 0.7.0 supports Python 3.x (previous versions were Python 2.x only)