from typing import Dict, Any
import logging

from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from llama_index.llms.gemini import Gemini
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.vector_stores.neo4jvector import Neo4jVectorStore
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.vector_stores.elasticsearch import ElasticsearchStore, AsyncBM25Strategy
from llama_index.vector_stores.opensearch import OpensearchVectorStore, OpensearchVectorClient
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.graph_stores.kuzu import KuzuPropertyGraphStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.storage.docstore import SimpleDocumentStore
from qdrant_client import QdrantClient, AsyncQdrantClient
import kuzu
import os

from config import LLMProvider, VectorDBType, GraphDBType, SearchDBType

logger = logging.getLogger(__name__)

def get_embedding_dimension(llm_provider: LLMProvider, llm_config: Dict[str, Any]) -> int:
    """
    Get the embedding dimension based on LLM provider and specific model.
    Centralized function to avoid repeating logic across all database factories.
    """
    if llm_provider == LLMProvider.OPENAI:
        embedding_model = llm_config.get("embedding_model", "text-embedding-3-small")
        # OpenAI embedding dimensions by model
        if "text-embedding-3-large" in embedding_model:
            return 3072
        elif "text-embedding-3-small" in embedding_model:
            return 1536
        elif "text-embedding-ada-002" in embedding_model:
            return 1536
        else:
            return 1536  # Default for OpenAI
    
    elif llm_provider == LLMProvider.OLLAMA:
        embedding_model = llm_config.get("embedding_model", "mxbai-embed-large")
        # Ollama embedding dimensions by model
        if "mxbai-embed-large" in embedding_model:
            return 1024
        elif "nomic-embed-text" in embedding_model:
            return 768
        elif "all-minilm" in embedding_model:
            return 384
        else:
            return 1024  # Default for Ollama
    
    elif llm_provider == LLMProvider.AZURE_OPENAI:
        # Azure OpenAI uses same models as OpenAI
        embedding_model = llm_config.get("embedding_model", "text-embedding-3-small")
        if "text-embedding-3-large" in embedding_model:
            return 3072
        elif "text-embedding-3-small" in embedding_model:
            return 1536
        else:
            return 1536  # Default for Azure OpenAI
    
    else:
        # Default fallback for other providers
        logger.warning(f"Unknown embedding dimension for provider {llm_provider}, defaulting to 1536")
        return 1536

class LLMFactory:
    """Factory for creating LLM instances based on configuration"""
    
    @staticmethod
    def create_llm(provider: LLMProvider, config: Dict[str, Any]):
        """Create LLM instance based on provider and configuration"""
        
        logger.info(f"Creating LLM with provider: {provider}")
        
        if provider == LLMProvider.OPENAI:
            return OpenAI(
                model=config.get("model", "gpt-4o-mini"),
                temperature=config.get("temperature", 0.1),
                api_key=config.get("api_key"),
                max_tokens=config.get("max_tokens", 4000),
                request_timeout=config.get("timeout", 120.0)
            )
        
        elif provider == LLMProvider.OLLAMA:
            model = config.get("model", "llama3.1:8b")
            base_url = config.get("base_url", "http://localhost:11434")
            timeout = config.get("timeout", 300.0)
            logger.info(f"Configuring Ollama LLM - Model: {model}, Base URL: {base_url}, Timeout: {timeout}s")
            return Ollama(
                model=model,
                base_url=base_url,
                temperature=config.get("temperature", 0.1),
                request_timeout=timeout
            )
        
        elif provider == LLMProvider.GEMINI:
            return Gemini(
                model=config.get("model", "models/gemini-1.5-flash"),
                api_key=config.get("api_key"),
                temperature=config.get("temperature", 0.1),
                request_timeout=config.get("timeout", 120.0)
            )
        
        elif provider == LLMProvider.AZURE_OPENAI:
            return AzureOpenAI(
                engine=config["engine"],
                model=config.get("model", "gpt-4"),
                temperature=config.get("temperature", 0.1),
                azure_endpoint=config["azure_endpoint"],
                api_key=config["api_key"],
                api_version=config.get("api_version", "2024-02-01"),
                request_timeout=config.get("timeout", 120.0)
            )
        
        elif provider == LLMProvider.ANTHROPIC:
            return Anthropic(
                model=config.get("model", "claude-3-5-sonnet-20241022"),
                api_key=config.get("api_key"),
                temperature=config.get("temperature", 0.1),
                request_timeout=config.get("timeout", 120.0)
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def create_embedding_model(provider: LLMProvider, config: Dict[str, Any]):
        """Create embedding model based on provider"""
        
        logger.info(f"Creating embedding model with provider: {provider}")
        
        if provider in [LLMProvider.OPENAI, LLMProvider.AZURE_OPENAI]:
            if provider == LLMProvider.AZURE_OPENAI:
                return AzureOpenAIEmbedding(
                    model=config.get("embedding_model", "text-embedding-3-small"),
                    azure_endpoint=config["azure_endpoint"],
                    api_key=config["api_key"],
                    api_version=config.get("api_version", "2024-02-01")
                )
            else:
                return OpenAIEmbedding(
                    model_name=config.get("embedding_model", "text-embedding-3-small"),
                    api_key=config.get("api_key")
                )
        
        elif provider == LLMProvider.OLLAMA:
            embedding_model = config.get("embedding_model", "mxbai-embed-large")
            base_url = config.get("base_url", "http://localhost:11434")
            logger.info(f"Configuring Ollama Embeddings - Model: {embedding_model}, Base URL: {base_url}")
            return OllamaEmbedding(
                model_name=embedding_model,
                base_url=base_url
            )
        
        else:
            # Default to OpenAI for other providers
            logger.warning(f"No embedding model implementation for {provider}, using OpenAI default")
            return OpenAIEmbedding(model_name="text-embedding-3-small")

class DatabaseFactory:
    """Factory for creating database connections"""
    
    @staticmethod
    def create_vector_store(db_type: VectorDBType, config: Dict[str, Any], llm_provider: LLMProvider = None, llm_config: Dict[str, Any] = None):
        """Create vector store based on database type"""
        
        logger.info(f"Creating vector store with type: {db_type}")
        
        # Get embedding dimension from centralized function
        embed_dim = config.get("embed_dim")
        if embed_dim is None and llm_provider and llm_config:
            embed_dim = get_embedding_dimension(llm_provider, llm_config)
            logger.info(f"Detected embedding dimension: {embed_dim} for provider: {llm_provider}")
        elif embed_dim is None:
            embed_dim = 1536  # Fallback default
            logger.warning(f"No embedding dimension detected, using fallback: {embed_dim}")
        
        if db_type == VectorDBType.NONE:
            logger.info("Vector search disabled - no vector store created")
            return None
        
        elif db_type == VectorDBType.QDRANT:
            client = QdrantClient(
                host=config.get("host", "localhost"),
                port=config.get("port", 6333),
                api_key=config.get("api_key"),
                https=config.get("https", False),  # Default to HTTP for local instances
                check_compatibility=False  # Skip version compatibility check
            )
            aclient = AsyncQdrantClient(
                host=config.get("host", "localhost"),
                port=config.get("port", 6333),
                api_key=config.get("api_key"),
                https=config.get("https", False),  # Default to HTTP for local instances
                check_compatibility=False  # Skip version compatibility check
            )
            collection_name = config.get("collection_name", "hybrid_search")
            logger.info(f"Creating Qdrant vector store - Collection: {collection_name}, Embed dim: {embed_dim}")
            
            return QdrantVectorStore(
                client=client,
                aclient=aclient,
                collection_name=collection_name
            )
        
        elif db_type == VectorDBType.NEO4J:
            url = config.get("url", "bolt://localhost:7687")
            index_name = config.get("index_name", "hybrid_search_vector")
            logger.info(f"Creating Neo4j vector store - URL: {url}, Index: {index_name}, Embed dim: {embed_dim}")
            
            return Neo4jVectorStore(
                username=config.get("username", "neo4j"),
                password=config["password"],
                url=url,
                embedding_dimension=embed_dim,
                database=config.get("database", "neo4j"),
                index_name=index_name
            )
        
        elif db_type == VectorDBType.ELASTICSEARCH:
            from llama_index.vector_stores.elasticsearch import AsyncDenseVectorStrategy
            
            index_name = config.get("index_name", "hybrid_search_vector")
            es_url = config.get("url", "http://localhost:9200")
            logger.info(f"Creating Elasticsearch vector store - Index: {index_name}, URL: {es_url}, Embed dim: {embed_dim}")
            
            return ElasticsearchStore(
                index_name=index_name,
                es_url=es_url,
                es_user=config.get("username"),
                es_password=config.get("password"),
                retrieval_strategy=AsyncDenseVectorStrategy()  # Pure vector search (fix query parsing issue)
            )
        
        elif db_type == VectorDBType.OPENSEARCH:
            from llama_index.vector_stores.opensearch import OpensearchVectorClient
            
            # Create OpenSearch vector client with hybrid search pipeline
            logger.info(f"Creating OpenSearch vector store with embedding dimension: {embed_dim}")
            
            client = OpensearchVectorClient(
                endpoint=config.get("url", "http://localhost:9201"),
                index=config.get("index_name", "hybrid_search_vector"),
                dim=embed_dim,
                embedding_field=config.get("embedding_field", "embedding"),
                text_field=config.get("text_field", "content"),
                search_pipeline=config.get("search_pipeline", "hybrid-search-pipeline"),  # Enable hybrid search pipeline
                http_auth=(config.get("username"), config.get("password")) if config.get("username") else None
            )
            
            return OpensearchVectorStore(client)
        
        else:
            raise ValueError(f"Unsupported vector database: {db_type}")
    
    @staticmethod
    def create_graph_store(db_type: GraphDBType, config: Dict[str, Any], schema_config: Dict[str, Any] = None, has_separate_vector_store: bool = False, llm_provider: LLMProvider = None, llm_config: Dict[str, Any] = None):
        """Create graph store based on database type"""
        
        logger.info(f"Creating graph store with type: {db_type}")
        
        if db_type == GraphDBType.NONE:
            logger.info("Graph search disabled - no graph store created")
            return None
        
        elif db_type == GraphDBType.NEO4J:
            return Neo4jPropertyGraphStore(
                username=config.get("username", "neo4j"),
                password=config["password"],
                url=config.get("url", "bolt://localhost:7687"),
                database=config.get("database", "neo4j"),
                refresh_schema=False  # Disable APOC schema refresh to avoid apoc.meta.data calls
            )
        
        elif db_type == GraphDBType.KUZU:
            from config import SAMPLE_SCHEMA, KUZU_SCHEMA
            
            db_path = config.get("db_path", "./kuzu_db")
            
            # For development/testing: ensure clean schema by recreating database
            # This prevents "Table Entity does not exist" errors when switching models or schemas
            import os
            import shutil
            if os.path.exists(db_path):
                try:
                    shutil.rmtree(db_path)
                    logger.info(f"Cleaned existing Kuzu database at {db_path} for fresh schema")
                except Exception as e:
                    logger.warning(f"Could not clean Kuzu database: {e}")
            
            kuzu_db = kuzu.Database(db_path)
            
            # Get relationship schema - use provided or Kuzu-specific default
            relationship_schema = None
            if schema_config and "validation_schema" in schema_config:
                # Extract relationships from validation_schema
                validation_data = schema_config["validation_schema"]
                if isinstance(validation_data, dict) and "relationships" in validation_data:
                    relationship_schema = validation_data["relationships"]
                elif isinstance(validation_data, list):
                    relationship_schema = validation_data
                logger.info("Using provided schema for Kuzu")
            else:
                # Use Kuzu-specific schema (Entity/Chunk labels only)
                logger.info("Using default KUZU_SCHEMA for Kuzu (Entity/Chunk labels)")
                relationship_schema = KUZU_SCHEMA["validation_schema"]["relationships"]
            
            # Use Approach 2 (separate vector store) when available
            if has_separate_vector_store:
                # Approach 2: Kuzu for graph relationships, separate vector store for embeddings
                logger.info("Using Kuzu Approach 2: separate vector store for embeddings")
                graph_store = KuzuPropertyGraphStore(
                    kuzu_db,
                    has_structured_schema=False,  # Disable structured schema validation
                    use_vector_index=False,  # Disable Kuzu's vector index, use separate vector store
                )
                
                # Initialize schema to prevent "Table Entity does not exist" error
                try:
                    graph_store.init_schema()
                    logger.info("Kuzu Approach 2 schema initialized successfully")
                    
                    # Verify schema was actually created
                    # COMMENTED OUT: Causes syntax and lock issues with Kuzu
                    # conn = kuzu.Connection(kuzu_db)
                    # result = conn.execute("SHOW TABLES")
                    # tables = result.get_as_df()
                    # logger.info(f"Kuzu tables after init_schema: {tables}")
                    
                except Exception as e:
                    logger.warning(f"Auto schema initialization failed: {e}")
                    # Solution 3: Manual table creation as fallback
                    try:
                        conn = kuzu.Connection(kuzu_db)
                        
                        # Check what tables exist before manual creation
                        # COMMENTED OUT: Causes lock issues with Kuzu concurrency
                        # try:
                        #     result = conn.execute("CALL show_tables() RETURN *")
                        #     existing_tables = result.get_as_df()
                        #     logger.info(f"Existing tables before manual creation: {existing_tables}")
                        # except Exception as e:
                        #     logger.info(f"Could not check existing tables: {e}")
                        
                        # Create proper schema for Kuzu + Qdrant integration (matching KUZU_SCHEMA)
                        # Create Chunk table (KUZU_SCHEMA expects "Chunk", not "DOCUMENT")
                        conn.execute("""
                            CREATE NODE TABLE IF NOT EXISTS Chunk(
                                id INT64 PRIMARY KEY,
                                title STRING,
                                qdrant_id STRING,
                                text STRING,
                                metadata STRING
                            )
                        """)
                        # Create Entity table (matching KUZU_SCHEMA expectations)
                        conn.execute("""
                            CREATE NODE TABLE IF NOT EXISTS Entity(
                                id INT64 PRIMARY KEY,
                                name STRING,
                                qdrant_id STRING,
                                type STRING,
                                description STRING
                            )
                        """)
                        # Create relationship tables matching KUZU_SCHEMA
                        conn.execute("""
                            CREATE REL TABLE IF NOT EXISTS WORKS_FOR(
                                FROM Entity TO Entity,
                                type STRING
                            )
                        """)
                        conn.execute("""
                            CREATE REL TABLE IF NOT EXISTS LOCATED_IN(
                                FROM Entity TO Entity,
                                type STRING
                            )
                        """)
                        conn.execute("""
                            CREATE REL TABLE IF NOT EXISTS USES(
                                FROM Entity TO Entity,
                                type STRING
                            )
                        """)
                        conn.execute("""
                            CREATE REL TABLE IF NOT EXISTS COLLABORATES_WITH(
                                FROM Entity TO Entity,
                                type STRING
                            )
                        """)
                        conn.execute("""
                            CREATE REL TABLE IF NOT EXISTS DEVELOPS(
                                FROM Entity TO Entity,
                                type STRING
                            )
                        """)
                        conn.execute("""
                            CREATE REL TABLE IF NOT EXISTS MENTIONS(
                                FROM Chunk TO Entity,
                                context STRING
                            )
                        """)
                        
                        # Verify manual creation worked
                        logger.info("Kuzu comprehensive tables created manually as fallback")
                        logger.info("Created tables: Chunk, Entity, WORKS_FOR, LOCATED_IN, USES, COLLABORATES_WITH, DEVELOPS, MENTIONS")
                        
                    except Exception as manual_error:
                        logger.error(f"Manual table creation also failed: {manual_error}")
                
                return graph_store
            else:
                # Approach 1: Kuzu with built-in vector index (if no separate vector store)
                # Use the proper embedding model based on LLM provider
                if llm_provider and llm_config:
                    embed_model = LLMFactory.create_embedding_model(llm_provider, llm_config)
                    # Handle both enum and string values for llm_provider
                    provider_name = llm_provider.value if hasattr(llm_provider, 'value') else str(llm_provider)
                    logger.info(f"Using Kuzu Approach 1: built-in vector index with {provider_name} embeddings")
                else:
                    # Fallback to OpenAI if no provider specified
                    from llama_index.embeddings.openai import OpenAIEmbedding
                    embed_model = OpenAIEmbedding(model_name="text-embedding-3-small")
                    logger.warning("No LLM provider specified for Kuzu, falling back to OpenAI embeddings")
                
                graph_store = KuzuPropertyGraphStore(
                    kuzu_db,
                    has_structured_schema=False,  # Disable structured schema validation  
                    use_vector_index=True,  # Enable Kuzu's vector index
                    embed_model=embed_model
                )
                
                # CRITICAL: Initialize schema to prevent "Table Entity does not exist" error
                try:
                    graph_store.init_schema()
                    logger.info("Kuzu schema initialized successfully")
                except Exception as e:
                    logger.warning(f"Auto schema initialization failed: {e}")
                    # Solution 3: Manual table creation as fallback  
                    try:
                        conn = kuzu.Connection(kuzu_db)
                        # Create comprehensive schema for PropertyGraphIndex (Approach 1 - built-in vectors)
                        conn.execute("""
                            CREATE NODE TABLE IF NOT EXISTS DOCUMENT(
                                id INT64 PRIMARY KEY,
                                title STRING,
                                text STRING,
                                metadata STRING
                            )
                        """)
                        conn.execute("""
                            CREATE NODE TABLE IF NOT EXISTS ENTITY(
                                id INT64 PRIMARY KEY,
                                name STRING,
                                type STRING,
                                description STRING
                            )
                        """)
                        conn.execute("""
                            CREATE REL TABLE IF NOT EXISTS RELATIONSHIP(
                                FROM ENTITY TO ENTITY,
                                type STRING,
                                description STRING
                            )
                        """)
                        conn.execute("""
                            CREATE REL TABLE IF NOT EXISTS MENTIONS(
                                FROM DOCUMENT TO ENTITY,
                                context STRING
                            )
                        """)
                        logger.info("Kuzu schema created manually for Approach 1 (built-in vectors)")
                    except Exception as manual_error:
                        logger.error(f"Manual table creation also failed: {manual_error}")
                
                return graph_store
        
        else:
            raise ValueError(f"Unsupported graph database: {db_type}")
    
    @staticmethod
    def create_search_store(db_type: SearchDBType, config: Dict[str, Any], vector_db_type: VectorDBType = None, llm_provider: LLMProvider = None, llm_config: Dict[str, Any] = None):
        """Create search store for full-text search"""
        
        logger.info(f"Creating search store with type: {db_type}")
        
        # Get embedding dimension from centralized function
        embed_dim = config.get("embed_dim")
        if embed_dim is None and llm_provider and llm_config:
            embed_dim = get_embedding_dimension(llm_provider, llm_config)
            logger.info(f"Detected embedding dimension for search store: {embed_dim} for provider: {llm_provider}")
        elif embed_dim is None:
            embed_dim = 1536  # Fallback default
            logger.warning(f"No embedding dimension detected for search store, using fallback: {embed_dim}")
        
        if db_type == SearchDBType.NONE:
            logger.info("Full-text search disabled - no search store created")
            return None
        
        elif db_type == SearchDBType.BM25:
            # BM25 is handled differently - it's a retriever, not a store
            # We'll return None and handle it in the hybrid system
            logger.info("BM25 search selected - will be handled by BM25Retriever")
            return None
        
        elif db_type == SearchDBType.ELASTICSEARCH:
            from llama_index.vector_stores.elasticsearch import AsyncBM25Strategy
            
            index_name = config.get("index_name", "hybrid_search_fulltext")
            es_url = config.get("url", "http://localhost:9200")
            logger.info(f"Creating Elasticsearch search store - Index: {index_name}, URL: {es_url}, Embed dim: {embed_dim}")
            
            return ElasticsearchStore(
                index_name=index_name,
                es_url=es_url,
                es_user=config.get("username"),
                es_password=config.get("password"),
                retrieval_strategy=AsyncBM25Strategy()  # Explicit BM25 for keyword-only search
            )
        
        elif db_type == SearchDBType.OPENSEARCH:
            # Only create OpenSearch search store if vector DB is NOT OpenSearch (to avoid hybrid mode conflicts)
            if vector_db_type == VectorDBType.OPENSEARCH:
                logger.info("OpenSearch search store skipped - vector DB is also OpenSearch (using native hybrid search)")
                return None
            
            # Create OpenSearch vector store for fulltext-only search
            from llama_index.vector_stores.opensearch import OpensearchVectorStore, OpensearchVectorClient
            
            # Create OpenSearch vector client for fulltext search
            logger.info(f"Creating OpenSearch search store with embedding dimension: {embed_dim}")
            
            client = OpensearchVectorClient(
                endpoint=config.get("url", "http://localhost:9201"),
                index=config.get("index_name", "hybrid_search_fulltext"),
                dim=embed_dim,
                embedding_field=config.get("embedding_field", "embedding"),
                text_field=config.get("text_field", "content"),
                http_auth=(config.get("username"), config.get("password")) if config.get("username") else None
            )
            
            logger.info("OpenSearch search store created for fulltext-only search (VectorStoreQueryMode.TEXT_SEARCH)")
            return OpensearchVectorStore(client)
        
        else:
            raise ValueError(f"Unsupported search database: {db_type}")
    
    @staticmethod
    def create_bm25_retriever(docstore, config: Dict[str, Any] = None):
        """Create BM25 retriever with optional persistence"""
        
        logger.info("Creating BM25 retriever")
        
        if config is None:
            config = {}
        
        # Create BM25 retriever
        bm25_retriever = BM25Retriever.from_defaults(
            docstore=docstore,
            similarity_top_k=config.get("similarity_top_k", 10)
        )
        
        # Handle persistence if configured
        persist_dir = config.get("persist_dir")
        if persist_dir:
            # Ensure directory exists
            os.makedirs(persist_dir, exist_ok=True)
            logger.info(f"BM25 index will be persisted to: {persist_dir}")
            
            # The BM25Retriever uses the docstore which is already configured for persistence
            # The docstore will handle the actual persistence when the vector index is persisted
        
        return bm25_retriever