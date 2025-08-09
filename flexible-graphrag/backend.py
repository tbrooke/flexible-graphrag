"""
Shared backend core for Flexible GraphRAG
This module contains the business logic that can be called by both FastAPI and FastMCP servers
"""

import logging
import uuid
import asyncio
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass
from datetime import datetime
from typing import List, Dict, Any, Union, Optional
from pathlib import Path

from config import Settings
from hybrid_system import HybridSearchSystem
from sources import FileSystemSource

logger = logging.getLogger(__name__)

# Global processing status storage
PROCESSING_STATUS = {}

# File processing phases for dynamic time estimation
PROCESSING_PHASES = {
    "docling": {"weight": 0.2, "name": "Converting document"},
    "chunking": {"weight": 0.1, "name": "Splitting into chunks"}, 
    "kg_extraction": {"weight": 0.6, "name": "Extracting knowledge graph"},
    "indexing": {"weight": 0.1, "name": "Building indexes"}
}

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
    
    # Processing status management
    
    def _create_processing_id(self) -> str:
        """Create a unique processing ID"""
        return str(uuid.uuid4())[:8]
    
    def _estimate_processing_time(self, data_source: str = None, paths: List[str] = None, content: str = None) -> str:
        """Estimate processing time based on input size and type"""
        try:
            if content:
                # Text content - quick processing
                char_count = len(content)
                if char_count < 1000:
                    return "30-60 seconds"
                elif char_count < 5000:
                    return "1-2 minutes"
                else:
                    return "2-3 minutes"
            
            elif paths:
                import os
                total_size = 0
                file_count = 0
                has_complex_files = False
                
                for path in paths:
                    if os.path.isfile(path):
                        file_count += 1
                        size = os.path.getsize(path)
                        total_size += size
                        
                        # Check for complex file types
                        ext = os.path.splitext(path)[1].lower()
                        if ext in ['.pdf', '.docx', '.pptx', '.xlsx']:
                            has_complex_files = True
                    elif os.path.isdir(path):
                        # Estimate directory contents
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    file_count += 1
                                    size = os.path.getsize(file_path)
                                    total_size += size
                                    ext = os.path.splitext(file)[1].lower()
                                    if ext in ['.pdf', '.docx', '.pptx', '.xlsx']:
                                        has_complex_files = True
                                except:
                                    continue
                
                # Size-based estimation
                size_mb = total_size / (1024 * 1024)
                
                if file_count == 0:
                    return "30 seconds"
                elif file_count == 1 and size_mb < 1:
                    return "30-60 seconds"  # Single small file
                elif file_count == 1 and size_mb < 5:
                    return "1-2 minutes"    # Single medium file
                elif file_count == 1:
                    return "2-4 minutes"    # Single large file
                elif file_count <= 5 and not has_complex_files:
                    return "1-3 minutes"    # Few simple files
                elif file_count <= 10:
                    return "2-5 minutes"    # Several files
                else:
                    return "3-8 minutes"    # Many files
            
            return "2-4 minutes"  # Default fallback
            
        except Exception as e:
            logger.warning(f"Error estimating processing time: {e}")
            return "2-4 minutes"  # Safe fallback
    
    def _update_processing_status(self, processing_id: str, status: str, message: str, progress: int = 0, 
                                  current_file: str = None, current_phase: str = None, 
                                  files_completed: int = 0, total_files: int = 0,
                                  estimated_time_remaining: str = None):
        """Update processing status with dynamic timing information"""
        current_time = datetime.now()
        existing_status = PROCESSING_STATUS.get(processing_id, {})
        started_at = existing_status.get("started_at", current_time.isoformat())
        
        # Calculate dynamic time estimates if we have timing info
        if isinstance(started_at, str):
            start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        else:
            start_time = started_at
            
        elapsed_seconds = (current_time - start_time).total_seconds()
        
        # Build enhanced status
        status_update = {
            "processing_id": processing_id,
            "status": status,
            "message": message,
            "progress": progress,
            "updated_at": current_time.isoformat(),
            "started_at": started_at if isinstance(started_at, str) else started_at.isoformat()
        }
        
        # Add file-level progress information
        if current_file:
            status_update["current_file"] = current_file
        if current_phase:
            status_update["current_phase"] = current_phase
        if total_files > 0:
            status_update["files_completed"] = files_completed
            status_update["total_files"] = total_files
            status_update["file_progress"] = f"File {files_completed + 1} of {total_files}"
            
        # Add dynamic time estimation
        if estimated_time_remaining:
            status_update["estimated_time_remaining"] = estimated_time_remaining
        elif total_files > 0 and files_completed > 0 and elapsed_seconds > 0:
            # Calculate based on files completed so far
            avg_time_per_file = elapsed_seconds / files_completed
            remaining_files = total_files - files_completed
            estimated_remaining = avg_time_per_file * remaining_files
            
            if estimated_remaining < 60:
                status_update["estimated_time_remaining"] = f"{int(estimated_remaining)} seconds"
            elif estimated_remaining < 3600:
                status_update["estimated_time_remaining"] = f"{int(estimated_remaining / 60)} minutes"
            else:
                status_update["estimated_time_remaining"] = f"{estimated_remaining / 3600:.1f} hours"
        
        PROCESSING_STATUS[processing_id] = status_update
        if total_files > 0:
            logger.info(f"Processing {processing_id}: {status} - {message} ({files_completed + 1}/{total_files} files)")
        else:
            logger.info(f"Processing {processing_id}: {status} - {message}")
    
    def get_processing_status(self, processing_id: str) -> Dict[str, Any]:
        """Get processing status by ID"""
        if processing_id not in PROCESSING_STATUS:
            return {"success": False, "error": f"Processing ID {processing_id} not found"}
        
        return {"success": True, "processing": PROCESSING_STATUS[processing_id]}
    
    def cancel_processing(self, processing_id: str) -> Dict[str, Any]:
        """Cancel a processing operation"""
        if processing_id not in PROCESSING_STATUS:
            return {"success": False, "error": f"Processing ID {processing_id} not found"}
            
        status = PROCESSING_STATUS[processing_id]
        if status["status"] in ["started", "processing"]:
            self._update_processing_status(
                processing_id, 
                "cancelled", 
                "Processing cancelled by user", 
                status.get("progress", 0)
            )
            return {"success": True, "message": "Processing cancelled successfully"}
        else:
            return {"success": False, "error": f"Cannot cancel processing in status: {status['status']}"}
    
    def _is_processing_cancelled(self, processing_id: str) -> bool:
        """Check if processing has been cancelled"""
        return (processing_id in PROCESSING_STATUS and 
                PROCESSING_STATUS[processing_id]["status"] == "cancelled")
    
    async def _cleanup_partial_processing(self, processing_id: str):
        """Clean up partial processing artifacts when cancelled"""
        try:
            logger.info(f"Cleaning up partial processing for {processing_id}")
            
            # Check if we have a fully functional system (completed previous ingestion)
            has_complete_system = (
                hasattr(self.system, 'vector_index') and self.system.vector_index is not None and
                hasattr(self.system, 'graph_index') and self.system.graph_index is not None and
                hasattr(self.system, 'hybrid_retriever') and self.system.hybrid_retriever is not None
            )
            
            if has_complete_system:
                # System was fully functional from previous ingestion - preserve it
                logger.info(f"Preserving existing functional system state after cancellation of {processing_id}")
                # Only clean up processing-specific state, not the core indexes
                if processing_id in PROCESSING_STATUS:
                    PROCESSING_STATUS[processing_id]["status"] = "cancelled"
                    PROCESSING_STATUS[processing_id]["message"] = "Processing cancelled - existing data preserved"
            else:
                # System was in partial state, safe to clear everything
                logger.info(f"Clearing partial system state after cancellation of {processing_id}")
                if hasattr(self.system, 'vector_index'):
                    self.system.vector_index = None
                if hasattr(self.system, 'graph_index'):
                    self.system.graph_index = None
                if hasattr(self.system, 'hybrid_retriever'):
                    self.system.hybrid_retriever = None
                
                # Also call the system's clear method if it exists
                if hasattr(self.system, '_clear_partial_state'):
                    self.system._clear_partial_state()
            
            logger.info(f"Cleanup completed for {processing_id}")
        except Exception as e:
            logger.error(f"Error during cleanup for {processing_id}: {str(e)}")
    
    # Core business logic methods
    
    async def ingest_documents(self, data_source: str = None, paths: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Start async document ingestion and return processing ID"""
        processing_id = self._create_processing_id()
        
        # Start processing immediately in background
        self._update_processing_status(
            processing_id, 
            "started", 
            "Complex document processing has started, please wait...", 
            0
        )
        
        # Start background task
        asyncio.create_task(self._process_documents_async(processing_id, data_source, paths, **kwargs))
        
        estimated_time = self._estimate_processing_time(data_source, paths)
        
        return {
            "processing_id": processing_id,
            "status": "started", 
            "message": "Document processing has started, please wait...",
            "estimated_time": estimated_time
        }
    
    async def _process_documents_async(self, processing_id: str, data_source: str = None, paths: List[str] = None, **kwargs):
        """Background task for document processing"""
        try:
            data_source = data_source or self.settings.data_source
            
            # Check for cancellation before starting
            if self._is_processing_cancelled(processing_id):
                return
                
            self._update_processing_status(
                processing_id, 
                "processing", 
                f"Initializing {data_source} document ingestion...", 
                10
            )
            
            if data_source == "filesystem":
                file_paths = paths or self.settings.source_paths
                if not file_paths:
                    self._update_processing_status(
                        processing_id, 
                        "failed", 
                        "No file paths provided for filesystem source", 
                        0
                    )
                    return
                
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
                
                self._update_processing_status(
                    processing_id, 
                    "processing", 
                    f"Processing {len(cleaned_paths)} file(s)...", 
                    30,
                    total_files=len(cleaned_paths),
                    files_completed=0
                )
                
                # Check for cancellation before heavy processing
                if self._is_processing_cancelled(processing_id):
                    return
                    
                self._update_processing_status(
                    processing_id, 
                    "processing", 
                    "Extracting text and generating embeddings...", 
                    50
                )
                
                self._update_processing_status(
                    processing_id, 
                    "processing", 
                    "Building knowledge graph from documents...", 
                    70
                )
                
                # Actual processing with cancellation support
                await self.system.ingest_documents(
                    cleaned_paths, 
                    processing_id=processing_id,
                    status_callback=self._update_processing_status
                )
                
                self._update_processing_status(
                    processing_id, 
                    "completed", 
                    f"Successfully ingested {len(cleaned_paths)} document(s)! Knowledge graph and vector index ready.", 
                    100
                )
                
            elif data_source == "cmis":
                self._update_processing_status(
                    processing_id, 
                    "processing", 
                    "Connecting to CMIS repository...", 
                    20
                )
                
                # Check for cancellation before connecting
                if self._is_processing_cancelled(processing_id):
                    return
                    
                self._update_processing_status(
                    processing_id, 
                    "processing", 
                    "Scanning CMIS repository for documents...", 
                    40
                )
                
                self._update_processing_status(
                    processing_id, 
                    "processing", 
                    "Downloading and processing CMIS documents...", 
                    60
                )
                
                cmis_config = kwargs.get('cmis_config')
                if cmis_config:
                    await self.system.ingest_cmis(cmis_config, processing_id=processing_id, status_callback=self._update_processing_status)
                else:
                    await self.system.ingest_cmis(processing_id=processing_id, status_callback=self._update_processing_status)
                    
                self._update_processing_status(
                    processing_id, 
                    "completed", 
                    "Successfully ingested documents from CMIS repository!", 
                    100
                )
                
            elif data_source == "alfresco":
                self._update_processing_status(
                    processing_id, 
                    "processing", 
                    "Connecting to Alfresco repository...", 
                    20
                )
                
                # Check for cancellation before connecting
                if self._is_processing_cancelled(processing_id):
                    return
                    
                self._update_processing_status(
                    processing_id, 
                    "processing", 
                    "Scanning Alfresco repository for documents...", 
                    40
                )
                
                self._update_processing_status(
                    processing_id, 
                    "processing", 
                    "Downloading and processing Alfresco documents...", 
                    60
                )
                
                alfresco_config = kwargs.get('alfresco_config')
                if alfresco_config:
                    await self.system.ingest_alfresco(alfresco_config, processing_id=processing_id, status_callback=self._update_processing_status)
                else:
                    await self.system.ingest_alfresco(processing_id=processing_id, status_callback=self._update_processing_status)
                    
                self._update_processing_status(
                    processing_id, 
                    "completed", 
                    "Successfully ingested documents from Alfresco repository!", 
                    100
                )
                
            else:
                self._update_processing_status(
                    processing_id, 
                    "failed", 
                    f"Unsupported data source: {data_source}", 
                    0
                )
                
        except RuntimeError as e:
            if "cancelled by user" in str(e):
                logger.info(f"Processing {processing_id} was cancelled by user")
                # Clean up any partial indexes that might have been created
                await self._cleanup_partial_processing(processing_id)
            else:
                logger.error(f"Runtime error in processing {processing_id}: {str(e)}")
                self._update_processing_status(
                    processing_id, 
                    "failed", 
                    f"Document processing failed: {str(e)}", 
                    0
                )
        except Exception as e:
            # Handle LLM self-cancellation and timeout errors gracefully
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['timeout', 'timed out', 'request timeout', 'connection timeout']):
                logger.warning(f"LLM timeout in processing {processing_id}: {str(e)}")
                self._update_processing_status(
                    processing_id, 
                    "failed", 
                    f"Processing timeout - LLM took too long to respond. Try increasing timeout or using smaller documents: {str(e)}", 
                    0
                )
            elif any(keyword in error_str for keyword in ['cancelled', 'aborted', 'interrupted']):
                logger.warning(f"LLM self-cancelled in processing {processing_id}: {str(e)}")
                self._update_processing_status(
                    processing_id, 
                    "failed", 
                    f"LLM processing was interrupted. This can happen with complex documents: {str(e)}", 
                    0
                )
            else:
                logger.error(f"Error ingesting documents {processing_id}: {str(e)}")
                self._update_processing_status(
                    processing_id, 
                    "failed", 
                    f"Document processing failed: {str(e)}", 
                    0
                )
    
    async def search_documents(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Search documents using hybrid search"""
        try:
            results = await self.system.search(query, top_k=top_k)
            return {"success": True, "results": results}
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def qa_query(self, query: str) -> Dict[str, Any]:
        """Answer a question using the Q&A system"""
        try:
            query_engine = self.system.get_query_engine()
            response = await query_engine.aquery(query)
            answer = str(response)
            return {"success": True, "answer": answer}
        except Exception as e:
            logger.error(f"Error during Q&A query: {str(e)}")
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
        """Start async text ingestion and return processing ID"""
        processing_id = self._create_processing_id()
        
        # Start processing immediately in background
        self._update_processing_status(
            processing_id, 
            "started", 
            "Complex document processing has started, please wait...", 
            0
        )
        
        # Start background task
        asyncio.create_task(self._process_text_async(processing_id, content, source_name))
        
        estimated_time = self._estimate_processing_time(content=content)
        
        return {
            "processing_id": processing_id,
            "status": "started", 
            "message": "Text processing has started, please wait...",
            "estimated_time": estimated_time
        }
    
    async def _process_text_async(self, processing_id: str, content: str, source_name: str):
        """Background task for text processing"""
        try:
            self._update_processing_status(
                processing_id, 
                "processing", 
                "Creating document and initializing pipeline...", 
                10
            )
            
            self._update_processing_status(
                processing_id, 
                "processing", 
                "Processing text and generating embeddings...", 
                30
            )
            
            self._update_processing_status(
                processing_id, 
                "processing", 
                "Building vector index...", 
                50
            )
            
            self._update_processing_status(
                processing_id, 
                "processing", 
                "Extracting knowledge graph...", 
                70
            )
            
            self._update_processing_status(
                processing_id, 
                "processing", 
                "Creating graph index and relationships...", 
                85
            )
            
            # Actual processing with cancellation support
            await self.system.ingest_text(content=content, source_name=source_name, processing_id=processing_id)
            
            self._update_processing_status(
                processing_id, 
                "completed", 
                "Text content ingested successfully! Knowledge graph and vector index ready.", 
                100
            )
            
        except RuntimeError as e:
            if "cancelled by user" in str(e):
                logger.info(f"Text processing {processing_id} was cancelled by user")
                # Clean up any partial indexes that might have been created
                await self._cleanup_partial_processing(processing_id)
            else:
                logger.error(f"Runtime error in text processing {processing_id}: {str(e)}")
                self._update_processing_status(
                    processing_id, 
                    "failed", 
                    f"Processing failed: {str(e)}", 
                    0
                )
        except Exception as e:
            logger.error(f"Error ingesting text {processing_id}: {str(e)}")
            self._update_processing_status(
                processing_id, 
                "failed", 
                f"Processing failed: {str(e)}", 
                0
            )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status without triggering database initialization"""
        try:
            # Return status without initializing databases to avoid APOC calls
            return {
                "success": True, 
                "status": {
                    "has_vector_index": self._system is not None and self._system.vector_index is not None,
                    "has_graph_index": self._system is not None and self._system.graph_index is not None,
                    "has_hybrid_retriever": self._system is not None and self._system.hybrid_retriever is not None,
                    "config": {
                        "data_source": self.settings.data_source,
                        "vector_db": self.settings.vector_db,
                        "graph_db": self.settings.graph_db,
                        "search_db": self.settings.search_db,
                        "llm_provider": self.settings.llm_provider
                    },
                    "system_initialized": self._system is not None
                }
            }
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