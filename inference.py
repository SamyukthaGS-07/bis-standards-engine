"""
inference.py — Mandatory judging entry point
=============================================
Judges run: python inference.py --input hidden_private_dataset.json --output team_results.json

This file MUST:
  - Read JSON from --input
  - Pass each query through the RAG pipeline
  - Write results to --output in strict schema
  - Never crash

Output schema per item:
  {
    "id": <str>,
    "retrieved_standards": [<str>, ...],  # IS numbers, ordered by rank
    "latency_seconds": <float>
  }
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

# ── Ensure src is importable ───────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from src.graph.standards_graph import StandardsGraph
from src.retriever.hybrid_retriever import BISRetriever
from src.llm.rationale_generator import LLMRationaleGenerator


GRAPH_PATH  = os.environ.get("GRAPH_PATH",  "data/graph.pkl")
CHROMA_PATH = os.environ.get("CHROMA_PATH", "data/chroma_db")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")
TOP_K = 5   # retrieve top-5 for MRR@5


def load_engine():
    print("[inference] Loading graph ...")
    graph = StandardsGraph.load(GRAPH_PATH)

    print("[inference] Loading retriever ...")
    retriever = BISRetriever(graph, chroma_path=CHROMA_PATH)

    # LLM is optional for inference.py — metrics only need standard IDs
    llm = LLMRationaleGenerator(provider=LLM_PROVIDER)

    return graph, retriever, llm


def run_query(retriever, query: str) -> tuple[list[str], float]:
    """Run a single query. Returns (standard_id_list, latency_seconds)."""
    t0 = time.time()
    result = retriever.retrieve(query, top_k=TOP_K)
    latency = round(time.time() - t0, 4)
    standard_ids = [r["standard_id"] for r in result["results"]]
    return standard_ids, latency


def main():
    parser = argparse.ArgumentParser(description="BIS Standards Inference Script")
    parser.add_argument("--input",  required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to write output JSON file")
    args = parser.parse_args()

    # ── Load input ─────────────────────────────────────────────────────────
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[inference] ERROR: Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    print(f"[inference] Loaded {len(queries)} queries from {input_path}")

    # ── Load engine ────────────────────────────────────────────────────────
    try:
        graph, retriever, llm = load_engine()
    except Exception as e:
        print(f"[inference] FATAL: Could not load engine: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ── Run queries ────────────────────────────────────────────────────────
    output = []
    total = len(queries)

    for i, item in enumerate(queries, 1):
        item_id = item.get("id", str(i))
        query   = item.get("query", "")

        if not query.strip():
            print(f"[inference] [{i}/{total}] Empty query for id={item_id}, skipping.")
            output.append({
                "id": item_id,
                "retrieved_standards": [],
                "latency_seconds": 0.0,
            })
            continue

        try:
            standard_ids, latency = run_query(retriever, query)
            print(f"[inference] [{i}/{total}] id={item_id} | {latency}s | {standard_ids[:3]}")
        except Exception as e:
            # NEVER crash — write empty result and continue
            print(f"[inference] [{i}/{total}] ERROR on id={item_id}: {e}")
            traceback.print_exc()
            standard_ids, latency = [], 0.0

        output.append({
            "id": item_id,
            "retrieved_standards": standard_ids,
            "latency_seconds": latency,
        })

    # ── Write output ───────────────────────────────────────────────────────
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    avg_latency = sum(r["latency_seconds"] for r in output) / max(len(output), 1)
    print(f"\n[inference] Done. {len(output)} results written to {output_path}")
    print(f"[inference] Avg latency: {avg_latency:.3f}s")


if __name__ == "__main__":
    main()
