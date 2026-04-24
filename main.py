from fastapi import FastAPI
from api.ingest_routes import ingest_router
from api import query_routes
from api import auth_routes

app = FastAPI(title="SMART-RAG API")
app.include_router(ingest_router)
app.include_router(query_routes.router)
app.include_router(auth_routes.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the SMART-RAG API"}