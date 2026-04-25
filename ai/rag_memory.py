from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

try:
    import chromadb
except Exception:
    chromadb = None

from .config import EMBEDDING_MODEL, VECTOR_COLLECTION, VECTOR_DB_PATH, get_openai_client


@lru_cache(maxsize=1)
def _get_vector_client():
    if chromadb is None:
        return None
    return chromadb.PersistentClient(path=VECTOR_DB_PATH)


def _get_collection():
    vector_client = _get_vector_client()
    if vector_client is None:
        return None

    return vector_client.get_or_create_collection(
        name=VECTOR_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def rag_is_available():
    return _get_collection() is not None and get_openai_client() is not None


def _embed_text(text):
    client = get_openai_client()
    if client is None:
        raise RuntimeError("OPENAI_API_KEY topilmadi.")

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def save_chat_turn(session_id, user_query, assistant_response):
    collection = _get_collection()
    if collection is None:
        return {"saved": False, "reason": "Vector DB mavjud emas."}

    try:
        document = f"Savol: {user_query}\nJavob: {assistant_response}"
        embedding = _embed_text(document)
        created_at = datetime.now(timezone.utc).isoformat()
        record_id = f"{session_id}-{uuid4().hex}"

        collection.add(
            ids=[record_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[{"session_id": session_id, "created_at": created_at}],
        )
        return {"saved": True, "id": record_id}
    except Exception as exc:
        return {"saved": False, "reason": str(exc)}


def retrieve_similar_history(session_id, query, top_k=4):
    collection = _get_collection()
    if collection is None:
        return []

    try:
        top_k = max(1, min(int(top_k), 10))
        query_embedding = _embed_text(query)
        include_fields = ["documents", "metadatas", "distances"]

        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"session_id": session_id},
            include=include_fields,
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        if not documents:
            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=include_fields,
            )
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]

        rows = []
        for idx, doc in enumerate(documents):
            metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
            distance = distances[idx] if idx < len(distances) else None
            similarity = None if distance is None else 1.0 / (1.0 + float(distance))
            rows.append(
                {
                    "document": doc,
                    "metadata": metadata,
                    "distance": distance,
                    "similarity": similarity,
                }
            )

        return rows
    except Exception:
        return []


def format_rag_context(history_rows):
    if not history_rows:
        return "O'xshash oldingi suhbat topilmadi."

    lines = []
    for idx, item in enumerate(history_rows, start=1):
        similarity = item.get("similarity")
        similarity_text = "n/a" if similarity is None else f"{similarity:.3f}"
        lines.append(
            f"{idx}) similarity={similarity_text}\n{item.get('document', '')}"
        )

    return "\n\n".join(lines)
