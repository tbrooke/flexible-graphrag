from llama_index.core import VectorStoreIndex, PropertyGraphIndex, StorageContext, Settings
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import KeywordExtractor, SummaryExtractor
from llama_index.core.indices.property_graph import SchemaLLMPathExtractor, SimpleLLMPathExtractor
from typing import List, Dict, Any, Union
from pathlib import Path
import logging
import asyncio

from config import Settings as AppSettings, SAMPLE_SCHEMA, SearchDBType
from document_processor import DocumentProcessor
from factories import LLMFactory, DatabaseFactory
from sources import FileSystemSource, CmisSource, AlfrescoSource

logger = logging.getLogger(__name__)

class SchemaManager:
    """Manages schema definitions for entity and relationship extraction"""
    
    def __init__(self, schema_config: Dict[str, Any] = None):
        self.schema_config = schema_config or {}
    
    def create_extractor(self, llm, use_schema: bool = True):
        """Create knowledge graph extractor with optional schema enforcement"""
        
        if not use_schema or not self.schema_config:
            return SimpleLLMPathExtractor(
                llm=llm,
                max_paths_per_chunk=10,
                num_workers=4
            )
        
        # Create schema-guided extractor
        return SchemaLLMPathExtractor(
            llm=llm,
            possible_entities=self.schema_config.get("entities", []),
            possible_relations=self.schema_config.get("relations", []),
            kg_validation_schema=self.schema_config.get("validation_schema"),
            strict=self.schema_config.get("strict", True),
            max_triplets_per_chunk=self.schema_config.get("max_triplets_per_chunk", 10),
            num_workers=4
        )

class HybridSearchSystem:
    """Configurable hybrid search system with full-text, vector, and graph search"""
    
    def __init__(self, config: AppSettings):
        self.config = config
        self.document_processor = DocumentProcessor()
        self.schema_manager = SchemaManager(config.schema_config)
        
        # Initialize LLM and embedding models
        self.llm = LLMFactory.create_llm(config.llm_provider, config.llm_config)
        self.embed_model = LLMFactory.create_embedding_model(config.llm_provider, config.llm_config)
        
        # Set global settings
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        Settings.chunk_size = config.chunk_size
        
        # Initialize database connections
        self._setup_databases()
        
        # Initialize indexes
        self.vector_index = None
        self.graph_index = None
        self.hybrid_retriever = None
        
        logger.info("HybridSearchSystem initialized successfully")
    
    def _setup_databases(self):
        """Initialize database connections based on configuration"""
        
        # Vector database
        self.vector_store = DatabaseFactory.create_vector_store(
            self.config.vector_db, 
            self.config.vector_db_config or {}
        )
        
        # Graph database
        self.graph_store = DatabaseFactory.create_graph_store(
            self.config.graph_db,
            self.config.graph_db_config or {}
        )
        
        # Search database - handle BM25 or external search engines
        if self.config.search_db == SearchDBType.BM25:
            self.search_store = None  # BM25 is handled by BM25Retriever
            logger.info("Using BM25 retriever for full-text search (no external search engine required)")
        else:
            self.search_store = DatabaseFactory.create_search_store(
                self.config.search_db,
                self.config.search_db_config or {}
            )
            logger.info(f"Using external search engine: {self.config.search_db}")
        
        logger.info("Database connections established")
    
    @classmethod
    def from_settings(cls, settings: AppSettings):
        """Create HybridSearchSystem from Settings object"""
        return cls(settings)
    
    async def ingest_documents(self, file_paths: List[Union[str, Path]]):
        """Process and ingest documents into all search modalities"""
        
        # Step 1: Convert documents using Docling
        logger.info("Converting documents with Docling...")
        documents = await self.document_processor.process_documents(file_paths)
        
        if not documents:
            raise ValueError("No documents were successfully processed")
        
        # Step 2: Process documents into nodes once
        logger.info("Processing documents into nodes...")
        transformations = [
            SentenceSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            ),
            KeywordExtractor(keywords=5),
            SummaryExtractor(summaries=["prev", "self", "next"]),
            self.embed_model
        ]
        
        # Process documents through transformations to get nodes
        pipeline = IngestionPipeline(transformations=transformations)
        nodes = pipeline.run(documents=documents)
        
        logger.info(f"Generated {len(nodes)} nodes from {len(documents)} documents")
        
        # Step 3: Create vector index from processed nodes
        logger.info("Creating vector index from nodes...")
        vector_storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.vector_index = VectorStoreIndex(
            nodes=nodes,
            storage_context=vector_storage_context,
            show_progress=True
        )
        
        # Step 4: Create graph index using the same nodes
        logger.info("Creating graph index from same nodes...")
        kg_extractor = self.schema_manager.create_extractor(
            self.llm, 
            use_schema=self.config.schema_config is not None
        )
        
        graph_storage_context = StorageContext.from_defaults(
            property_graph_store=self.graph_store,
            docstore=self.vector_index.docstore  # Share the same docstore
        )
        
        # Use asyncio.get_event_loop().run_in_executor to avoid event loop conflict
        import asyncio
        import functools
        
        loop = asyncio.get_event_loop()
        create_graph_index = functools.partial(
            PropertyGraphIndex.from_documents,
            documents=documents,
            llm=self.llm,
            embed_model=self.embed_model,
            kg_extractors=[kg_extractor],
            storage_context=graph_storage_context,
            transformations=[],  # Skip transformations since already processed
            show_progress=True
        )
        
        self.graph_index = await loop.run_in_executor(None, create_graph_index)
        
        # Step 4: Setup hybrid retriever
        self._setup_hybrid_retriever()
        
        # Step 5: Persist indexes if configured
        self._persist_indexes()
        
        logger.info("Document ingestion completed successfully!")
    
    async def ingest_cmis(self):
        """Ingest documents from CMIS source"""
        logger.info("Starting CMIS document ingestion...")
        
        # Initialize CMIS source
        cmis_source = CmisSource(
            url=self.config.llm_config.get("cmis_url"),
            username=self.config.llm_config.get("cmis_username"),
            password=self.config.llm_config.get("cmis_password"),
            folder_path=self.config.llm_config.get("cmis_folder_path", "/")
        )
        
        # Get documents from CMIS
        cmis_docs = cmis_source.list_files()
        
        # Process documents (this would need enhancement to handle CMIS document download)
        # For now, we'll pass the document names as a placeholder
        file_paths = [doc['name'] for doc in cmis_docs]
        await self.ingest_documents(file_paths)
    
    async def ingest_alfresco(self):
        """Ingest documents from Alfresco source"""
        logger.info("Starting Alfresco document ingestion...")
        
        # Initialize Alfresco source
        alfresco_source = AlfrescoSource(
            base_url=self.config.llm_config.get("alfresco_url"),
            username=self.config.llm_config.get("alfresco_username"),
            password=self.config.llm_config.get("alfresco_password"),
            path=self.config.llm_config.get("alfresco_path", "/")
        )
        
        # Get documents from Alfresco
        alfresco_docs = alfresco_source.list_files()
        
        # Process documents (this would need enhancement to handle Alfresco document download)
        # For now, we'll pass the document names as a placeholder
        file_paths = [doc['name'] for doc in alfresco_docs]
        await self.ingest_documents(file_paths)
    
    async def ingest_text(self, content: str, source_name: str = "text_input"):
        """Ingest raw text content"""
        logger.info(f"Ingesting text content from: {source_name}")
        
        # Create document from text
        document = self.document_processor.process_text_content(content, source_name)
        
        # Process similar to file ingestion but with single document
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap
                ),
                KeywordExtractor(keywords=5),
                SummaryExtractor(summaries=["prev", "self", "next"]),
                self.embed_model
            ]
        )
        
        nodes = pipeline.run(documents=[document])
        
        # Update or create indexes
        if self.vector_index is None:
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            self.vector_index = VectorStoreIndex.from_documents(
                documents=[document],
                storage_context=storage_context,
                embed_model=self.embed_model
            )
        else:
            # Add to existing index
            self.vector_index.insert_nodes(nodes)
        
        # Update graph index
        kg_extractor = self.schema_manager.create_extractor(
            self.llm, 
            use_schema=self.config.schema_config is not None
        )
        
        if self.graph_index is None:
            graph_storage_context = StorageContext.from_defaults(
                property_graph_store=self.graph_store
            )
            self.graph_index = PropertyGraphIndex.from_documents(
                documents=[document],
                llm=self.llm,
                embed_model=self.embed_model,
                kg_extractors=[kg_extractor],
                storage_context=graph_storage_context
            )
        else:
            # Add to existing graph index
            self.graph_index.insert_nodes(nodes)
        
        # Setup hybrid retriever
        self._setup_hybrid_retriever()
        
        logger.info("Text content ingestion completed successfully!")
    
    def _setup_hybrid_retriever(self):
        """Setup hybrid retriever combining all search modalities"""
        
        if not self.vector_index or not self.graph_index:
            logger.warning("Cannot setup hybrid retriever: missing indexes")
            return
        
        # Vector retriever
        vector_retriever = self.vector_index.as_retriever(
            similarity_top_k=10,
            embed_model=self.embed_model
        )
        
        # BM25 retriever for full-text search
        bm25_config = {
            "similarity_top_k": self.config.bm25_similarity_top_k,
            "persist_dir": self.config.bm25_persist_dir
        }
        
        # Ensure we have nodes in the docstore
        if not self.vector_index.docstore.docs:
            logger.warning("Docstore is empty, skipping BM25 retriever creation")
            bm25_retriever = None
        else:
            logger.info(f"Creating BM25 retriever with {len(self.vector_index.docstore.docs)} documents")
            bm25_retriever = DatabaseFactory.create_bm25_retriever(
                docstore=self.vector_index.docstore,
                config=bm25_config
            )
        
        # Graph retriever
        graph_retriever = self.graph_index.as_retriever(
            include_text=True,
            similarity_top_k=5
        )
        
        # Combine retrievers with fusion
        retrievers = [vector_retriever, graph_retriever]
        if bm25_retriever is not None:
            retrievers.insert(1, bm25_retriever)  # Add BM25 in the middle
            logger.info("Fusion retriever created with vector, BM25, and graph retrievers")
        else:
            logger.info("Fusion retriever created with vector and graph retrievers only (BM25 skipped)")
        
        self.hybrid_retriever = QueryFusionRetriever(
            retrievers=retrievers,
            mode="reciprocal_rerank",
            similarity_top_k=15,
            num_queries=1
        )
        
        logger.info("Hybrid retriever setup completed")
    
    def _persist_indexes(self):
        """Persist indexes to disk if configured"""
        
        # Persist vector index if persist directory is configured
        if hasattr(self.config, 'vector_persist_dir') and self.config.vector_persist_dir:
            logger.info(f"Persisting vector index to: {self.config.vector_persist_dir}")
            self.vector_index.storage_context.persist(persist_dir=self.config.vector_persist_dir)
        
        # Persist graph index if persist directory is configured
        if hasattr(self.config, 'graph_persist_dir') and self.config.graph_persist_dir:
            logger.info(f"Persisting graph index to: {self.config.graph_persist_dir}")
            self.graph_index.storage_context.persist(persist_dir=self.config.graph_persist_dir)
        
        # BM25 persistence is handled automatically by the BM25Retriever
        # when it uses the persisted docstore from the vector index
        
        logger.info("Index persistence completed")
    
    async def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Execute hybrid search across all modalities"""
        
        if not self.hybrid_retriever:
            raise ValueError("System not initialized. Please ingest documents first.")
        
        # Execute hybrid search
        results = await self.hybrid_retriever.aretrieve(query)
        
        # Deduplicate results based on content
        seen_content = set()
        deduplicated_results = []
        
        for result in results:
            # Use first 100 characters as a simple content hash for deduplication
            content_hash = result.text[:100].strip()
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                deduplicated_results.append(result)
        
        # Format and rank results
        formatted_results = []
        for i, result in enumerate(deduplicated_results[:top_k]):
            formatted_results.append({
                "rank": i + 1,
                "content": result.text,
                "score": getattr(result, 'score', 0.0),
                "source": result.metadata.get("source", "Unknown"),
                "file_type": result.metadata.get("file_type", "Unknown"),
                "file_name": result.metadata.get("file_name", "Unknown")
            })
        
        return formatted_results
    
    def get_query_engine(self, **kwargs):
        """Get query engine for Q&A"""
        if not self.hybrid_retriever:
            raise ValueError("System not initialized. Please ingest documents first.")
        
        # Create query engine from the retriever
        from llama_index.core.query_engine import RetrieverQueryEngine
        
        return RetrieverQueryEngine.from_args(
            retriever=self.hybrid_retriever,
            llm=self.llm,
            **kwargs
        )
    
    def state(self) -> Dict[str, Any]:
        """Get current system state"""
        return {
            "has_vector_index": self.vector_index is not None,
            "has_graph_index": self.graph_index is not None,
            "has_hybrid_retriever": self.hybrid_retriever is not None,
            "config": {
                "data_source": self.config.data_source,
                "vector_db": self.config.vector_db,
                "graph_db": self.config.graph_db,
                "llm_provider": self.config.llm_provider
            }
        }