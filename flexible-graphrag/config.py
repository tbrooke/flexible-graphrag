from enum import Enum
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
import os
import json

class DataSourceType(str, Enum):
    FILESYSTEM = "filesystem"
    CMIS = "cmis"
    ALFRESCO = "alfresco"

class VectorDBType(str, Enum):
    QDRANT = "qdrant"
    NEO4J = "neo4j"
    ELASTICSEARCH = "elasticsearch"
    OPENSEARCH = "opensearch"

class GraphDBType(str, Enum):
    NEO4J = "neo4j"
    KUZU = "kuzu"

class SearchDBType(str, Enum):
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
    
    # Optional schema
    schema_config: Optional[Dict[str, Any]] = None
    
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
                    "max_tokens": 4000
                }
            elif self.llm_provider == LLMProvider.OLLAMA:
                self.llm_config = {
                    "model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    "embedding_model": "mxbai-embed-large",
                    "temperature": 0.1,
                    "timeout": 60.0
                }
        
        # Set default database configs if not provided
        if not self.vector_db_config:
            if self.vector_db == VectorDBType.NEO4J:
                self.vector_db_config = {
                    "username": os.getenv("NEO4J_USER", "neo4j"),
                    "password": os.getenv("NEO4J_PASSWORD", "password"),
                    "url": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                    "embed_dim": 1536 if self.llm_provider == LLMProvider.OPENAI else 1024
                }
        
        if not self.graph_db_config:
            if self.graph_db == GraphDBType.NEO4J:
                self.graph_db_config = {
                    "username": os.getenv("NEO4J_USER", "neo4j"),
                    "password": os.getenv("NEO4J_PASSWORD", "password"),
                    "url": os.getenv("NEO4J_URI", "bolt://localhost:7687")
                }

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "use_enum_values": True,
        "extra": "allow"
    }

# Sample schema configuration
SAMPLE_SCHEMA = {
    "entities": ["Person", "Organization", "Location", "Technology", "Project", "Document"],
    "relations": ["WORKS_FOR", "LOCATED_IN", "USES", "COLLABORATES_WITH", "DEVELOPS", "MENTIONS"],
    "validation_schema": {
        "relationships": [
            ("Person", "WORKS_FOR", "Organization"),
            ("Person", "LOCATED_IN", "Location"),
            ("Organization", "USES", "Technology"),
            ("Person", "COLLABORATES_WITH", "Person"),
            ("Organization", "DEVELOPS", "Project"),
            ("Document", "MENTIONS", "Person"),
            ("Document", "MENTIONS", "Organization"),
            ("Document", "MENTIONS", "Technology")
        ]
    },
    "strict": False,
    "max_triplets_per_chunk": 15
}