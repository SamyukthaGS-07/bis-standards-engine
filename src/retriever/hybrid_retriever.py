"""
Hybrid Retriever
=================
Combines:
  1. Semantic search (dense embeddings via ChromaDB)
  2. BM25 keyword search (sparse)
  3. Graph expansion
  4. Query understanding with boosting
"""

import json
import re
import time
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

from src.graph.standards_graph import StandardsGraph


# ── Query Understanding ────────────────────────────────────────────────────

MATERIAL_HINTS = {
    "Cement": ["cement", "opc", "ppc", "portland", "clinker", "binding", "mortar",
               "slag cement", "pozzolana", "hydrophobic", "sulphate resisting",
               "white cement", "high alumina", "supersulphated", "rapid hardening"],
    "Steel": ["steel", "rebar", "reinforcement", "tmt", "iron", "bar", "rod",
              "fe 415", "fe 500", "deformed", "cold twisted", "wire"],
    "Concrete": ["concrete", "rcc", "mix", "admixture", "curing", "m20", "m25",
                 "m30", "prestressed", "reinforced concrete"],
    "Aggregates": ["aggregate", "sand", "gravel", "crushed", "coarse", "fine aggregate",
                   "natural sources", "coarse and fine", "structural concrete"],
    "Bricks & Masonry": ["brick", "block", "masonry", "clay", "aac", "fly ash brick",
                          "lightweight block", "hollow block", "solid block", "concrete block",
                          "lightweight concrete", "autoclaved", "aerated", "cellular"],
    "Waterproofing": ["waterproof", "damp", "bitumen", "seal", "membrane", "joint sealant"],
    "Timber & Wood": ["timber", "wood", "plywood", "board", "flush door"],
    "Paints & Coatings": ["paint", "coating", "primer", "varnish", "distemper"],
    "Asbestos": ["asbestos", "asbestos cement", "corrugated sheet", "roofing sheet",
                 "semi-corrugated", "cladding"],
    "Pipes & Fittings": ["pipe", "fitting", "drainage", "sewerage", "conduit",
                          "precast concrete pipe", "water main"],
}

# Query-level keyword boosts — if query contains these, boost matching standards
QUERY_BOOSTS = [
    # (query_keywords, standard_id_fragment, boost_score)
    (["lightweight", "light weight", "aerated", "cellular", "aac"], "2185", 2.0),
    (["hollow", "solid", "concrete block", "masonry block", "masonry unit"], "2185", 1.5),
    (["coarse and fine", "natural sources", "structural concrete", "aggregate for concrete"], "383", 2.0),
    (["portland slag", "slag cement"], "455", 2.0),
    (["pozzolana", "pozzolanic", "fly ash cement", "fly ash based"], "1489", 2.0),
    (["calcined clay", "calcined clay based"], "1489", 2.0),
    (["masonry cement", "mortar cement", "not structural"], "3466", 2.0),
    (["supersulphated", "super sulphated", "marine", "aggressive water"], "6909", 2.0),
    (["white portland", "white cement", "architectural", "decorative"], "8042", 2.0),
    (["53 grade", "high strength cement", "opc 53"], "12269", 2.0),
    (["43 grade", "opc 43"], "8112", 2.0),
    (["33 grade", "opc 33", "ordinary portland cement"], "269", 1.5),
    (["rapid hardening", "quick setting"], "8041", 2.0),
    (["hydrophobic", "water repellent cement"], "8043", 2.0),
    (["sulphate resisting", "sulphate resistant"], "12330", 2.0),
    (["high alumina", "aluminous"], "6452", 2.0),
    (["precast concrete pipe", "concrete pipe", "water main", "without reinforcement"], "458", 2.0),
    (["asbestos cement sheet", "corrugated asbestos", "semi-corrugated", "roofing cladding"], "459", 2.0),
    (["sand masonry", "masonry mortar", "sand for mortar"], "2116", 2.0),
    (["artificial lightweight aggregate", "lightweight aggregate"], "9142", 2.0),
]


def understand_query(query: str) -> dict:
    q_lower = query.lower()
    detected_categories = []
    for cat, hints in MATERIAL_HINTS.items():
        if any(h in q_lower for h in hints):
            detected_categories.append(cat)

    # Find boost targets
    boost_targets = {}
    for query_kws, std_fragment, boost in QUERY_BOOSTS:
        if any(kw in q_lower for kw in query_kws):
            boost_targets[std_fragment] = boost_targets.get(std_fragment, 0) + boost

    return {
        "original": query,
        "detected_categories": detected_categories,
        "boost_targets": boost_targets,
        "is_structural": any(w in q_lower for w in
                             ["structural", "load bearing", "rcc", "foundation", "column", "beam"]),
    }


# ── Reciprocal Rank Fusion ─────────────────────────────────────────────────

def rrf_fuse(results_a: list, results_b: list, k: int = 60) -> list:
    scores: dict = {}
    all_items: dict = {}

    for rank, item in enumerate(results_a, 1):
        sid = item["standard_id"]
        scores[sid] = scores.get(sid, 0) + 1 / (k + rank)
        all_items[sid] = item

    for rank, item in enumerate(results_b, 1):
        sid = item["standard_id"]
        scores[sid] = scores.get(sid, 0) + 1 / (k + rank)
        all_items[sid] = item

    fused = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    result = []
    for sid in fused:
        item = all_items[sid].copy()
        item["retrieval_score"] = scores[sid]
        result.append(item)
    return result


def apply_boosts(results: list, boost_targets: dict) -> list:
    """Boost scores of standards whose ID matches query-specific patterns."""
    if not boost_targets:
        return results
    for item in results:
        sid = item.get("standard_id", "")
        for fragment, boost in boost_targets.items():
            if fragment in sid:
                item["retrieval_score"] = item.get("retrieval_score", 0) * boost
                break
    results.sort(key=lambda x: x.get("retrieval_score", 0), reverse=True)
    return results


# ── Main Retriever ─────────────────────────────────────────────────────────

class BISRetriever:
    def __init__(self, graph: StandardsGraph, chroma_path: str = "data/chroma_db",
                 collection_name: str = "bis_standards"):
        self.graph = graph
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self._chroma_client = None
        self._collection = None
        self._bm25 = None
        self._bm25_corpus = []
        self._load_or_build()

    def _load_or_build(self):
        print("[Retriever] Initialising ChromaDB ...")
        self._chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-small-en-v1.5"
        )
        existing = [c.name for c in self._chroma_client.list_collections()]
        if self.collection_name in existing:
            self._collection = self._chroma_client.get_collection(
                name=self.collection_name, embedding_function=ef
            )
            print(f"[Retriever] Loaded existing collection ({self._collection.count()} docs)")
        else:
            self._collection = self._chroma_client.create_collection(
                name=self.collection_name,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )
            print("[Retriever] Created new collection — run index_standards() to populate.")
        self._build_bm25()

    def index_standards(self, standards: list, batch_size: int = 100) -> None:
        print(f"[Retriever] Indexing {len(standards)} standards into ChromaDB ...")
        ids, documents, metadatas = [], [], []

        for std in standards:
            sid = std["standard_id"]
            # Rich document — title repeated for emphasis, scope, keywords
            title = std.get("title", "")
            scope = std.get("scope", "")
            keywords = " ".join(std.get("keywords", []))
            doc = f"{sid} {title} {title} {scope} {keywords}".strip()

            meta = {
                "standard_id": sid,
                "title": title[:500],
                "material_category": std.get("material_category", "Other"),
                "applications": ",".join(std.get("applications", [])),
                "year": std.get("year") or "",
                "page": str(std.get("page", 0)),
            }
            ids.append(sid)
            documents.append(doc)
            metadatas.append(meta)

        for i in range(0, len(ids), batch_size):
            self._collection.add(
                ids=ids[i: i + batch_size],
                documents=documents[i: i + batch_size],
                metadatas=metadatas[i: i + batch_size],
            )
            print(f"[Retriever] Indexed batch {i // batch_size + 1}")

        print("[Retriever] Indexing complete.")
        self._build_bm25()

    def _build_bm25(self):
        standards = self.graph.get_all_standards()
        if not standards:
            return
        self._bm25_corpus = standards
        tokenized = []
        for std in standards:
            title = std.get("title", "")
            tokens = (
                std.get("standard_id", "").lower().split()
                + title.lower().split()
                + title.lower().split()  # double weight title
                + std.get("scope", "").lower().split()
                + std.get("keywords", [])
            )
            tokenized.append(tokens)
        self._bm25 = BM25Okapi(tokenized)
        print(f"[Retriever] BM25 index built with {len(standards)} documents.")

    def _semantic_search(self, query: str, top_k: int = 10,
                         category_filter: Optional[str] = None) -> list:
        where = {}
        if category_filter:
            where = {"material_category": category_filter}

        kwargs = {
            "query_texts": [query],
            "n_results": min(top_k, self._collection.count() or 1),
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)
        output = []
        for i, sid in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i] if results.get("distances") else 0
            score = 1 - distance
            record = self.graph.get_standard(sid) or {}
            output.append({**record, **meta, "retrieval_score": score, "standard_id": sid})
        return output

    def _bm25_search(self, query: str, top_k: int = 10) -> list:
        if not self._bm25:
            return []
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] == 0:
                continue
            std = self._bm25_corpus[idx]
            results.append({**std, "retrieval_score": float(scores[idx])})
        return results

    def retrieve(self, query: str, top_k: int = 5) -> dict:
        t_start = time.time()

        query_meta = understand_query(query)
        category_filter = query_meta["detected_categories"][0] \
            if query_meta["detected_categories"] else None

        # Semantic search
        semantic = self._semantic_search(query, top_k=10, category_filter=category_filter)
        if len(semantic) < 3:
            semantic = self._semantic_search(query, top_k=10)

        # BM25
        bm25_results = self._bm25_search(query, top_k=10)

        # Fuse
        fused = rrf_fuse(semantic, bm25_results)

        # Apply query-specific boosts BEFORE graph expansion
        fused = apply_boosts(fused, query_meta.get("boost_targets", {}))

        # Graph expansion
        expanded = self.graph.expand_results(fused, top_k=top_k)

        # Apply boosts again after expansion
        expanded = apply_boosts(expanded, query_meta.get("boost_targets", {}))

        latency = time.time() - t_start

        return {
            "query": query,
            "query_analysis": query_meta,
            "results": expanded[:top_k],
            "latency_seconds": round(latency, 3),
        }
