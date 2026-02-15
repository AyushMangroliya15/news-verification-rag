# Architecture Diagram - Mermaid Code

## Complete System Architecture

```mermaid
graph TB
    subgraph "API Layer"
        API[FastAPI Server]
        EP1[POST verify]
        EP2[GET health]
        EP3[GET status]
        API --> EP1
        API --> EP2
        API --> EP3
    end

    subgraph "Claim Processing"
        CI[Claim Intake]
        VAL[Validate]
        NORM[Normalize]
        CI --> VAL
        CI --> NORM
    end

    subgraph "Orchestrator - Agentic Loop"
        ORCH[Orchestrator]
        MERGE[Merge & Dedupe]
        LOOP{Iteration Loop<br/>Max 3 iterations}
        ORCH --> LOOP
        LOOP --> MERGE
    end

    subgraph "Evidence Gathering"
        WEB[Web Agent]
        RAG[RAG Agent]
        SP[Search Planner]
        TC[Tavily Client]
        VS[Vector Store<br/>ChromaDB]
        EMB[Embeddings<br/>OpenAI]
        
        SP --> WEB
        WEB --> TC
        RAG --> VS
        VS --> EMB
    end

    subgraph "Evidence Processing"
        RERANK[Reranker<br/>Cross-Encoder]
        EVAL[Evidence Evaluator]
        STANCE[Stance Classification<br/>LLM Batch]
        SUFF[Sufficiency Check]
        CONFLICT[Conflict Detection]
        
        RERANK --> EVAL
        EVAL --> STANCE
        EVAL --> SUFF
        EVAL --> CONFLICT
    end

    subgraph "Verdict Formation"
        VF[Verdict Former]
        DECIDE[Verdict Decision]
        REASON[Reasoning Generation<br/>LLM]
        CRED[Source Credibility<br/>Domain Filter]
        VALID[Validation Rules]
        
        VF --> DECIDE
        VF --> REASON
        VF --> CRED
        VF --> VALID
    end

    subgraph "Supporting Services"
        URL_UTIL[URL Utils<br/>Homepage Detection]
        KB_REFRESH[KB Refresh Job<br/>Cron]
    end

    EP1 --> CI
    VAL --> ORCH
    LOOP --> WEB
    LOOP --> RAG
    MERGE --> RERANK
    CONFLICT --> VF
    VF --> API

    style API fill:#e1f5ff
    style ORCH fill:#fff4e1
    style WEB fill:#e8f5e9
    style RAG fill:#e8f5e9
    style RERANK fill:#f3e5f5
    style VF fill:#ffe1f5
    style VS fill:#fff9e1
```

## Evidence Flow Diagram

```mermaid
flowchart LR
    subgraph "Input"
        CLAIM[Claim Text]
    end
    
    subgraph "Evidence Sources"
        TAVILY[Tavily API<br/>Live Web Search]
        CHROMA[ChromaDB<br/>Knowledge Base]
    end
    
    subgraph "Processing"
        MERGE[Merge &<br/>Dedupe]
        RERANK[Rerank<br/>Hybrid Score]
        STANCE[Stance<br/>Classification]
    end
    
    subgraph "Output"
        VERDICT[Verdict]
        CITATIONS[Citations]
    end
    
    CLAIM --> TAVILY
    CLAIM --> CHROMA
    TAVILY --> MERGE
    CHROMA --> MERGE
    MERGE --> RERANK
    RERANK --> STANCE
    STANCE --> VERDICT
    STANCE --> CITATIONS
    
    style CLAIM fill:#e1f5ff
    style TAVILY fill:#e8f5e9
    style CHROMA fill:#fff9e1
    style VERDICT fill:#ffe1f5
    style CITATIONS fill:#f3e5f5
```

