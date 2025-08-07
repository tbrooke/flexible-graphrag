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
from config import Settings, DataSourceType
from backend import get_backend

# Load environment variables
load_dotenv()

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
        logger.info(f"Processing ingest request: {request}")
        logger.info(f"Data source: {request.data_source}, Paths: {request.paths}")
        
        data_source = request.data_source or str(settings.data_source)
        paths = request.paths
        
        # Log start of processing
        logger.info(f"Starting document ingestion for {len(paths) if paths else 0} paths")
        
        # Prepare additional kwargs for data source configs
        kwargs = {}
        if request.cmis_config:
            kwargs['cmis_config'] = request.cmis_config.dict()
        if request.alfresco_config:
            kwargs['alfresco_config'] = request.alfresco_config.dict()
        
        result = await backend_instance.ingest_documents(data_source=data_source, paths=paths, **kwargs)
        
        if result["success"]:
            logger.info("Ingestion completed successfully")
            return {"status": "success", "message": result["message"]}
        else:
            logger.error(f"Ingestion failed: {result['error']}")
            raise HTTPException(400, result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
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
async def test_sample(sample_text: str = None):
    """Test endpoint with sample text for quick testing."""
    try:
        sample = sample_text or """The son of Duke Leto Atreides and the Lady Jessica, Paul is the heir of House Atreides,
an aristocratic family that rules the planet Caladan, the rainy planet, since 10191."""
        
        logger.info("Processing sample text for testing")
        result = await backend_instance.ingest_text(content=sample, source_name="sample-test")
        
        if result["success"]:
            logger.info("Sample text processing completed")
            return {"status": "success", "message": result["message"]}
        else:
            raise HTTPException(500, result["error"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing sample text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
            "python_info": "/api/python-info"
        },
        "frontends": {
            "angular": "/angular",
            "react": "/react", 
            "vue": "/vue"
        },
        "mcp_server": "Available as separate fastmcp-server.py"
    }

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

# Serve all built frontends at different routes
frontends_served = []

# Serve Angular frontend
if os.path.exists("../flexible-graphrag-ui/frontend-angular/dist"):
    app.mount("/angular", StaticFiles(directory="../flexible-graphrag-ui/frontend-angular/dist", html=True), name="angular-frontend")
    frontends_served.append("Angular at /angular")

# Serve React frontend  
if os.path.exists("../flexible-graphrag-ui/frontend-react/build"):
    app.mount("/react", StaticFiles(directory="../flexible-graphrag-ui/frontend-react/build", html=True), name="react-frontend")
    frontends_served.append("React at /react")

# Serve Vue frontend
if os.path.exists("../flexible-graphrag-ui/frontend-vue/dist"):
    app.mount("/vue", StaticFiles(directory="../flexible-graphrag-ui/frontend-vue/dist", html=True), name="vue-frontend")
    frontends_served.append("Vue at /vue")

# Default redirect to first available frontend
if frontends_served:
    logger.info(f"Serving frontends: {', '.join(frontends_served)}")
    
    @app.get("/")
    async def root():
        available_frontends = {}
        if os.path.exists("../flexible-graphrag-ui/frontend-angular/dist"):
            available_frontends["angular"] = "/angular"
        if os.path.exists("../flexible-graphrag-ui/frontend-react/build"):
            available_frontends["react"] = "/react"
        if os.path.exists("../flexible-graphrag-ui/frontend-vue/dist"):
            available_frontends["vue"] = "/vue"
            
        return {
            "message": "Flexible GraphRAG API", 
            "frontends": available_frontends,
            "api": "/api",
            "info": "/api/info"
        }
else:
    logger.warning("No frontend build directories found. API will be available but no UI will be served.")
    
    @app.get("/")
    async def root():
        return {"message": "Flexible GraphRAG API", "api": "/api", "note": "No frontends built"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
