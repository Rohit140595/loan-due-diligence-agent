"""
Migration script: load fixtures/applicants.json's news_articles into a
Chroma vector collection (db/chroma/), used by the search_news tool.

Unlike the other 5 tools (exact key lookup -> SQLite, see
migrate_to_sqlite.py), news relevance is a semantic-similarity problem
-- a real news API wouldn't return results keyed by applicant_id, it
would return whatever's semantically relevant to a query. This
collection is queried by embedding similarity (filtered to the right
applicant via metadata), not by a literal ID match.

Run with: `python scripts/migrate_news_to_chroma.py`

Re-runnable: deletes and recreates the collection each time, so it's
safe to run again after editing fixtures/applicants.json.
"""

import json
from pathlib import Path

import chromadb

ROOT = Path(__file__).parent.parent
CHROMA_PATH = ROOT / "db" / "chroma"
APPLICANTS_JSON = ROOT / "fixtures" / "applicants.json"
COLLECTION_NAME = "news_articles"


def migrate():
    """
    Rebuild the db/chroma/ "news_articles" collection from scratch using
    the current contents of fixtures/applicants.json. Each article's
    headline + snippet becomes one embedded document, tagged with
    applicant_id (for filtering at query time), company_name, and the
    original headline/snippet text (so search_news can return the
    original text instead of re-deriving it from the embedded string).
    """
    with open(APPLICANTS_JSON) as f:
        applicants = json.load(f)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        # No existing collection to delete -- fine on a first run.
        pass
    collection = client.create_collection(COLLECTION_NAME)

    documents, metadatas, ids = [], [], []
    for applicant_id, data in applicants.items():
        company_name = data["company_name"]
        for i, article in enumerate(data.get("news_articles", [])):
            # The embedded text combines headline + snippet so similarity
            # search has more context to match against than the headline
            # alone would provide.
            documents.append(f"{article['headline']}. {article['snippet']}")
            metadatas.append(
                {
                    "applicant_id": applicant_id,
                    "company_name": company_name,
                    "headline": article["headline"],
                    "snippet": article["snippet"],
                }
            )
            # One unique ID per article, scoped by applicant so a
            # re-run with new/different articles doesn't collide.
            ids.append(f"{applicant_id}-{i}")

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"Migrated {len(documents)} news articles to {CHROMA_PATH}")


if __name__ == "__main__":
    migrate()
