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
from cmis_util import CMISHandler
from neo4j_util import Neo4jHandler

# Load environment variables
load_dotenv()

# Configure logging with both file and console output
log_filename = f'cmis-graphrag-api-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Starting application with log file: {log_filename}")

# Initialize FastAPI app
app = FastAPI(
    title="CMIS GraphRAG API",
    description="API for processing CMIS documents with GraphRAG",
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
class ProcessFolderRequest(BaseModel):
    folder_path: str

class QueryRequest(BaseModel):
    question: str

class Document(BaseModel):
    id: str
    name: str
    content: str

# Initialize handlers
cmis_handler = None
neo4j_handler = None

def get_cmis_handler():
    global cmis_handler
    if cmis_handler is None:
        cmis_handler = CMISHandler(
            url=os.getenv("CMIS_URL", "http://localhost:8080/alfresco/api/-default-/public/cmis/versions/1.1/atom"),
            username=os.getenv("CMIS_USERNAME", "admin"),
            password=os.getenv("CMIS_PASSWORD", "admin")
        )
    return cmis_handler

def get_neo4j_handler():
    global neo4j_handler
    if neo4j_handler is None:
        # Parse USE_OPENAI exactly like in cmis-graphrag.py
        USE_OPENAI = os.getenv("USE_OPENAI", "true").strip().lower() in ("true")
        logger.info(f"USE_OPENAI parsed as: {USE_OPENAI}")
        
        neo4j_handler = Neo4jHandler(
            uri=os.getenv("NEO4J_URI", "neo4j://localhost:7689"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            use_openai=USE_OPENAI,
            api_key=os.getenv("OPENAI_API_KEY", ""),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        )
    return neo4j_handler

# Lifecycle events for proper resource cleanup
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the application shuts down."""
    logger.info("Application shutdown: cleaning up resources")
    global neo4j_handler
    if neo4j_handler:
        logger.info("Closing Neo4j connection")
        neo4j_handler.close()
        neo4j_handler = None

# API Endpoints
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/process-folder")
async def process_folder(request: ProcessFolderRequest):
    try:
        logger.info(f"Processing folder: {request.folder_path}")
        cmis = get_cmis_handler()
        neo4j = get_neo4j_handler()
        
        await cmis.process_folder(
            folder_path=request.folder_path,
            process_doc_callback=neo4j.process_document
        )
        logger.info(f"Successfully processed folder: {request.folder_path}")
        return {"status": "success", "message": f"Processed folder: {request.folder_path}"}
    except Exception as e:
        logger.error(f"Error processing folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def query_graph(request: QueryRequest):
    try:
        logger.info(f"Processing query: {request.question}")
        neo4j = get_neo4j_handler()
        answer = await neo4j.query_graph(request.question)
        logger.info("Query processing completed successfully")
        # Return the answer directly in the response
        return {"status": "success", "answer": answer}
    except Exception as e:
        logger.error(f"Error querying graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph")
async def get_graph_data():
    try:
        logger.info("Fetching graph data")
        neo4j = get_neo4j_handler()
        
        # Execute Cypher query to get all nodes and relationships
        with neo4j.driver.session() as session:
            # Get nodes
            nodes_result = session.run("""
                MATCH (n)
                WHERE n:Document OR EXISTS(n.name) OR EXISTS(n.title)
                RETURN 
                    id(n) AS id, 
                    labels(n) AS labels, 
                    properties(n) AS properties
                LIMIT 1000
            """)
            
            nodes = [{"id": str(record["id"]), 
                     "labels": record["labels"], 
                     "properties": record["properties"]} 
                    for record in nodes_result]
            
            # Get relationships
            rels_result = session.run("""
                MATCH (n)-[r]->(m)
                WHERE (n:Document OR EXISTS(n.name) OR EXISTS(n.title))
                   OR (m:Document OR EXISTS(m.name) OR EXISTS(m.title))
                RETURN 
                    id(r) AS id, 
                    type(r) AS type, 
                    id(startNode(r)) AS source, 
                    id(endNode(r)) AS target, 
                    properties(r) AS properties
                LIMIT 2000
            """)
            
            relationships = [{"id": str(record["id"]), 
                             "type": record["type"], 
                             "source": str(record["source"]), 
                             "target": str(record["target"]), 
                             "properties": record["properties"]} 
                            for record in rels_result]
        
        logger.info(f"Graph data fetched successfully: {len(nodes)} nodes, {len(relationships)} relationships")
        return {"nodes": nodes, "relationships": relationships}
    except Exception as e:
        logger.error(f"Error fetching graph data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test-sample")
async def test_sample(sample_text: str = None):
    """Test endpoint with sample text for quick testing without CMIS."""
    try:
        sample = sample_text or """The son of Duke Leto Atreides and the Lady Jessica, Paul is the heir of House Atreides,
an aristocratic family that rules the planet Caladan, the rainy planet, since 10191."""
        
        logger.info("Processing sample text for testing")
        neo4j = get_neo4j_handler()
        
        await neo4j.process_document(
            doc_id="sample-test",
            doc_name="Sample Test Document",
            content=sample
        )
        
        logger.info("Sample text processing completed")
        return {"status": "success", "message": "Sample text processed successfully"}
    except Exception as e:
        logger.error(f"Error processing sample text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

# Serve React app in production
if os.path.exists("../flexible-graphrag-ui/frontend-react/build"):
    app.mount("/", StaticFiles(directory="../flexible-graphrag-ui/frontend-react/build", html=True), name="frontend")
elif os.path.exists("../flexible-graphrag-ui/frontend-angular/dist"):
    app.mount("/", StaticFiles(directory="../flexible-graphrag-ui/frontend-angular/dist", html=True), name="frontend")
elif os.path.exists("../flexible-graphrag-ui/frontend-vue/dist"):
    app.mount("/", StaticFiles(directory="../flexible-graphrag-ui/frontend-vue/dist", html=True), name="frontend")
else:
    logger.warning("No frontend build directory found. API will be available but no UI will be served.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
