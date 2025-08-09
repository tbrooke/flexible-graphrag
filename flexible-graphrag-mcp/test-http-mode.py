#!/usr/bin/env python3
"""
Test script to verify HTTP mode functionality for MCP Inspector
"""

import sys
import time
import subprocess
import requests
from pathlib import Path

def test_http_mode():
    """Test the HTTP mode of the MCP server"""
    print("🧪 Testing HTTP Mode for MCP Inspector")
    print("=" * 50)
    
    # Check if backend is running
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        print("✅ Backend server is running")
    except requests.exceptions.RequestException:
        print("❌ Backend server not running. Please start it first:")
        print("   cd ../flexible-graphrag && python main.py")
        return False
    
    # Test HTTP mode startup
    try:
        print("\n🚀 Testing HTTP mode startup...")
        
        # Start the server in HTTP mode with a short timeout to test startup
        proc = subprocess.Popen([
            sys.executable, "main.py", "--http", "--port", "3001"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Give it a moment to start
        time.sleep(3)
        
        # Check if process is still running (good sign)
        if proc.poll() is None:
            print("✅ HTTP mode server started successfully")
            
            # Try to terminate gracefully
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            
            return True
        else:
            # Process exited, check for errors
            stdout, stderr = proc.communicate()
            print("❌ HTTP mode failed to start")
            if stderr:
                print(f"Error: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing HTTP mode: {e}")
        return False

def check_config_files():
    """Check that MCP Inspector config files exist"""
    print("\n📁 Checking MCP Inspector config files...")
    
    config_files = [
        "mcp-inspector/pipx-config.json",
        "mcp-inspector/uvx-config.json"
    ]
    
    all_exist = True
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"✅ {config_file}")
        else:
            print(f"❌ {config_file} - Missing!")
            all_exist = False
    
    return all_exist

if __name__ == "__main__":
    print("FastMCP HTTP Mode Test")
    print("=" * 30)
    
    # Check config files
    configs_ok = check_config_files()
    
    # Test HTTP mode
    http_ok = test_http_mode()
    
    print("\n" + "=" * 50)
    if configs_ok and http_ok:
        print("🎉 All tests passed! HTTP mode is working correctly.")
        print("\nNext steps:")
        print("1. Use one of the config files in mcp-inspector/")
        print("2. Start the MCP server with: flexible-graphrag-mcp --http --port 3001")
        print("3. Connect MCP Inspector to http://localhost:3001")
    else:
        print("❌ Some tests failed. Please check the output above.")
        
    sys.exit(0 if (configs_ok and http_ok) else 1)
