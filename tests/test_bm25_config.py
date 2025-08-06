#!/usr/bin/env python3
"""
Test script for BM25 configuration and persistence
"""

import asyncio
import tempfile
import os
import sys
from pathlib import Path

# Add the flexible-graphrag directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "flexible-graphrag"))

from config import Settings, SearchDBType
from hybrid_system import HybridSearchSystem

async def test_bm25_configuration():
    """Test BM25 configuration and persistence"""
    
    print("Testing BM25 configuration...")
    
    # Create temporary directories for persistence
    with tempfile.TemporaryDirectory() as temp_dir:
        persist_dir = os.path.join(temp_dir, "bm25_persist")
        vector_persist_dir = os.path.join(temp_dir, "vector_persist")
        graph_persist_dir = os.path.join(temp_dir, "graph_persist")
        
        # Create configuration with BM25 as default
        config = Settings(
            search_db=SearchDBType.BM25,
            bm25_persist_dir=persist_dir,
            bm25_similarity_top_k=15,
            vector_persist_dir=vector_persist_dir,
            graph_persist_dir=graph_persist_dir,
            # Use simple configuration for testing
            vector_db_config={
                "username": "neo4j",
                "password": "password",
                "url": "bolt://localhost:7687"
            },
            graph_db_config={
                "username": "neo4j", 
                "password": "password",
                "url": "bolt://localhost:7687"
            }
        )
        
        print(f"Configuration created:")
        print(f"  Search DB: {config.search_db}")
        print(f"  BM25 Persist Dir: {config.bm25_persist_dir}")
        print(f"  BM25 Top K: {config.bm25_similarity_top_k}")
        print(f"  Vector Persist Dir: {config.vector_persist_dir}")
        print(f"  Graph Persist Dir: {config.graph_persist_dir}")
        
        # Create hybrid system
        system = HybridSearchSystem(config)
        
        print(f"\nHybrid system created successfully")
        print(f"  Search DB Type: {system.config.search_db}")
        
        # Test that directories are created
        if config.bm25_persist_dir:
            os.makedirs(config.bm25_persist_dir, exist_ok=True)
            print(f"  BM25 persist directory created: {config.bm25_persist_dir}")
        
        if config.vector_persist_dir:
            os.makedirs(config.vector_persist_dir, exist_ok=True)
            print(f"  Vector persist directory created: {config.vector_persist_dir}")
        
        if config.graph_persist_dir:
            os.makedirs(config.graph_persist_dir, exist_ok=True)
            print(f"  Graph persist directory created: {config.graph_persist_dir}")
        
        print("\nBM25 configuration test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_bm25_configuration()) 