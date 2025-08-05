import logging
import sys
from datetime import datetime
import asyncio
import os
from dotenv import load_dotenv
from cmis_util import CMISHandler
from neo4j_util import Neo4jHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'cmis-graphrag-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# Sample text for testing
SAMPLE_TEXT =  """The son of Duke Leto Atreides and the Lady Jessica, Paul is the heir of House Atreides,
an aristocratic family that rules the planet Caladan, the rainy planet, since 10191."""

# Define folder path in CMIS repo to process
FOLDER_PATH = os.getenv("FOLDER_PATH", "/Shared/GraphRAG")

# Define CMIS connection parameters
CMIS_URL = os.getenv("CMIS_URL", "http://localhost:8080/alfresco/api/-default-/public/cmis/versions/1.1/atom")
CMIS_USERNAME = os.getenv("CMIS_USERNAME", "admin")
CMIS_PASSWORD = os.getenv("CMIS_PASSWORD", "admin")

# Define Neo4j connection parameters
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7689")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Define OpenAI and Ollama configuration
USE_OPENAI = os.getenv("USE_OPENAI", "true").strip().lower() in ("true")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Define question configuration
QUESTION = os.getenv("QUESTION", "Who started CMIS?")

async def main():
    try:
        # Initialize CMIS handler
        cmis_handler = CMISHandler(
            url=CMIS_URL,
            username=CMIS_USERNAME,
            password=CMIS_PASSWORD
        )

        # Initialize Neo4j handler
        neo4j_handler = Neo4jHandler(
            uri=NEO4J_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            use_openai=USE_OPENAI,
            api_key=OPENAI_API_KEY,
            ollama_model=OLLAMA_MODEL,
            openai_model=OPENAI_MODEL
        )
        
        # Process documents
        logger.info("Starting document processing...")
        folder_path = FOLDER_PATH
        
        # Use sample text for testing
        """
        await neo4j_handler.process_document(
            doc_id="sample-starwars",
            doc_name="Star Wars Test Document",
            content=SAMPLE_TEXT
        )
        """

        await cmis_handler.process_folder(
            folder_path=folder_path,
            process_doc_callback=neo4j_handler.process_document
        )
        
        logger.info("Document processing completed")
        # Example query
        logger.info("Starting query processing...")

        #question = "Who is Paul Atreides?" # for testing
        question = QUESTION
        answer = await neo4j_handler.query_graph(question)
        logger.info("Query processing completed")
        print("\nQuery:", question)
        print("Answer:", answer)
        
    except Exception as e:
        logger.error(f"Top-level error: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        # Cleanup
        if 'neo4j_handler' in locals():
            neo4j_handler.close()

if __name__ == "__main__":
    asyncio.run(main())
