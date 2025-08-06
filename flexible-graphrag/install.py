#!/usr/bin/env python3
"""
Installation script for flexible-graphrag
Usage: uv run install.py
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"  Command: {cmd}")
        print(f"  Error: {e.stderr}")
        return False

def main():
    """Main installation process"""
    print("🚀 Installing flexible-graphrag dependencies...")
    
    # Check if we're in the right directory
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found. Please run this from the flexible-graphrag directory.")
        sys.exit(1)
    
    # Install Python dependencies
    success = run_command(
        "uv pip install -r requirements.txt",
        "Installing Python dependencies"
    )
    
    if not success:
        print("\n❌ Installation failed. Please check the error messages above.")
        sys.exit(1)
    
    print("\n✅ Installation completed successfully!")
    print("\n📝 Next steps:")
    print("   1. Configure your .env file with database and LLM credentials")
    print("   2. Start the server: uv run start.py")
    print("   3. Open http://localhost:8000 in your browser")
    print("\n💡 For development with auto-reload:")
    print("   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload")

if __name__ == "__main__":
    main()