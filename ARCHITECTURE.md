# News Claim Verification System - Architecture Documentation

## System Overview

A hybrid RAG + agentic fact-checking system that verifies news claims by gathering evidence from both live web search (Tavily) and a knowledge base (ChromaDB), then uses LLM-based evaluation to produce verdicts with citations.

## Architecture Diagram

See [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) for detailed diagrams:

- [Complete System Architecture](ARCHITECTURE_DIAGRAM.md#complete-system-architecture)
- [Evidence Flow Diagram](ARCHITECTURE_DIAGRAM.md#evidence-flow-diagram)

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

### 3. Claim Decomposer (`claim_decomposer.py`)
- **Purpose**: LLM-based extraction of sub-claims for separate verification. The LLM is asked to extract sub-claims for any claim whose length is at least `DECOMPOSE_MIN_CLAIM_LENGTH` (default 20). The min length is only to avoid calling the LLM for trivial one-word input; short-but-composite claims (e.g. two claims in one sentence) can be decomposed.
- **LLM Mode** (default): Asks the LLM to list distinct factual claims as a JSON array; parses and caps at `DECOMPOSE_MAX_SUBCLAIMS`
- **Rules Fallback**: When `DECOMPOSE_USE_LLM` is false, splits on sentence boundaries or conjunctions (e.g. " and ", ", ")
- **Output**: Returns `[claim]` (no decomposition) when disabled, claim below min length, or when LLM returns 0–1 sub-claims or on error; otherwise returns list of sub-claim strings

### 4. Orchestrator (`orchestrator.py`)
- **Entry Point**: `run_verification_with_decomposition(claim)` — calls decomposer, then either single-claim pipeline or per–sub-claim verification + aggregation
- **Single Sub-claim**: When the decomposer returns one sub-claim (whether input was short or long), runs `run_verification(claim)` once (no `sub_results` in response)
- **Multiple Sub-claims**: When the decomposer returns 2+ sub-claims, runs `run_verification` per sub-claim, then **Verdict Aggregator**; response includes `sub_results` for UI breakdown
- **Core Loop** (per claim): Agentic iteration (max 3 attempts), WEB + RAG retrieval, merge & dedupe, rerank, stance/sufficiency/conflict, verdict formation
- **Adaptive Refinement**: Increases `top_k` and switches to current-affairs-only if insufficient evidence
- **Early Exit**: Stops when sufficient evidence found with no conflicts

### 5. Evidence Gathering

#### 5.1 Web Agent (`web_agent.py`)
- Uses **Search Planner** to generate 2-4 optimized queries
- Calls **Tavily API** for live web search
- Returns article-specific URLs with snippets
- Deduplicates by URL

#### 5.2 Search Planner (`search_planner.py`)
- **Query Generation**: Creates multiple search variants
  - Quoted key phrases for specificity
  - Fact-check framing
  - Debunk queries for refuting evidence
- **Key Phrase Extraction**: Identifies important terms (quoted phrases, capitalized entities)

#### 5.3 RAG Agent (`rag_agent.py`)
- **Vector Retrieval**: Queries ChromaDB using semantic similarity
- **Collections**:
  - `current_affairs_24h`: Recent news (refreshed daily)
  - `static_gk`: General knowledge (static)
- **Embedding**: Uses OpenAI embeddings for query encoding
- Supports current-affairs-only mode for recent claims

#### 5.4 Tavily Client (`tavily_client.py`)
- **API Integration**: Tavily search API (optimized for AI/LLM)
- **Features**: Article-specific URLs, high relevance, timeout handling
- Returns structured results: title, URL, snippet

#### 5.5 Vector Store (`vector_store.py`)
- **ChromaDB**: Persistent vector database
- **Operations**: Query by embedding, add documents, clone collections
- **Metadata**: Stores URL, title, snippet, source, date

#### 5.6 Embeddings (`embeddings.py`)
- **OpenAI Embeddings**: Wrapper for text-embedding-3-small
- Batch processing support
- Used for both RAG queries and KB refresh

### 6. Evidence Processing

#### 6.1 Reranker (`reranker.py`)
- **Hybrid Scoring**: Combines three signals
  - **Semantic Relevance** (70%): Cross-encoder model (ms-marco-MiniLM-L-6-v2)
  - **URL Quality** (20%): Article-specific vs homepage detection
  - **Source Preference** (10%): Tavily > RAG
- **Diversity**: Limits to 2 results per domain
- **Homepage Filtering**: Removes low-quality URLs before reranking

#### 6.2 Evidence Evaluator (`evidence_evaluator.py`)
- **Stance Classification**: LLM batch processing (supports/refutes/neutral)
- **Sufficiency Check**: Validates minimum evidence count
- **Conflict Detection**: Identifies contradictory evidence
- Uses OpenAI for batch stance classification (up to 30 items)

### 7. Verdict Formation

#### 7.1 Verdict Former (`verdict_former.py`)
- **Verdict Decision**: Rule-based from evidence state
  - Not Enough Evidence: insufficient or no evidence
  - Mixed/Disputed: conflicting stances
  - Supported: only supporting evidence
  - Refuted: only refuting evidence
- **Reasoning Generation**: LLM-generated explanation (2-4 sentences)
- **Citation Processing**: Converts evidence to citations, applies credibility filter

#### 7.2 Source Credibility (`source_credibility.py`)
- **Domain Filtering**: Allows only credible domains (configurable allowlist)
- **Fallback Logic**: Uses all citations if credible filter too restrictive (<3 or <30% of total)
- **Default Domains**: Reuters, AP, BBC, NYT, Snopes, Wikipedia, Britannica, etc.

#### 7.3 Validation Rules (`validation_rules.py`)
- **Citation Validation**: Ensures citations match evidence URLs
- **Minimum Sources**: Requires min sources for Supported/Refuted verdicts
- **Safety**: Downgrades to "Not Enough Evidence" if insufficient citations

### 8. Verdict Aggregator (`verdict_aggregator.py`)
- **Purpose**: When a claim was decomposed, combines per–sub-claim verification results into one overall verdict, reasoning, and citation list
- **Verdict Rules** (priority order): Any Refuted → Refuted; any Mixed/Disputed → Mixed/Disputed; all Supported → Supported; all Not Enough Evidence/Unverifiable → Not Enough Evidence; else Mixed/Disputed
- **Citations**: Merge and deduplicate by URL, cap at 25
- **Reasoning**: LLM summarization of sub-results (with fallback to concatenation)
- **Output**: Adds `sub_results` array (each item: `claim`, `verdict`, `reasoning`, `citations`) for the browser extension "Breakdown by sub-claim" UI

### 9. Supporting Services

#### 9.1 URL Utils (`url_utils.py`)
- **Homepage Detection**: Identifies category/homepage URLs vs article URLs
- **Pattern Matching**: Recognizes common homepage patterns
- Used by reranker and merge logic

#### 9.2 KB Refresh Job (`jobs/refresh_kb.py`)
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
3. **Decomposition** (optional): If enabled and claim length ≥ `DECOMPOSE_MIN_CLAIM_LENGTH` (default 20), Claim Decomposer (LLM or rules) extracts sub-claims. If one sub-claim → single-claim path; if 2+ sub-claims → per–sub-claim path and aggregation.
4. **Per-claim verification** (for the single claim or each sub-claim):
   - **Orchestration Loop** (max 3 iterations):
     - **Gather Evidence**: Web Agent (Search Planner → Tavily) + RAG Agent (embed → Vector Store)
     - **Merge**: Combine, dedupe by URL, filter homepages
     - **Rerank**: Hybrid scoring, diversity filtering
     - **Evaluate**: Attach stances, check sufficiency, detect conflicts
     - **Early Exit**: If sufficient and no conflict, break
     - **Refine**: Increase top_k, switch to current-affairs-only
   - **Form Verdict**: Verdict Former (decide verdict, generate reasoning, filter citations, validation rules)
5. **Aggregation** (when decomposed): Verdict Aggregator merges sub-results into one verdict, reasoning, citations, and builds `sub_results` for the UI.
6. **Response**: Return verdict, reasoning, citations; when decomposed, include `sub_results`.

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
2. **Claim Decomposition**: LLM-based extraction of sub-claims (any claim above small min length); when 2+ sub-claims are returned they are verified separately and aggregated so one refuted part yields overall Refuted; response includes `sub_results` for UI breakdown
3. **Agentic Loop**: Iterative refinement when initial evidence insufficient
4. **Hybrid Reranking**: Multi-signal scoring (relevance + quality + source)
5. **Credibility Filtering**: Smart fallback to preserve evidence diversity
6. **Atomic KB Updates**: Safe collection swapping prevents downtime
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
- **Decomposition**: `DECOMPOSE_ENABLED` (default: true), `DECOMPOSE_MIN_CLAIM_LENGTH` (default: 20, min length to call decomposition LLM), `DECOMPOSE_MAX_SUBCLAIMS` (default: 5), `DECOMPOSE_USE_LLM` (default: true)
- **Orchestration**: `AGENTIC_LOOP_MAX_ITER` (default: 3)
- **RAG**: `RAG_TOP_K` (default: 10), `RERANK_TOP_K` (default: 25)
- **Credibility**: `CREDIBLE_DOMAINS` (comma-separated)
- **API keys**: `OPENAI_API_KEY`, `TAVILY_API_KEY`

