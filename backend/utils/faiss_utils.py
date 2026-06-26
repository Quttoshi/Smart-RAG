import os
from langchain_community.vectorstores import FAISS

def faiss_index_exists(path: str) -> bool:
    return os.path.isfile(os.path.join(path, "index.faiss"))

def load_faiss_store(path, embeddings):
    if not faiss_index_exists(path):
        return None

    try:
        return FAISS.load_local(
            path,
            embeddings,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        return None
