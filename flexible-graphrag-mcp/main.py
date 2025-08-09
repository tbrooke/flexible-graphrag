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

# Windows encoding is handled by environment variables in Claude Desktop config:
# PYTHONIOENCODING=utf-8 and PYTHONLEGACYWINDOWSSTDIO=1

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
async def ingest_documents(data_source: str = "filesystem", paths: str = None) -> Dict[str, Any]:
    """
    Ingest documents from a data source
    
    Args:
        data_source: Type of data source (filesystem, cmis, alfresco)  
        paths: Single file path or JSON array of paths (for filesystem source)
    """
    try:
        request_data = {"data_source": data_source}
        if paths:
            # Handle both single path string and JSON array string
            import json
            try:
                # Try to parse as JSON array first
                parsed_paths = json.loads(paths)
                if isinstance(parsed_paths, list):
                    request_data["paths"] = parsed_paths
                else:
                    request_data["paths"] = [str(parsed_paths)]
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as single path
                request_data["paths"] = [paths]
            
        result = await make_api_call("POST", "/api/ingest", request_data)
        return result  # Return the async processing response directly
    except Exception as e:
        return {
            "processing_id": "error", 
            "status": "failed", 
            "message": f"Failed to start document processing: {str(e) or 'Unknown error'}", 
            "progress": 0
        }

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
async def ingest_text(content: str, source_name: str = "mcp-input") -> Dict[str, Any]:
    """
    Ingest raw text content into the knowledge graph
    
    Args:
        content: Text content to ingest
        source_name: Name/identifier for this text source
    """
    try:
        request_data = {"content": content, "source_name": source_name}
        result = await make_api_call("POST", "/api/ingest-text", request_data)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
async def check_processing_status(processing_id: str) -> Dict[str, Any]:
    """
    Check the status of an async processing operation
    
    Args:
        processing_id: The processing ID returned from ingest_text
    """
    try:
        result = await make_api_call("GET", f"/api/processing-status/{processing_id}")
        return {"success": True, "processing": result}
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

def main():
    """Run the MCP server"""
    import sys
    
    # Check for HTTP mode via command line arguments
    http_mode = "--http" in sys.argv or "--serve" in sys.argv
    
    # Check for --transport http pattern
    if "--transport" in sys.argv:
        try:
            transport_idx = sys.argv.index("--transport") + 1
            if transport_idx < len(sys.argv) and sys.argv[transport_idx].lower() == "http":
                http_mode = True
        except (IndexError, ValueError):
            pass
    port = 3001  # Default MCP Inspector port
    host = "localhost"  # Default host
    
    # Parse port argument
    if "--port" in sys.argv:
        try:
            port_idx = sys.argv.index("--port") + 1
            port = int(sys.argv[port_idx])
        except (IndexError, ValueError):
            port = 3001
    
    # Parse host argument
    if "--host" in sys.argv:
        try:
            host_idx = sys.argv.index("--host") + 1
            host = sys.argv[host_idx]
        except IndexError:
            host = "localhost"
    
    # Log to stderr instead of stdout to avoid interfering with MCP protocol
    sys.stderr.write("🚀 Starting Flexible GraphRAG MCP Server\n")
    sys.stderr.write(f"📡 Backend URL: {BACKEND_URL}\n")
    
    if http_mode:
        sys.stderr.write(f"🌐 Running in HTTP mode on {host}:{port}\n")
        sys.stderr.write("🔍 Suitable for MCP Inspector debugging\n")
    else:
        sys.stderr.write("📱 Running in stdio mode for Claude Desktop\n")
    
    sys.stderr.write("🛠️  Available tools:\n")
    sys.stderr.write("   • get_system_status\n")
    sys.stderr.write("   • ingest_documents\n")
    sys.stderr.write("   • search_documents\n") 
    sys.stderr.write("   • query_documents\n")
    sys.stderr.write("   • test_with_sample\n")
    sys.stderr.write("   • ingest_text\n")
    sys.stderr.write("   • check_processing_status\n")
    sys.stderr.write("   • get_python_info\n")
    sys.stderr.write("   • health_check\n")
    sys.stderr.flush()
    
    # Run the MCP server
    try:
        # Apply nest_asyncio to handle nested event loops
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass
    
    if http_mode:
        # Run HTTP server for MCP Inspector
        asyncio.run(mcp.run_http_async(host=host, port=port))
    else:
        # Run stdio server for Claude Desktop
        asyncio.run(mcp.run_async())

if __name__ == "__main__":
    main()