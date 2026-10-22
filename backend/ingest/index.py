"""Stage 2b: embed chunks and build the ChromaDB (semantic) and BM25 (lexical) indexes.

data/chunks.jsonl -> data/chroma/ + data/bm25.pkl
Run from backend/:  python -m ingest.index

Chunks are embedded most-important-first. If the free daily embedding quota runs out, the index
is built from the chunks embedded so far; rerunning the next day continues where it stopped.
"""
import json
import pickle
import re
import shutil

import chromadb
from rank_bm25 import BM25Okapi

import config
from ingest.embed import embed_documents
from ingest.tokenize_he import tokenize

COLLECTION = "fnx_chunks"
METADATA_KEYS = ("url", "title", "display_title", "section", "source_type", "category", "crawled_at",
                 "content_hash")

# Lower = embedded first. Articles, fund-track data pages and legal terms are least likely to be asked.
CATEGORY_PRIORITY = {"claims": 0, "service": 1, "faq": 1, "pdf": 2, "product": 3, "other": 4, "corporate": 6}
LOW_VALUE_RE = re.compile(r"_information/|-information/|/articles?/|/tz[a-z]+/|terms-of-use|class-actions|/magazine/")


def priority(chunk: dict) -> tuple[int, str]:
    p = CATEGORY_PRIORITY.get(chunk["category"], 4)
    if LOW_VALUE_RE.search(chunk["url"]):
        p = 5
    return p, chunk["chunk_id"]


def load_chunks() -> list[dict]:
    with config.CHUNKS_FILE.open(encoding="utf-8") as f:
        return sorted((json.loads(line) for line in f), key=priority)


def build_chroma(chunks: list[dict], vectors: list[list[float]]) -> None:
    # Rebuild from scratch: cheap (vectors are cached) and avoids stale chunks after a refresh.
    shutil.rmtree(config.CHROMA_DIR, ignore_errors=True)
    db = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    col = db.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    for i in range(0, len(chunks), 500):
        batch = chunks[i:i + 500]
        col.add(
            ids=[c["chunk_id"] for c in batch],
            embeddings=vectors[i:i + 500],
            documents=[c["text"] for c in batch],
            metadatas=[{k: c[k] for k in METADATA_KEYS} for c in batch],
        )
    print(f"ChromaDB: {col.count()} chunks")


def build_bm25(chunks: list[dict]) -> None:
    bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])
    with config.BM25_FILE.open("wb") as f:
        pickle.dump({"ids": [c["chunk_id"] for c in chunks], "bm25": bm25}, f)
    print(f"BM25: {len(chunks)} chunks")


def main() -> None:
    chunks = load_chunks()
    vectors = embed_documents([c["text"] for c in chunks], budget=config.INDEX_DAILY_EMBED_BUDGET)
    # Both indexes hold the same chunk set, so every search hit has its text and metadata in Chroma.
    ready = [(c, v) for c, v in zip(chunks, vectors) if v is not None]
    print(f"indexing {len(ready)}/{len(chunks)} chunks")
    build_chroma([c for c, _ in ready], [v for _, v in ready])
    build_bm25([c for c, _ in ready])


if __name__ == "__main__":
    main()
