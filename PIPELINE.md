# AML SAR Generation Pipeline — Technical Deep Dive

> **Version:** 2.0 (7-Agent Architecture)
> **Framework:** LangGraph + FastAPI + PostgreSQL/pgvector + Ollama (Mistral 7B)
> **Status:** Production-ready local system — fully offline, zero cloud dependencies

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Pipeline Data Flow](#2-pipeline-data-flow)
3. [Agent State Schema](#3-agent-state-schema)
4. [Node 1 — Ingestion Agent](#4-node-1--ingestion-agent)
5. [Node 2 — Analytics Agent + Typology Engine](#5-node-2--analytics-agent--typology-engine)
6. [Node 3 — Correlation Agent (Graph Analysis)](#6-node-3--correlation-agent-graph-analysis)
7. [Node 4 — Narrative Agent (CoT + RAG)](#7-node-4--narrative-agent-cot--rag)
8. [Node 5 — Quality Review Agent](#8-node-5--quality-review-agent)
9. [Node 6 — Compliance Agent](#9-node-6--compliance-agent)
10. [Node 7 — Audit Logger](#10-node-7--audit-logger)
11. [RAG Knowledge Base](#11-rag-knowledge-base)
12. [Typology Engine — Detection Logic](#12-typology-engine--detection-logic)
13. [LLM Integration (Ollama)](#13-llm-integration-ollama)
14. [Database Schema](#14-database-schema)
15. [API Endpoints](#15-api-endpoints)
16. [Logging & Observability](#16-logging--observability)
17. [Test Data — Synthetic Customers](#17-test-data--synthetic-customers)

---

## 1. Architecture Overview

The system implements an **agentic AI pipeline** for generating Suspicious Activity Reports (SARs). Seven specialized agents are orchestrated by **LangGraph** in a linear state machine. Each agent reads from and writes to a shared `AgentState` dictionary, creating a fully traceable chain of analysis.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FASTAPI APPLICATION                         │
│                                                                    │
│   POST /cases/{id}/run-analysis?customer_id=N                      │
│                          │                                         │
│                          ▼                                         │
│              ┌──────────────────────┐                              │
│              │  AgentOrchestrator   │ (LangGraph StateGraph)       │
│              └──────────┬───────────┘                              │
│                         │                                          │
│   ┌─────────────────────┼─────────────────────────────────┐       │
│   │                     ▼                                 │       │
│   │  ┌──────────┐  ┌──────────┐  ┌─────────────┐        │       │
│   │  │ 1.INGEST │→ │ 2.ANALYT │→ │ 3.CORRELATE │        │       │
│   │  │          │  │ +Typology│  │ (Graph)     │        │       │
│   │  └──────────┘  └──────────┘  └──────┬──────┘        │       │
│   │                                      │               │       │
│   │  ┌──────────┐  ┌──────────┐  ┌──────┴──────┐        │       │
│   │  │ 7.AUDIT  │← │ 6.COMPLY │← │ 5.QUALITY  │        │       │
│   │  │          │  │          │  │             │        │       │
│   │  └──────────┘  └──────────┘  └──────┬──────┘        │       │
│   │                                      │               │       │
│   │                               ┌──────┴──────┐        │       │
│   │                               │ 4.NARRATIVE │        │       │
│   │                               │ (3-step CoT │        │       │
│   │                               │  + RAG)     │        │       │
│   │                               └─────────────┘        │       │
│   └──────────────────────────────────────────────────────┘       │
│                                                                    │
│   External Dependencies:                                           │
│   ├── PostgreSQL + pgvector (data + embeddings)                    │
│   ├── Ollama (Mistral 7B for text, nomic-embed-text for vectors)   │
│   └── NetworkX (graph analysis)                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

| Principle | Implementation |
|-----------|---------------|
| **100% Offline** | Ollama runs locally; no API calls to OpenAI/Claude/etc. |
| **Full Traceability** | Every agent action stored in `audit_logs` + `agent_reasoning` tables |
| **Deterministic Routing** | Linear LangGraph edges — no conditional branching, predictable execution |
| **Separation of Concerns** | Each agent has exactly one responsibility |
| **Fail-Safe** | Pipeline errors caught at API level; partial results still returned |

---

## 2. Pipeline Data Flow

```
Customer ID
    │
    ▼
┌─────────────────┐
│ Load from DB    │  → accounts, transactions
│ (main.py)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌────────────────────┐
│ 1. INGESTION    │ ──→ │ Validated txn list  │
│ Validate fields │     │ ingestion_complete  │
└────────┬────────┘     └────────────────────┘
         │
         ▼
┌─────────────────┐     ┌────────────────────────────────────┐
│ 2. ANALYTICS    │ ──→ │ risk_score, anomalies,              │
│ + TypologyEngine│     │ matched_typologies [name, conf, ev] │
└────────┬────────┘     └────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────┐
│ 3. CORRELATION  │ ──→ │ graph_results (hub patterns,  │
│ (NetworkX Graph)│     │ communities, fan-out degree)  │
└────────┬────────┘     └──────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────┐
│ 4. NARRATIVE    │ ──→ │ sar_draft (3,000-5,000 chars)             │
│ 3-step CoT +   │     │ reasoning_chain [summary, reasoning, sar] │
│ RAG retrieval   │     │ rag_context [guidance, templates]         │
└────────┬────────┘     └──────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────┐
│ 5. QUALITY      │ ──→ │ quality_score (0-100)         │
│ LLM Review      │     │ quality_issues [list]         │
└────────┬────────┘     └──────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────┐
│ 6. COMPLIANCE   │ ──→ │ recommended_action            │
│ Decision logic  │     │ (FILE_SAR / ESCALATE / CLOSE) │
└────────┬────────┘     └──────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────┐
│ 7. AUDIT        │ ──→ │ audit_log_id, audit_complete  │
│ Final summary   │     │ All reasoning IDs collected   │
└─────────────────┘     └──────────────────────────────┘
```

**Total LLM calls per pipeline run:** 4–5 (1 for analytics summary, 3 for narrative CoT, 1 for quality review)
**Typical execution time:** 2–3 minutes (depends on Ollama/GPU speed)

---

## 3. Agent State Schema

All seven agents read from and write to this shared state dictionary. Defined as a `TypedDict` in `agent_orchestrator.py`:

```python
class AgentState(TypedDict):
    # ── Core identifiers ──
    case_id: str                        # UUID for this analysis run
    customer_id: int                    # Database customer ID

    # ── Data ──
    transactions: List[Dict]            # Raw transaction records

    # ── Analytics outputs ──
    analytics_results: Dict             # {risk_score, anomalies, structuring_detected}
    matched_typologies: List[Dict]      # From TypologyEngine (see §12)
    analytics_reasoning_id: int         # DB ID for stored reasoning

    # ── Graph / Correlation outputs ──
    graph_results: Dict                 # {suspicious_patterns, communities, hub_nodes}
    correlation_reasoning_id: int

    # ── RAG context ──
    rag_context: List[Dict]             # Retrieved regulatory documents

    # ── Narrative outputs ──
    sar_draft: str                      # Final SAR text (3,000-5,000 chars)
    reasoning_chain: List[Dict]         # 3-step CoT outputs
    narrative_reasoning_id: int

    # ── Quality review outputs ──
    quality_score: int                  # 0-100 score
    quality_issues: List[str]           # Issues found during review

    # ── Compliance outputs ──
    compliance_validation: Dict         # Validation results
    recommended_action: str             # FILE_SAR / ESCALATE / CLOSE

    # ── Audit ──
    risk_score: float
    reasoning_steps: List[Dict]
    data_references: List[str]
    audit_log_id: int
    ingestion_complete: bool
    audit_complete: bool
```

---

## 4. Node 1 — Ingestion Agent

**File:** `app/agents/ingestion_agent.py`
**Purpose:** Validate and sanitize incoming transaction data.
**LLM calls:** 0

### What It Does

1. Receives raw transaction list from `state["transactions"]`
2. Validates each transaction has required fields: `id`, `account_id`, `amount`, `timestamp`
3. Separates valid vs. invalid transactions
4. Logs validation results to the audit trail

### Input State
| Field | Type | Description |
|-------|------|-------------|
| `transactions` | `List[Dict]` | Raw transaction records from DB |
| `case_id` | `str` | Case identifier |

### Output State Changes
| Field | Value |
|-------|-------|
| `transactions` | Filtered to only valid transactions |
| `ingestion_complete` | `True` |
| `audit_logs` | New entry: valid/error counts |

### Validation Rules
```python
required_fields = ["id", "account_id", "amount", "timestamp"]
```
Transactions missing any of these fields are dropped and logged as errors.

---

## 5. Node 2 — Analytics Agent + Typology Engine

**File:** `app/agents/analytics_agent.py`
**Purpose:** Run statistical anomaly detection, then match against known ML typologies.
**LLM calls:** 0 (pure computation)

### What It Does

1. Calls `AnalyticsEngine.analyze(transactions)` for statistical analysis:
   - Calculates mean, std deviation of amounts
   - Flags transactions > 2σ as anomalies
   - Detects structuring patterns (amounts clustering below $10k)
   - Computes base risk score
2. Calls `TypologyEngine.match(transactions, analytics_results, graph_results)`:
   - Runs 5 pattern detectors (see §12)
   - Returns matched typologies with confidence scores
3. Boosts risk score based on typology confidence:
   ```python
   if matched_typologies:
       best = max(t["confidence"] for t in matched_typologies)
       state["risk_score"] = min(1.0, base_risk * 0.4 + best * 0.6)
   ```

### Output State Changes
| Field | Value |
|-------|-------|
| `analytics_results` | `{risk_score, anomalies, anomaly_count, structuring_detected}` |
| `matched_typologies` | List of matched typology dicts |
| `analytics_reasoning_id` | DB record ID |

---

## 6. Node 3 — Correlation Agent (Graph Analysis)

**File:** `app/agents/correlation_agent.py`
**Purpose:** Build a transaction graph and detect network-level patterns.
**LLM calls:** 0

### What It Does

1. Calls `GraphAnalyzer.analyze(transactions)` which uses **NetworkX** to:
   - Build a directed graph where nodes are accounts/counterparties and edges are transactions
   - Detect **hub nodes** (entities with high in/out degree)
   - Identify **communities** using modularity-based detection
   - Find **fan-out patterns** (one source → many recipients)
   - Calculate centrality metrics
2. Stores reasoning and suspicious patterns in the state

### Output State Changes
| Field | Value |
|-------|-------|
| `graph_results` | `{suspicious_patterns, communities, node_count, edge_count}` |
| `correlation_reasoning_id` | DB record ID |

### Graph Pattern Types Detected
| Pattern | Trigger |
|---------|---------|
| `high_degree_hub` | Node with ≥10 connections |
| `fan_out` | Single source → 5+ unique recipients |
| `community_isolation` | Small community with high internal density |

---

## 7. Node 4 — Narrative Agent (CoT + RAG)

**File:** `app/agents/narrative_agent.py`
**Purpose:** Generate the SAR narrative using 3-step Chain-of-Thought reasoning with RAG context.
**LLM calls:** 3 (one per CoT step)

This is the most complex and critical agent in the pipeline. It implements a **3-step Chain-of-Thought (CoT)** process:

### Step 1: Data Summary
**Prompt to LLM:**
> You are an AML data analyst. Summarize the following financial data concisely.

The LLM receives:
- Customer ID
- Transaction summary (first 20 transactions)
- Analytics results (risk score, anomaly count, structuring detected)
- Graph results (patterns, hub nodes)
- Typology matches (name, confidence, evidence)

**Output:** A 200-400 word data summary stored in `reasoning_chain[0]`

### Step 2: Reasoning Analysis
**Prompt to LLM:**
> You are a senior AML compliance investigator. Based on the data summary below, explain WHY this activity is suspicious. Cite specific evidence.

The LLM also receives:
- **RAG Context** — Regulatory guidance retrieved from the knowledge base (see §11)
- Primary typology name and confidence
- Typology evidence bullets

**Output:** Detailed reasoning explaining the suspicious nature, stored in `reasoning_chain[1]`

### Step 3: SAR Draft
**Prompt to LLM:**
> You are writing a Suspicious Activity Report (SAR) for a US financial institution. Use the following template structure and reasoning to produce the final narrative.

The LLM receives:
- **RAG Template** — A SAR template retrieved from the knowledge base
- Data summary from Step 1
- Reasoning from Step 2
- Case details (case ID, customer ID, risk score)

**Output:** The final SAR narrative (3,000-5,000 characters), stored in `state["sar_draft"]`

### RAG Retrieval (Pre-Step)

Before the 3 steps, the agent retrieves context from the knowledge base:

```python
kb = KnowledgeBase(self.db)
guidance = kb.search(f"SAR filing requirements for {primary_typology}", top_k=2)
template = kb.search("SAR narrative template format structure", top_k=1)
```

The retrieved documents provide:
- Regulatory language and citation requirements
- Template structure for the final SAR format

### Output State Changes
| Field | Value |
|-------|-------|
| `sar_draft` | Final SAR text (3,000-5,000 chars) |
| `reasoning_chain` | `[{step: "1_data_summary", output: ...}, {step: "2_reasoning", ...}, {step: "3_sar_draft", ...}]` |
| `rag_context` | Retrieved regulatory documents |
| `narrative_reasoning_id` | DB record ID |

---

## 8. Node 5 — Quality Review Agent

**File:** `app/agents/quality_agent.py`
**Purpose:** LLM-based review of the SAR draft against a quality checklist.
**LLM calls:** 1 (review) + optionally 1 (improvement if score < 60)

### Quality Checklist

The agent evaluates the SAR against these criteria:

| # | Checklist Item |
|---|---------------|
| 1 | Contains specific transaction amounts and dates |
| 2 | Identifies the suspicious activity pattern clearly |
| 3 | References the customer and account information |
| 4 | Explains WHY the activity is suspicious (not just WHAT) |
| 5 | Uses professional, regulatory-appropriate language |
| 6 | Meets minimum length for adequate detail (>500 chars) |
| 7 | Includes a clear conclusion or recommendation |
| 8 | Free of contradictions or factual errors |

### Review Process

1. Sends the SAR draft + case context to LLM with the checklist
2. LLM evaluates each item as **PASS** or **FAIL**
3. Parses the response for:
   - `QUALITY_SCORE: [0-100]`
   - `CRITICAL_ISSUES: [list]`
   - `SUGGESTIONS: [list]`
4. If score < 60, sends an improvement prompt to LLM to fix critical issues
5. Stores the final score and issues in state

### Output State Changes
| Field | Value |
|-------|-------|
| `quality_score` | Integer 0-100 |
| `quality_issues` | List of identified issues |
| `sar_draft` | May be updated if auto-improvement triggered |

### Score Interpretation
| Range | Meaning |
|-------|---------|
| 85-100 | Excellent — ready for filing |
| 70-84 | Good — minor improvements suggested |
| 50-69 | Fair — significant issues flagged |
| 0-49 | Poor — auto-improvement attempted |

---

## 9. Node 6 — Compliance Agent

**File:** `app/agents/compliance_agent.py`
**Purpose:** Make the final FILE/ESCALATE/CLOSE decision based on aggregated evidence.
**LLM calls:** 0

### Decision Logic

```python
if risk_score >= 0.7:
    recommended_action = "FILE_SAR"
elif risk_score >= 0.4:
    recommended_action = "ESCALATE"
else:
    recommended_action = "CLOSE"
```

The compliance agent also validates:
- SAR draft exists and is non-empty
- Risk score is within valid range (0.0 - 1.0)
- At least one reasoning step exists

### Output State Changes
| Field | Value |
|-------|-------|
| `recommended_action` | `FILE_SAR` / `ESCALATE` / `CLOSE` |
| `compliance_validation` | `{checks_passed, sar_present, risk_valid}` |

---

## 10. Node 7 — Audit Logger

**File:** `app/agents/audit_logger.py`
**Purpose:** Finalize the audit trail and create a summary record.
**LLM calls:** 0

### What It Does

1. Collects all reasoning IDs from previous agents:
   - `analytics_reasoning_id`
   - `correlation_reasoning_id`
   - `narrative_reasoning_id`
2. Creates a final audit summary with:
   - Case ID
   - All reasoning references
   - Final risk score
   - Recommended action
3. Writes the summary to `audit_logs` table
4. Sets `audit_complete = True`

### Output State Changes
| Field | Value |
|-------|-------|
| `audit_log_id` | Database ID of the final audit record |
| `audit_complete` | `True` |

---

## 11. RAG Knowledge Base

**File:** `app/services/knowledge_base.py`
**Storage:** PostgreSQL with `pgvector` extension

### How It Works

The knowledge base stores **8 synthetic regulatory documents** that are seeded on backend startup. Each document is:
1. Chunked into sections
2. Embedded using `nomic-embed-text` (768-dim vectors) via Ollama
3. Stored in the `embeddings` table with the vector

### Documents Seeded

| Category | Documents |
|----------|-----------|
| **SAR Filing Requirements** | BSA filing rules, FinCEN requirements, thresholds and timelines |
| **Typology Guidance** | Structuring/Smurfing indicators, Layering patterns, Round-tripping red flags |
| **SAR Templates** | Standard SAR narrative template with section structure |
| **Regulatory References** | FATF recommendations, FFIEC BSA/AML Manual excerpts |

### Retrieval Process

```python
def search(self, query: str, top_k: int = 3) -> List[Dict]:
    query_embedding = generate_embedding(query)              # 768-dim vector
    results = db.execute(
        "SELECT content_text, 1 - (embedding <=> CAST(:vec AS vector)) AS similarity "
        "FROM embeddings ORDER BY embedding <=> CAST(:vec AS vector) LIMIT :k",
        {"vec": str(query_embedding), "k": top_k}
    )
    return [{"text": r.content_text, "similarity": r.similarity} for r in results]
```

**Typical similarity scores:** 0.65 - 0.80 (cosine distance)

---

## 12. Typology Engine — Detection Logic

**File:** `app/services/typology_engine.py`

The engine contains 5 rule-based detectors, each analyzing transaction DataFrames:

### Typology 1: Smurfing / Structuring

| Parameter | Value |
|-----------|-------|
| **Trigger** | ≥5 deposits between $4,000-$10,000 within a 14-day sliding window |
| **Additional Check** | ≥3 unique counterparties |
| **Confidence Formula** | `0.4 + (deposit_count × 0.03) + (unique_parties × 0.02)` |
| **Max Confidence** | 0.95 (boosted to 0.98 if analytics confirms structuring) |
| **Regulatory Ref** | BSA §5324, 31 CFR 1010.314 |

### Typology 2: Layering

| Parameter | Value |
|-----------|-------|
| **Trigger** | Deposit > $50,000 followed by ≥4 outbound transfers within 24 hours |
| **Additional Check** | Transfers go to multiple unique recipients |
| **Confidence Formula** | `0.5 + (transfer_count × 0.03) + (dispersal_pct × 0.2)` |
| **Max Confidence** | 0.95 |
| **Regulatory Ref** | FATF ML Typology Report, FinCEN Advisory FIN-2020-A003 |

### Typology 3: Round-Tripping / Circular Flow

| Parameter | Value |
|-----------|-------|
| **Trigger** | ≥2 instances of: outbound transfer > $10k, then return from *different entity* at ±15% amount within 14 days |
| **Confidence Formula** | `0.5 + (trip_count × 0.1)` |
| **Max Confidence** | 0.95 |
| **Regulatory Ref** | FATF Trade-Based ML Report |

### Typology 4: Rapid Movement / Pass-Through

| Parameter | Value |
|-----------|-------|
| **Trigger** | ≥2 instances of: deposit > $20k followed by withdrawal at 90-105% amount within 24 hours |
| **Confidence Formula** | `0.5 + (event_count × 0.1)` |
| **Max Confidence** | 0.95 |
| **Regulatory Ref** | FinCEN SAR Narrative Guidance, FFIEC BSA/AML Manual |

### Typology 5: Shell Company Fan-Out

| Parameter | Value |
|-----------|-------|
| **Trigger** | Deposit > $100k followed by ≥8 transfers to ≥6 unique recipients on same day |
| **Additional Check** | Graph analysis for hub pattern confirmation |
| **Confidence Formula** | `0.5 + (recipient_count × 0.03) + (0.1 if hub_detected)` |
| **Max Confidence** | 0.95 |
| **Regulatory Ref** | FATF Beneficial Ownership Guidance, FinCEN Shell Company Advisory |

### Typology Match Output Format

Each matched typology returns:
```json
{
    "typology": "SMURFING",
    "name": "Structuring / Smurfing",
    "confidence": 0.95,
    "evidence": [
        "15 deposits below $10k CTR threshold",
        "5 unique counterparties identified",
        "Activity concentrated in 12 day(s)",
        "Aggregate amount: $119,850.00"
    ],
    "regulatory_reference": "BSA §5324, 31 CFR 1010.314",
    "risk_weight": 0.9,
    "transaction_count": 15,
    "total_amount": 119850.00
}
```

---

## 13. LLM Integration (Ollama)

**File:** `app/llm.py`

### Models Used

| Model | Purpose | Size |
|-------|---------|------|
| `mistral:7b-instruct-q4_K_M` | Text generation (narrative, quality review) | ~4.1 GB |
| `nomic-embed-text:latest` | Embedding generation (RAG retrieval) | ~274 MB |

### API Configuration

```python
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

def generate_text(prompt: str) -> str:
    response = requests.post(f"{OLLAMA_URL}/api/generate", json={
        "model": "mistral:7b-instruct-q4_K_M",
        "prompt": prompt,
        "stream": False
    })
    return response.json()["response"]

def generate_embedding(text: str) -> List[float]:
    response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    })
    return response.json()["embedding"]  # 768-dimensional vector
```

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Text generation per call | 15-40 seconds |
| Embedding generation per call | 0.5-2 seconds |
| Total LLM calls per pipeline | 4-5 |
| Total pipeline time | 2-3 minutes |

---

## 14. Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `users` | Authentication (email, hashed password) |
| `customers` | Customer records (name, risk_profile) |
| `accounts` | Bank accounts (linked to customers, balance) |
| `transactions` | Financial transactions (amount, type, timestamp, counterparty) |
| `embeddings` | pgvector table for RAG (content_text, 768-dim vector) |
| `audit_logs` | Agent actions (case_id, agent_name, input/output JSON) |
| `agent_reasoning` | Detailed reasoning (case_id, agent_name, reasoning JSON, data references) |

### Key Relationships

```
customers (1) ──→ (N) accounts (1) ──→ (N) transactions
                                              │
                                    ┌─────────┘
                                    ▼
                            analysis pipeline
                                    │
                                    ▼
                        audit_logs + agent_reasoning
```

---

## 15. API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | No | Register new user |
| `POST` | `/auth/login` | No | Login, returns JWT |
| `GET` | `/customers` | JWT | List all customers with stats |
| `POST` | `/cases/create` | JWT | Create a new case for a customer |
| `POST` | `/cases/{id}/run-analysis?customer_id=N` | JWT | **Run full 7-agent pipeline** |
| `GET` | `/cases/{id}` | JWT | Get case audit logs |
| `POST` | `/cases/{id}/export-docx-body` | JWT | Export SAR to Word |
| `POST` | `/cases/{id}/export-pdf-body` | JWT | Export SAR to PDF |
| `GET` | `/health` | No | Health check |

### Pipeline Response Format

```json
{
    "case_id": "a1b2c3d4-...",
    "customer_id": 11,
    "risk_score": 0.855,
    "sar_draft": "SUSPICIOUS ACTIVITY REPORT...",
    "recommended_action": "FILE_SAR",
    "audit_log_id": 42,
    "quality_score": 85,
    "matched_typologies": [
        {
            "typology": "SMURFING",
            "name": "Structuring / Smurfing",
            "confidence": 0.95,
            "evidence": ["15 deposits below $10k..."],
            "regulatory_reference": "BSA §5324..."
        }
    ]
}
```

---

## 16. Logging & Observability

The backend produces structured logs at three levels:

### Level 1 — API Layer (`aml.api`)
```
12:45:01 │ INFO  │ aml.api         │ 🚀 Starting 7-agent pipeline for Case abc12345 / Customer 11
12:45:01 │ INFO  │ aml.api         │    📊 Found 1 accounts: [19]
12:45:01 │ INFO  │ aml.api         │    💳 Found 50 transactions
12:47:30 │ INFO  │ aml.api         │ ✅ Pipeline complete: risk=0.86, quality=85, rec=FILE_SAR
```

### Level 2 — Pipeline Layer (`aml.pipeline`)
```
12:45:01 │ INFO  │ aml.pipeline    │ ━━━ [INGESTION] starting ━━━
12:45:01 │ INFO  │ aml.pipeline    │     [INGESTION] ✓ done
12:45:02 │ INFO  │ aml.pipeline    │ ━━━ [ANALYTICS] starting ━━━
12:45:03 │ INFO  │ aml.pipeline    │     [ANALYTICS] ✓ done
```

### Level 3 — Agent Layer (`aml.agents`)
```
12:45:01 │ INFO  │ aml.agents      │   ▸ IngestionAgent → logging action to audit trail
12:45:02 │ INFO  │ aml.agents      │   ▸ AnalyticsAgent → storing reasoning
12:46:15 │ INFO  │ aml.agents      │   ▸ NarrativeAgent → storing reasoning (1_data_summary)
12:46:45 │ INFO  │ aml.agents      │   ▸ NarrativeAgent → storing reasoning (2_reasoning)
12:47:10 │ INFO  │ aml.agents      │   ▸ NarrativeAgent → storing reasoning (3_sar_draft)
```

---

## 17. Test Data — Synthetic Customers

Generated by `generate_data.py`. 10 customers with IDs **11-20**:

### Suspicious Customers (11-15)

| ID | Name | Assigned Typology | Risk Profile | Data Pattern |
|----|------|-------------------|-------------|-------------|
| 11 | Customer 1 (Ltd) | Smurfing | HIGH | 15+ deposits between $4k-$10k from 5+ unique sources |
| 12 | Customer 2 (Inc) | Layering | HIGH | $75k deposit → immediate fan-out to 6+ recipients |
| 13 | Customer 3 (GmbH) | Round-Tripping | HIGH | $30k sent out, $28k-$34k returned from different entity |
| 14 | Customer 4 (SA) | Rapid Movement | HIGH | $50k deposit → $48k withdrawal within hours |
| 15 | Customer 5 (Holdings) | Shell Fan-Out | HIGH | $200k wire → 10+ transfers to shell entities |

### Clean Customers (16-20)

| ID | Name | Risk Profile | Data Pattern |
|----|------|-------------|-------------|
| 16-20 | Customer 6-10 | LOW | Normal salary deposits, utility payments, rent |

Each customer has:
- 1-3 accounts (checking, savings, business)
- 20-50 baseline legitimate transactions
- Additional typology-specific transactions (for IDs 11-15)

---

## Summary

The pipeline transforms raw transaction data into a regulatory-ready SAR through seven specialized steps:

```
Raw Transactions → Validation → Statistical Analysis + Typology Matching
    → Graph Analysis → 3-Step AI Narrative (with RAG) → Quality Review
    → Compliance Decision → Audit Trail
```

Every step is logged, every reasoning is stored, and every decision is traceable — meeting the regulatory requirement for full auditability in AML compliance.
