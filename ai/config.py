import os
from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
RAG_TOP_K = _safe_int(os.getenv("RAG_TOP_K", "4"), 4)
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", ".vectordb")
VECTOR_COLLECTION = os.getenv("VECTOR_COLLECTION", "sales_chat_history")

API_KEY = os.getenv("OPENAI_API_KEY")


@lru_cache(maxsize=1)
def get_openai_client():
    if not API_KEY:
        return None
    return OpenAI(api_key=API_KEY)
