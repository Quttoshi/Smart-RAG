from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.ingest_routes import ingest_router
from api import query_routes
from api import auth_routes
from utils.config import settings

app = FastAPI(title="SMART-RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(query_routes.router)
app.include_router(auth_routes.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the SMART-RAG API"}
