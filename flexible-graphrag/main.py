import os
import logging
import sys
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
from pathlib import Path
import uvicorn
from dotenv import load_dotenv
import importlib.metadata
import nest_asyncio
from config import Settings, DataSourceType
from backend import get_backend

# Load environment variables
load_dotenv()

# Fix for Windows event loop issues with Ollama/LlamaIndex
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Apply nest_asyncio to allow nested event loops (required for LlamaIndex in FastAPI)
nest_asyncio.apply()

# Configure logging with both file and console output
log_filename = f'flexible-graphrag-api-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'

# Force logging to work properly with uvicorn
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
logger.info(f"Starting application with log file: {log_filename}")

# Force flush
file_handler.flush()
console_handler.flush()

# Initialize FastAPI app
app = FastAPI(
    title="Flexible GraphRAG API",
    description="API for processing documents with configurable hybrid search (vector, graph, full-text)",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class CmisConfig(BaseModel):
    url: str
    username: str
    password: str
    folder_path: str

class AlfrescoConfig(BaseModel):
    url: str
    username: str
    password: str
    path: str

class IngestRequest(BaseModel):
    paths: Optional[List[str]] = None  # overrides config
    data_source: Optional[str] = None  # filesystem, cmis, alfresco
    cmis_config: Optional[CmisConfig] = None
    alfresco_config: Optional[AlfrescoConfig] = None

class QueryRequest(BaseModel):
    query: str
    top_k: int = 10
    query_type: Optional[str] = "hybrid"  # hybrid, qa

class TextIngestRequest(BaseModel):
    content: str
    source_name: Optional[str] = "sample-test"

class Document(BaseModel):
    id: str
    name: str
    content: str

# Initialize system
settings = Settings()
backend_instance = get_backend()

# Lifecycle events for proper resource cleanup
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the application shuts down."""
    logger.info("Application shutdown: cleaning up resources")

# API Endpoints
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/ingest")
async def ingest(request: IngestRequest):
    try:
        logger.info(f"Starting async document ingestion: {request}")
        logger.info(f"Data source: {request.data_source}, Paths: {request.paths}")
        
        data_source = request.data_source or str(settings.data_source)
        paths = request.paths
        
        # Prepare additional kwargs for data source configs
        kwargs = {}
        if request.cmis_config:
            kwargs['cmis_config'] = request.cmis_config.dict()
        if request.alfresco_config:
            kwargs['alfresco_config'] = request.alfresco_config.dict()
        
        result = await backend_instance.ingest_documents(data_source=data_source, paths=paths, **kwargs)
        
        logger.info(f"Document ingestion started with ID: {result['processing_id']}")
        return result
            
    except Exception as e:
        logger.error(f"Error starting document ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def search(request: QueryRequest):
    try:
        logger.info(f"Processing {request.query_type} query: {request.query}")
        
        if request.query_type == "qa":
            # Q&A query - return answer
            result = await backend_instance.qa_query(request.query)
            if result["success"]:
                logger.info("Q&A query completed successfully")
                return {"success": True, "answer": result["answer"]}
            else:
                raise HTTPException(500, result["error"])
        else:
            # Hybrid search - return results
            result = await backend_instance.search_documents(request.query, request.top_k)
            if result["success"]:
                logger.info("Hybrid search completed successfully")
                return {"success": True, "results": result["results"]}
            else:
                raise HTTPException(500, result["error"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def query_graph(request: QueryRequest):
    try:
        logger.info(f"Processing query: {request.query}")
        result = await backend_instance.query_documents(request.query, request.top_k)
        
        if result["success"]:
            logger.info("Query processing completed successfully")
            return {"status": "success", "answer": result["answer"]}
        else:
            raise HTTPException(500, result["error"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying system: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    try:
        logger.info("Fetching system status")
        result = backend_instance.get_system_status()
        
        if result["success"]:
            logger.info("Status fetched successfully")
            return {"status": "success", "system_status": result["status"]}
        else:
            raise HTTPException(500, result["error"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test-sample")
async def test_sample_default():
    """Test endpoint with configurable sample text using async processing."""
    try:
        content = settings.sample_text
        source_name = "sample-test"
        
        logger.info("Starting async sample text processing")
        result = await backend_instance.ingest_text(content=content, source_name=source_name)
        
        # Return the async processing response (same format as ingest-text)
        logger.info(f"Sample text processing started with ID: {result['processing_id']}")
        return result
    except Exception as e:
        logger.error(f"Error starting sample text processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest-text")
async def ingest_custom_text(request: TextIngestRequest):
    """Start async text ingestion and return processing ID."""
    try:
        logger.info(f"Starting async text ingestion: source='{request.source_name}'")
        result = await backend_instance.ingest_text(content=request.content, source_name=request.source_name)
        
        logger.info(f"Text ingestion started with ID: {result['processing_id']}")
        return result
    except Exception as e:
        logger.error(f"Error starting text ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/processing-status/{processing_id}")
async def get_processing_status(processing_id: str):
    """Get processing status by ID."""
    try:
        logger.info(f"Checking processing status for ID: {processing_id}")
        result = backend_instance.get_processing_status(processing_id)
        
        if result["success"]:
            logger.info(f"Status retrieved for {processing_id}: {result['processing']['status']}")
            return result["processing"]
        else:
            raise HTTPException(404, result["error"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cancel-processing/{processing_id}")
async def cancel_processing(processing_id: str):
    """Cancel processing by ID."""
    try:
        logger.info(f"Cancelling processing for ID: {processing_id}")
        result = backend_instance.cancel_processing(processing_id)
        
        if result["success"]:
            logger.info(f"Processing {processing_id} cancelled successfully")
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(400, result["error"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/processing-events/{processing_id}")
async def processing_events(processing_id: str):
    """Server-Sent Events for real-time processing updates (UI clients only)."""
    from fastapi.responses import StreamingResponse
    import json
    import time
    
    def event_stream():
        while True:
            result = backend_instance.get_processing_status(processing_id)
            if result["success"]:
                status_data = result["processing"]
                yield f"data: {json.dumps(status_data)}\n\n"
                
                # Stop streaming if completed or failed
                if status_data["status"] in ["completed", "failed"]:
                    break
            else:
                yield f"data: {json.dumps({'error': result['error']})}\n\n"
                break
                
            time.sleep(2)  # Poll every 2 seconds
    
    return StreamingResponse(
        event_stream(), 
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@app.get("/api/info")
async def get_api_info():
    """Get API information and available endpoints"""
    return {
        "name": "Flexible GraphRAG API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "ingest": "/api/ingest",
            "search": "/api/search", 
            "query": "/api/query",
            "status": "/api/status",
            "test_sample": "/api/test-sample",
            "python_info": "/api/python-info",
            "graph": "/api/graph"
        },
        "frontends": {
            "angular": "/angular",
            "react": "/react", 
            "vue": "/vue"
        },
        "mcp_server": "Available as separate fastmcp-server.py"
    }

@app.get("/api/graph")
async def get_graph_data(limit: int = 50):
    """Get graph data for visualization (nodes and relationships)"""
    try:
        # Check if system is initialized and has graph store
        if not hasattr(backend_instance, '_system') or backend_instance._system is None:
            return {"error": "System not initialized - please ingest documents first"}
        
        if not hasattr(backend_instance.system, 'graph_store') or backend_instance.system.graph_store is None:
            return {"error": "Graph database not configured"}
        
        # Check if it's Kuzu or Neo4j
        graph_store = backend_instance.system.graph_store
        
        # Detect database type
        graph_store_type = type(graph_store).__name__
        
        if "Kuzu" in graph_store_type or hasattr(graph_store, '_kuzu_db') or hasattr(graph_store, '_db'):
            # Try to get Kuzu database connection
            kuzu_db = None
            if hasattr(graph_store, 'db'):
                kuzu_db = graph_store.db
            elif hasattr(graph_store, '_kuzu_db'):
                kuzu_db = graph_store._kuzu_db
            elif hasattr(graph_store, '_db'):
                kuzu_db = graph_store._db
            elif hasattr(graph_store, 'client') and hasattr(graph_store.client, '_db'):
                kuzu_db = graph_store.client._db
            
            if kuzu_db is None:
                return {"error": f"Kuzu database not accessible in {graph_store_type}", "database": "kuzu"}
            
            try:
                # Query Kuzu database directly
                import kuzu
                conn = kuzu.Connection(kuzu_db)
                
                # Absolute simplest query - just check tables
                try:
                    # Use CALL statement to check database structure
                    result = conn.execute("CALL show_tables()")
                    tables_df = result.get_as_df()
                    tables = tables_df.to_dict('records') if not tables_df.empty else []
                    
                    return {
                        "database": "kuzu",
                        "store_type": graph_store_type,
                        "status": "connected",
                        "tables": tables,
                        "message": "Kuzu database accessible - use Kuzu Explorer at http://localhost:8002 for visualization"
                    }
                except Exception as table_error:
                    # Even simpler - just confirm connection works
                    return {
                        "database": "kuzu", 
                        "store_type": graph_store_type,
                        "status": "connected_basic",
                        "message": "Kuzu database connected but queries may have issues. Use Kuzu Explorer at http://localhost:8002",
                        "table_error": str(table_error)
                    }
            except Exception as e:
                return {"error": f"Error querying Kuzu: {str(e)}", "database": "kuzu", "store_type": graph_store_type}
                
        else:  # Neo4j or other
            return {"error": f"Graph visualization only implemented for Kuzu currently (detected: {graph_store_type})", "database": "other"}
            
    except Exception as e:
        return {"error": f"Error fetching graph data: {str(e)}"}

@app.get("/api/python-info")
async def python_info():
    """Return information about the Python interpreter being used."""
    # More reliable way to check if running in a virtual environment
    in_virtualenv = False
    venv_path = os.environ.get("VIRTUAL_ENV", "")
    
    # If VIRTUAL_ENV is set, use that
    if venv_path:
        in_virtualenv = True
    # Otherwise check if the Python executable is in a venv directory structure
    elif "venv" in sys.executable or "virtualenv" in sys.executable:
        in_virtualenv = True
        # Try to extract the venv path from the executable path
        venv_path = sys.executable
        if "\\Scripts\\" in venv_path:
            venv_path = venv_path.split("\\Scripts\\")[0]
        elif "/bin/" in venv_path:
            venv_path = venv_path.split("/bin/")[0]
    
    # Read requirements.txt
    requirements = []
    req_file_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_file_path):
        with open(req_file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    requirements.append(line)
    
    # Get installed packages
    installed_packages: Dict[str, str] = {}
    try:
        for dist in importlib.metadata.distributions():
            try:
                name = dist.metadata["Name"].lower()
                installed_packages[name] = dist.version
            except (KeyError, AttributeError):
                # Skip packages with missing metadata
                pass
    except Exception as e:
        logger.warning(f"Error getting installed packages: {str(e)}")
        # Empty dict as fallback
        installed_packages = {}
    
    # Check requirements against installed packages
    req_status = []
    for req in requirements:
        original_req = req
        # Handle requirements with version specifiers
        if "==" in req:
            pkg_name, version_spec = req.split("==", 1)
            pkg_name = pkg_name.strip().lower()
        elif ">=" in req:
            pkg_name, version_spec = req.split(">=", 1)
            pkg_name = pkg_name.strip().lower()
        elif "[" in req:
            # Handle packages with extras like 'package[extra]'
            pkg_name = req.split("[", 1)[0].strip().lower()
        else:
            pkg_name = req.strip().lower()
        
        # For packages with extras, we need to check the base package name
        base_pkg_name = pkg_name.split("[")[0] if "[" in pkg_name else pkg_name
        
        installed_version = installed_packages.get(base_pkg_name)
        req_status.append({
            "name": pkg_name,
            "required": original_req,
            "installed": installed_version if installed_version else "Not installed"
        })
    
    return {
        "python_path": sys.executable,
        "python_version": sys.version,
        "virtual_env": venv_path if in_virtualenv else "Not in a virtual environment",
        "in_virtualenv": in_virtualenv,
        "requirements": req_status
    }

# Backend API only - no frontend serving
@app.get("/")
async def root():
    return {
        "message": "Flexible GraphRAG API", 
        "api": "/api",
        "info": "/api/info",
        "note": "Backend API only - use separate dev servers for UIs"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
