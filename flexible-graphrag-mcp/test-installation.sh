#!/bin/bash
# Test script for different MCP installation methods
# Run this from the flexible-graphrag-mcp directory

echo "=== Testing Flexible GraphRAG MCP Installation Methods ==="

# Test 1: pipx
echo -e "\n1. Testing pipx installation..."
if command -v pipx &> /dev/null; then
    if pipx install . --force &> /dev/null; then
        echo "✅ pipx install successful"
        if flexible-graphrag-mcp --help &> /dev/null; then
            echo "✅ pipx command works"
        else
            echo "❌ pipx command failed"
        fi
    else
        echo "❌ pipx install failed"
    fi
else
    echo "❌ pipx not found - install with: python -m pip install --user pipx"
fi

# Test 2: uvx
echo -e "\n2. Testing uvx..."
if command -v uvx &> /dev/null; then
    if uvx --from . flexible-graphrag-mcp --help &> /dev/null; then
        echo "✅ uvx works"
    else
        echo "❌ uvx failed"
    fi
else
    echo "❌ uvx not found - install with: uv tool install uvx"
fi

# Test 3: uv run
echo -e "\n3. Testing uv run..."
if command -v uv &> /dev/null; then
    if uv run main.py --help &> /dev/null; then
        echo "✅ uv run works"
    else
        echo "❌ uv run failed"
    fi
else
    echo "❌ uv not found - install from: https://docs.astral.sh/uv/"
fi

# Test 4: Direct Python
echo -e "\n4. Testing direct Python..."
if python main.py --help &> /dev/null; then
    echo "✅ Direct Python works"
else
    echo "❌ Direct Python failed"
fi

echo -e "\n=== Configuration Files ==="
echo "Copy the appropriate config from ./claude-desktop-configs/ to:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "~/Library/Application Support/Claude/claude_desktop_config.json"
else
    echo "~/.config/claude/claude_desktop_config.json"
fi

echo -e "\nAvailable configs:"
echo "  macOS (use one of these):"
echo "    - claude-desktop-configs/macos/pipx-config.json"
echo "    - claude-desktop-configs/macos/uvx-config.json"
echo "  MCP Inspector (HTTP mode):"
echo "    - mcp-inspector/pipx-config.json"
echo "    - mcp-inspector/uvx-config.json"

echo -e "\n=== Next Steps ==="
echo "1. Choose your preferred installation method"
echo "2. Copy the corresponding config to Claude Desktop"
echo "3. Update paths in the config to match your system"
echo "4. Restart Claude Desktop"
echo "5. Test with: @flexible-graphrag Check system status"
