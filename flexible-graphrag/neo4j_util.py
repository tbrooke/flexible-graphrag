from neo4j import GraphDatabase
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.llm import OllamaLLM
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.embeddings import OllamaEmbeddings
from neo4j_graphrag.retrievers import VectorRetriever
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.indexes import create_vector_index
from neo4j_graphrag.indexes import upsert_vectors
from neo4j_graphrag.types import EntityType

import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# Optional Schema definition
USE_SCHEMA = False  # Global flag to control schema usage

ENTITIES = [
    # entities can be defined with a simple label...
    "Person",
    # ... or with a dict if more details are needed,
    # such as a description:
    {"label": "House", "description": "Family the person belongs to"},
    # or a list of properties the LLM will try to attach to the entity:
    {"label": "Planet", "properties": [{"name": "weather", "type": "STRING"}]},
]

# same thing for relationships:
RELATIONS = [
    "PARENT_OF",
    {
        "label": "HEIR_OF",
        "description": "Used for inheritor relationship between father and sons",
    },
    {"label": "RULES", "properties": [{"name": "fromYear", "type": "INTEGER"}]},
]

POTENTIAL_SCHEMA = [
    ("Person", "PARENT_OF", "Person"),
    ("Person", "HEIR_OF", "House"),
    ("House", "RULES", "Planet"),
]

MODEL_PARAMS = {
    "max_tokens": 4000,
    "temperature": 0.1
}

# Index configuration
INDEX_BASE_NAME = "vector_index"
INDEX_LABEL = "Chunk"
INDEX_EMBEDDING_PROPERTY = "embedding"


class Neo4jHandler:
    def __init__(
        self, 
        uri: str, 
        user: str, 
        password: str, 
        use_openai: bool = False,
        api_key: Optional[str] = None,
        ollama_model: str = "llama3",
        openai_model: str = "gpt-4o-mini"
    ):
        """Initialize Neo4j connection and components."""
        try:
            # Initialize Neo4j driver
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info("Successfully initialized Neo4j driver")
                        
            # Initialize components based on configuration
            if use_openai:
                if not api_key:
                    raise ValueError("OpenAI API key is required when use_openai is True")
                self.llm = OpenAILLM(api_key=api_key, model_name=openai_model, model_params=MODEL_PARAMS)
                self.embedder = OpenAIEmbeddings(model="text-embedding-3-large")
                self.model_type = "openai"
                # Set OpenAI specific index parameters
                self.index_dimensions = 3072
                self.similarity_fn = "cosine"
                self.index_name = f"{INDEX_BASE_NAME}_openai"
                logger.info(f"Successfully initialized OpenAI components with model: {openai_model}")
            else:
                self.llm = OllamaLLM(model_name=ollama_model, model_params=MODEL_PARAMS)
                self.embedder = OllamaEmbeddings(model="mxbai-embed-large")
                self.model_type = "ollama"
                # Set Ollama specific index parameters
                self.index_dimensions = 1024
                self.similarity_fn = "cosine"
                self.index_name = f"{INDEX_BASE_NAME}_ollama"
                logger.info(f"Successfully initialized Ollama components with model: {ollama_model}")
                
            # Set up vector index if it doesn't exist
            logger.info("Checking for existing vector index...")
            if not self._index_exists(self.index_name):
                logger.info(f"Creating new vector index: {self.index_name}")
                create_vector_index(
                    self.driver,
                    self.index_name,
                    label=INDEX_LABEL,
                    embedding_property=INDEX_EMBEDDING_PROPERTY,
                    dimensions=self.index_dimensions,
                    similarity_fn=self.similarity_fn,
                )
                logger.info(f"Vector index setup completed with name: {self.index_name}")
            else:
                logger.info(f"Vector index {self.index_name} already exists")

            # Initialize retriever
            self.retriever = VectorRetriever(self.driver, self.index_name, self.embedder)

            # Initialize GraphRAG
            self.graphrag = GraphRAG(
                retriever=self.retriever,
                llm=self.llm
            )

        except Exception as e:
            logger.error(f"Error initializing Neo4jHandler: {str(e)}")
            raise

    def _index_exists(self, index_name: str) -> bool:
        """Check if a vector index exists in Neo4j."""
        try:
            with self.driver.session() as session:
                result = session.run(
                    "SHOW INDEXES YIELD name WHERE name = $index_name",
                    index_name=index_name
                )
                return result.single() is not None
        except Exception as e:
            logger.error(f"Error checking if index exists: {str(e)}")
            return False

    async def process_document(self, doc_id: str, doc_name: str, content: str) -> None:
        """Process a single document and build a knowledge graph."""
        try:
            logger.info(f"Processing document: {doc_name}")
            
            # Build the knowledge graph
            try:
                if USE_SCHEMA:
                    kg_builder = SimpleKGPipeline(
                        embedder=self.embedder,
                        driver=self.driver,
                        llm=self.llm,
                        entities=ENTITIES,
                        relations=RELATIONS,
                        potential_schema=POTENTIAL_SCHEMA,
                        enforce_schema="NONE",
                        from_pdf=content.endswith('.pdf'),
                    )
                else:
                    kg_builder = SimpleKGPipeline(
                        embedder=self.embedder,
                        driver=self.driver,
                        llm=self.llm,
                        from_pdf=content.endswith('.pdf'),
                    )
            except Exception as e:
                logger.error(f"Error creating SimpleKGPipeline: {str(e)}")
                raise
            
            if content.endswith('.pdf'):
                await kg_builder.run_async(file_path=content)
            else:
                await kg_builder.run_async(text=content)
                
            logger.info(f"Successfully built knowledge graph for document: {doc_name}")
        except Exception as e:
            logger.error(f"Error processing document {doc_name}: {str(e)}")
            raise

    async def query_graph(self, question: str) -> str:
        """Query the knowledge graph using GraphRAG."""
        try:
            logger.info(f"Processing query: {question}")
            response = self.graphrag.search(query_text=question, retriever_config={"top_k": 5})
            logger.info("Successfully generated response with GraphRAG")
            return response.answer
        except Exception as e:
            logger.error(f"Error querying graph: {str(e)}")
            raise

    def close(self) -> None:
        """Close Neo4j connection."""
        if hasattr(self, 'driver'):
            self.driver.close()
            logger.info("Neo4j connection closed") 