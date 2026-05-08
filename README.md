# Smart RAG

Smart RAG is a full-stack Retrieval Augmented Generation app with a FastAPI backend and a React chatbot frontend. Users can register, log in, upload documents or raw text, ask questions, and inspect retrieved source context.

## Features

- Document ingestion for TXT, PDF, and DOCX files
- Raw text ingestion
- Chatbot-first RAG interface
- FAISS vector search
- Sentence Transformers embeddings
- OpenAI chat completion support
- Redis-backed users, metadata, and query cache
- JWT authentication
- Source/context inspection in the frontend
- Docker setup for local full-stack testing

## Tech Stack

**Backend**
- FastAPI
- LangChain
- FAISS
- Sentence Transformers
- OpenAI API
- Redis
- JWT auth
- Uvicorn

**Frontend**
- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query
- Axios
- Lucide React

## Project Structure

```txt
Smart-RAG/
├── backend/
│   ├── api/
│   ├── app/
│   ├── auth/
│   ├── rag/
│   ├── scripts/
│   ├── smart_rag/
│   ├── utils/
│   ├── .env.example
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   ├── .env.example
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── docker-compose.dev.yml
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.12+
- uv
- Node.js 24+
- npm
- Redis
- OpenAI API key
- Docker, optional

## Backend Setup

From the project root:

```powershell
cd backend
uv venv
uv pip install -r requirements.txt
```

Create `backend/.env` from `backend/.env.example`:

```env
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini
VECTOR_STORE_PATH=./vector_store
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000
SECRET_KEY=change-this-to-a-secure-secret-key-min-32-characters
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@example.com
```

Start the backend:

```powershell
uv run uvicorn main:app --reload
```

Backend URL:

```txt
http://localhost:8000
```

API docs:

```txt
http://localhost:8000/docs
```

## Frontend Setup

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

```txt
http://localhost:5173
```

The frontend defaults to:

```env
VITE_API_BASE_URL=http://localhost:8000
```

To override it, create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Docker

Create `backend/.env` first, then run from the project root:

```powershell
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Redis: `localhost:6379`

For backend Docker development with reload:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

## API Endpoints

### Health

- `GET /api/health`

### Authentication

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET /api/auth/users`
- `DELETE /api/auth/users/{user_id}`

### Ingestion

- `POST /ingest/upload-text`
- `POST /ingest/upload-file`
- `GET /ingest/sources`
- `DELETE /ingest/clear-all`

### Query

- `POST /api/query`
- `GET /api/cache/stats`

## Admin User

After Redis and the backend environment are configured:

```powershell
cd backend
uv run python scripts/init_admin.py
```

## Deployment Notes

Frontend and backend are intended to deploy separately.

Recommended setup:

- Frontend: Vercel or Netlify
- Backend: Render, Railway, or Fly.io
- Redis: Upstash Redis or managed Redis from your backend host
- Vector store: persistent backend disk for MVP, hosted vector DB later

Frontend deployment env:

```env
VITE_API_BASE_URL=https://your-backend-domain.com
```

Backend deployment env:

```env
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini
REDIS_HOST=your_redis_host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
VECTOR_STORE_PATH=/app/vector_store
CORS_ORIGINS=https://your-frontend-domain.com
SECRET_KEY=your_secret_key
```

For production, make sure `VECTOR_STORE_PATH` points to persistent storage. If the backend host uses ephemeral storage, uploaded/indexed documents may disappear after restarts.

## Useful Commands

Backend:

```powershell
cd backend
uv run uvicorn main:app --reload
```

Frontend:

```powershell
cd frontend
npm run dev
```

Frontend build:

```powershell
cd frontend
npm run build
```

Docker:

```powershell
docker compose up --build
```

## Git Safety

Do not commit real environment files:

- `backend/.env`
- `frontend/.env`

Use `.env.example` files for shared configuration templates.

## License

MIT
