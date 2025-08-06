#!/usr/bin/env python3
"""
Standalone FastMCP Server for Flexible GraphRAG
This is a proper remote MCP server that calls the shared backend
"""

import asyncio
import sys
import os
import logging
from typing import List, Dict, Any, Optional

# Add the flexible-graphrag directory to the path to access shared backend
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'flexible-graphrag'))

from fastmcp import FastMCP
from backend import get_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("flexible-graphrag-mcp")

@mcp.tool()
def get_system_status() -> Dict[str, Any]:
    """Get system status and configuration"""
    try:
        backend = get_backend()
        return backend.get_system_status()
    except Exception as e:
        logger.error(f"Error in get_system_status: {e}")
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
        backend = get_backend()
        return await backend.ingest_documents(data_source=data_source, paths=paths)
    except Exception as e:
        logger.error(f"Error in ingest_documents: {e}")
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
        backend = get_backend()
        return await backend.search_documents(query=query, top_k=top_k)
    except Exception as e:
        logger.error(f"Error in search_documents: {e}")
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
        backend = get_backend()
        return await backend.query_documents(query=query, top_k=top_k)
    except Exception as e:
        logger.error(f"Error in query_documents: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def ingest_text(content: str, source_name: str = "mcp-input") -> Dict[str, Any]:
    """
    Ingest raw text content
    
    Args:
        content: Text content to ingest
        source_name: Name for the text source
    """
    try:
        backend = get_backend()
        return await backend.ingest_text(content=content, source_name=source_name)
    except Exception as e:
        logger.error(f"Error in ingest_text: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def get_config() -> Dict[str, Any]:
    """Get current system configuration"""
    try:
        backend = get_backend()
        return backend.get_config()
    except Exception as e:
        logger.error(f"Error in get_config: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def health_check() -> Dict[str, Any]:
    """Check if the system is healthy and responsive"""
    try:
        backend = get_backend()
        return backend.health_check()
    except Exception as e:
        logger.error(f"Error in health_check: {e}")
        return {"success": False, "error": str(e)}

async def main():
    """Run the MCP server"""
    logger.info("🚀 Starting Standalone Flexible GraphRAG MCP Server")
    logger.info("🛠️  Available tools:")
    logger.info("   • get_system_status - Get system status and configuration")
    logger.info("   • ingest_documents - Ingest documents from various sources")
    logger.info("   • search_documents - Hybrid search for document retrieval") 
    logger.info("   • query_documents - AI-generated answers from documents")
    logger.info("   • ingest_text - Ingest raw text content")
    logger.info("   • get_config - Get current configuration")
    logger.info("   • health_check - System health check")
    logger.info("")
    logger.info("📡 This MCP server uses the shared backend directly (no HTTP overhead)")
    
    # Run the MCP server
    await mcp.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server error: {e}")
        sys.exit(1)