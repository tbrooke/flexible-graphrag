from enum import Enum
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any, Literal
import os
import json

class DataSourceType(str, Enum):
    FILESYSTEM = "filesystem"
    CMIS = "cmis"
    ALFRESCO = "alfresco"
    UPLOAD = "upload"

class VectorDBType(str, Enum):
    NONE = "none"  # Disable vector search
    QDRANT = "qdrant"
    NEO4J = "neo4j"
    ELASTICSEARCH = "elasticsearch"
    OPENSEARCH = "opensearch"

class GraphDBType(str, Enum):
    NONE = "none"  # Disable graph search
    NEO4J = "neo4j"
    KUZU = "kuzu"

class SearchDBType(str, Enum):
    NONE = "none"  # Disable fulltext search
    BM25 = "bm25"  # Built-in BM25 from LlamaIndex (default)
    ELASTICSEARCH = "elasticsearch"
    OPENSEARCH = "opensearch"

class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"

class Settings(BaseSettings):
    # Data source configuration
    data_source: DataSourceType = DataSourceType.FILESYSTEM
    source_paths: Optional[List[str]] = Field(None, description="Files or folders; CMIS/Alfresco config in env")
    
    # Sample text configuration
    sample_text: str = Field(
        default="""The son of Duke Leto Atreides and the Lady Jessica, Paul is the heir of House Atreides,
an aristocratic family that rules the planet Caladan, the rainy planet, since 10191.""",
        description="Default sample text for testing"
    )
    
    @field_validator('source_paths', mode='before')
    @classmethod
    def parse_source_paths(cls, v):
        if isinstance(v, str):
            try:
                # Try to parse as JSON
                return json.loads(v)
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as single path
                return [v]
        return v
    
    # Database configurations
    vector_db: VectorDBType = VectorDBType.NEO4J
    graph_db: GraphDBType = GraphDBType.NEO4J
    search_db: SearchDBType = SearchDBType.BM25  # Built-in BM25 from LlamaIndex (default)
    
    # LLM configuration
    llm_provider: LLMProvider = LLMProvider.OPENAI
    llm_config: Dict[str, Any] = {}
    
    # Schema system
    schema_name: str = Field("none", description="Name of schema to use: 'none', 'default', or custom name")
    schemas: List[Dict[str, Any]] = Field(default_factory=list, description="Array of named schemas")
    
    # Knowledge graph extraction control
    enable_knowledge_graph: bool = Field(True, description="Enable knowledge graph extraction for graph functionality")
    
    # Database connection parameters
    vector_db_config: Dict[str, Any] = {}
    graph_db_config: Dict[str, Any] = {}
    search_db_config: Dict[str, Any] = {}
    
    # BM25 specific configuration
    bm25_persist_dir: Optional[str] = Field(None, description="Directory to persist BM25 index")
    bm25_similarity_top_k: int = Field(10, description="Number of top results for BM25 search")
    
    # Persistence configuration
    vector_persist_dir: Optional[str] = Field(None, description="Directory to persist vector index")
    graph_persist_dir: Optional[str] = Field(None, description="Directory to persist graph index")
    
    # Processing parameters
    chunk_size: int = 1024
    chunk_overlap: int = 128
    max_triplets_per_chunk: int = 10
    
    # Document processing timeouts (in seconds) - DIFFERENT from LLM timeouts
    docling_timeout: int = Field(300, description="Timeout for single document Docling conversion in seconds (default: 5 minutes) - separate from LLM request timeouts")
    docling_cancel_check_interval: float = Field(0.5, description="How often to check for cancellation during Docling processing in seconds - enables mid-file cancellation")
    
    # Knowledge graph extraction timeouts and progress
    kg_extraction_timeout: int = Field(3600, description="Timeout for knowledge graph extraction per document in seconds (default: 1 hour for large documents)")
    kg_progress_reporting: bool = Field(True, description="Enable detailed progress reporting during knowledge graph extraction")
    kg_batch_size: int = Field(10, description="Number of chunks to process in each batch during KG extraction")
    kg_cancel_check_interval: float = Field(2.0, description="How often to check for cancellation during KG extraction in seconds")
    
    # Environment-based defaults
    def __init__(self, **data):
        super().__init__(**data)
        
        # Set default LLM config based on provider if not provided
        if not self.llm_config:
            if self.llm_provider == LLMProvider.OPENAI:
                self.llm_config = {
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "embedding_model": "text-embedding-3-small",
                    "temperature": 0.1,
                    "max_tokens": 4000,
                    "timeout": float(os.getenv("OPENAI_TIMEOUT", "120.0"))
                }
            elif self.llm_provider == LLMProvider.OLLAMA:
                self.llm_config = {
                    "model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    "embedding_model": "mxbai-embed-large",
                    "temperature": 0.1,
                    "timeout": float(os.getenv("OLLAMA_TIMEOUT", "300.0"))  # Higher default for local processing
                }
            elif self.llm_provider == LLMProvider.AZURE_OPENAI:
                self.llm_config = {
                    "engine": os.getenv("AZURE_OPENAI_ENGINE"),
                    "model": os.getenv("AZURE_OPENAI_MODEL", "gpt-4"),
                    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                    "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                    "temperature": 0.1,
                    "timeout": float(os.getenv("AZURE_OPENAI_TIMEOUT", "120.0"))
                }
            elif self.llm_provider == LLMProvider.ANTHROPIC:
                self.llm_config = {
                    "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "temperature": 0.1,
                    "timeout": float(os.getenv("ANTHROPIC_TIMEOUT", "120.0"))
                }
            elif self.llm_provider == LLMProvider.GEMINI:
                self.llm_config = {
                    "model": os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash"),
                    "api_key": os.getenv("GEMINI_API_KEY"),
                    "temperature": 0.1,
                    "timeout": float(os.getenv("GEMINI_TIMEOUT", "120.0"))
                }
        
        # Set default database configs if not provided
        if not self.vector_db_config:
            if self.vector_db == VectorDBType.NEO4J:
                self.vector_db_config = {
                    "username": os.getenv("NEO4J_USER", "neo4j"),
                    "password": os.getenv("NEO4J_PASSWORD", "password"),
                    "url": os.getenv("NEO4J_URI", "bolt://localhost:7687"),  # Standard Neo4j port
                    "database": os.getenv("NEO4J_DATABASE", "neo4j"),
                    "index_name": os.getenv("NEO4J_VECTOR_INDEX", "hybrid_search_vector"),
                    "embed_dim": 1536 if self.llm_provider == LLMProvider.OPENAI else 1024
                }
            elif self.vector_db == VectorDBType.QDRANT:
                self.vector_db_config = {
                    "host": os.getenv("QDRANT_HOST", "localhost"),
                    "port": int(os.getenv("QDRANT_PORT", "6333")),
                    "api_key": os.getenv("QDRANT_API_KEY"),
                    "collection_name": os.getenv("QDRANT_COLLECTION", "hybrid_search"),
                    "https": os.getenv("QDRANT_HTTPS", "false").lower() == "true",
                    "embed_dim": 1536 if self.llm_provider == LLMProvider.OPENAI else 1024  # Ollama compatibility
                }
            elif self.vector_db == VectorDBType.OPENSEARCH:
                self.vector_db_config = {
                    "url": os.getenv("OPENSEARCH_URL", "http://localhost:9201"),
                    "index_name": os.getenv("OPENSEARCH_INDEX", "hybrid_search_vector"),
                    "username": os.getenv("OPENSEARCH_USERNAME"),
                    "password": os.getenv("OPENSEARCH_PASSWORD"),
                    "embed_dim": 1536 if self.llm_provider == LLMProvider.OPENAI else 1024,  # Ollama compatibility
                    "embedding_field": "embedding",
                    "text_field": "content",
                    "search_pipeline": "hybrid-search-pipeline"
                }
        
        if not self.graph_db_config:
            if self.graph_db == GraphDBType.NEO4J:
                self.graph_db_config = {
                    "username": os.getenv("NEO4J_USER", "neo4j"),
                    "password": os.getenv("NEO4J_PASSWORD", "password"),
                    "url": os.getenv("NEO4J_URI", "bolt://localhost:7689"),  # Updated default port
                    "database": os.getenv("NEO4J_DATABASE", "neo4j")
                }
        
        if not self.search_db_config:
            if self.search_db == SearchDBType.OPENSEARCH:
                self.search_db_config = {
                    "url": os.getenv("OPENSEARCH_URL", "http://localhost:9201"),
                    "index_name": os.getenv("OPENSEARCH_INDEX", "hybrid_search_fulltext"),
                    "username": os.getenv("OPENSEARCH_USERNAME"),
                    "password": os.getenv("OPENSEARCH_PASSWORD"),
                    "embed_dim": 1536 if self.llm_provider == LLMProvider.OPENAI else 1024,  # Ollama compatibility
                    "embedding_field": "embedding",
                    "text_field": "content"
                }
            elif self.search_db == SearchDBType.ELASTICSEARCH:
                self.search_db_config = {
                    "url": os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"),
                    "index_name": os.getenv("ELASTICSEARCH_INDEX", "hybrid_search_fulltext"),
                    "username": os.getenv("ELASTICSEARCH_USERNAME"),
                    "password": os.getenv("ELASTICSEARCH_PASSWORD"),
                    "embed_dim": 1536 if self.llm_provider == LLMProvider.OPENAI else 1024  # Ollama compatibility
                }
    
    def get_active_schema(self) -> Optional[Dict[str, Any]]:
        """Get the currently active schema based on schema_name"""
        if self.schema_name == "none":
            return None
        elif self.schema_name == "default":
            return SAMPLE_SCHEMA
        else:
            # Look for named schema in schemas array
            for schema_def in self.schemas:
                if schema_def.get("name") == self.schema_name:
                    return schema_def.get("schema", {})
            
            # If named schema not found, log warning and return None
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Schema '{self.schema_name}' not found in schemas array. Available schemas: {[s.get('name') for s in self.schemas]}")
            return None

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "use_enum_values": True,
        "extra": "allow"
    }

# Sample schema configuration
SAMPLE_SCHEMA = {
    "entities": Literal["PERSON", "ORGANIZATION", "LOCATION", "TECHNOLOGY", "PROJECT", "DOCUMENT"],
    "relations": Literal["WORKS_FOR", "LOCATED_IN", "USES", "COLLABORATES_WITH", "DEVELOPS", "MENTIONS"],
    "validation_schema": {
        "relationships": [
            ("PERSON", "WORKS_FOR", "ORGANIZATION"),
            ("PERSON", "LOCATED_IN", "LOCATION"),
            ("ORGANIZATION", "USES", "TECHNOLOGY"),
            ("PERSON", "COLLABORATES_WITH", "PERSON"),
            ("ORGANIZATION", "DEVELOPS", "PROJECT"),
            ("DOCUMENT", "MENTIONS", "PERSON"),
            ("DOCUMENT", "MENTIONS", "ORGANIZATION"),
            ("DOCUMENT", "MENTIONS", "TECHNOLOGY")
        ]
    },
    "strict": False,
    "max_triplets_per_chunk": 15
}

# Kuzu-specific schema that uses only Entity and Chunk labels
KUZU_SCHEMA = {
    "entities": Literal["Entity"],  # Use Literal type for Pydantic compatibility
    "relations": Literal["WORKS_FOR", "LOCATED_IN", "USES", "COLLABORATES_WITH", "DEVELOPS", "MENTIONS"],
    "validation_schema": {
        "relationships": [
            ("Entity", "WORKS_FOR", "Entity"),
            ("Entity", "LOCATED_IN", "Entity"),
            ("Entity", "USES", "Entity"),
            ("Entity", "COLLABORATES_WITH", "Entity"),
            ("Entity", "DEVELOPS", "Entity"),
            ("Chunk", "MENTIONS", "Entity"),
            ("Entity", "MENTIONS", "Entity")
        ]
    },
    "strict": True,  # Kuzu enforces stricter schema validation
    "max_triplets_per_chunk": 15
}