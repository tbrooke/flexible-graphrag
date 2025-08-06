"""
Shared backend core for Flexible GraphRAG
This module contains the business logic that can be called by both FastAPI and FastMCP servers
"""

import logging
from typing import List, Dict, Any, Union, Optional
from pathlib import Path

from config import Settings
from hybrid_system import HybridSearchSystem
from sources import FileSystemSource

logger = logging.getLogger(__name__)

class FlexibleGraphRAGBackend:
    """Shared backend core for both REST API and MCP server"""
    
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self._system = None
        logger.info("FlexibleGraphRAGBackend initialized")
    
    @property
    def system(self) -> HybridSearchSystem:
        """Lazy-load the hybrid search system"""
        if self._system is None:
            self._system = HybridSearchSystem.from_settings(self.settings)
            logger.info("HybridSearchSystem initialized")
        return self._system
    
    # Core business logic methods
    
    async def ingest_documents(self, data_source: str = None, paths: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Ingest documents from various data sources"""
        try:
            data_source = data_source or self.settings.data_source
            
            if data_source == "filesystem":
                file_paths = paths or self.settings.source_paths
                if not file_paths:
                    return {"success": False, "error": "No file paths provided for filesystem source"}
                
                # Clean paths - remove extra quotes that might come from frontend
                cleaned_paths = []
                for path in file_paths:
                    if isinstance(path, str):
                        # Remove surrounding quotes if present
                        cleaned_path = path.strip('"').strip("'")
                        cleaned_paths.append(cleaned_path)
                        logger.info(f"Cleaned path: {path} -> {cleaned_path}")
                    else:
                        cleaned_paths.append(path)
                
                await self.system.ingest_documents(cleaned_paths)
                return {"success": True, "message": f"Ingested documents from {len(cleaned_paths)} paths"}
                
            elif data_source == "cmis":
                await self.system.ingest_cmis()
                return {"success": True, "message": "Ingested documents from CMIS"}
                
            elif data_source == "alfresco":
                await self.system.ingest_alfresco()
                return {"success": True, "message": "Ingested documents from Alfresco"}
                
            else:
                return {"success": False, "error": f"Unsupported data source: {data_source}"}
                
        except Exception as e:
            logger.error(f"Error during ingestion: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def search_documents(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Search documents using hybrid search"""
        try:
            results = await self.system.search(query, top_k=top_k)
            return {"success": True, "results": results}
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def query_documents(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Query documents with AI-generated answers"""
        try:
            query_engine = self.system.get_query_engine()
            response = await query_engine.aquery(query)
            return {"success": True, "answer": str(response)}
        except Exception as e:
            logger.error(f"Error during query: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def ingest_text(self, content: str, source_name: str = "text_input") -> Dict[str, Any]:
        """Ingest raw text content"""
        try:
            await self.system.ingest_text(content=content, source_name=source_name)
            return {"success": True, "message": "Text content ingested successfully"}
        except Exception as e:
            logger.error(f"Error ingesting text: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            return {"success": True, "status": self.system.state()}
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            "success": True,
            "config": {
                "data_source": self.settings.data_source,
                "vector_db": self.settings.vector_db,
                "graph_db": self.settings.graph_db,
                "llm_provider": self.settings.llm_provider
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check"""
        return {"success": True, "status": "ok"}

# Global backend instance
_backend_instance = None

def get_backend() -> FlexibleGraphRAGBackend:
    """Get the global backend instance"""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = FlexibleGraphRAGBackend()
    return _backend_instance