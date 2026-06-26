# Semantic search over a Chroma vector collection -- unlike the other 6
# tools (exact key lookup -> SQLite), news relevance is genuinely a
# similarity-search problem, so this is the one place a vector DB is the
# right tool rather than a relational store. See README "Data storage"
# section for the full rationale.
#
# Returns RAW articles only -- sentiment/relevance interpretation is the
# agent's job, not this tool's (unchanged from the original fixture-based
# version).

from pathlib import Path

import chromadb

from .applicant_profile import get_applicant_profile

CHROMA_PATH = Path(__file__).parent.parent / "db" / "chroma"
COLLECTION_NAME = "news_articles"

_client = None
_collection = None


def _get_collection():
    # Lazy singleton: the embedding model chromadb loads on first query
    # is the expensive part, so only do it once per process, not once
    # per call.
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = _client.get_collection(COLLECTION_NAME)
    return _collection


def search_news(applicant_id: str) -> list:
    profile = get_applicant_profile(applicant_id)
    company_name = profile.get("company_name")
    if company_name is None:
        return [{"error": f"No applicant found with id {applicant_id}"}]

    collection = _get_collection()
    results = collection.query(
        query_texts=[f"{company_name} negative news lawsuit complaint violation risk concerns"],
        n_results=3,
        where={"applicant_id": applicant_id},
    )

    metadatas = results.get("metadatas", [[]])[0]
    return [
        {"headline": m["headline"], "snippet": m["snippet"]}
        for m in metadatas
    ]
