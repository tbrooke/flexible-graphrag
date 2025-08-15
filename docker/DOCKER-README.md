# Flexible GraphRAG Docker Deployment

This directory contains a modular Docker Compose setup for Flexible GraphRAG with support for multiple databases and easy configuration management.

## 🏗️ Architecture

The deployment is organized into modular YAML files:

```
docker/
├── docker-compose.yaml         # Main production compose file
├── docker-compose.minimal.yaml # Minimal setup (Neo4j only)
├── docker-compose.dev.yaml     # Development setup
└── includes/
    ├── neo4j.yaml              # Neo4j graph database
    ├── kuzu.yaml               # Kuzu graph database + web explorer
    ├── qdrant.yaml             # Qdrant vector database
    ├── elasticsearch.yaml      # Elasticsearch search engine
    ├── opensearch.yaml         # OpenSearch search engine + dashboards
    ├── alfresco.yaml           # Alfresco Community (full stack)
    ├── app-stack.yaml          # Flexible GraphRAG backend + UIs
    └── proxy.yaml              # NGINX reverse proxy
```

## 🚀 Quick Start

### 1. Setup Environment

**Linux/macOS:**
```bash
chmod +x docker-setup.sh
./docker-setup.sh
```

**Windows PowerShell:**
```powershell
.\docker-setup.ps1
```

**Windows Command Prompt:**
```cmd
docker-setup.bat
```

### 2. Configure Environment

```bash
cp env-sample.txt .env
# Edit .env with your configuration
```

### 3. Start Services

**All services:**
```bash
docker-compose -f docker/docker-compose.yaml up -d
```

**Alternative deployment options:**
```bash
# Minimal setup (Neo4j only)
docker-compose -f docker/docker-compose.minimal.yaml up -d

# Development setup
docker-compose -f docker/docker-compose.dev.yaml up -d

# Custom selection (comment out unwanted databases in docker/docker-compose.yaml)
docker-compose -f docker/docker-compose.yaml up -d
```

## 🗄️ Database Support

### Graph Databases

#### Neo4j
- **Image**: `neo4j:5.26.0`
- **Ports**: 7474 (HTTP), 7687 (Bolt)
- **Features**: APOC, Graph Data Science
- **Volume**: `neo4j_data`, `neo4j_logs`
- **Access**: http://localhost/neo4j/

#### Kuzu
- **Image**: `kuzudb/kuzu:latest` + `kuzudb/explorer:latest`
- **Ports**: 6527 (server), 8001 (explorer)
- **Features**: Embedded graph, Cypher support
- **Volume**: `kuzu_data`
- **Access**: http://localhost/kuzu-explorer/

### Vector Databases

#### Qdrant
- **Image**: `qdrant/qdrant:v1.7.4`
- **Ports**: 6333 (REST), 6334 (gRPC)
- **Volume**: `qdrant_data`
- **Access**: http://localhost/qdrant/

### Search Engines

#### Elasticsearch
- **Image**: `docker.elastic.co/elasticsearch/elasticsearch:8.12.0`
- **Ports**: 9200, 9300
- **Volume**: `elasticsearch_data`
- **Access**: http://localhost/elasticsearch/

#### OpenSearch
- **Image**: `opensearchproject/opensearch:2.12.0`
- **Ports**: 9201, 9301, 5601 (dashboards)
- **Volume**: `opensearch_data`
- **Access**: http://localhost/opensearch-dashboards/

### Content Management

#### Alfresco Community
- **Based on**: [Official ACS Deployment](https://github.com/Alfresco/acs-deployment)
- **Services**: Repository, Share, Solr, Transform, PostgreSQL
- **Ports**: 8080 (repo), 8180 (share), 5432 (postgres)
- **Volumes**: `alfresco_data`, `alfresco_db_data`
- **Access**: http://localhost/share/

## 🔧 Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Database selection
VECTOR_DB=neo4j|qdrant|elasticsearch|opensearch
GRAPH_DB=neo4j|kuzu
SEARCH_DB=elasticsearch|opensearch|bm25

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200

# OpenSearch
OPENSEARCH_URL=http://opensearch:9200

# LLM Provider (external Ollama)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### Selective Database Deployment

To disable databases you don't need, comment out their include lines in `docker/docker-compose.yaml`:

```yaml
include:
  - docker/includes/neo4j.yaml          # ✅ Keep this
  # - docker/includes/kuzu.yaml         # ❌ Comment out to disable
  - docker/includes/qdrant.yaml         # ✅ Keep this
  # - docker/includes/elasticsearch.yaml # ❌ Comment out to disable
  # - docker/includes/opensearch.yaml   # ❌ Comment out to disable
  # - docker/includes/alfresco.yaml     # ❌ Comment out to disable
  - docker/includes/app-stack.yaml      # ✅ Always needed
  - docker/includes/proxy.yaml          # ✅ Always needed
```

## 🌐 Service URLs

After startup, services are available at:

| Service | URL | Description |
|---------|-----|-------------|
| **Main Application** |
| React UI | http://localhost/ui/react/ | Primary frontend |
| Angular UI | http://localhost/ui/angular/ | Alternative frontend |
| Vue UI | http://localhost/ui/vue/ | Alternative frontend |
| Backend API | http://localhost/api/ | REST API |
| **Database Admin** |
| Neo4j Browser | http://localhost/neo4j/ | Graph database admin |
| Kuzu Explorer | http://localhost/kuzu-explorer/ | Graph database explorer |
| Qdrant Dashboard | http://localhost/qdrant/ | Vector database admin |
| Elasticsearch | http://localhost/elasticsearch/ | Search engine API |
| OpenSearch Dashboards | http://localhost/opensearch-dashboards/ | Search analytics |
| **Content Management** |
| Alfresco Share | http://localhost/share/ | Document management |
| Alfresco Repository | http://localhost/alfresco/ | API access |

## 🔄 Data Persistence

All database data is stored in named Docker volumes that persist across container restarts:

- `neo4j_data` - Neo4j graph data
- `kuzu_data` - Kuzu graph data  
- `qdrant_data` - Qdrant vector data
- `elasticsearch_data` - Elasticsearch indices
- `opensearch_data` - OpenSearch indices
- `alfresco_data` - Alfresco content store
- `alfresco_db_data` - Alfresco PostgreSQL data

## 🔌 External LLM Access

For external Ollama access from Docker containers:

```bash
# Make sure Ollama is running on host
ollama serve

# Configure backend to access host Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## 🛠️ Development

### Building Custom Images

```bash
# Backend only
docker-compose build flexible-graphrag-backend

# Specific UI
docker-compose build flexible-graphrag-ui-react

# All services
docker-compose build
```

### Logs and Debugging

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f flexible-graphrag-backend

# Database logs
docker-compose logs -f neo4j
```

### Health Checks

All services include health checks. Check status:

```bash
docker-compose -f docker/docker-compose.yaml ps
```

### Testing the Setup

**Linux/macOS:**
```bash
chmod +x test-docker-setup.sh
./test-docker-setup.sh
```

**Windows PowerShell:**
```powershell
.\test-docker-setup.ps1
```

**Windows Command Prompt:**
```cmd
test-docker-setup.bat
```

## 🧹 Cleanup

```bash
# Stop services
docker-compose -f docker/docker-compose.yaml down

# Remove volumes (⚠️ deletes all data)
docker-compose -f docker/docker-compose.yaml down -v

# Remove images
docker-compose -f docker/docker-compose.yaml down --rmi all
```

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts**: Modify port mappings in individual YAML files
2. **Memory issues**: Increase Docker memory limits or reduce services
3. **Permission errors**: Check volume mount permissions
4. **Network connectivity**: Ensure Docker network exists

### Resource Requirements

**Minimum requirements:**
- RAM: 8GB (for basic setup)
- Disk: 20GB free space
- Docker: 20.10+, Compose V2

**Recommended for full stack:**
- RAM: 16GB+
- Disk: 50GB+ free space
- CPU: 4+ cores

## 📚 Integration with MCP Server

The Docker setup works seamlessly with the MCP server:

1. Install MCP server: `uvx flexible-graphrag-mcp`
2. Configure to point to `http://localhost/api/`
3. All database services are accessible through the unified API

This modular approach allows you to run exactly what you need while maintaining easy access to all Flexible GraphRAG features.
