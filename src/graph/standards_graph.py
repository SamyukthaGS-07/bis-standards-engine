"""
BIS Standards Knowledge Graph
==============================
Builds a graph where:
  - Nodes = individual standards
  - Edges = relationships (co-referenced, same category, supersedes, related material)

This is the key differentiator vs. flat RAG.
When you retrieve IS 12269, the graph surfaces IS 269, IS 8112 automatically —
because they're connected by domain logic, not just text similarity.
"""

import json
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Optional
import networkx as nx


EDGE_WEIGHTS = {
    "cross_reference": 1.0,   # Explicitly mentioned in each other's text
    "same_category": 0.6,     # Same material category
    "same_application": 0.5,  # Share application domain
    "keyword_overlap": 0.4,   # Share significant keywords
}

# Known supersession relationships in BIS (manually curated)
KNOWN_SUPERSESSIONS = {
    "IS 269": "IS 1489",   # PPC partly supersedes OPC scope
    "IS 8112": "IS 12269", # 53 grade is stronger version
}


class StandardsGraph:
    def __init__(self):
        self.G = nx.Graph()
        self.standards_map: dict[str, dict] = {}  # id -> full record

    def build(self, standards: list[dict]) -> None:
        print(f"[Graph] Building graph with {len(standards)} standards ...")

        # Add all nodes first
        for std in standards:
            sid = std["standard_id"]
            self.standards_map[sid] = std
            self.G.add_node(
                sid,
                title=std.get("title", ""),
                category=std.get("material_category", "Other"),
                applications=std.get("applications", []),
                keywords=std.get("keywords", []),
                year=std.get("year"),
            )

        # Edge type 1: Explicit cross-references in text
        for std in standards:
            sid = std["standard_id"]
            for ref in std.get("related_standards", []):
                if ref in self.standards_map and ref != sid:
                    if self.G.has_edge(sid, ref):
                        self.G[sid][ref]["weight"] = min(
                            1.0, self.G[sid][ref]["weight"] + EDGE_WEIGHTS["cross_reference"]
                        )
                    else:
                        self.G.add_edge(sid, ref, weight=EDGE_WEIGHTS["cross_reference"], relation="cross_reference")

        # Edge type 2: Same material category
        category_groups: dict[str, list[str]] = defaultdict(list)
        for std in standards:
            cat = std.get("material_category", "Other")
            if cat != "Other":
                category_groups[cat].append(std["standard_id"])

        for cat, members in category_groups.items():
            for i, a in enumerate(members):
                for b in members[i + 1:]:
                    if not self.G.has_edge(a, b):
                        self.G.add_edge(a, b, weight=EDGE_WEIGHTS["same_category"], relation="same_category")
                    # Don't override stronger cross_reference edges

        # Edge type 3: Application overlap
        app_groups: dict[str, list[str]] = defaultdict(list)
        for std in standards:
            for app in std.get("applications", []):
                app_groups[app].append(std["standard_id"])

        for app, members in app_groups.items():
            for i, a in enumerate(members):
                for b in members[i + 1:]:
                    if not self.G.has_edge(a, b):
                        self.G.add_edge(a, b, weight=EDGE_WEIGHTS["same_application"], relation="same_application")

        # Edge type 4: Keyword overlap (top keywords only)
        for i, std_a in enumerate(standards):
            kw_a = set(std_a.get("keywords", []))
            if not kw_a:
                continue
            for std_b in standards[i + 1:]:
                kw_b = set(std_b.get("keywords", []))
                overlap = len(kw_a & kw_b)
                if overlap >= 3:
                    sid_a, sid_b = std_a["standard_id"], std_b["standard_id"]
                    if not self.G.has_edge(sid_a, sid_b):
                        weight = min(EDGE_WEIGHTS["keyword_overlap"] * overlap / 5, EDGE_WEIGHTS["keyword_overlap"])
                        self.G.add_edge(sid_a, sid_b, weight=weight, relation="keyword_overlap")

        print(f"[Graph] Nodes: {self.G.number_of_nodes()}, Edges: {self.G.number_of_edges()}")

    def get_neighbors(self, standard_id: str, top_k: int = 5) -> list[dict]:
        """
        Given a standard ID, return its most strongly connected neighbors.
        This is what expands retrieval results beyond pure vector search.
        """
        if standard_id not in self.G:
            return []

        neighbors = []
        for neighbor in self.G.neighbors(standard_id):
            edge = self.G[standard_id][neighbor]
            neighbors.append({
                "standard_id": neighbor,
                "weight": edge.get("weight", 0),
                "relation": edge.get("relation", "unknown"),
                **self.standards_map.get(neighbor, {}),
            })

        neighbors.sort(key=lambda x: x["weight"], reverse=True)
        return neighbors[:top_k]

    def expand_results(self, initial_results: list[dict], top_k: int = 5) -> list[dict]:
        """
        Given a list of retrieved standards, expand them using graph neighbors.
        Deduplicates and re-ranks by combined retrieval score + graph weight.
        """
        seen = set()
        expanded = []

        for result in initial_results:
            sid = result.get("standard_id")
            if sid and sid not in seen:
                seen.add(sid)
                result["source"] = "vector_retrieval"
                expanded.append(result)

            # Pull in graph neighbors
            for neighbor in self.get_neighbors(sid, top_k=3):
                nid = neighbor["standard_id"]
                if nid not in seen:
                    seen.add(nid)
                    # Graph-expanded results get slightly lower score
                    neighbor["retrieval_score"] = result.get("retrieval_score", 0.5) * neighbor["weight"]
                    neighbor["source"] = "graph_expansion"
                    expanded.append(neighbor)

        # Re-rank: vector score * 0.7 + graph proximity * 0.3
        expanded.sort(key=lambda x: x.get("retrieval_score", 0), reverse=True)
        return expanded[:top_k]

    def get_standard(self, standard_id: str) -> Optional[dict]:
        return self.standards_map.get(standard_id)

    def get_all_standards(self) -> list[dict]:
        return list(self.standards_map.values())

    def save(self, path: str) -> None:
        data = {
            "graph": nx.node_link_data(self.G),
            "standards_map": self.standards_map,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        print(f"[Graph] Saved to {path}")

    @classmethod
    def load(cls, path: str) -> "StandardsGraph":
        with open(path, "rb") as f:
            data = pickle.load(f)
        sg = cls()
        sg.G = nx.node_link_graph(data["graph"])
        sg.standards_map = data["standards_map"]
        print(f"[Graph] Loaded: {sg.G.number_of_nodes()} nodes, {sg.G.number_of_edges()} edges")
        return sg

    def category_subgraph(self, category: str) -> list[str]:
        """Return all standard IDs in a given material category."""
        return [
            n for n, d in self.G.nodes(data=True)
            if d.get("category") == category
        ]


if __name__ == "__main__":
    import sys
    standards_path = sys.argv[1] if len(sys.argv) > 1 else "data/standards.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "data/graph.pkl"

    with open(standards_path) as f:
        standards = json.load(f)

    sg = StandardsGraph()
    sg.build(standards)
    sg.save(output_path)
    print(f"[Graph] Done. Saved graph to {output_path}")
