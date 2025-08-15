# Changelog

All notable changes to this project will be documented in this file.

## [2025-08-15] - Frontend Environment Variables & Vector Database Validation

### Fixed
- **Frontend Environment Variable Issues**
  - Vue frontend template compilation errors with `import.meta.env` expressions
  - React JSX environment variable resolution using computed placeholders  
  - Angular production environment forcing Docker URLs for standalone deployments
  - TypeScript compilation errors for window environment declarations

### Enhanced
- **Flexible Environment Configuration**
  - Vue: Computed properties with fallback defaults for environment variables
  - React: useMemo hooks for optimized environment resolution
  - Angular: Runtime environment service supporting both standalone and Docker modes
  - Production builds no longer require Docker infrastructure

### Validated
- **Complete Vector Database Support**
  - Qdrant: Dedicated vector store with external container configuration
  - Elasticsearch: Dual-purpose vector and fulltext search with separate indexes
  - Neo4j: Vector database support with separate VECTOR_DB_CONFIG requirements
  - OpenSearch: Hybrid search with single index and pipeline-based score fusion
  - BM25: Local filesystem storage without external SEARCH_DB_CONFIG

### Documentation
- Updated Neo4j vector index cleanup commands (`hybrid_search_vector` vs `vector`)
- Clarified BM25 configuration requirements and local storage approach
- Simplified Neo4j cleanup instructions using `SHOW INDEXES` commands

## [2025-08-14] - Environment Configuration & Documentation

### Added
- **Comprehensive Environment Configuration System**
  - Complete `docs/ENVIRONMENT-CONFIGURATION.md` with 5-section structure guide
  - Clean separation of schema, database, and source configurations  
  - Database switching patterns and configuration best practices
  - Missing Kuzu configuration with proper JSON format examples

### Enhanced
- **Environment File Organization**
  - Moved schema configuration to dedicated section in `env-sample.txt`
  - Fixed Neo4j default URI from incorrect port 7689 to standard 7687
  - Added proper DB_CONFIG examples with JSON format for all database types
  - Organized into logical sections for easy database switching

### Documentation
- Created supporting documentation: `SOURCE-PATH-EXAMPLES.md`, `TIMEOUT-CONFIGURATIONS.md`
- Updated `docs/SCHEMA-EXAMPLES.md` to focus purely on schema examples
- Established clean separation of concerns with cross-referenced documentation
- Maintained backward compatibility while improving organization

## [2025-08-13] - Kuzu Integration & Docker Full-Stack

### Added
- **Complete Kuzu Graph Database Integration**
  - Kuzu support as alternative to Neo4j using Approach 2 (separate vector stores)
  - Dual schema system: KUZU_SCHEMA for Kuzu, SAMPLE_SCHEMA for Neo4j
  - LLM provider awareness for embedding models (OpenAI/Ollama/Azure)
  - Graph API endpoint `/api/graph` for programmatic access to Kuzu data

- **Docker Infrastructure Overhaul**  
  - Fixed all Docker networking issues with Node.js 24 updates
  - NGINX proxy configuration with proper upstream routing
  - Standardized port allocation resolving conflicts
  - Frontend Docker configurations with internal networking support

### Enhanced
- **Database Architecture Flexibility**
  - Clean separation: Kuzu for graphs, Qdrant for vectors, Elasticsearch for search
  - Schema validation system with `has_structured_schema=False` for Kuzu
  - Identical search performance across Neo4j and Kuzu backends
  - Multiple visualization options: Kuzu Explorer, Neo4j Browser, API access

## [2025-08-12] - Async Processing & Event Loop Resolution

### Fixed
- **Ollama Event Loop Issues**
  - Comprehensive async approach with global `nest_asyncio.apply()`
  - Consistent async methods: `aquery()`, `aretrieve()` for all LLM providers
  - Windows event loop policy fixes with `WindowsSelectorEventLoopPolicy`
  - Simplified architecture removing complex fallback mechanisms

### Enhanced
- **Unified Async Architecture**
  - Applied async patterns to all LLM providers, not just Ollama
  - LlamaIndex integration following library recommendations
  - Removed thread isolation in favor of proper async handling

## [2025-08-11] - OpenSearch Native Hybrid Search

### Added
- **OpenSearch Native Hybrid Search Implementation**
  - Single retriever using `VectorStoreQueryMode.HYBRID` 
  - Eliminated async connection conflicts from dual retrievers
  - Native OpenSearch score fusion instead of manual combination
  - Automated pipeline creation with `scripts/create_opensearch_pipeline.py`

### Enhanced
- **Search Architecture Improvements**
  - Hybrid mode detection in factories.py for OpenSearch
  - Fulltext-only mode using `VectorStoreQueryMode.TEXT_SEARCH`
  - Re-enabled async support in QueryFusionRetriever
  - Better relevance than manual fusion approaches

## [2025-08-10] - Database Integration & Hybrid Search Testing

### Added
- **Comprehensive Hybrid Search System**
  - Dual-index Elasticsearch hybrid search (vector + fulltext)
  - Working configurations for Qdrant+Elasticsearch+Kibana combinations
  - OpenSearch factory configuration with `OpensearchVectorClient`
  - Pure RAG mode with `ENABLE_KNOWLEDGE_GRAPH=false`

### Fixed
- **BM25 Standalone Search Issues**
  - Document storage overwriting preventing proper indexing
  - Early exit logic incorrectly assuming BM25 required vector docstore
  - Zero-relevance filtering to exclude irrelevant results
  - Direct retriever usage for single-modality scenarios

### Enhanced
- **UI Client Improvements**
  - Zero results feedback across all frontend clients (Vue, Angular, React)
  - Accumulative document storage across multiple ingestions
  - Professional "No results found" messages with search term display

## [2025-08-09] - MCP Server and Async Processing

### Added
- **MCP Server Implementation**
  - FastMCP-based Model Context Protocol server for Claude Desktop integration
  - HTTP and stdio transport modes (`--transport http`, `--http`, `--serve` flags)
  - Command-line argument parsing for host, port, and transport configuration
  - Multiple installation methods: pipx, uvx, direct Python execution
  - Platform-specific Claude Desktop configurations (Windows/macOS)
  - MCP Inspector debugging support with dedicated configurations
- **MCP Tools**
  - `get_system_status`, `ingest_documents`, `ingest_text`, `search_documents`
  - `query_documents`, `test_with_sample`, `check_processing_status`
  - `get_python_info`, `health_check`
- **Asynchronous Processing Pattern**
  - Background task processing with processing ID system
  - Real-time progress updates with percentage, current file, and phase information
  - Dynamic time estimation based on content size and file count
  - Processing cancellation support with graceful cleanup
  - Server-Sent Events (SSE) endpoints for real-time UI updates
- **UI Enhancements**
  - Progress bars with 0-100% completion tracking across all clients
  - Cancel processing buttons with proper state management
  - Time estimation displays and file-level progress indicators
  - Phase tracking (docling, chunking, indexing, kg_extraction)
  - Auto-clearing status messages and manual dismiss options

### Fixed
- **Asyncio Event Loop Conflicts**
  - Added `nest_asyncio` support to handle nested event loops
  - Wrapped LlamaIndex operations in `loop.run_in_executor()` 
  - Resolved `asyncio.run() cannot be called from a running event loop` errors
- **Neo4j Compatibility Issues**
  - Added `refresh_schema=False` to prevent APOC `apoc.meta.data` calls during initialization
  - Fixed Cypher syntax incompatibility between Neo4j 25.x and LlamaIndex 0.5.0
  - Updated cleanup commands to include `entity` index and LlamaIndex constraints
- **Package Installation Issues**
  - Fixed `pyproject.toml` from `packages = ["."]` to `py-modules = ["main"]` for uvx support
  - Added proper script entry points for system-wide command availability
- **Processing State Management**
  - Implemented intelligent cleanup that preserves functional systems after cancellation
  - Fixed search functionality after completed ingestion followed by cancelled operation
- **UI Client Issues**
  - Fixed Angular compilation errors (MatProgressBarModule, RxJS imports, TypeScript types)
  - Corrected snackbar duration and auto-clearing logic
  - Added proper async status polling in all three UI frameworks

### Changed
- **API Response Format**
  - Ingestion endpoints now return immediate `AsyncProcessingResponse` with `processing_id`
  - Added `/api/processing-status/{id}` and `/api/processing-events/{id}` endpoints
  - Separated `/api/test-sample` (default) and `/api/ingest-text` (custom content) endpoints
  - Enhanced `/api/status` to include `search_db` configuration
- **Configuration Management**
  - Made sample text configurable via `SAMPLE_TEXT` environment variable
  - Organized Claude Desktop configs by platform (windows/, macos/)
  - Separated MCP Inspector configs by transport (stdio/HTTP)
  - Added Unicode environment variables for Windows compatibility

### Documentation
- Comprehensive README.md with multiple installation methods
- QUICK-USAGE-GUIDE.md for streamlined setup
- Platform-specific configuration examples and troubleshooting guides
- Ready-to-use Claude Desktop JSON configurations
- MCP Inspector configs for both stdio and HTTP modes
- Test scripts for installation validation (PowerShell and Bash)

## [2025-08-07] - UI Client Updates and Data Sources

### Added
- React and Vue client modifications to match Angular's data source selection capabilities
- Hybrid search with results list (in addition to Q&A AI query mode)
- CMIS and Alfresco data sources beyond filesystem (Alfresco uses CMIS for getObjectByPath)
- Support for additional document formats that Docling supports

### Changed
- Updated screen images to reflect new hybrid search functionality

## [2025-08-06] - LlamaIndex Integration and Configuration

### Added
- **LlamaIndex Integration**
  - Replaced LangChain with LlamaIndex for document processing
  - VectorStoreIndex and PropertyGraphIndex implementation
  - IngestionPipeline with SentenceSplitter, KeywordExtractor, SummaryExtractor
- **Configurable Architecture**
  - Vector database, graph database, and search database configuration
  - Support for multiple database backends (Neo4j, Qdrant, etc.)
  - Environment-based configuration management
- **Hybrid Search System**
  - Combined vector similarity, BM25 full-text search, and graph traversal
  - AI Q&A mode alongside hybrid search results
  - Configurable retrieval strategies
- **Multi-Source Data Ingestion**
  - Filesystem, CMIS, and Alfresco data source support
  - Docling integration for PDF and Microsoft Office documents
  - Smart table-to-markdown conversion with fallback to text extraction
- **Document Processing**
  - Support for 12+ file formats via Docling
  - Intelligent chunking and metadata extraction
  - Knowledge graph entity and relationship extraction

### Changed
- **Architecture Migration**
  - Migrated from cmis-graphrag/langchain/neo4j-graphrag stack
  - Unified configuration system across all components
  - Angular dialog updates (React and Vue clients pending similar changes)

### Fixed
- Document format support alignment with Docling capabilities
- Filesystem data source integration (CMIS and Alfresco integration planned)

### Technical
- Tested with Neo4j as graph and vector database
- LlamaIndex BM25 as full-text search engine
- Elasticsearch and OpenSearch integration marked for future development

## [2025-08-05] - Initial Project Setup

### Added
- Flexible GraphRAG initial project structure
- Reorganized from cmis-graphrag-ui with frontends moved to flexible-graphrag-ui subdirectory
- Backend moved to flexible-graphrag subdirectory

