# BIS Standards Recommendation Engine

> Graph-Augmented RAG for instant BIS SP 21 compliance — built for the BIS × SS Hackathon.

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
┌─────────────────────┐
│  Query Understanding │  ← Detects material category, application type
└─────────┬───────────┘
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

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/bis-standards-engine
cd bis-standards-engine
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (free at console.groq.com)
```

### 3. Run setup (parse PDF + build graph + index)

```bash
python setup.py --pdf path/to/BIS_SP21.pdf
```

This runs once and takes ~2–5 minutes. It produces:
- `data/standards.json` — structured standard records
- `data/graph.pkl` — knowledge graph
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
    "retrieved_standards": ["IS 12269", "IS 269", "IS 8112"],
    "latency_seconds": 1.234
  }
]
```

---

## Running the public test evaluation

```bash
# Run inference on public test set
python inference.py --input data/public_test.json --output data/public_results.json

# Run the organizer's eval script
python eval_script.py --input data/public_test.json --output data/public_results.json
```

---

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `GRAPH_PATH` | Path to graph.pkl | `data/graph.pkl` |
| `CHROMA_PATH` | Path to ChromaDB directory | `data/chroma_db` |
| `LLM_PROVIDER` | `groq` or `openai` | `groq` |
| `GROQ_API_KEY` | Your Groq API key | — |
| `OPENAI_API_KEY` | Your OpenAI API key (if using OpenAI) | — |

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Engine status + standards count |
| `/recommend` | POST | Main recommendation endpoint |
| `/standards/{id}` | GET | Full details for a single standard |
| `/categories` | GET | All material categories with counts |

### `/recommend` request body

```json
{
  "query": "High strength OPC cement for RCC columns",
  "top_k": 5,
  "include_rationale": true
}
```

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

---

## Project structure

```
bis-standards-engine/
├── inference.py          ← Judge entry point (DO NOT RENAME)
├── setup.py              ← One-command setup
├── eval_script.py        ← Organizer evaluation script (provided at Hour 0)
├── requirements.txt
├── .env.example
├── src/
│   ├── parser/
│   │   └── parse_sp21.py       ← PDF → structured JSON
│   ├── graph/
│   │   └── standards_graph.py  ← Knowledge graph builder
│   ├── retriever/
│   │   └── hybrid_retriever.py ← BM25 + semantic + graph fusion
│   ├── llm/
│   │   └── rationale_generator.py ← Explanation-only LLM
│   └── api/
│       └── app.py              ← FastAPI server
├── data/
│   ├── standards.json    ← Parsed standards (auto-generated)
│   ├── graph.pkl         ← Knowledge graph (auto-generated)
│   └── public_results.json ← Results on public test set
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── SearchScreen.jsx
    │   │   └── ResultsScreen.jsx
    │   ├── App.jsx
    │   └── main.jsx
    └── package.json
```

---

## Team

Built for the BIS × SS Hackathon — May 2026.

Dataset: BIS SP 21 (Summaries of Indian Standards for Building Materials)
