# Smart RAG 🚀

A production-ready Retrieval Augmented Generation (RAG) system built with **FastAPI**, **LangChain**, and **FAISS**. This system enables intelligent document ingestion, semantic search, and context-aware query responses using modern LLMs.

## Features ✨

- **Document Ingestion**: Process and index documents (PDF, DOCX, TXT) with automatic text splitting
- **Vector Search**: High-performance semantic search using FAISS vector database
- **Intelligent Caching**: Redis-based caching layer for optimized performance
- **JWT Authentication**: Secure API endpoints with token-based authentication
- **LLM Integration**: Built-in support for Groq API with LangChain
- **Embeddings**: Sentence Transformers for high-quality vector embeddings
- **REST API**: Comprehensive FastAPI endpoints for all RAG operations

## Tech Stack 🛠️

- **Framework**: FastAPI
- **RAG Pipeline**: LangChain & LangChain-Community
- **Vector Database**: FAISS
- **Embeddings**: Sentence Transformers
- **LLM**: Groq API
- **Authentication**: JWT (python-jose)
- **Caching**: Redis
- **Server**: Uvicorn
- **Validation**: Pydantic

## Project Structure 📁

```
smart-rag/
├── api/                      # API routes
│   ├── auth_routes.py       # Authentication endpoints
│   ├── ingest_routes.py     # Document ingestion
│   └── query_routes.py      # Query and retrieval endpoints
├── auth/                     # Authentication & security
│   ├── jwt_handler.py       # JWT token management
│   ├── password_handler.py  # Password hashing & validation
│   ├── user_manager.py      # User management
│   └── models.py            # Auth data models
├── rag/                      # RAG core logic
│   └── smart_rag.py        # Main RAG pipeline
├── smart_rag/               # RAG utilities
│   ├── ingest.py           # Document ingestion logic
│   └── redis_cache.py      # Redis caching layer
├── utils/                    # Utility modules
│   ├── config.py           # Configuration settings
│   ├── faiss_utils.py      # FAISS operations
│   ├── file_utils.py       # File processing
│   ├── logger.py           # Logging setup
│   ├── redis_client.py     # Redis client
│   ├── text_utils.py       # Text processing
│   └── validation_utils.py # Validation helpers
├── scripts/                  # Utility scripts
│   └── init_admin.py       # Admin initialization
├── main.py                  # FastAPI application entry
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Installation 📦

### Prerequisites
- Python 3.8+
- Redis server
- Groq API key

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/smart-rag.git
   cd smart-rag
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   VECTOR_STORE_PATH=./vector_store
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=optional_password
   ```

## Usage 🚀

### Start the server
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Interactive API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Initialize Admin User
```bash
python scripts/init_admin.py
```

## API Endpoints 📡

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `POST /auth/refresh` - Refresh JWT token

### Document Ingestion
- `POST /ingest/documents` - Upload and process documents
- `GET /ingest/documents` - List indexed documents
- `DELETE /ingest/documents/{doc_id}` - Delete document

### Query & Retrieval
- `POST /query/search` - Semantic search across documents
- `POST /query/rag` - Full RAG query with LLM response
- `GET /query/sources/{query_id}` - Get sources for a query

## Configuration ⚙️

Edit `utils/config.py` to customize:
- FAISS index parameters
- Text splitting strategies
- Redis cache TTL
- LLM model selection
- Embedding model

## Development 💻

### Run tests
```bash
pytest
```

### Code formatting
```bash
black .
isort .
```

### Type checking
```bash
mypy .
```

## Contributing 🤝

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Support 💬

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Built using FastAPI & LangChain** 
