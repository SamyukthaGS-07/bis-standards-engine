# BIS Standards Recommendation Engine
 
> Graph-Augmented RAG for instant BIS SP 21 compliance — built for the BIS × SS Hackathon.
 
**Team TARS** — Samyuktha G S · Shri Nithee V · Abiranjana S
 
---
 
## Evaluation Results (Public Test Set)
 
| Metric | Score | Target | Status |
|---|---|---|---|
| **Hit Rate @3** | **100%** | >80% | ✅ Exceeds |
| **MRR @5** | **1.000** | >0.70 | ✅ Perfect |
| **Avg Latency** | **0.25s** | <5.0s | ✅ 20× faster |
 
All 10 public test queries returned the correct standard at **Rank #1**.
Evaluated using the official `eval_script.py` provided by organizers.
 
---
 
## What makes this different
 
Most RAG systems treat the BIS SP 21 PDF like a novel — random text chunks, flat vector search, hope for the best.
 
This system treats SP 21 like what it actually is: a **structured standards ontology**.
 
| Other Systems | This System |
|---|---|
| Random PDF chunking | Structured record extraction per standard |
| Flat vector search | Semantic + BM25 hybrid (RRF fusion) |
| LLM picks standards | LLM only writes explanations — never selects |
| Hope for no hallucinations | Architecturally impossible to hallucinate |
| No domain awareness | Knowledge graph of inter-standard relationships |
 
---
 
## Architecture
 
```
Product Description (input)
        │
        ▼
┌──────────────────────┐
│  Query Understanding │  ← Detects material category, application type
└─────────┬────────────┘
          │
    ┌─────┴──────┐
    │            │
    ▼            ▼
Semantic      BM25 Keyword
Search        Search
(ChromaDB)    (rank-bm25)
    │            │
    └─────┬──────┘
          │
          ▼
  ┌───────────────┐
  │  RRF Fusion   │  ← Reciprocal Rank Fusion
  └───────┬───────┘
          │
          ▼
  ┌───────────────┐
  │ Graph Expand  │  ← Surfaces related standards via knowledge graph
  └───────┬───────┘
          │
          ▼
  ┌───────────────┐
  │ LLM Rationale │  ← Writes explanation ONLY — never selects standards
  └───────┬───────┘
          │
          ▼
  Top 3–5 Standards + Explanation (output)
```
 
**Key numbers:** 577 standards indexed · 51,823 knowledge graph edges · 0.25s avg query time
 
---
 
## Setup
 
### 1. Clone and install
 
```bash
git clone https://github.com/SamyukthaGS-07/bis-standards-engine
cd bis-standards-engine
pip install -r requirements.txt
```
 
### 2. Set environment variables
 
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (free at console.groq.com)
```
 
### 3. Run setup (parse PDF + build graph + index)
 
Place `BIS_SP21.pdf` in the project root, then:
 
```bash
python setup.py --pdf BIS_SP21.pdf
```
 
This runs once (~10-15 minutes). It produces:
- `data/standards.json` — 577 structured standard records
- `data/graph.pkl` — knowledge graph (577 nodes, 51,823 edges)
- `data/chroma_db/` — ChromaDB vector index
### 4. Start the API
 
```bash
uvicorn src.api.app:app --reload --port 8000
```
 
### 5. Start the UI
 
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```
 
---
 
## Running inference (for judges)
 
```bash
python inference.py --input hidden_private_dataset.json --output team_results.json
```
 
Output format (strict JSON schema):
 
```json
[
  {
    "id": "query_001",
    "retrieved_standards": ["IS 269: 1989", "IS 8112: 1989", "IS 12269: 1987"],
    "latency_seconds": 0.25
  }
]
```
 
---
 
## Running the public test evaluation
 
```bash
python inference.py --input data/public_test_set.json --output data/public_results.json
python merge_results.py
python eval_script.py --results data/eval_ready.json
```
 
---
 
## Environment variables
 
| Variable | Description | Default |
|---|---|---|
| `GRAPH_PATH` | Path to graph.pkl | `data/graph.pkl` |
| `CHROMA_PATH` | Path to ChromaDB directory | `data/chroma_db` |
| `LLM_PROVIDER` | `groq` or `openai` | `groq` |
| `GROQ_API_KEY` | Your Groq API key (free at console.groq.com) | — |
| `OPENAI_API_KEY` | Your OpenAI API key (optional fallback) | — |
 
---
 
## API Endpoints
 
| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Engine status + standards count |
| `/recommend` | POST | Main recommendation endpoint |
| `/standards/{id}` | GET | Full details for a single standard |
| `/categories` | GET | All material categories with counts |
 
---
 
## Tech stack
 
| Component | Tech |
|---|---|
| PDF Parsing | pdfplumber |
| Embeddings | BAAI/bge-small-en-v1.5 (sentence-transformers) |
| Vector DB | ChromaDB |
| Sparse Search | rank-bm25 (BM25Okapi) |
| Knowledge Graph | NetworkX |
| LLM | Groq (llama-3.1-8b-instant) — free, <1s latency |
| API | FastAPI |
| Frontend | React + Vite + Framer Motion |
 
No GPU required. Runs on any consumer laptop.
 
---
 
## Project structure
 
```
bis-standards-engine/
├── inference.py              ← Judge entry point (DO NOT RENAME)
├── setup.py                  ← One-command setup
├── eval_script.py            ← Organizer evaluation script
├── merge_results.py          ← Merges output with expected for eval
├── requirements.txt
├── .env.example
├── presentation.pdf          ← Slide deck
├── src/
│   ├── parser/parse_sp21.py          ← PDF to structured JSON
│   ├── graph/standards_graph.py      ← Knowledge graph builder
│   ├── retriever/hybrid_retriever.py ← BM25 + semantic + graph fusion
│   ├── llm/rationale_generator.py    ← Explanation-only LLM
│   └── api/app.py                    ← FastAPI server
├── data/
│   ├── public_test_set.json          ← Public test queries
│   ├── public_results.json           ← Our results on public test set
│   └── eval_ready.json               ← Merged eval input
└── frontend/                         ← React + Vite UI
```
 
---
 
## Team TARS

Samyuktha G S • Shri Nithee V • Abiranjana S

Built for the BIS × SS Hackathon — May 2026.
Dataset: BIS SP 21 (Summaries of Indian Standards for Building Materials)
