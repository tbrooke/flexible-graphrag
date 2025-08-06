#!/usr/bin/env python3
"""
MCP Server for Flexible GraphRAG
Uses the flexible-graphrag backend through HTTP API calls
"""

import asyncio
import os
import sys
import httpx
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP

# Add parent directory to path to import from flexible-graphrag
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'flexible-graphrag'))

# Default backend URL
BACKEND_URL = os.getenv("FLEXIBLE_GRAPHRAG_URL", "http://localhost:8000")

# Initialize MCP server
mcp = FastMCP("flexible-graphrag-mcp")

async def make_api_call(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP API call to the flexible-graphrag backend"""
    async with httpx.AsyncClient() as client:
        url = f"{BACKEND_URL}{endpoint}"
        
        if method.upper() == "GET":
            response = await client.get(url)
        elif method.upper() == "POST":
            response = await client.post(url, json=data or {})
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def get_system_status() -> Dict[str, Any]:
    """Get the current status of the flexible-graphrag system"""
    try:
        result = await make_api_call("GET", "/api/status")
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
async def ingest_documents(data_source: str = "filesystem", paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Ingest documents from a data source
    
    Args:
        data_source: Type of data source (filesystem, cmis, alfresco)
        paths: List of file/folder paths (for filesystem source)
    """
    try:
        request_data = {"data_source": data_source}
        if paths:
            request_data["paths"] = paths
            
        result = await make_api_call("POST", "/api/ingest", request_data)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
async def search_documents(query: str, top_k: int = 10) -> Dict[str, Any]:
    """
    Search documents using hybrid search
    
    Args:
        query: Search query string
        top_k: Number of results to return
    """
    try:
        request_data = {"query": query, "top_k": top_k}
        result = await make_api_call("POST", "/api/search", request_data)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
async def query_documents(query: str, top_k: int = 10) -> Dict[str, Any]:
    """
    Query documents with AI-generated answers
    
    Args:
        query: Question to ask
        top_k: Number of source documents to consider
    """
    try:
        request_data = {"query": query, "top_k": top_k}
        result = await make_api_call("POST", "/api/query", request_data)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
async def test_with_sample() -> Dict[str, Any]:
    """Test the system with sample text for quick verification"""
    try:
        result = await make_api_call("POST", "/api/test-sample")
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
async def get_python_info() -> Dict[str, Any]:
    """Get information about the Python environment of the backend"""
    try:
        result = await make_api_call("GET", "/api/python-info")
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Check if the backend is healthy and responsive"""
    try:
        result = await make_api_call("GET", "/api/health")
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def main():
    """Run the MCP server"""
    print(f"🚀 Starting Flexible GraphRAG MCP Server")
    print(f"📡 Backend URL: {BACKEND_URL}")
    print(f"🛠️  Available tools:")
    print(f"   • get_system_status")
    print(f"   • ingest_documents")
    print(f"   • search_documents") 
    print(f"   • query_documents")
    print(f"   • test_with_sample")
    print(f"   • get_python_info")
    print(f"   • health_check")
    
    # Run the MCP server
    await mcp.run()

if __name__ == "__main__":
    asyncio.run(main())