"""
Tool: search_news

Semantic search over a Chroma vector collection of news articles --
unlike the other 6 tools (exact key lookup -> SQLite via api.py), news
relevance is genuinely a similarity-search problem, so this is the one
place a vector DB is the right tool rather than a relational store. See
README "Data storage" for the full rationale.

Build the underlying collection first with:
    python scripts/migrate_news_to_chroma.py

Returns RAW articles only -- sentiment/relevance interpretation is the
agent's job, not this tool's. The tool's job is retrieval, not analysis.
"""

from pathlib import Path

import chromadb

from .applicant_profile import get_applicant_profile

CHROMA_PATH = Path(__file__).parent.parent / "db" / "chroma"
COLLECTION_NAME = "news_articles"

_client = None
_collection = None


def _get_collection():
    """
    Lazily connect to the Chroma collection and cache it at module
    level. Loading the embedding model on first use is the expensive
    part of a Chroma query, so this ensures it happens once per process
    rather than once per search_news() call.
    """
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = _client.get_collection(COLLECTION_NAME)
    return _collection


def search_news(applicant_id: str) -> list:
    """
    Return up to 3 news articles relevant to the given applicant's
    company, as a list of {"headline": str, "snippet": str} dicts (or
    an empty list if nothing relevant was indexed for this applicant).

    Looks up the company name via get_applicant_profile, then queries
    Chroma with a generic risk-oriented query string, scoped to this
    applicant only via metadata filtering (`where={"applicant_id": ...}`)
    -- this keeps the lookup applicant-specific while still ranking
    results by semantic relevance rather than a literal text match.
    """
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
