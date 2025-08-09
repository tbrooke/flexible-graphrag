# Flexible GraphRAG MCP Server

Model Context Protocol (MCP) server for Flexible GraphRAG system with optimized configurations for Claude Desktop and MCP Inspector.

## Quick Start

### 1. Choose Your Platform & Method

| Platform | Recommended | Alternative | Why |
|----------|-------------|-------------|-----|
| **Windows** | `pipx` | `uvx` | Clean system install vs. no install needed |
| **macOS** | `pipx` | `uvx` | Clean system install vs. no install needed |

### 2. Install

#### pipx (Recommended)
```bash
cd flexible-graphrag-mcp
pipx install .
```

#### uvx (No installation)
```bash
# Auto-installs when first used
uvx flexible-graphrag-mcp
```

### 3. Configure Claude Desktop

Copy the appropriate config file to your Claude Desktop configuration:

#### Windows
- **Config location**: `%APPDATA%\Claude\claude_desktop_config.json`
- **pipx**: Use `claude-desktop-configs/windows/pipx-config.json`
- **uvx**: Use `claude-desktop-configs/windows/uvx-config.json`

#### macOS
- **Config location**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **pipx**: Use `claude-desktop-configs/macos/pipx-config.json`
- **uvx**: Use `claude-desktop-configs/macos/uvx-config.json`

### 4. Test Installation

Restart Claude Desktop and test:
```
@flexible-graphrag Check system status
```

## Configuration Files

### Claude Desktop Configs

```
claude-desktop-configs/
├── windows/
│   ├── pipx-config.json    # Windows + pipx
│   └── uvx-config.json     # Windows + uvx
└── macos/
    ├── pipx-config.json    # macOS + pipx
    └── uvx-config.json     # macOS + uvx

mcp-inspector/
├── pipx-stdio-config.json  # MCP Inspector + pipx (stdio - try first)
├── pipx-http-config.json   # MCP Inspector + pipx (HTTP - fallback)
├── uvx-stdio-config.json   # MCP Inspector + uvx (stdio - try first)
└── uvx-http-config.json    # MCP Inspector + uvx (HTTP - fallback)
```

### Key Differences

#### Windows Configs
- Include Unicode environment variables (`PYTHONIOENCODING`, `PYTHONLEGACYWINDOWSSTDIO`)
- Prevent Unicode encoding errors with emojis and special characters

#### macOS Configs  
- Clean and simple - no special environment variables needed
- Standard MCP protocol over stdio

#### MCP Inspector Configs
- **stdio configs**: Standard MCP protocol - try these first
- **http configs**: HTTP transport fallback if stdio has issues (like proxy problems)
- HTTP mode runs on port 3001 by default (configurable with `--port` argument)
- Platform-independent - works on Windows, macOS, and Linux

## Installation Methods

### pipx (Recommended)

**Advantages:**
- ✅ Clean system-level installation
- ✅ Isolated dependencies
- ✅ Simple `flexible-graphrag-mcp` command
- ✅ Automatic PATH management

**Installation:**
```bash
cd flexible-graphrag-mcp
pipx install .
```

**Update:**
```bash
pipx reinstall flexible-graphrag-mcp
```

### uvx (Alternative)

**Advantages:**
- ✅ No installation required
- ✅ Automatic dependency management
- ✅ Always runs latest version
- ✅ Great for testing

**Usage:**
```bash
uvx flexible-graphrag-mcp
```

## Prerequisites

### Backend Server Required
The MCP server communicates with the FastAPI backend, so you must have it running:

```bash
cd flexible-graphrag
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### Environment Configuration
Ensure your `.env` file is properly configured in the main project directory:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# LLM Configuration
OPENAI_API_KEY=your-key
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
```

## HTTP Mode for MCP Inspector

For debugging with MCP Inspector, the server supports HTTP transport:

```bash
# Using pipx
flexible-graphrag-mcp --http --port 3001

# Using uvx  
uvx flexible-graphrag-mcp --http --port 3001

# Custom port
flexible-graphrag-mcp --http --port 8080
```

The HTTP mode is automatically configured in the `mcp-inspector/` config files and works better than stdio for debugging complex MCP interactions.

## Available Tools

- **`get_system_status()`** - System status and configuration
- **`ingest_documents(data_source, paths)`** - Ingest documents from various sources
- **`ingest_text(content, source_name)`** - Ingest custom text content
- **`search_documents(query, top_k)`** - Hybrid search for document retrieval
- **`query_documents(query, top_k)`** - AI-generated answers from documents
- **`test_with_sample()`** - Quick test with sample text
- **`check_processing_status(processing_id)`** - Check async operation status
- **`get_python_info()`** - Python environment information
- **`health_check()`** - Backend connectivity check

## Example Usage

### Basic Document Ingestion
```
@flexible-graphrag Please ingest documents from C:/Documents/research
```

### Custom Text Processing
```
@flexible-graphrag Ingest this text: "Claude is an AI assistant created by Anthropic."
```

### Search and Q&A
```
@flexible-graphrag Search for "machine learning algorithms" in the documents
```

```
@flexible-graphrag What are the main conclusions from the research papers?
```

### Async Processing
```
@flexible-graphrag Check processing status for ID abc123
```

## Troubleshooting

### Common Issues

#### pipx Command Not Found
```bash
# Install pipx
python -m pip install --user pipx
pipx ensurepath
```

#### uvx Command Not Found
```bash
# Install uvx via uv
uv tool install uvx
```

#### Unicode Errors on Windows
- Windows configs include required environment variables automatically
- If issues persist, check that you're using the correct Windows config file

#### Backend Connection Error
- Ensure FastAPI backend is running on `localhost:8000`
- Check that `.env` file is properly configured
- Test backend directly: `curl http://localhost:8000/api/health`

#### Claude Desktop Not Recognizing Server
- Restart Claude Desktop after config changes
- Check config file path and JSON syntax
- Verify command exists: run `flexible-graphrag-mcp` or `uvx flexible-graphrag-mcp` in terminal

## Development

### Test Scripts
```bash
# Windows
.\test-installation.ps1

# macOS/Linux
./test-installation.sh
```

These scripts test both installation methods and help verify everything works correctly.

### Adding New Tools
1. Add tool function to `main.py` with `@mcp.tool()` decorator
2. Update tool list in README
3. Test with MCP Inspector for debugging

## MCP Inspector Integration

Use the configs in `mcp-inspector/` directory for debugging with the MCP Inspector tool. These work with both pipx and uvx installations and are platform-independent.