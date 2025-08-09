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
        self.document_processor = DocumentProcessor(config)
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
    
    async def ingest_documents(self, file_paths: List[Union[str, Path]], processing_id: str = None, status_callback=None):
        """Process and ingest documents into all search modalities"""
        
        # Helper function to check cancellation
        def _check_cancellation():
            if processing_id:
                from backend import PROCESSING_STATUS
                return (processing_id in PROCESSING_STATUS and 
                        PROCESSING_STATUS[processing_id]["status"] == "cancelled")
            return False
        
        # Helper function to update progress with file info
        def _update_progress(message: str, progress: int, current_file: str = None, current_phase: str = None, files_completed: int = 0):
            if status_callback:
                status_callback(
                    processing_id=processing_id,
                    status="processing",
                    message=message,
                    progress=progress,
                    current_file=current_file,
                    current_phase=current_phase,
                    files_completed=files_completed,
                    total_files=len(file_paths)
                )
        
        # Check for partial state and clear it before starting new ingestion
        if (self.vector_index is None) != (self.graph_index is None):
            logger.warning("Detected partial system state - clearing before new ingestion")
            self._clear_partial_state()
        
        # Also clear if we have partial retriever setup
        if self.hybrid_retriever is None and (self.vector_index is not None or self.graph_index is not None):
            logger.warning("Detected incomplete retriever setup - clearing before new ingestion")
            self._clear_partial_state()
        
        # Step 1: Convert documents using Docling
        logger.info("Converting documents with Docling...")
        _update_progress("Converting documents with Docling...", 20, current_phase="docling")
        
        documents = await self.document_processor.process_documents(file_paths, processing_id=processing_id)
        
        if not documents:
            raise ValueError("No documents were successfully processed")
        
        # Check for cancellation after document processing
        if _check_cancellation():
            logger.info("Processing cancelled during document conversion")
            raise RuntimeError("Processing cancelled by user")
        
        # Step 2: Process documents into nodes once
        logger.info("Processing documents into nodes...")
        _update_progress("Splitting documents into chunks...", 30, current_phase="chunking")
        
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
        
        # Use run_in_executor to avoid asyncio conflict
        import asyncio
        import functools
        
        loop = asyncio.get_event_loop()
        run_pipeline = functools.partial(
            pipeline.run,
            documents=documents
        )
        
        nodes = await loop.run_in_executor(None, run_pipeline)
        
        logger.info(f"Generated {len(nodes)} nodes from {len(documents)} documents")
        
        # Check for cancellation after node processing
        if _check_cancellation():
            logger.info("Processing cancelled during node generation")
            raise RuntimeError("Processing cancelled by user")
        
        # Step 3: Create vector index from processed nodes
        logger.info("Creating vector index from nodes...")
        _update_progress("Building vector index...", 50, current_phase="indexing")
        
        vector_storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.vector_index = VectorStoreIndex(
            nodes=nodes,
            storage_context=vector_storage_context,
            show_progress=True
        )
        
        # Check for cancellation after vector index creation
        if _check_cancellation():
            logger.info("Processing cancelled during vector index creation")
            raise RuntimeError("Processing cancelled by user")
        
        # Step 4: Create graph index using the same nodes but with minimal knowledge graph extraction  
        logger.info("Creating graph index from same nodes...")
        _update_progress("Extracting knowledge graph...", 70, current_phase="kg_extraction")
        
        # Always use knowledge graph extraction for graph functionality
        kg_extractors = []
        if self.config.schema_config is not None:
            kg_extractor = self.schema_manager.create_extractor(
                self.llm, 
                use_schema=True
            )
            kg_extractors = [kg_extractor]
            logger.info("Using knowledge graph extraction with schema for graph functionality")
        else:
            # Use simple extractor if no schema provided
            kg_extractor = self.schema_manager.create_extractor(
                self.llm, 
                use_schema=False
            )
            kg_extractors = [kg_extractor]
            logger.info("Using simple knowledge graph extraction for graph functionality")
        
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
            kg_extractors=kg_extractors,  # Use empty list if no schema
            storage_context=graph_storage_context,
            transformations=[],  # Skip transformations since already processed
            show_progress=True,
            # Configure to minimize LLM-generated text in responses
            include_embeddings=True,
            include_metadata=True
        )
        
        self.graph_index = await loop.run_in_executor(None, create_graph_index)
        
        # Check for cancellation after graph index creation
        if _check_cancellation():
            logger.info("Processing cancelled during graph index creation")
            raise RuntimeError("Processing cancelled by user")
        
        # Step 4: Setup hybrid retriever
        self._setup_hybrid_retriever()
        
        # Step 5: Persist indexes if configured
        self._persist_indexes()
        
        logger.info("Document ingestion completed successfully!")
    
    async def ingest_cmis(self, cmis_config: dict = None, processing_id: str = None, status_callback=None):
        """Ingest documents from CMIS source"""
        logger.info("Starting CMIS document ingestion...")
        
        # Use provided config or fall back to global config
        if cmis_config:
            config = cmis_config
        else:
            config = {
                "url": self.config.llm_config.get("cmis_url"),
                "username": self.config.llm_config.get("cmis_username"),
                "password": self.config.llm_config.get("cmis_password"),
                "folder_path": self.config.llm_config.get("cmis_folder_path", "/")
            }
        
        # Initialize CMIS source
        cmis_source = CmisSource(
            url=config["url"],
            username=config["username"],
            password=config["password"],
            folder_path=config["folder_path"]
        )
        
        # Update status: Connected, now scanning
        if status_callback:
            status_callback(
                processing_id=processing_id,
                status="processing",
                message="Connected to CMIS! Scanning for documents...",
                progress=45
            )
        
        # Get documents from CMIS
        cmis_docs = cmis_source.list_files()
        
        if not cmis_docs:
            logger.warning("No supported documents found in CMIS repository")
            if status_callback:
                status_callback(
                    processing_id=processing_id,
                    status="completed",
                    message="No supported documents found in CMIS repository",
                    progress=100
                )
            return
        
        # Update status with document count
        if status_callback:
            status_callback(
                processing_id=processing_id,
                status="processing",
                message=f"Found {len(cmis_docs)} document(s) in CMIS repository",
                progress=50,
                total_files=len(cmis_docs),
                files_completed=0
            )
        
        # Create temporary directory for downloaded files
        import tempfile
        import os
        
        temp_dir = tempfile.mkdtemp(prefix="cmis_ingestion_")
        temp_files = []
        
        try:
            # Download all documents to temporary files
            for i, doc in enumerate(cmis_docs):
                try:
                    # Update progress during download
                    if status_callback:
                        download_progress = 50 + int((i / len(cmis_docs)) * 20)  # 50-70% for downloads
                        status_callback(
                            processing_id=processing_id,
                            status="processing",
                            message=f"Downloading document {i+1}/{len(cmis_docs)}: {doc['name']}",
                            progress=download_progress,
                            current_file=doc['name'],
                            current_phase="downloading",
                            files_completed=i,
                            total_files=len(cmis_docs)
                        )
                    
                    temp_file_path = cmis_source.download_document(doc, temp_dir)
                    temp_files.append(temp_file_path)
                    logger.info(f"Downloaded CMIS document: {doc['name']} -> {temp_file_path}")
                except Exception as e:
                    logger.error(f"Failed to download CMIS document {doc['name']}: {str(e)}")
                    continue
            
            if temp_files:
                # Update status: Starting document processing
                if status_callback:
                    status_callback(
                        processing_id=processing_id,
                        status="processing",
                        message=f"Processing {len(temp_files)} downloaded document(s)...",
                        progress=70,
                        total_files=len(temp_files),
                        files_completed=0
                    )
                
                # Process the downloaded files
                await self.ingest_documents(temp_files, processing_id=processing_id, status_callback=status_callback)
                logger.info(f"Successfully ingested {len(temp_files)} documents from CMIS")
            else:
                logger.warning("No documents were successfully downloaded from CMIS")
                if status_callback:
                    status_callback(
                        processing_id=processing_id,
                        status="completed",
                        message="No documents were successfully downloaded from CMIS",
                        progress=100
                    )
                
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                        logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_file}: {str(e)}")
            
            # Remove temporary directory
            try:
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_dir}: {str(e)}")
    
    async def ingest_alfresco(self, alfresco_config: dict = None, processing_id: str = None, status_callback=None):
        """Ingest documents from Alfresco source"""
        logger.info("Starting Alfresco document ingestion...")
        
        # Use provided config or fall back to global config
        if alfresco_config:
            config = alfresco_config
        else:
            config = {
                "url": self.config.llm_config.get("alfresco_url"),
                "username": self.config.llm_config.get("alfresco_username"),
                "password": self.config.llm_config.get("alfresco_password"),
                "path": self.config.llm_config.get("alfresco_path", "/")
            }
        
        # Initialize Alfresco source
        alfresco_source = AlfrescoSource(
            base_url=config["url"],
            username=config["username"],
            password=config["password"],
            path=config["path"]
        )
        
        # Update status: Connected, now scanning
        if status_callback:
            status_callback(
                processing_id=processing_id,
                status="processing",
                message="Connected to Alfresco! Scanning for documents...",
                progress=45
            )
        
        # Get documents from Alfresco
        alfresco_docs = alfresco_source.list_files()
        
        if not alfresco_docs:
            logger.warning("No supported documents found in Alfresco repository")
            if status_callback:
                status_callback(
                    processing_id=processing_id,
                    status="completed",
                    message="No supported documents found in Alfresco repository",
                    progress=100
                )
            return
        
        # Update status with document count
        if status_callback:
            status_callback(
                processing_id=processing_id,
                status="processing",
                message=f"Found {len(alfresco_docs)} document(s) in Alfresco repository",
                progress=50,
                total_files=len(alfresco_docs),
                files_completed=0
            )
        
        # Create temporary directory for downloaded files
        import tempfile
        import os
        
        temp_dir = tempfile.mkdtemp(prefix="alfresco_ingestion_")
        temp_files = []
        
        try:
            # Download all documents to temporary files
            for i, doc in enumerate(alfresco_docs):
                try:
                    # Update progress during download
                    if status_callback:
                        download_progress = 50 + int((i / len(alfresco_docs)) * 20)  # 50-70% for downloads
                        status_callback(
                            processing_id=processing_id,
                            status="processing",
                            message=f"Downloading document {i+1}/{len(alfresco_docs)}: {doc['name']}",
                            progress=download_progress,
                            current_file=doc['name'],
                            current_phase="downloading",
                            files_completed=i,
                            total_files=len(alfresco_docs)
                        )
                    
                    temp_file_path = alfresco_source.download_document(doc, temp_dir)
                    temp_files.append(temp_file_path)
                    logger.info(f"Downloaded Alfresco document: {doc['name']} -> {temp_file_path}")
                except Exception as e:
                    logger.error(f"Failed to download Alfresco document {doc['name']}: {str(e)}")
                    continue
            
            if temp_files:
                # Update status: Starting document processing
                if status_callback:
                    status_callback(
                        processing_id=processing_id,
                        status="processing",
                        message=f"Processing {len(temp_files)} downloaded document(s)...",
                        progress=70,
                        total_files=len(temp_files),
                        files_completed=0
                    )
                
                # Process the downloaded files
                await self.ingest_documents(temp_files, processing_id=processing_id, status_callback=status_callback)
                logger.info(f"Successfully ingested {len(temp_files)} documents from Alfresco")
            else:
                logger.warning("No documents were successfully downloaded from Alfresco")
                if status_callback:
                    status_callback(
                        processing_id=processing_id,
                        status="completed",
                        message="No documents were successfully downloaded from Alfresco",
                        progress=100
                    )
                
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                        logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_file}: {str(e)}")
            
            # Remove temporary directory
            try:
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_dir}: {str(e)}")
    
    async def ingest_text(self, content: str, source_name: str = "text_input", processing_id: str = None):
        """Ingest raw text content"""
        logger.info(f"Ingesting text content from: {source_name}")
        
        # Helper function to check cancellation
        def _check_cancellation():
            if processing_id:
                from backend import PROCESSING_STATUS
                return (processing_id in PROCESSING_STATUS and 
                        PROCESSING_STATUS[processing_id]["status"] == "cancelled")
            return False
        
        # Create document from text
        document = self.document_processor.process_text_content(content, source_name)
        
        # Check for cancellation after document processing
        if _check_cancellation():
            logger.info("Processing cancelled during text document creation")
            raise RuntimeError("Processing cancelled by user")
        
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
        
        # Use run_in_executor to avoid asyncio conflict
        import asyncio
        import functools
        
        loop = asyncio.get_event_loop()
        run_pipeline = functools.partial(
            pipeline.run,
            documents=[document]
        )
        
        nodes = await loop.run_in_executor(None, run_pipeline)
        
        # Check for cancellation after node processing
        if _check_cancellation():
            logger.info("Processing cancelled during text node generation")
            raise RuntimeError("Processing cancelled by user")
        
        # Update or create indexes
        if self.vector_index is None:
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            
            # Use run_in_executor to avoid asyncio conflict
            import asyncio
            import functools
            
            loop = asyncio.get_event_loop()
            create_vector_index = functools.partial(
                VectorStoreIndex.from_documents,
                documents=[document],
                storage_context=storage_context,
                embed_model=self.embed_model
            )
            
            self.vector_index = await loop.run_in_executor(None, create_vector_index)
        else:
            # Add to existing index
            self.vector_index.insert_nodes(nodes)
        
        # Check for cancellation after vector index creation/update
        if _check_cancellation():
            logger.info("Processing cancelled during text vector index creation")
            raise RuntimeError("Processing cancelled by user")
        
        # Update graph index - always use knowledge graph extraction for graph functionality
        kg_extractors = []
        if self.config.schema_config is not None:
            kg_extractor = self.schema_manager.create_extractor(
                self.llm, 
                use_schema=True
            )
            kg_extractors = [kg_extractor]
            logger.info("Using knowledge graph extraction with schema for text ingestion")
        else:
            # Use simple extractor if no schema provided
            kg_extractor = self.schema_manager.create_extractor(
                self.llm, 
                use_schema=False
            )
            kg_extractors = [kg_extractor]
            logger.info("Using simple knowledge graph extraction for text ingestion")
        
        if self.graph_index is None:
            graph_storage_context = StorageContext.from_defaults(
                property_graph_store=self.graph_store
            )
            
            # Use asyncio.get_event_loop().run_in_executor to avoid event loop conflict
            import asyncio
            import functools
            
            loop = asyncio.get_event_loop()
            create_graph_index = functools.partial(
                PropertyGraphIndex.from_documents,
                documents=[document],
                llm=self.llm,
                embed_model=self.embed_model,
                kg_extractors=kg_extractors,
                storage_context=graph_storage_context
            )
            
            self.graph_index = await loop.run_in_executor(None, create_graph_index)
        else:
            # Add to existing graph index
            self.graph_index.insert_nodes(nodes)
        
        # Check for cancellation after graph index creation/update
        if _check_cancellation():
            logger.info("Processing cancelled during text graph index creation")
            raise RuntimeError("Processing cancelled by user")
        
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
        
        # Graph retriever - configure to return original text from shared docstore
        graph_retriever = self.graph_index.as_retriever(
            include_text=True,
            similarity_top_k=5,
            # Return original document text from the shared docstore, not knowledge graph extraction results
            text_qa_template=None,  # Use default template
            include_metadata=True
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
    
    def _clear_partial_state(self):
        """Clear partial system state when inconsistencies are detected"""
        logger.info("Clearing partial system state")
        self.vector_index = None
        self.graph_index = None
        self.hybrid_retriever = None
        logger.info("System state cleared - requires re-ingestion")
    
    async def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Execute hybrid search across all modalities"""
        
        # Check for complete system initialization
        if not self.hybrid_retriever:
            raise ValueError("System not initialized. Please ingest documents first.")
        
        # Check for partial initialization state
        if not self.vector_index or not self.graph_index:
            logger.warning("System in partial state - missing indexes, clearing and requiring re-ingestion")
            self._clear_partial_state()
            raise ValueError("System not initialized. Please ingest documents first.")
        
        try:
            # Execute hybrid search
            results = await self.hybrid_retriever.aretrieve(query)
        except Exception as e:
            # Check if this is a Neo4j vector index error indicating partial state
            if "vector schema index" in str(e) or "There is no such vector schema index" in str(e):
                logger.warning(f"Detected missing vector indexes in Neo4j: {str(e)}")
                self._clear_partial_state()
                raise ValueError("System not initialized. Please ingest documents first.")
            else:
                # Re-raise other errors
                raise
        
        logger.info(f"Retrieved {len(results)} results from hybrid search")
        
        # Enhanced deduplication with multiple strategies
        seen_content = set()
        seen_sources = {}  # source -> content mapping for additional dedup
        deduplicated_results = []
        
        for result in results:
            source = result.metadata.get("source", "Unknown")
            full_text = result.text.strip()
            
            # Strategy 1: Extract core content by removing common prefixes
            core_content = self._extract_core_content(full_text)
            
            # Strategy 2: Create content hash from core content
            content_hash = core_content[:300].strip().lower()
            
            # Strategy 3: Check for exact source + core content combination
            content_key = f"{source}::{content_hash}"
            
            # Strategy 4: Check for very similar content from same source
            similar_found = False
            if source in seen_sources:
                for existing_content in seen_sources[source]:
                    # Check if content is very similar (overlap > 70%)
                    if len(content_hash) > 50 and len(existing_content) > 50:
                        overlap = len(set(content_hash.split()) & set(existing_content.split()))
                        total_words = len(set(content_hash.split()) | set(existing_content.split()))
                        if total_words > 0 and overlap / total_words > 0.7:
                            similar_found = True
                            break
            
            # Strategy 5: Check for entity-relationship patterns that might be duplicates
            if not similar_found and "->" in full_text:
                # This might be a graph result with entity-relationship format
                # Check if we already have the original text version
                for existing_result in deduplicated_results:
                    existing_text = existing_result.text.strip()
                    existing_core = self._extract_core_content(existing_text)
                    
                    # If existing result doesn't have entity-relationship format but has similar core content
                    if "->" not in existing_text and len(existing_core) > 50:
                        overlap = len(set(core_content.split()) & set(existing_core.split()))
                        total_words = len(set(core_content.split()) | set(existing_core.split()))
                        if total_words > 0 and overlap / total_words > 0.6:
                            similar_found = True
                            break
            
            if content_key not in seen_content and not similar_found:
                seen_content.add(content_key)
                if source not in seen_sources:
                    seen_sources[source] = []
                seen_sources[source].append(content_hash)
                deduplicated_results.append(result)
                logger.debug(f"Added result from {source}: {core_content[:100]}...")
            else:
                logger.debug(f"Deduplicated result from {source}: {core_content[:100]}...")
        
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
        
        logger.info(f"Returning {len(formatted_results)} deduplicated results")
        return formatted_results
    
    def _extract_core_content(self, text: str) -> str:
        """Extract core content by removing common prefixes and suffixes"""
        
        # Common prefixes to remove - expanded list for knowledge graph extraction results
        prefixes_to_remove = [
            "here are some facts extracted from the provided text:",
            "facts extracted from the provided text:",
            "extracted facts:",
            "key information:",
            "summary:",
            "important points:",
            "main points:",
            "key facts:",
            "extracted information:",
            "document summary:",
            "content summary:",
            "text summary:",
            "document facts:",
            "content facts:",
            "text facts:",
            "based on the provided text:",
            "from the provided text:",
            "the text contains:",
            "the document contains:",
            "the content includes:",
            "the information shows:",
            "the facts indicate:",
            "the data reveals:",
            "the analysis shows:",
            "the summary indicates:",
            "the key points are:",
            "the main findings are:",
            "the important details are:",
            "the relevant information is:",
            "the document states:",
            "the text states:",
            "the content states:",
            "the information states:",
            "the facts show:",
            "the data shows:",
            "the analysis reveals:",
            "the summary shows:",
            "the key points show:",
            "the main findings show:",
            "the important details show:",
            "the relevant information shows:",
            # Additional knowledge graph extraction prefixes
            "the following facts were extracted:",
            "extracted from the document:",
            "the document reveals:",
            "the text reveals:",
            "the content reveals:",
            "the information indicates:",
            "the facts demonstrate:",
            "the data indicates:",
            "the analysis indicates:",
            "the summary demonstrates:",
            "the key points indicate:",
            "the main findings indicate:",
            "the important details indicate:",
            "the relevant information indicates:",
            "the document demonstrates:",
            "the text demonstrates:",
            "the content demonstrates:",
            "the information demonstrates:",
            "the facts suggest:",
            "the data suggests:",
            "the analysis suggests:",
            "the summary suggests:",
            "the key points suggest:",
            "the main findings suggest:",
            "the important details suggest:",
            "the relevant information suggests:"
        ]
        
        # Convert to lowercase for comparison
        text_lower = text.lower().strip()
        
        # Remove prefixes
        for prefix in prefixes_to_remove:
            if text_lower.startswith(prefix.lower()):
                # Find the actual prefix in the original text (case-sensitive)
                prefix_start = text.lower().find(prefix.lower())
                if prefix_start != -1:
                    text = text[prefix_start + len(prefix):].strip()
                    break
        
        # Remove common suffixes
        suffixes_to_remove = [
            "end of document",
            "end of text",
            "document ends",
            "text ends",
            "this concludes the document",
            "this concludes the text",
            "this ends the document",
            "this ends the text"
        ]
        
        text_lower = text.lower().strip()
        for suffix in suffixes_to_remove:
            if text_lower.endswith(suffix.lower()):
                # Find the actual suffix in the original text (case-sensitive)
                suffix_start = text.lower().rfind(suffix.lower())
                if suffix_start != -1:
                    text = text[:suffix_start].strip()
                    break
        
        # Additional cleanup: remove entity-relationship patterns
        # Look for patterns like "Entity -> Relation -> Entity" and extract the original text
        import re
        
        # Pattern to find entity-relationship chains (more comprehensive)
        er_patterns = [
            r'^[A-Za-z\s]+->[A-Za-z\s]+->[A-Za-z\s]+:',
            r'^[A-Za-z\s]+->[A-Za-z\s]+:',
            r'^[A-Za-z\s]+->[A-Za-z\s]+->[A-Za-z\s]+->[A-Za-z\s]+:',
            r'^[A-Za-z\s]+->[A-Za-z\s]+->[A-Za-z\s]+->[A-Za-z\s]+->[A-Za-z\s]+:'
        ]
        
        for er_pattern in er_patterns:
            if re.match(er_pattern, text.strip()):
                # Try to find the original text after the entity-relationship chain
                # Look for common document start patterns
                original_patterns = [
                    r'LONDON.*?September.*?\d{4}.*?Alfresco',
                    r'[A-Z]{2,}.*?\d{1,2}.*?\d{4}.*?[A-Za-z]+',
                    r'[A-Z][a-z]+.*?\d{1,2},.*?\d{4}',
                    r'[A-Z][a-z]+.*?\d{1,2}.*?\d{4}',
                    r'[A-Z][a-z]+.*?\d{1,2}.*?\d{4}.*?[A-Za-z]+',
                    r'[A-Z]{2,}.*?\d{1,2}.*?\d{4}',
                    r'[A-Z][a-z]+.*?\d{1,2}.*?\d{4}.*?[A-Za-z]+.*?[A-Za-z]+'
                ]
                
                for pattern in original_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        # Extract from the match onwards
                        text = text[match.start():]
                        break
                break
        
        return text.strip()
    
    def get_query_engine(self, **kwargs):
        """Get query engine for Q&A"""
        
        # Check for complete system initialization
        if not self.hybrid_retriever:
            raise ValueError("System not initialized. Please ingest documents first.")
        
        # Check for partial initialization state
        if not self.vector_index or not self.graph_index:
            logger.warning("System in partial state - missing indexes, clearing and requiring re-ingestion")
            self._clear_partial_state()
            raise ValueError("System not initialized. Please ingest documents first.")
        
        # Create query engine from the retriever
        from llama_index.core.query_engine import RetrieverQueryEngine
        
        try:
            return RetrieverQueryEngine.from_args(
                retriever=self.hybrid_retriever,
                llm=self.llm,
                **kwargs
            )
        except Exception as e:
            # Check if this is a Neo4j vector index error indicating partial state
            if "vector schema index" in str(e) or "There is no such vector schema index" in str(e):
                logger.warning(f"Detected missing vector indexes in Neo4j: {str(e)}")
                self._clear_partial_state()
                raise ValueError("System not initialized. Please ingest documents first.")
            else:
                # Re-raise other errors
                raise
    
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