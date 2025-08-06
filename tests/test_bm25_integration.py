#!/usr/bin/env python3
"""
Integration tests for BM25 functionality in Flexible-GraphRAG
"""

import asyncio
import tempfile
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Add the flexible-graphrag directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "flexible-graphrag"))

from config import Settings, SearchDBType, VectorDBType, GraphDBType
from factories import DatabaseFactory
from hybrid_system import HybridSearchSystem

class TestBM25Configuration:
    """Test BM25 configuration and setup"""
    
    def test_bm25_default_configuration(self):
        """Test that BM25 is the default search database type"""
        config = Settings()
        assert config.search_db == SearchDBType.BM25
        assert config.bm25_similarity_top_k == 10
    
    def test_bm25_custom_configuration(self):
        """Test custom BM25 configuration"""
        config = Settings(
            search_db=SearchDBType.BM25,
            bm25_similarity_top_k=20,
            bm25_persist_dir="/tmp/bm25_test"
        )
        assert config.search_db == SearchDBType.BM25
        assert config.bm25_similarity_top_k == 20
        assert config.bm25_persist_dir == "/tmp/bm25_test"
    
    def test_search_db_type_enum(self):
        """Test that BM25 is properly added to SearchDBType enum"""
        assert hasattr(SearchDBType, 'BM25')
        assert SearchDBType.BM25 == "bm25"

class TestBM25Factory:
    """Test BM25 factory methods"""
    
    def test_create_search_store_bm25(self):
        """Test that BM25 search store creation returns None (handled by retriever)"""
        result = DatabaseFactory.create_search_store(SearchDBType.BM25, {})
        assert result is None
    
    def test_create_bm25_retriever(self):
        """Test BM25 retriever creation"""
        mock_docstore = Mock()
        config = {"similarity_top_k": 15, "persist_dir": "/tmp/test"}
        
        with patch('os.makedirs') as mock_makedirs:
            retriever = DatabaseFactory.create_bm25_retriever(mock_docstore, config)
            
            # Verify retriever was created
            assert retriever is not None
            # Verify directory creation was called
            mock_makedirs.assert_called_once_with("/tmp/test", exist_ok=True)
    
    def test_create_bm25_retriever_default_config(self):
        """Test BM25 retriever creation with default config"""
        mock_docstore = Mock()
        retriever = DatabaseFactory.create_bm25_retriever(mock_docstore)
        
        assert retriever is not None

class TestBM25HybridSystem:
    """Test BM25 integration with hybrid system"""
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Settings(
                search_db=SearchDBType.BM25,
                bm25_persist_dir=os.path.join(temp_dir, "bm25_persist"),
                bm25_similarity_top_k=15,
                vector_persist_dir=os.path.join(temp_dir, "vector_persist"),
                graph_persist_dir=os.path.join(temp_dir, "graph_persist"),
                # Mock database configs
                vector_db_config={"username": "test", "password": "test", "url": "bolt://localhost:7687"},
                graph_db_config={"username": "test", "password": "test", "url": "bolt://localhost:7687"}
            )
            yield config
    
    def test_hybrid_system_bm25_setup(self, temp_config):
        """Test that hybrid system properly handles BM25 setup"""
        with patch('factories.DatabaseFactory.create_vector_store') as mock_vector:
            with patch('factories.DatabaseFactory.create_graph_store') as mock_graph:
                with patch('factories.DatabaseFactory.create_search_store') as mock_search:
                    system = HybridSearchSystem(temp_config)
                    
                    # Verify search store creation was called with BM25
                    mock_search.assert_called_once_with(SearchDBType.BM25, {})
                    
                    # Verify search_store is None for BM25
                    assert system.search_store is None
    
    def test_hybrid_retriever_bm25_integration(self, temp_config):
        """Test that BM25 retriever is properly integrated in hybrid retriever"""
        with patch('factories.DatabaseFactory.create_vector_store'):
            with patch('factories.DatabaseFactory.create_graph_store'):
                with patch('factories.DatabaseFactory.create_search_store'):
                    system = HybridSearchSystem(temp_config)
                    
                    # Mock the indexes
                    system.vector_index = Mock()
                    system.graph_index = Mock()
                    
                    # Mock the docstore
                    system.vector_index.docstore = Mock()
                    
                    with patch('factories.DatabaseFactory.create_bm25_retriever') as mock_bm25:
                        mock_bm25.return_value = Mock()
                        system._setup_hybrid_retriever()
                        
                        # Verify BM25 retriever was created with correct config
                        mock_bm25.assert_called_once()
                        call_args = mock_bm25.call_args
                        assert call_args[0][0] == system.vector_index.docstore  # docstore
                        assert call_args[0][1]["similarity_top_k"] == 15  # config
                        assert call_args[0][1]["persist_dir"] == temp_config.bm25_persist_dir

class TestBM25Persistence:
    """Test BM25 persistence functionality"""
    
    def test_persistence_configuration(self):
        """Test that persistence directories are properly configured"""
        config = Settings(
            bm25_persist_dir="/tmp/bm25_persist",
            vector_persist_dir="/tmp/vector_persist",
            graph_persist_dir="/tmp/graph_persist"
        )
        
        assert config.bm25_persist_dir == "/tmp/bm25_persist"
        assert config.vector_persist_dir == "/tmp/vector_persist"
        assert config.graph_persist_dir == "/tmp/graph_persist"
    
    def test_persistence_directory_creation(self):
        """Test that persistence directories are created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            persist_dir = os.path.join(temp_dir, "bm25_persist")
            
            # Test directory creation
            os.makedirs(persist_dir, exist_ok=True)
            assert os.path.exists(persist_dir)
            assert os.path.isdir(persist_dir)

class TestBM25SearchTypes:
    """Test different search database type configurations"""
    
    def test_elasticsearch_configuration(self):
        """Test Elasticsearch configuration"""
        config = Settings(search_db=SearchDBType.ELASTICSEARCH)
        assert config.search_db == SearchDBType.ELASTICSEARCH
    
    def test_opensearch_configuration(self):
        """Test OpenSearch configuration"""
        config = Settings(search_db=SearchDBType.OPENSEARCH)
        assert config.search_db == SearchDBType.OPENSEARCH
    
    def test_bm25_vs_external_search(self):
        """Test that BM25 and external search engines are handled differently"""
        bm25_config = Settings(search_db=SearchDBType.BM25)
        es_config = Settings(search_db=SearchDBType.ELASTICSEARCH)
        
        assert bm25_config.search_db != es_config.search_db
        assert bm25_config.search_db == SearchDBType.BM25
        assert es_config.search_db == SearchDBType.ELASTICSEARCH

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 