"""
BIS Standards Recommendation Engine — FastAPI Backend
"""

import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.graph.standards_graph import StandardsGraph
from src.retriever.hybrid_retriever import BISRetriever
from src.llm.rationale_generator import LLMRationaleGenerator


# ── App state ──────────────────────────────────────────────────────────────

class AppState:
    graph: Optional[StandardsGraph] = None
    retriever: Optional[BISRetriever] = None
    llm: Optional[LLMRationaleGenerator] = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models and indexes on startup."""
    graph_path = os.environ.get("GRAPH_PATH", "data/graph.pkl")
    chroma_path = os.environ.get("CHROMA_PATH", "data/chroma_db")
    llm_provider = os.environ.get("LLM_PROVIDER", "groq")

    if Path(graph_path).exists():
        state.graph = StandardsGraph.load(graph_path)
        state.retriever = BISRetriever(state.graph, chroma_path=chroma_path)
        state.llm = LLMRationaleGenerator(provider=llm_provider)
        print("[API] Engine ready.")
    else:
        print(f"[API] WARNING: Graph not found at {graph_path}. Run setup first.")
    yield


app = FastAPI(
    title="BIS Standards Recommendation Engine",
    description="Graph-augmented RAG for BIS SP 21 compliance",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    include_rationale: bool = True
    category_filter: Optional[str] = None


class StandardResult(BaseModel):
    standard_id: str
    title: str
    material_category: str
    applications: list[str]
    rationale: str
    confidence: str
    key_requirement: str
    source: str  # "vector_retrieval" | "graph_expansion"
    retrieval_score: float


class RecommendationResponse(BaseModel):
    query: str
    summary: str
    recommendations: list[StandardResult]
    latency_seconds: float
    query_analysis: dict


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok" if state.retriever else "not_ready",
        "standards_count": state.graph.G.number_of_nodes() if state.graph else 0,
    }


@app.post("/recommend", response_model=RecommendationResponse)
def recommend(req: QueryRequest):
    if not state.retriever:
        raise HTTPException(status_code=503, detail="Engine not initialized. Run setup first.")

    t0 = time.time()

    # Retrieve
    retrieval = state.retriever.retrieve(req.query, top_k=req.top_k)
    raw_results = retrieval["results"]

    # Generate rationale
    rationale_data = {"summary": "", "standards": []}
    if req.include_rationale and state.llm and raw_results:
        rationale_data = state.llm.generate_rationale(req.query, raw_results)

    # Build rationale lookup
    rationale_map = {
        s["standard_id"]: s
        for s in rationale_data.get("standards", [])
    }

    # Merge retrieval + rationale
    recommendations = []
    for res in raw_results:
        sid = res.get("standard_id", "")
        rat = rationale_map.get(sid, {})
        recommendations.append(
            StandardResult(
                standard_id=sid,
                title=res.get("title", ""),
                material_category=res.get("material_category", "Other"),
                applications=res.get("applications", []) if isinstance(res.get("applications"), list)
                             else res.get("applications", "").split(","),
                rationale=rat.get("rationale", res.get("scope", "")[:200]),
                confidence=rat.get("confidence", "medium"),
                key_requirement=rat.get("key_requirement", ""),
                source=res.get("source", "vector_retrieval"),
                retrieval_score=round(res.get("retrieval_score", 0), 4),
            )
        )

    total_latency = round(time.time() - t0, 3)

    return RecommendationResponse(
        query=req.query,
        summary=rationale_data.get("summary", ""),
        recommendations=recommendations,
        latency_seconds=total_latency,
        query_analysis=retrieval.get("query_analysis", {}),
    )


@app.get("/standards/{standard_id}")
def get_standard(standard_id: str):
    if not state.graph:
        raise HTTPException(status_code=503, detail="Engine not initialized.")
    std = state.graph.get_standard(standard_id)
    if not std:
        raise HTTPException(status_code=404, detail=f"{standard_id} not found.")
    neighbors = state.graph.get_neighbors(standard_id, top_k=5)
    return {**std, "related": neighbors}


@app.get("/categories")
def get_categories():
    if not state.graph:
        raise HTTPException(status_code=503, detail="Engine not initialized.")
    from collections import Counter
    cats = Counter(
        d.get("category") for _, d in state.graph.G.nodes(data=True)
    )
    return dict(cats)
