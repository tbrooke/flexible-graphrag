#!/usr/bin/env python3
"""
Basic tests to verify test structure and imports work correctly
"""

import sys
import os
from pathlib import Path

# Add the flexible-graphrag directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "flexible-graphrag"))

def test_imports():
    """Test that all required modules can be imported"""
    
    # Test config imports
    from config import Settings, SearchDBType, VectorDBType, GraphDBType
    assert Settings is not None
    assert SearchDBType.BM25 == "bm25"
    assert VectorDBType.NEO4J == "neo4j"
    assert GraphDBType.NEO4J == "neo4j"
    
    # Test factory imports
    from factories import DatabaseFactory, LLMFactory
    assert DatabaseFactory is not None
    assert LLMFactory is not None
    
    # Test hybrid system imports
    from hybrid_system import HybridSearchSystem
    assert HybridSearchSystem is not None

def test_basic_configuration():
    """Test basic configuration creation"""
    from config import Settings, SearchDBType
    
    config = Settings()
    assert config.search_db == SearchDBType.BM25
    assert config.bm25_similarity_top_k == 10

def test_search_db_types():
    """Test all search database types"""
    from config import SearchDBType
    
    # Test all search types exist
    assert SearchDBType.BM25 == "bm25"
    assert SearchDBType.ELASTICSEARCH == "elasticsearch"
    assert SearchDBType.OPENSEARCH == "opensearch"
    
    # Test they are different
    assert SearchDBType.BM25 != SearchDBType.ELASTICSEARCH
    assert SearchDBType.BM25 != SearchDBType.OPENSEARCH
    assert SearchDBType.ELASTICSEARCH != SearchDBType.OPENSEARCH

def test_persistence_config():
    """Test persistence configuration options"""
    from config import Settings
    
    config = Settings(
        bm25_persist_dir="/tmp/bm25",
        vector_persist_dir="/tmp/vector",
        graph_persist_dir="/tmp/graph"
    )
    
    assert config.bm25_persist_dir == "/tmp/bm25"
    assert config.vector_persist_dir == "/tmp/vector"
    assert config.graph_persist_dir == "/tmp/graph"

if __name__ == "__main__":
    # Run basic tests
    test_imports()
    test_basic_configuration()
    test_search_db_types()
    test_persistence_config()
    print("All basic tests passed!") 