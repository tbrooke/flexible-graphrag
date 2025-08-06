"""
Pytest configuration for Flexible-GraphRAG tests
"""

import sys
import os
from pathlib import Path

# Add the flexible-graphrag directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "flexible-graphrag"))

# Test configuration
def pytest_configure(config):
    """Configure pytest for Flexible-GraphRAG tests"""
    config.addinivalue_line(
        "markers", "bm25: marks tests as BM25 related"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )

def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their names"""
    for item in items:
        if "bm25" in item.nodeid.lower():
            item.add_marker(pytest.mark.bm25)
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
        if "unit" in item.nodeid.lower():
            item.add_marker(pytest.mark.unit) 