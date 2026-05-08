import os
from langchain_community.vectorstores import FAISS

def load_faiss_store(path, embeddings):
    if not os.path.exists(path):
        return None

    try:
        return FAISS.load_local(
            path,
            embeddings,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        return None
