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
from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.vector_stores.opensearch import OpensearchVectorStore
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.graph_stores.kuzu import KuzuPropertyGraphStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.storage.docstore import SimpleDocumentStore
from qdrant_client import QdrantClient
import kuzu
import os

from config import LLMProvider, VectorDBType, GraphDBType, SearchDBType

logger = logging.getLogger(__name__)

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
                max_tokens=config.get("max_tokens", 4000)
            )
        
        elif provider == LLMProvider.OLLAMA:
            return Ollama(
                model=config.get("model", "llama3.1:8b"),
                base_url=config.get("base_url", "http://localhost:11434"),
                temperature=config.get("temperature", 0.1),
                request_timeout=config.get("timeout", 60.0)
            )
        
        elif provider == LLMProvider.GEMINI:
            return Gemini(
                model=config.get("model", "models/gemini-1.5-flash"),
                api_key=config.get("api_key"),
                temperature=config.get("temperature", 0.1)
            )
        
        elif provider == LLMProvider.AZURE_OPENAI:
            return AzureOpenAI(
                engine=config["engine"],
                model=config.get("model", "gpt-4"),
                temperature=config.get("temperature", 0.1),
                azure_endpoint=config["azure_endpoint"],
                api_key=config["api_key"],
                api_version=config.get("api_version", "2024-02-01")
            )
        
        elif provider == LLMProvider.ANTHROPIC:
            return Anthropic(
                model=config.get("model", "claude-3-5-sonnet-20241022"),
                api_key=config.get("api_key"),
                temperature=config.get("temperature", 0.1)
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
            return OllamaEmbedding(
                model_name=config.get("embedding_model", "mxbai-embed-large"),
                base_url=config.get("base_url", "http://localhost:11434")
            )
        
        else:
            # Default to OpenAI for other providers
            logger.warning(f"No embedding model implementation for {provider}, using OpenAI default")
            return OpenAIEmbedding(model_name="text-embedding-3-small")

class DatabaseFactory:
    """Factory for creating database connections"""
    
    @staticmethod
    def create_vector_store(db_type: VectorDBType, config: Dict[str, Any]):
        """Create vector store based on database type"""
        
        logger.info(f"Creating vector store with type: {db_type}")
        
        if db_type == VectorDBType.QDRANT:
            client = QdrantClient(
                host=config.get("host", "localhost"),
                port=config.get("port", 6333),
                api_key=config.get("api_key")
            )
            return QdrantVectorStore(
                client=client,
                collection_name=config.get("collection_name", "hybrid_search")
            )
        
        elif db_type == VectorDBType.NEO4J:
            return Neo4jVectorStore(
                username=config.get("username", "neo4j"),
                password=config["password"],
                url=config.get("url", "bolt://localhost:7687"),
                embedding_dimension=config.get("embed_dim", 1536)
            )
        
        elif db_type == VectorDBType.ELASTICSEARCH:
            return ElasticsearchStore(
                index_name=config.get("index_name", "hybrid_search"),
                es_url=config.get("url", "http://localhost:9200"),
                es_user=config.get("username"),
                es_password=config.get("password")
            )
        
        elif db_type == VectorDBType.OPENSEARCH:
            return OpensearchVectorStore(
                index_name=config.get("index_name", "hybrid_search"),
                endpoint=config.get("url", "http://localhost:9200"),
                http_auth=(config.get("username"), config.get("password")) if config.get("username") else None
            )
        
        else:
            raise ValueError(f"Unsupported vector database: {db_type}")
    
    @staticmethod
    def create_graph_store(db_type: GraphDBType, config: Dict[str, Any]):
        """Create graph store based on database type"""
        
        logger.info(f"Creating graph store with type: {db_type}")
        
        if db_type == GraphDBType.NEO4J:
            return Neo4jPropertyGraphStore(
                username=config.get("username", "neo4j"),
                password=config["password"],
                url=config.get("url", "bolt://localhost:7687")
            )
        
        elif db_type == GraphDBType.KUZU:
            db_path = config.get("db_path", "./kuzu_db")
            kuzu_db = kuzu.Database(db_path)
            return KuzuPropertyGraphStore(kuzu_db)
        
        else:
            raise ValueError(f"Unsupported graph database: {db_type}")
    
    @staticmethod
    def create_search_store(db_type: SearchDBType, config: Dict[str, Any]):
        """Create search store for full-text search"""
        
        logger.info(f"Creating search store with type: {db_type}")
        
        if db_type == SearchDBType.BM25:
            # BM25 is handled differently - it's a retriever, not a store
            # We'll return None and handle it in the hybrid system
            logger.info("BM25 search selected - will be handled by BM25Retriever")
            return None
        
        elif db_type == SearchDBType.ELASTICSEARCH:
            return ElasticsearchStore(
                index_name=config.get("index_name", "fulltext_search"),
                es_url=config.get("url", "http://localhost:9200"),
                es_user=config.get("username"),
                es_password=config.get("password"),
                hybrid_search=True
            )
        
        elif db_type == SearchDBType.OPENSEARCH:
            return OpensearchVectorStore(
                index_name=config.get("index_name", "fulltext_search"),
                endpoint=config.get("url", "http://localhost:9200"),
                http_auth=(config.get("username"), config.get("password")) if config.get("username") else None
            )
        
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