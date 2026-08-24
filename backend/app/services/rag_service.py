"""RAGService — patient-history retrieval via ChromaDB.

Security invariant (req #37): every query is filtered by patient_id via
ChromaDB metadata `where` clause BEFORE semantic search runs. There is no
code path here that performs a global, unfiltered retrieval.
"""
import logging

import chromadb

from app.core.config import get_settings

logger = logging.getLogger("rag_service")
settings = get_settings()

_client: chromadb.ClientAPI | None = None
_COLLECTION_NAME = "patient_history"


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
    return _client


def _get_collection():
    client = _get_client()
    return client.get_or_create_collection(name=_COLLECTION_NAME)


def index_document(document_id: str, patient_id: str, appointment_id: str | None, document_type: str, text: str, doctor_id: str | None = None, date: str | None = None) -> None:
    """Index one chunk of patient history. Called from the RAGIndexWorker
    asynchronously after a visit completes — never on the booking critical path.
    """
    collection = _get_collection()
    metadata = {
        "patient_id": patient_id,
        "document_type": document_type,
        "appointment_id": appointment_id or "",
        "doctor_id": doctor_id or "",
        "date": date or "",
    }
    collection.upsert(ids=[document_id], documents=[text], metadatas=[metadata])


def retrieve_relevant_history(patient_id: str, query: str, top_k: int | None = None) -> list[dict]:
    """Retrieve top-K relevant chunks for ONE patient only. `patient_id` here
    must always come from the authenticated session/appointment relationship
    — never from a raw client-supplied value without an authorization check
    upstream (enforced in the API layer / chatbot tool layer).
    """
    collection = _get_collection()
    k = top_k or settings.RAG_TOP_K
    try:
        results = collection.query(
            query_texts=[query],
            n_results=k,
            where={"patient_id": patient_id},  # mandatory metadata filter — patient isolation
        )
    except Exception as e:
        logger.warning("RAG retrieval failed for patient %s: %s", patient_id, e)
        return []

    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(docs)

    seen = set()
    out = []
    for doc, meta, dist in zip(docs, metadatas, distances):
        key = doc[:100]
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": doc, "metadata": meta, "distance": dist})
    return out


def build_compact_context(chunks: list[dict], max_chars: int = 2000) -> str:
    """Compacts retrieved chunks into a bounded context block so we never
    send a patient's entire history to Groq (req #38)."""
    parts = []
    total = 0
    for c in chunks:
        piece = f"[{c['metadata'].get('document_type', 'note')} on {c['metadata'].get('date', 'unknown date')}] {c['text']}"
        if total + len(piece) > max_chars:
            break
        parts.append(piece)
        total += len(piece)
    return "\n".join(parts)
