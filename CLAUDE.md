# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GraphRAG is an intelligent graph-based RAG (Retrieval-Augmented Generation) travel assistant. It combines Neo4j graph database with Milvus vector database to provide multi-hop reasoning and hybrid retrieval capabilities for travel-related queries.

The system supports both CLI and Web UI interfaces, with automated data collection from multiple sources using integrated third-party tools.

## Architecture

### High-Level Structure

```
Rag_python/
├── rag_graph/                 # Main application code
│   ├── main.py               # Entry point - delegates to CLI
│   ├── cli.py                # Typer-based CLI with Rich UI
│   ├── web/app.py            # FastAPI web application
│   ├── rag_modules/          # Core RAG implementation
│   │   ├── graph_rag_retrieval.py       # Graph traversal retrieval
│   │   ├── hybrid_retrieval.py          # Traditional + vector retrieval
│   │   ├── intelligent_query_router.py  # Route queries to appropriate strategy
│   │   ├── milvus_index_construction.py # Vector index management
│   │   ├── graph_data_preparation.py    # Neo4j data ingestion
│   │   └── generation_integration.py    # LLM response generation
│   ├── collectors/           # Data collection system
│   │   ├── processor.py      # Data processing pipeline
│   │   ├── adapters/         # Third-party tool adapters
│   │   └── core/             # Collection core logic
│   └── web/routers/          # FastAPI API routes
├── config/                   # Configuration management
│   ├── config.py             # GraphRAGConfig dataclass
│   ├── .env                  # Environment variables (user-created)
│   ├── .env.example          # Environment template
│   └── docker-compose.yml    # Neo4j + Milvus infrastructure
├── ToolBbrowser/             # Git submodule - Browser automation (Node.js/pnpm)
└── Scrapling-main/           # Git submodule - Python scraping framework
```

### RAG Pipeline Flow

1. **Query Layer**: User input received via CLI (`cli.py`) or Web API (`web/routers/chat.py`)
2. **Routing Layer**: `IntelligentQueryRouter` decides between graph RAG, traditional retrieval, or hybrid
3. **Retrieval Layer**:
   - `GraphRAGRetrieval`: Multi-hop traversal using Neo4j
   - `HybridRetrieval`: Vector search via Milvus + keyword search
4. **Generation Layer**: `GenerationIntegrationModule` uses LangChain with OpenAI-compatible APIs

### Data Collection

The system integrates two third-party tools via git submodules:
- **ToolBbrowser** (`ToolBbrowser/`): Browser automation with MCP server support
- **Scrapling** (`Scrapling-main/`): Undetectable Python web scraping framework

## Common Commands

### Environment Setup

```bash
# Create conda environment
conda create -n rag_graph python=3.12.7
conda activate rag_graph

# Install Python dependencies
cd rag_graph
pip install -r requirement.txt

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with your API keys and passwords
```

### Installing Third-Party Tools

```bash
# Install both ToolBbrowser and Scrapling (via git submodules)
./setup-tools.sh

# Or install individually
./setup-tools.sh --toolbbrowser
./setup-tools.sh --scrapling

# Manual installation if needed
git submodule update --init --recursive
cd ToolBbrowser && pnpm install && pnpm build && cd ..
cd Scrapling-main && pip install -e . && cd ..
```

### Infrastructure Management

```bash
# Start Neo4j and Milvus infrastructure
cd rag_graph
python main.py service up

# Check service status
python main.py service status

# View logs
python main.py service logs
python main.py service logs -s neo4j -f  # Follow Neo4j logs

# Restart specific service
python main.py service restart neo4j

# Stop infrastructure
python main.py service down
```

### Running the Application

```bash
# CLI mode (default)
cd rag_graph
python main.py              # Interactive CLI
python main.py start        # Same as above
python main.py start -a     # Auto-start infrastructure if not running

# Single query mode
python main.py query "北京有哪些必去的景点？"

# Web UI mode
python main.py web          # Default port 8080
python main.py web --port 8000 --reload  # Dev mode

# System health check
python main.py doctor
```

### CLI Commands in Interactive Mode

When running the interactive CLI:
- `/help` - Show available commands
- `/stats` - Display system statistics
- `/quit` or `/exit` - Exit the application
- `Ctrl+C` (twice) - Force quit

## Configuration

All configuration is managed via `config/.env` (copy from `.env.example`):

Key configuration sections:
- **Neo4j**: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- **Milvus**: `MILVUS_HOST`, `MILVUS_PORT`, `MILVUS_COLLECTION_NAME`
- **LLM**: `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL` (OpenAI-compatible)
- **Embedding**: `EMBEDDING_MODEL` (default: BAAI/bge-small-zh-v1.5)
- **Collection Tools**: `TOOLBBROWSER_ENABLED`, `SCRAPLING_ENABLED`

## Key Dependencies

- **Graph Database**: Neo4j 5.x with APOC plugin
- **Vector Database**: Milvus 2.x (with etcd and MinIO)
- **LLM Framework**: LangChain 0.3.x with OpenAI-compatible APIs
- **Web Framework**: FastAPI + Uvicorn
- **CLI Framework**: Typer + Rich + Prompt Toolkit
- **ML/AI**: PyTorch 2.6, Transformers, Sentence-Transformers

## Development Notes

- Python 3.12+ required
- Docker required for Neo4j and Milvus infrastructure
- Node.js 18+ required for ToolBbrowser
- Third-party tools are git submodules - use `setup-tools.sh` for installation
- The CLI (`cli.py`) is the main interface; `main.py` is a thin wrapper
- Web UI static files are served from `rag_graph/web/static/`
- Data is stored in `data/` and cache in `rag_graph/cache/`

## Project Entry Points

| File | Purpose |
|------|---------|
| `rag_graph/main.py` | CLI entry point, dependency checks |
| `rag_graph/cli.py` | Typer CLI application with all commands |
| `rag_graph/web/app.py` | FastAPI application factory |
| `config/config.py` | Configuration dataclass and defaults |
