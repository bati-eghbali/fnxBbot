"""Hybrid retrieval: ChromaDB (semantic) + BM25 (lexical), fused with Reciprocal Rank Fusion.

Defense layer 2: an absolute cosine-similarity floor. RRF scores are relative (there is always a
"best" result), so relevance is judged on the raw vector similarity instead.
"""
import pickle
from dataclasses import dataclass, field
from functools import lru_cache

import chromadb

import config
from ingest.embed import DailyQuotaExhausted, embed_query
from ingest.index import COLLECTION
from ingest.tokenize_he import tokenize, word_forms

RRF_K = 60


@dataclass
class Chunk:
    chunk_id: str
    url: str
    title: str
    section: str
    text: str
    source_type: str
    similarity: float = 0.0  # cosine similarity to the query (0 if found by BM25 only)
    score: float = 0.0       # fused RRF score


@dataclass
class SearchResult:
    chunks: list[Chunk] = field(default_factory=list)
    best_similarity: float = 0.0
    mode: str = "hybrid"            # "lexical" when the query embedding was unavailable
    lexical_coverage: float = 0.0

    @property
    def found(self) -> bool:
        return bool(self.chunks)


@lru_cache(maxsize=1)
def _collection():
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR)).get_collection(COLLECTION)


@lru_cache(maxsize=1)
def _bm25():
    with config.BM25_FILE.open("rb") as f:
        return pickle.load(f)


def _to_chunk(chunk_id: str, doc: str, meta: dict, similarity: float = 0.0) -> Chunk:
    return Chunk(chunk_id=chunk_id, url=meta["url"], title=meta.get("display_title") or meta["title"],
                 section=meta.get("section", ""),
                 text=doc, source_type=meta.get("source_type", "html"), similarity=similarity)


def _bm25_ranked(query: str) -> list[str]:
    bm = _bm25()
    scores = bm["bm25"].get_scores(tokenize(query))
    return [bm["ids"][i] for i in scores.argsort()[::-1][:config.TOP_K_EACH] if scores[i] > 0]


def _lexical_search(query: str, top_k: int) -> SearchResult:
    """Fallback when the query cannot be embedded (free daily quota used up). Relevance floor:
    the best chunk must contain most of the question's content words."""
    ranked = _bm25_ranked(query)[:top_k]
    if not ranked:
        return SearchResult(mode="lexical")
    got = _collection().get(ids=ranked, include=["documents", "metadatas"])
    by_id = {cid: _to_chunk(cid, doc, meta) for cid, doc, meta in zip(got["ids"], got["documents"], got["metadatas"])}
    chunks = [by_id[cid] for cid in ranked if cid in by_id]
    words = word_forms(query)
    best_tokens = set(tokenize(chunks[0].text)) if chunks else set()
    coverage = sum(bool(forms & best_tokens) for forms in words) / max(len(words), 1)
    if coverage < config.MIN_LEXICAL_COVERAGE:
        return SearchResult(mode="lexical", lexical_coverage=coverage)
    return SearchResult(chunks=chunks, mode="lexical", lexical_coverage=coverage)


def search(query: str, top_k: int = config.TOP_K_FINAL, min_similarity: float = config.MIN_COSINE_SIM) -> SearchResult:
    try:
        query_vec = embed_query(query)
    except DailyQuotaExhausted:
        return _lexical_search(query, top_k)
    col = _collection()
    vec = col.query(query_embeddings=[query_vec], n_results=config.TOP_K_EACH,
                    include=["documents", "metadatas", "distances"])
    vector_hits = {
        cid: _to_chunk(cid, doc, meta, similarity=1.0 - dist)
        for cid, doc, meta, dist in zip(vec["ids"][0], vec["documents"][0], vec["metadatas"][0], vec["distances"][0])
    }
    best = max((c.similarity for c in vector_hits.values()), default=0.0)
    if best < min_similarity:
        return SearchResult(best_similarity=best)

    bm25_ranked = _bm25_ranked(query)

    fused: dict[str, float] = {}
    for ranking in (list(vector_hits), bm25_ranked):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)

    top_ids = sorted(fused, key=fused.get, reverse=True)[:top_k]
    missing = [cid for cid in top_ids if cid not in vector_hits]
    if missing:
        got = col.get(ids=missing, include=["documents", "metadatas"])
        for cid, doc, meta in zip(got["ids"], got["documents"], got["metadatas"]):
            vector_hits[cid] = _to_chunk(cid, doc, meta)

    chunks = []
    for cid in top_ids:
        c = vector_hits[cid]
        c.score = fused[cid]
        chunks.append(c)
    return SearchResult(chunks=chunks, best_similarity=best)


def page_chunks(url: str) -> list[Chunk]:
    """All chunks of one page, in document order."""
    got = _collection().get(where={"url": url}, include=["documents", "metadatas"])
    chunks = [_to_chunk(cid, doc, meta) for cid, doc, meta in zip(got["ids"], got["documents"], got["metadatas"])]
    return sorted(chunks, key=lambda c: c.chunk_id)
