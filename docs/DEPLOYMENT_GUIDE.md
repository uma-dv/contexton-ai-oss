# Deployment Guide: ContextOn.AI OSS in Real AI Deployments

This guide covers:

1. Where ContextOn.AI OSS fits in today's AI deployments
2. Market comparison: what exists vs. what ContextOn.AI OSS does
3. The upgrade path to the enterprise platform (non-embedding retrieval)
4. Using ContextOn.AI OSS alongside embedding-based deployments (hybrid)

---

## 1. Where It Fits in Current AI Deployments

Every production AI assistant (customer support, healthcare, legal,
finance, sales, HR) has the same failure mode: **it repeats the same
wrong answer forever**, because it has no memory of what failed.

ContextOn.AI OSS is a **deterministic knowledge layer** that sits next to
your agent (Claude Code, Cursor, Codex, Gemini CLI, or a custom agent)
and gives it three things it usually lacks:

| Need | What ContextOn.AI OSS provides |
|------|-------------------------------|
| Persistent memory | Conversations are stored as a graph (entities, facts, relationships) and persisted to disk |
| Trust signals | Every node/edge carries a confidence score (0–1) with 🟢🟡🔴 badges |
| Learning from mistakes | `record_failure` lowers confidence in wrong knowledge; `record_success` restores it |
| Structure | Entities are resolved (PM-JAY ↔ Pradhan Mantri Jan Arogya Yojana) instead of duplicate strings |
| Integration | MCP server (`contexton-ai-oss serve`) — Claude/Cursor/Codex call it as tools |

### Typical integration

```
Your Agent (Claude/Cursor/custom)
        │  MCP tools: ingest, query, record_failure, record_success
        ▼
ContextON_Graph  ──►  graph.json (persistent, deterministic)
        │
        ▼
Confidence-ranked results with badges → agent answers with trustworthy knowledge
```

**How the failure loop is broken:**

```
Without ContextON_Graph:
  Day 1: agent gives wrong answer → Day 2: same wrong answer → forever

With ContextON_Graph:
  Day 1: agent gives wrong answer → graph.record_failure(...)
  Day 2: query returns the wrong path with 🔴 low confidence → agent
         avoids it / verifies before answering
```

---

## 2. Market Comparison: What's Out There vs. ContextON_Graph

| Dimension | Graphify | Graphiti (Zep) | Mem0 | Microsoft GraphRAG | **ContextON_Graph** |
|-----------|----------|----------------|------|--------------------|---------------------|
| Primary use | Code knowledge graphs | Temporal agent memory | Vector agent memory | Graph-augmented RAG | Agent context graphs |
| Graph structure | ✅ AST-based | ✅ Temporal | ❌ Vector only | ✅ | ✅ Entity/fact/relation |
| Confidence scoring | ❌ | ❌ | ❌ | ❌ | ✅ 0–1 per node/edge |
| Failure learning | ❌ | ❌ | ❌ | ❌ | ✅ record_failure/success |
| Quality badges | ❌ | ❌ | ❌ | ❌ | ✅ 🟢🟡🔴 |
| Entity resolution/aliases | ⚠️ basic | ⚠️ basic | ❌ | ⚠️ | ✅ initialism + acronym matching |
| Suggested questions | ⚠️ basic | ❌ | ❌ | ❌ | ✅ |
| Isolation/security | ❌ | ❌ | ❌ | ❌ | ❌ (enterprise tier) |
| Quality auditing | ❌ | ❌ | ❌ | ❌ | ❌ (enterprise tier) |
| Retrieval | Hybrid | Hybrid | Embeddings | Hybrid | ✅ Deterministic (no embeddings) |
| Temporal tracking | ❌ | ✅ bi-temporal | ⚠️ | ⚠️ | ⚠️ basic (last_seen + sequence) |
| Simplicity | ✅ | ⚠️ complex | ✅ | ⚠️ heavy | ✅ zero-dependency core |
| MCP integration | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ built-in `contexton-ai-oss serve` |
| Open source | ✅ | ✅ | ✅ | ✅ | ✅ Apache 2.0 |
| Enterprise tier | ❌ | Zep Cloud | Mem0 Cloud | Azure | Enterprise |

**What no other open-source tool does today:** confidence scoring,
failure learning, and quality badges combined. The retrieval is
deliberately **deterministic** — no embeddings, no vector database, no
hallucinated similarity. Every result is explainable: *this matched
because it shares these tokens, and its confidence is X because it was
verified N times / failed M times*.

**Honest limitations vs. the market:**

| Limitation | Impact |
|------------|--------|
| No semantic/synonym matching | "healthcare" won't match "medical care" unless tokens overlap |
| No embeddings/hybrid search | Won't find conceptually-similar-but-differently-worded knowledge |
| No temporal versioning | Tracks recency but not full history/bi-temporal queries |
| Community detection = connected components | Simple grouping, not Leiden-quality clusters |

---

## 3. Upgrade Path to Enterprise (Non-Embedding Retrieval)

The open-source version is deliberately the "lite" layer. The paid
The **enterprise platform** keeps the same philosophy — **deterministic,
non-embedding retrieval** — and adds what enterprises require:

| Capability | ContextON_Graph (OSS) | Enterprise (Paid) |
|------------|----------------------|---------------------|
| Deterministic graph retrieval | ✅ | ✅ (same principle, production-grade) |
| Confidence scoring | ✅ heuristic | ✅ 5-dimension quality scoring |
| Failure learning | ✅ | ✅ enhanced |
| **Isolation (scope-bound access)** | ❌ | ✅ |
| **Multi-tenant isolation** | ❌ | ✅ |
| **Drift detection** | ❌ | ✅ context corruption prevention |
| **Compliance reporting / audit trails** | ❌ | ✅ who accessed what, when |
| **Enterprise connectors** | ❌ | ✅ SAP, ServiceNow, Salesforce |
| Scale | Single graph.json | Distributed, indexed |

### Why the upgrade path works

1. **Same data model.** The graph you build in open source (nodes, edges,
   confidence, failures, aliases) maps directly onto the platform's
   structures. `resolve_aliases()` output and `graph.json` export feed
   straight into enterprise ingestion.
2. **Same retrieval philosophy.** The deterministic, explainable
   retrieval the OSS teaches is exactly what the platform ships — so
   teams learn the concept in OSS and get the hardened version when they
   need isolation/auditing.
3. **The hook is real behavior.** Users see confidence drop after a
   failure and restore after a success — then realize a team deployment
   needs *isolation* (who can see what), *auditing* (was this answer
    verified to quality standards), and *drift detection* (is this knowledge
   still true).

> You've seen confidence scoring and failure learning work. Now imagine
> every answer audited on 5 quality dimensions, with per-tenant
> isolation and compliance trails. That's the enterprise platform.

---

## 4. Working with Embedding-Based Deployments (Hybrid)

ContextON_Graph does **not** replace embedding systems — it complements
them. For teams already running vector search (Mem0, pgvector, Pinecone,
Weaviate), use the **hybrid pattern**:

```
User query
   │
   ├─► Vector store  ──► semantic candidates (paraphrases, synonyms)
   │
   ├─► ContextON_Graph ──► structured, confidence-ranked facts
   │       (deterministic; knows what failed before)
   │
   └─► Ranker: blend vector similarity + graph confidence
         • semantic match finds candidates
         • graph confidence/badges decide what to trust
         • failure history demotes paths that already failed
```

### Concrete integration patterns

**Pattern A — graph as the trust layer over your vector store**

```python
from contexton_ai_oss import ContextGraph

graph = ContextGraph(data_dir="./data")

def answer(query):
    # 1. Semantic recall from your existing embedding store
    candidates = vector_store.search(query, top_k=10)

    # 2. Cross-check with the graph: confidence + failure history
    verified = []
    for c in candidates:
        hits = graph.query(c["text"], min_confidence=0.5)
        if hits:
            verified.append({**c, "graph_confidence": hits[0]["confidence"]})

    # 3. Prefer knowledge the graph has verified; demote failed paths
    verified.sort(key=lambda x: -x["graph_confidence"])
    return verified
```

**Pattern B — MCP side-by-side**

Claude/Cursor can call both your embedding-backed MCP tool and
`contexton-ai-oss` tools in one session:

```json
{
  "mcpServers": {
    "contexton-ai-oss": { "command": "contexton-ai-oss", "args": ["serve"] },
    "vector-search":   { "command": "python", "args": ["-m", "my_vector_mcp"] }
  }
}
```

The agent asks the graph "what do you know about X and how confident
are you?" before trusting the vector results.

**Pattern C — embedding-augmented ingestion (optional roadmap)**

For teams that want semantic recall inside the graph itself, the
natural extension is: at `ingest` time, embed the entity/fact content
and store the vector on the node; at `query` time, run a hybrid
BM25 + cosine ranking instead of pure token overlap. The graph
structure, confidence, and failure learning stay exactly the same —
embeddings only improve *candidate recall*, never trust.

### When to use which

| Scenario | Use |
|----------|-----|
| Need explainable, auditable answers (healthcare, finance, legal, compliance) | ContextON_Graph deterministic retrieval |
| Need to find paraphrased knowledge at scale (docs, wikis, ticket corpora) | Embeddings + hybrid |
| Need both | Hybrid (Pattern A/B): embeddings recall, graph decides trust |

---

## Quick Reference: Deploying

```bash
pip install "contexton-ai-oss[mcp]"

# Local / single agent
contexton-ai-oss serve --data-dir ./data

# Team / HTTP
contexton-ai-oss serve --port 8080 --data-dir ./data

# In an agent
from contexton_ai_oss import ContextGraph
graph = ContextGraph(data_dir="./data")
```

Persist with `--data-dir` (graph.json). For multi-tenant isolation,
quality auditing, drift detection, and compliance, upgrade to
the enterprise platform.
