# One-time migration: load fixtures/applicants.json's news_articles into
# a Chroma vector collection. Unlike the other 5 tools (exact key lookup
# -> SQLite), news relevance is a semantic-similarity problem -- a real
# news API wouldn't return results keyed by applicant_id, it would
# return whatever's semantically relevant to a query. This collection is
# queried by embedding similarity (filtered to the right applicant via
# metadata), not by a literal ID match.
#
# Re-runnable: deletes and recreates the collection each time.

import json
from pathlib import Path

import chromadb

ROOT = Path(__file__).parent.parent
CHROMA_PATH = ROOT / "db" / "chroma"
APPLICANTS_JSON = ROOT / "fixtures" / "applicants.json"
COLLECTION_NAME = "news_articles"


def migrate():
    with open(APPLICANTS_JSON) as f:
        applicants = json.load(f)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    documents, metadatas, ids = [], [], []
    for applicant_id, data in applicants.items():
        company_name = data["company_name"]
        for i, article in enumerate(data.get("news_articles", [])):
            documents.append(f"{article['headline']}. {article['snippet']}")
            metadatas.append(
                {
                    "applicant_id": applicant_id,
                    "company_name": company_name,
                    "headline": article["headline"],
                    "snippet": article["snippet"],
                }
            )
            ids.append(f"{applicant_id}-{i}")

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"Migrated {len(documents)} news articles to {CHROMA_PATH}")


if __name__ == "__main__":
    migrate()
