#!/usr/bin/env python3
"""
Startup script for flexible-graphrag using uvicorn
Usage: uv run start.py
"""

import uvicorn
import platform

if __name__ == "__main__":
    # Disable reload on Windows to prevent multiprocessing conflicts
    is_windows = platform.system() == "Windows"
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=not is_windows,  # Disable reload on Windows
        log_level="info"
    )