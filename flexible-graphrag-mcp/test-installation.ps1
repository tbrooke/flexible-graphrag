# Test script for different MCP installation methods
# Run this from the flexible-graphrag-mcp directory

Write-Host "=== Testing Flexible GraphRAG MCP Installation Methods ===" -ForegroundColor Green

# Test 1: pipx
Write-Host "`n1. Testing pipx installation..." -ForegroundColor Yellow
try {
    pipx install . --force
    Write-Host "✅ pipx install successful" -ForegroundColor Green
    
    # Test the command
    & flexible-graphrag-mcp --help 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ pipx command works" -ForegroundColor Green
    } else {
        Write-Host "❌ pipx command failed" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ pipx install failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: uvx
Write-Host "`n2. Testing uvx..." -ForegroundColor Yellow
try {
    & uvx --from . flexible-graphrag-mcp --help 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ uvx works" -ForegroundColor Green
    } else {
        Write-Host "❌ uvx failed" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ uvx failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: uv run
Write-Host "`n3. Testing uv run..." -ForegroundColor Yellow
try {
    & uv run main.py --help 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ uv run works" -ForegroundColor Green
    } else {
        Write-Host "❌ uv run failed" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ uv run failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Direct Python
Write-Host "`n4. Testing direct Python..." -ForegroundColor Yellow
try {
    & python main.py --help 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Direct Python works" -ForegroundColor Green
    } else {
        Write-Host "❌ Direct Python failed" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Direct Python failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Configuration Files ===" -ForegroundColor Green
Write-Host "Copy the appropriate config from ./claude-desktop-configs/ to:"
Write-Host "%APPDATA%\Claude\claude_desktop_config.json" -ForegroundColor Cyan

Write-Host "`nAvailable configs:" -ForegroundColor Yellow
Write-Host "  Windows (use one of these):" -ForegroundColor Cyan
Write-Host "    - claude-desktop-configs/windows/pipx-config.json" -ForegroundColor White
Write-Host "    - claude-desktop-configs/windows/uvx-config.json" -ForegroundColor White
Write-Host "  MCP Inspector (HTTP mode):" -ForegroundColor Cyan  
Write-Host "    - mcp-inspector/pipx-config.json" -ForegroundColor White
Write-Host "    - mcp-inspector/uvx-config.json" -ForegroundColor White

Write-Host "`n=== Next Steps ===" -ForegroundColor Green
Write-Host "1. Choose your preferred installation method"
Write-Host "2. Copy the corresponding config to Claude Desktop"
Write-Host "3. Update paths in the config to match your system"
Write-Host "4. Restart Claude Desktop"
Write-Host "5. Test with: @flexible-graphrag Check system status"
