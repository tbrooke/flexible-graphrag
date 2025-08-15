# Vector Dimension Compatibility Guide

This document explains critical vector dimension compatibility issues when switching between different embedding models in Flexible GraphRAG.

## ⚠️ Critical Issue: Vector Dimension Incompatibility

When switching between different LLM providers or embedding models, you **MUST delete existing vector indexes** because different models produce embeddings with different dimensions.

### Why This Matters

Vector databases create indexes optimized for specific dimensions. When you change embedding models, the new embeddings won't fit the existing index structure, causing errors like:

- `Dimension mismatch error`
- `Vector size incompatible with index`
- `Index dimension does not match embedding dimension`

## 📊 Embedding Dimensions by Provider

### OpenAI
- **text-embedding-3-large**: `3072` dimensions
- **text-embedding-3-small**: `1536` dimensions (default)
- **text-embedding-ada-002**: `1536` dimensions

### Ollama
- **mxbai-embed-large**: `1024` dimensions (default)
- **nomic-embed-text**: `768` dimensions
- **all-minilm**: `384` dimensions

### Azure OpenAI
- Same as OpenAI models: `1536` or `3072` dimensions

### Other Providers
- **Default fallback**: `1536` dimensions

## 🗂️ Vector Database Cleanup Instructions

### Qdrant

**Using Qdrant Dashboard:**
1. Open Qdrant Dashboard: http://localhost:6333/dashboard
2. Go to "Collections" tab
3. Find `hybrid_search_vector` (or your collection name) in the collections list
4. Click the **3 dots (⋮)** menu next to the collection
5. Select **"Delete"**
6. Confirm the deletion

### Neo4j

**Using Neo4j Browser:**
1. Open Neo4j Browser: http://localhost:7474 (or your Neo4j port)
2. Login with your credentials
3. **Drop Vector Index:**
   - Run: `SHOW INDEXES`
   - Run: `DROP INDEX hybrid_search_vector IF EXISTS`
   - Run: `SHOW INDEXES` to verify cleanup

### Elasticsearch

**Using Kibana Dashboard:**
1. Open Kibana: http://localhost:5601 (if Kibana is running)
2. Choose **"Management"** from the main menu
3. Click **"Index Management"**
4. Select `hybrid_search_vector` from the indices list
5. Choose **"Manage index"** (blue button)
6. Choose **"Delete index"**
7. Confirm the deletion

**Alternative - Using Elasticsearch REST API:**
```bash
# Delete the vector index via curl
curl -X DELETE "http://localhost:9200/hybrid_search_vector"
```

### OpenSearch

**Using OpenSearch Dashboards:**
1. Open OpenSearch Dashboards: http://localhost:5601 (if running) or http://localhost:9201/_dashboards
2. Go to **"Index Management"** (in the main menu or under "Management")
3. Click on **"Indices"** tab
4. Find `hybrid_search_vector` in the indices list
5. Click the **checkbox** next to the index
6. Click **"Actions"** → **"Delete"**
7. Confirm the deletion by typing **"delete"**

**Alternative - Using OpenSearch REST API:**
```bash
# Delete the vector index via curl
curl -X DELETE "http://localhost:9201/hybrid_search_vector"
```

## 🔄 Safe Migration Process

When switching embedding models, follow this process:

### 1. Backup Important Data (Optional)
```bash
# Export any important data before deletion
# (Implementation depends on your database)
```

### 2. Update Configuration
```bash
# Edit your .env file
LLM_PROVIDER=ollama  # Changing from openai to ollama
OLLAMA_MODEL=mxbai-embed-large  # 1024 dimensions
```

### 3. Clean Vector Database
Choose the appropriate cleanup method from above based on your vector database.

### 4. Restart Services
```bash
# Restart your application
cd flexible-graphrag
uv run start.py
```

### 5. Re-ingest Documents
```bash
# Re-process your documents with the new embedding model
curl -X POST "http://localhost:8000/api/ingest" \
  -H "Content-Type: application/json" \
  -d '{"data_source": "filesystem", "paths": ["./your_documents"]}'
```

## 🚨 Common Error Messages

### Qdrant
```
Vector dimension mismatch: expected 1536, got 1024
```

### Neo4j
```
Vector index dimension (1536) does not match embedding dimension (1024)
```

### Elasticsearch/OpenSearch
```
mapper_parsing_exception: dimension mismatch
```

## 📋 Configuration Detection

The system automatically detects embedding dimensions in `flexible-graphrag/factories.py`:

```python
def get_embedding_dimension(llm_provider: LLMProvider, llm_config: Dict[str, Any]) -> int:
    if llm_provider == LLMProvider.OPENAI:
        return 1536  # or 3072 for large models
    elif llm_provider == LLMProvider.OLLAMA:
        return 1024  # default for mxbai-embed-large
    # ... other providers
```

The dimension is automatically applied to vector database configurations in `config.py`:

```python
"embed_dim": 1536 if self.llm_provider == LLMProvider.OPENAI else 1024
```


## 🐛 Ollama + Kuzu Configuration Issue

### **Problem**: Kuzu Approach 2 + Ollama Incompatibility

When using **Ollama** with **Kuzu + Qdrant** (Approach 2), you may encounter:
- `"cannot unpack non-iterable NoneType object"` during PropertyGraphIndex creation
- Compatibility issues with vector store parameter passing

### **Solution**: Automatic Kuzu Approach 1 for Ollama

The system automatically uses **Kuzu Approach 1** (built-in vector index) when Ollama is detected:

**Configuration**:
```bash
LLM_PROVIDER=ollama
GRAPH_DB=kuzu
VECTOR_DB=qdrant  # This will be automatically ignored for Ollama
```

**Result**:
- ✅ **Kuzu handles both graph AND vectors** (1024 dimensions for Ollama)
- ✅ **No separate vector database needed** for Ollama
- ✅ **Simpler setup** with single database

**Log Confirmation**:
```
Using Kuzu Approach 1: built-in vector index with ollama embeddings
```

### **Why This Works**

- **OpenAI**: Uses Kuzu Approach 2 (Kuzu + Qdrant separation)
- **Ollama**: Uses Kuzu Approach 1 (Kuzu built-in vector index)
- **Automatic**: No configuration changes needed

## ✅ Best Practices

1. **Plan Your Embedding Model**: Choose your embedding model before ingesting large document collections
2. **Test with Small Data**: Verify compatibility with a small test dataset first
3. **Document Your Configuration**: Keep track of which embedding model you're using
4. **Backup Strategy**: Consider backup procedures if you need to preserve processed data
5. **Environment Separation**: Use different databases/collections for different embedding models
6. **Consistent Naming**: Use explicit collection/database names to avoid defaults mismatches
7. **Ollama + Kuzu**: Let the system automatically use Approach 1 - no special configuration needed

## 🔍 Verification

After switching models and cleaning databases, verify the setup:

```bash
# Test with a small document
curl -X POST "http://localhost:8000/api/test-sample" \
  -H "Content-Type: application/json" \
  -d '{}'

# Check system status
curl "http://localhost:8000/api/status"
```

## 📚 Related Documentation

- [Main README](README.md) - Full system setup
- [Neo4j Cleanup](flexible-graphrag/README-neo4j.md) - Detailed Neo4j cleanup procedures
- [Docker Setup](docker/README.md) - Container-based deployment
- [Configuration Guide](flexible-graphrag/README.md) - Environment configuration
