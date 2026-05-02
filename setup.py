"""
setup.py — One-command setup
============================
Run this ONCE after cloning the repo and placing the BIS SP 21 PDF.

  python setup.py --pdf path/to/BIS_SP21.pdf

This will:
  1. Parse the PDF into structured standard records  → data/standards.json
  2. Build the knowledge graph                       → data/graph.pkl
  3. Index all standards into ChromaDB               → data/chroma_db/
  4. Validate against public test set (optional)     → data/public_results.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.parser.parse_sp21 import parse_pdf
from src.graph.standards_graph import StandardsGraph
from src.retriever.hybrid_retriever import BISRetriever


def main():
    parser = argparse.ArgumentParser(description="BIS Engine Setup")
    parser.add_argument("--pdf", required=True, help="Path to BIS SP 21 PDF")
    parser.add_argument("--data-dir", default="data", help="Output data directory")
    parser.add_argument("--test-set", default=None, help="Optional: path to public test set JSON")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    standards_path = data_dir / "standards.json"
    graph_path     = data_dir / "graph.pkl"
    chroma_path    = str(data_dir / "chroma_db")

    t_total = time.time()

    # ── Step 1: Parse PDF ──────────────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 1: Parsing BIS SP 21 PDF")
    print("="*60)
    standards = parse_pdf(args.pdf, str(standards_path))
    print(f"✓ Extracted {len(standards)} standards → {standards_path}")

    # ── Step 2: Build graph ────────────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 2: Building Knowledge Graph")
    print("="*60)
    sg = StandardsGraph()
    sg.build(standards)
    sg.save(str(graph_path))
    print(f"✓ Graph saved → {graph_path}")
    print(f"  Nodes: {sg.G.number_of_nodes()}  |  Edges: {sg.G.number_of_edges()}")

    # ── Step 3: Index into ChromaDB ────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 3: Indexing into ChromaDB (semantic search)")
    print("="*60)
    retriever = BISRetriever(sg, chroma_path=chroma_path)
    retriever.index_standards(standards)
    print(f"✓ ChromaDB index built → {chroma_path}")

    # ── Step 4: Validate on public test set ───────────────────────────────
    if args.test_set and Path(args.test_set).exists():
        print("\n" + "="*60)
        print("STEP 4: Validating on Public Test Set")
        print("="*60)
        with open(args.test_set) as f:
            test_queries = json.load(f)

        results = []
        for item in test_queries:
            r = retriever.retrieve(item["query"], top_k=5)
            results.append({
                "id": item.get("id", ""),
                "query": item["query"],
                "retrieved_standards": [x["standard_id"] for x in r["results"]],
                "latency_seconds": r["latency_seconds"],
            })

        results_path = data_dir / "public_results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"✓ Public test results → {results_path}")

    elapsed = round(time.time() - t_total, 1)
    print(f"\n{'='*60}")
    print(f"✓ SETUP COMPLETE in {elapsed}s")
    print(f"{'='*60}")
    print(f"\nNext steps:")
    print(f"  Start API:    uvicorn src.api.app:app --reload --port 8000")
    print(f"  Run eval:     python inference.py --input data/public_test.json --output data/results.json")
    print(f"  Start UI:     cd frontend && npm install && npm run dev")


if __name__ == "__main__":
    main()
