# News Claim Verification System - Architecture Documentation

## System Overview

A hybrid RAG + agentic fact-checking system that verifies news claims by gathering evidence from both live web search (Tavily) and a knowledge base (ChromaDB), then uses LLM-based evaluation to produce verdicts with citations.

## Architecture Diagram

- [Complete system architecture link](https://mermaid.live/view#pako:eNqNVmtv4jgU_StWVppPbZd3CxqNBCFQtryUUEZaMxqZ5AashgQ5TjVM1f--1zZQZ2GrRQKRe_w49_jc67w5YRaB03E2gu23ZNFbpQQ_ebE2gZXTnY_ImB1ArByDqQ8G6YDlUoEBiFcQPz5Ab16l81mwIBjm8aGE1OjQW5AtsERuS0BdA7lkssh_lDYit7ff1JrXgrVrwboJQhqt0ot03ITxHZmLLIQ85-nGzsodUQOPUslewKKx7I7pkiU8YtIOT2f-hE4zsUPotw24hgtOu4ipOZ8RnIlwC7kUTGaC3JLuBlLJQzLOsr3Ndea7j9Qea-0-8fyhRycgNkC-kD5Exd4mN57N5m8jCTiNZ6le-eta_Pltwn6ROuEnIH8v76bZq7nllXRY7_hZVt4rjyANgQyZ3KItysJ_93r0O6xNshZTvzuk-L2IB3MaAMPkyTxhaVpy38KlC_bKkwNxE16etgzoEkKla4A_oJN2tyLbsX7PNuOkR73dGqIIaeZ61GwPaXdkjbG5aAUwhVI-OrhwS7kYTwQ2IWPZSe9_aXfdtb7nd6dP1MdjS19AmKxElue3XqqKu1Saysjn9bxXlhT_8k6w6E5djwaSqRFYDrhfzEPtCL30eDwhPSZDu3yD58GABkWMA1HyEKXfQvhi18NsOhiP3AV1szROeCjRlRKPAhe9KqrJyYhTKiL1pMOG5zUAuVwJnxh8JvQSRKS4DVRFK262zMsBtfGSrH3PHfW9M96HkOfl1HyvG8ymeEgsz1I8QDKE9FhnJ1VtuXyvT4OsEOoIBER8zRMuD3pkH-3KUzLgiSxxwERH_VOTUnXtFwnkV9VdDrQkhvVF2FC9CCtOF0G96WeSBsV-nwmpMlb3BEf_2qI---Ofz4vRmOIf8ix5YsrtMdvBnmH3uuaSp95P3xv4XvBIn3rEh1hAviV_ZeuT80-DLUZ4fZgkRub55ArV10zk3MrOhXyOYOWaiO5yR42UP0305CwjyNF7R33wUjqLIg8J6Fsq5knS-QOqcTOObUw3WQPGcdyAqg2qlnKc-BA3oW1jqrX8J2Yq6bhsHZpx04aR52lHRagEBR9k2lB1bvAdgUdOJ2ZJDjcOVgAaEZ-dNzVr5WBf38HK6eDfiIkXdczvOGnP0r-zbOd0pChwmsiKzfa8SLFXN2qfM_TLxxA8OBBuVqTS6dSqTb2G03lzfjmdeqtxV2081GuVWqPWbjYebpwDDqq07tr3zYdqpdZq1tv1ysP7jfNb71q5a9Vb1ep9s9luVNrt1v39jYMFhU1vYl589PvP-z9VLJLn)

- [Evidence flow diagram](https://mermaid.live/view#pako:eNqFVF1vmzAU_SvIk_aUdiGEkKCpEiVoRc1HRVCmjfTBgUuwCjgyJm0W5b_PsWlG0knl6XLuucfHx5YPKKYJIBulOX2NM8y4NglWpSa-ql5vGN5m2gr55bbmK6Tw0-dOHH8auTkmhRbCG39WLSgTVXxQ8HYkgTIGbUFrFkPVFgudpT_5FYV4R_K95jz539fs292E7ED7CWttAZjF2XNr8YdgPnUiN2O0wON7yX4s6WsOyQa0e1zBp3aeGBUmKlJu2kamXvDDi6bAhMxXKTuGpN5Ca-3AC5zZYxQAw-WLpDzs14wk2iKmrE1chM7M9aIFx2LXkijSEiumJMac0PJTi_OaX4W-9IKx74bRElhCYt5OxA-d0J_PFpFLuJSv_q8vz027ublrQr9GVbQKVQwJy2AarmRco7KUoApIoaqWsIpDwaqWcLOlD_h5Qxfh8H0OjdmU5Ln9BfTUTNN2tzHdtIepCaOLYeVetdM0HYHebjd2zv2T_sX4u613hgFmaqIO2ogrgOwU5xV0UAGswKd_dDgNrxDPoIAVskWZYPZyOtOjGNri8jelBbI5q8UYo_UmO4vU2wRzGBMs7sM_ijhOYC6tS45sUyog-4DekG3o_VtTt_SuPhgN-5ZpDTpoj2zdsASsj0zL6A77en_UP3bQH7lo97ZnDSzDHIyMnj4wesZQCEJCOGVT9STIl-H4Fw1BNSc)

## Component Details

### 1. API Layer (`main.py`)
- **FastAPI Server**: RESTful API for browser extension
- **Endpoints**:
  - `POST /verify`: Main verification endpoint
  - `GET /health`: Health check
  - `GET /status`: System status

### 2. Claim Intake (`claim_intake.py`)
- **Normalize**: Unicode normalization, whitespace collapse
- **Validate**: Length checks (max 2000 chars), non-empty validation
- Ensures consistent input format before processing

### 3. Orchestrator (`orchestrator.py`)
- **Core Loop**: Agentic iteration (max 3 attempts)
- **Evidence Gathering**: Parallel WEB + RAG retrieval
- **Merge & Dedupe**: Combines evidence, removes duplicates by URL, filters homepages
- **Adaptive Refinement**: Increases `top_k` and switches to current-affairs-only if insufficient evidence
- **Early Exit**: Stops when sufficient evidence found with no conflicts

### 4. Evidence Gathering

#### 4.1 Web Agent (`web_agent.py`)
- Uses **Search Planner** to generate 2-4 optimized queries
- Calls **Tavily API** for live web search
- Returns article-specific URLs with snippets
- Deduplicates by URL

#### 4.2 Search Planner (`search_planner.py`)
- **Query Generation**: Creates multiple search variants
  - Quoted key phrases for specificity
  - Fact-check framing
  - Debunk queries for refuting evidence
- **Key Phrase Extraction**: Identifies important terms (quoted phrases, capitalized entities)

#### 4.3 RAG Agent (`rag_agent.py`)
- **Vector Retrieval**: Queries ChromaDB using semantic similarity
- **Collections**:
  - `current_affairs_24h`: Recent news (refreshed daily)
  - `static_gk`: General knowledge (static)
- **Embedding**: Uses OpenAI embeddings for query encoding
- Supports current-affairs-only mode for recent claims

#### 4.4 Tavily Client (`tavily_client.py`)
- **API Integration**: Tavily search API (optimized for AI/LLM)
- **Features**: Article-specific URLs, high relevance, timeout handling
- Returns structured results: title, URL, snippet

#### 4.5 Vector Store (`vector_store.py`)
- **ChromaDB**: Persistent vector database
- **Operations**: Query by embedding, add documents, clone collections
- **Metadata**: Stores URL, title, snippet, source, date

#### 4.6 Embeddings (`embeddings.py`)
- **OpenAI Embeddings**: Wrapper for text-embedding-3-small
- Batch processing support
- Used for both RAG queries and KB refresh

### 5. Evidence Processing

#### 5.1 Reranker (`reranker.py`)
- **Hybrid Scoring**: Combines three signals
  - **Semantic Relevance** (70%): Cross-encoder model (ms-marco-MiniLM-L-6-v2)
  - **URL Quality** (20%): Article-specific vs homepage detection
  - **Source Preference** (10%): Tavily > RAG
- **Diversity**: Limits to 2 results per domain
- **Homepage Filtering**: Removes low-quality URLs before reranking

#### 5.2 Evidence Evaluator (`evidence_evaluator.py`)
- **Stance Classification**: LLM batch processing (supports/refutes/neutral)
- **Sufficiency Check**: Validates minimum evidence count
- **Conflict Detection**: Identifies contradictory evidence
- Uses OpenAI for batch stance classification (up to 30 items)

### 6. Verdict Formation

#### 6.1 Verdict Former (`verdict_former.py`)
- **Verdict Decision**: Rule-based from evidence state
  - Not Enough Evidence: insufficient or no evidence
  - Mixed/Disputed: conflicting stances
  - Supported: only supporting evidence
  - Refuted: only refuting evidence
- **Reasoning Generation**: LLM-generated explanation (2-4 sentences)
- **Citation Processing**: Converts evidence to citations, applies credibility filter

#### 6.2 Source Credibility (`source_credibility.py`)
- **Domain Filtering**: Allows only credible domains (configurable allowlist)
- **Fallback Logic**: Uses all citations if credible filter too restrictive (<3 or <30% of total)
- **Default Domains**: Reuters, AP, BBC, NYT, Snopes, Wikipedia, Britannica, etc.

#### 6.3 Validation Rules (`validation_rules.py`)
- **Citation Validation**: Ensures citations match evidence URLs
- **Minimum Sources**: Requires min sources for Supported/Refuted verdicts
- **Safety**: Downgrades to "Not Enough Evidence" if insufficient citations

### 7. Supporting Services

#### 7.1 URL Utils (`url_utils.py`)
- **Homepage Detection**: Identifies category/homepage URLs vs article URLs
- **Pattern Matching**: Recognizes common homepage patterns
- Used by reranker and merge logic

#### 7.2 KB Refresh Job (`jobs/refresh_kb.py`)
- **Scheduled Task**: Runs daily via cron
- **Process**:
  1. Fetches current affairs from Tavily using diverse queries
  2. Chunks content (sentence-aware, 512 chars, 100 overlap)
  3. Embeds in batches
  4. Stores in temp collection
  5. Atomically swaps to live collection
- **Credible-First**: Prioritizes credible domains in results

## Data Flow

### Verification Flow

1. **Request**: User submits claim via `/verify`
2. **Intake**: Claim normalized and validated
3. **Orchestration Loop** (max 3 iterations):
   - **Gather Evidence**:
     - Web Agent: Search Planner → Tavily → Evidence Items
     - RAG Agent: Embed claim → Vector Store → Evidence Items
   - **Merge**: Combine, dedupe by URL, filter homepages
   - **Rerank**: Hybrid scoring, diversity filtering
   - **Evaluate**: Attach stances, check sufficiency, detect conflicts
   - **Early Exit**: If sufficient and no conflict, break
   - **Refine**: Increase top_k, switch to current-affairs-only
4. **Form Verdict**:
   - Decide verdict from evidence state
   - Generate reasoning via LLM
   - Filter citations by credibility
   - Apply validation rules
5. **Response**: Return verdict, reasoning, citations

### KB Refresh Flow

1. **Query Generation**: Use default or configured queries
2. **Tavily Search**: Fetch top results per query
3. **Credible Prioritization**: Sort by domain credibility
4. **Chunking**: Split content into overlapping chunks
5. **Embedding**: Batch embed chunks
6. **Storage**: Write to temp collection
7. **Atomic Swap**: Clone temp → live, delete temp

## Key Design Decisions

1. **Hybrid Evidence**: Combines live web (Tavily) + knowledge base (RAG) for comprehensive coverage
2. **Agentic Loop**: Iterative refinement when initial evidence insufficient
3. **Hybrid Reranking**: Multi-signal scoring (relevance + quality + source)
4. **Credibility Filtering**: Smart fallback to preserve evidence diversity
5. **Atomic KB Updates**: Safe collection swapping prevents downtime
7. **Homepage Filtering**: Removes low-quality category pages
8. **Diversity**: Limits results per domain for better coverage

## Technology Stack

- **Framework**: FastAPI
- **Vector DB**: ChromaDB (persistent)
- **Embeddings**: OpenAI (text-embedding-3-small)
- **LLM**: OpenAI (gpt-4o-mini)
- **Reranker**: Sentence Transformers (CrossEncoder)
- **Web Search**: Tavily API
- **Storage**: File-based (ChromaDB)

## Configuration

Key configurable parameters (via environment variables):
- `AGENTIC_LOOP_MAX_ITER`: Max iterations (default: 3)
- `RAG_TOP_K`: Initial RAG retrieval count (default: 10)
- `RERANK_TOP_K`: Top results after reranking (default: 25)
- `CREDIBLE_DOMAINS`: Domain allowlist (comma-separated)
- `TAVILY_API_KEY`: Tavily API key
- `OPENAI_API_KEY`: OpenAI API key

