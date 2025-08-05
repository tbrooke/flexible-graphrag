# Flexible GraphRAG with Angular, React, and Vue Frontends

This project provides simple Angular, React, and Vue user interfaces using TypeScript with a Python FastAPI backend based on the [cmis-graphrag-ui](https://github.com/stevereiner/cmis-graphrag-ui) project

These frontends provide for entering a folder path in a CMIS repository for processing. 
Processing uses the [neo4j-graphrag](https://github.com/neo4j/neo4j-graphrag-python) python package from Neo4j (which uses LLMs) to build knowledge graphs in Neo4j. 
The UI provides for entering text queries that are given to neo4j-graphrag for combined Graph / GraphRAG and Vector / RAG question answering using LLMs.

## Frontend Screenshots

| Angular UI | React UI | Vue UI |
|------------|----------|--------|
| ![Angular UI](./angular-ui.png) | ![React UI](./react-ui.png) | ![Vue UI](./vue-ui.png) |

## Notes
   - Only supports PDF documents currently.
   - Try with a folder with a or few small PDF documents in it initially.
   - Doesn't support replacing previous KG building if repeat the same document 
   (will get duplicate doc and chunk nodes, shouldn't duplicate entity and relationship nodes)
   - GraphRAG would be for a select set of docs needing more accuracy with answers to questions. 
   - Also would help if your organization wants to have a Schema to create knowledge graphs using your standard entity and relation terms (not used, but sample code in backend\neo4j_util.py)
   - Regular vector RAG and full text searching can still be used (or combined with GraphRAG)
   - If your running a local LLM (with Ollama) you should have a good Nvida card with large memory (4090,5090) and your system should have a large amount of memory. Then you can use a medium model. Otherwise use a small model. May want to use smaller models to save disk space. Can't use the large ones unless your GPU has a even larger amount of memory say a RTX Pro 6000 with 96 GB of memory on your server (llama-3.3-70b-instruct@q8_0: Benchmarks show that this model can run on the RTX PRO 6000, utilizing approximately 81GB of VRAM.) And your server would need 96 GB or recommended 192 GB of memory to run the LLM. It should be greater than or recommended double the amount of memory your GPU has.
   - If using OpenAI, you need a key and you may not want to send critical information.

## Prerequisites

- Python 3.10+ (supports 3.10, 3.11, 3.12, 3.13)
- UV package manager
- Node.js 16+
- npm or yarn
- Neo4j graph database
- CMIS-compliant repository (e.g., Alfresco, etc.)
- Ollama or OpenAI with API key (for LLM processing)

## Setup

### Python Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd flexible-graphrag
   ```

2. Create a virtual environment using UV and activate it:
   ```bash
   # From project root directory
   uv venv
   .\.venv\Scripts\Activate  # On Windows (works in both Command Prompt and PowerShell)
   # or
   source .venv/bin/activate  # on macOS/Linux
   ```

3. Install Python dependencies:
   ```bash
   # Navigate to flexible-graphrag directory and install requirements
   cd flexible-graphrag
   uv pip install -r requirements.txt
   ```

4. Create a `.env` file in the flexible-graphrag directory with your configuration:
   ```
   CMIS_URL=http://your-cmis-server/alfresco/api/-default-/public/cmis/versions/1.1/atom
   CMIS_USERNAME=your-username
   CMIS_PASSWORD=your-password
   NEO4J_URI=neo4j://localhost:7689
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-neo4j-password
   USE_OPENAI=true  # Set to false to use Ollama
   OPENAI_API_KEY=your-openai-api-key  # If using OpenAI
   OPENAI_MODEL=gpt-4.1-mini  # If using OpenAI set OpenAI model
   LAMA_MODEL=llama3.1:8b  # If using Ollama set Ollama model
   ```

### Frontend Setup

Choose one of the following frontend options to work with:

#### React Frontend

1. Navigate to the React frontend directory:
   ```bash
   cd flexible-graphrag-ui/frontend-react
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the development server (uses Vite):
   ```bash
   npm run dev
   ```

The React frontend will be available at `http://localhost:5174`.

#### Angular Frontend

1. Navigate to the Angular frontend directory:
   ```bash
   cd flexible-graphrag-ui/frontend-angular
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the development server (uses Angular CLI):
   ```bash
   npm start
   ```

The Angular frontend will be available at `http://localhost:4200`.

#### Vue Frontend

1. Navigate to the Vue frontend directory:
   ```bash
   cd flexible-graphrag-ui/frontend-vue
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the development server (uses Vite):
   ```bash
   npm run dev
   ```

The Vue frontend will be available at `http://localhost:3000`.

## Running the Application

### Start the Python Backend

From the project root directory:

```bash
cd flexible-graphrag
uvicorn main:app --reload
```

The backend will be available at `http://localhost:8000`.

### Start Your Preferred Frontend

Follow the instructions in the Frontend Setup section for your chosen frontend framework.

## Full-Stack Debugging

The project includes a `sample-launch.json` file with VS Code debugging configurations for all three frontend options and the backend. Copy this file to `.vscode/launch.json` to use these configurations.

Key debugging configurations include:

1. **Full Stack with React and Python**: Debug both the React frontend and Python backend simultaneously
2. **Full Stack with Angular and Python**: Debug both the Angular frontend and Python backend simultaneously
3. **Full Stack with Vue and Python**: Debug both the Vue frontend and Python backend simultaneously
4. Note when ending debugging, you will need to stop the Python backend and the frontend separately.

Each configuration sets up the appropriate ports, source maps, and debugging tools for a seamless development experience. You may need to adjust the ports and paths in the `launch.json` file to match your specific setup.

## Usage

1. **Process Documents**:
   - Enter the path to a folder in your CMIS repository (e.g., `/Shared/GraphRAG`)
   - Click "Process Folder" to vector index and build knowledge graphs of the entities and relationships in the content of the documents in the folder. 
   - The documents are processed using the [neo4j-graphrag](https://github.com/neo4j/neo4j-graphrag-python) python package from Neo4j (which uses LLMs) to build knowledge graphs in Neo4j.
   
     

2. **Query Neo4j using GrapRAG with the Knowledge Graphs**:
   - Enter a question in the query box
   - Click "Ask" to get an answer based on the processed documents
   _ The [neo4j-graphrag](https://github.com/neo4j/neo4j-graphrag-python) package is used for this also (again LLMs are used)
   
3. **Testing Cleanup**
   - Between tests you can delete detach nodes and relations in Neo4j, drop only vector_index_openai, vector_index_ollama and __entity__id indexes 
   - Use on a test Neo4j database no one else is using
   - See https://github.com/stevereiner/cmis-graphrag at the end for cleanup commands you can enter in the neo4j console 

## Project Structure

- `/flexible-graphrag`: Python FastAPI backend
  - `main.py`: FastAPI application with endpoints for processing and querying
  - `cmis_util.py`: CMIS repository interaction utilities
  - `neo4j_util.py`: Neo4j graph database utilities
  - `requirements.txt`: Python dependencies
  - Based on code from the [cmis-graphrag](https://github.com/stevereiner/cmis-graphrag) project, which demonstrates CMIS integration with Neo4j GraphRAG
  - See the [cmis-graphrag README](https://github.com/stevereiner/cmis-graphrag/blob/main/README.md) for more details on the original implementation
  - Uses the [neo4j-graphrag](https://github.com/neo4j/neo4j-graphrag-python) package from Neo4j ([documentation](https://neo4j.com/docs/neo4j-graphrag-python/current/))

- `/flexible-graphrag-ui`: Frontend applications
  - `/frontend-react`: React + TypeScript frontend (built with Vite)
    - `/src`: Source code
    - `vite.config.ts`: Vite configuration
    - `tsconfig.json`: TypeScript configuration
    - `package.json`: Node.js dependencies and scripts

  - `/frontend-angular`: Angular + TypeScript frontend (built with Angular CLI)
    - `/src`: Source code
    - `angular.json`: Angular configuration
    - `tsconfig.json`: TypeScript configuration
    - `package.json`: Node.js dependencies and scripts

  - `/frontend-vue`: Vue + TypeScript frontend (built with Vite)
    - `/src`: Source code
    - `vite.config.ts`: Vite configuration
    - `tsconfig.json`: TypeScript configuration
    - `package.json`: Node.js dependencies and scripts

## License

This project is licensed under the terms of the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
