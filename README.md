# News Claim Verification System

A hybrid RAG + agentic fact-checking system that verifies news claims by gathering evidence from both live web search (Tavily) and a knowledge base (ChromaDB), then uses LLM-based evaluation to produce verdicts with citations.

## Features

- **Dual Evidence Sources**: Combines live web search (Tavily) with knowledge base (ChromaDB)
- **Claim Decomposition**: LLM-based extraction of sub-claims for any claim above a small length threshold; when the LLM returns 2+ sub-claims they are verified separately and aggregated into one verdict with optional per–sub-claim breakdown
- **Agentic Loop**: Iterative refinement (max 3 attempts) when evidence is insufficient
- **Hybrid Reranking**: Multi-signal scoring (semantic relevance + URL quality + source preference)
- **LLM Evaluation**: Batch stance classification and reasoning generation
- **Credibility Filtering**: Smart domain-based citation filtering with fallback
- **RESTful API**: FastAPI-based endpoints for browser extension integration

## Prerequisites

- Python 3.10+
- OpenAI API key
- Tavily API key

## Installation

1. Clone the repository and navigate to the project directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the `backend/` directory with the following variables:

```env
# Required API Keys
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Optional Configuration
OPENAI_LLM_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RAG_TOP_K=10
RERANK_TOP_K=25
AGENTIC_LOOP_MAX_ITER=3
CLAIM_MAX_LENGTH=2000
MIN_SOURCES_FOR_VERDICT=1

# Claim decomposition (LLM extracts sub-claims; min length skips LLM for trivial input)
DECOMPOSE_ENABLED=true
DECOMPOSE_MIN_CLAIM_LENGTH=20
DECOMPOSE_MAX_SUBCLAIMS=5
DECOMPOSE_USE_LLM=true

# Credible Domains (comma-separated, optional)
# If not set, uses default list (Reuters, BBC, NYT, Snopes, Wikipedia, etc.)
CREDIBLE_DOMAINS=reuters.com,bbc.com,nytimes.com,snopes.com
```

## Running the Server

Start the FastAPI server:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## API Endpoints

### `POST /verify`
Verify a news claim.

**Request:**
```json
{
  "claim": "Tug of war was in the Olympics from 1900 to 1920."
}
```

**Response (single claim or after aggregation):**
```json
{
  "verdict": "Supported",
  "reasoning": "Multiple sources confirm that tug of war was an Olympic event...",
  "citations": [
    {
      "title": "1900 Summer Olympics - Wikipedia",
      "url": "https://en.wikipedia.org/wiki/1900_Summer_Olympics",
      "snippet": "Tug of war was contested at the 1900, 1904, 1908, 1912, and 1920 Olympics."
    }
  ],
  "sub_results": []
}
```

When the LLM extracts **multiple sub-claims** (claim length ≥ `DECOMPOSE_MIN_CLAIM_LENGTH`, default 20), the response includes **`sub_results`**: an array of per–sub-claim results, each with `claim`, `verdict`, `reasoning`, and `citations`. The browser extension uses this to show a "Breakdown by sub-claim" section. The min length is only to avoid calling the LLM for trivial one-word input.

**Verdict Types:**
- `Supported`: Evidence supports the claim
- `Refuted`: Evidence contradicts the claim
- `Not Enough Evidence`: Insufficient evidence to determine
- `Mixed / Disputed`: Conflicting evidence found
- `Unverifiable`: Claim cannot be verified

### `GET /health`
Health check endpoint.

### `GET /status`
System status including configured search provider.

## Knowledge Base Refresh

Refresh the knowledge base with current affairs (run daily via cron):

```bash
cd backend
python -m backend.jobs.refresh_kb
```

This job:
- Fetches current affairs from Tavily using diverse queries
- Chunks and embeds content
- Updates ChromaDB collections atomically

## Project Structure

```
backend/
├── main.py                 # FastAPI application
├── config.py               # Configuration from environment
├── constants.py            # Constants and enums
├── models.py               # Data models
├── services/               # Core services
│   ├── orchestrator.py     # Verification pipeline with optional decomposition
│   ├── claim_decomposer.py # LLM-based extraction of sub-claims (or rules when LLM disabled)
│   ├── verdict_aggregator.py # Aggregates sub-claim results into one verdict and sub_results
│   ├── web_agent.py        # Tavily web search
│   ├── rag_agent.py        # ChromaDB retrieval
│   ├── reranker.py         # Evidence reranking
│   ├── evidence_evaluator.py  # Stance classification
│   ├── verdict_former.py   # Verdict formation
│   └── ...
├── jobs/
│   └── refresh_kb.py       # KB refresh job
└── chroma_data/           # ChromaDB persistent storage
```

## Technology Stack

- **Framework**: FastAPI
- **Vector DB**: ChromaDB
- **Embeddings**: OpenAI (text-embedding-3-small)
- **LLM**: OpenAI (gpt-4o-mini)
- **Reranker**: Sentence Transformers (CrossEncoder)
- **Web Search**: Tavily API

## Architecture

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md)

