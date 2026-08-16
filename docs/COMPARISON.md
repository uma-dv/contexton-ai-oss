# ContextOn.AI OSS vs The Market

**Verified Feature Comparison (August 2026)**

---

## Executive Summary

ContextOn.AI OSS introduces **two novel features** not found in any existing tool:

1. **Failure Learning** - Agents learn from mistakes and avoid unreliable paths
2. **Confidence Scoring** - Every piece of knowledge has a trust indicator

No other knowledge graph tool offers these features.

---

## Market Leaders (Verified Data)

### Graphify
- **GitHub Stars:** 105,000+
- **Focus:** Code knowledge graphs for AI coding assistants
- **Key Features:**
  - AST parsing via tree-sitter (36+ languages)
  - Community detection (Leiden algorithm)
  - EXTRACTED/INFERRED edge tagging
  - Graph visualization (graph.html)
  - MCP server support
  - Git hooks for auto-sync
- **Strengths:** Simple to use, works with Claude/Cursor/Codex
- **Weaknesses:** No memory, no learning, no confidence scoring

### Graphiti (Zep)
- **GitHub Stars:** 45,000+
- **Focus:** Temporal knowledge graphs for agent memory
- **Key Features:**
  - Bi-temporal data model (event time + ingestion time)
  - Real-time incremental updates
  - Hybrid search (semantic + keyword + graph)
  - MCP server implementation
  - Neo4j and FalkorDB backends
- **Strengths:** Temporal awareness, production-grade
- **Weaknesses:** Complex setup, no confidence scoring, no failure learning

### Mem0
- **GitHub Stars:** 48,000+
- **Focus:** Universal memory layer for AI agents
- **Key Features:**
  - Vector-based memory
  - Three-tier memory (user/session/agent)
  - Hybrid store (vectors + graph relationships)
  - Simple API
- **Strengths:** Easy to use, drop-in memory
- **Weaknesses:** No knowledge graph structure, no confidence, no failure learning

### Microsoft GraphRAG
- **GitHub Stars:** 25,000+
- **Focus:** Graph-augmented RAG pipeline
- **Key Features:**
  - Entity extraction
  - Community hierarchy
  - Local and global search
  - Neo4j integration
- **Strengths:** Enterprise-grade, scalable
- **Weaknesses:** Heavy, complex setup, no failure learning

### TrustGraph
- **GitHub Stars:** 10,000+
- **Focus:** Ontology-driven context graphs
- **Key Features:**
  - OntologyRAG methodology
  - Custom ontology engineering
  - 3D visualization
  - Context Cores (versioned context)
- **Strengths:** Domain modeling, structured extraction
- **Weaknesses:** Complex, enterprise-only focus

---

## Feature Comparison Table

| Feature | Graphify | Graphiti | Mem0 | GraphRAG | TrustGraph | **ContextON_Graph** |
|---------|----------|----------|------|----------|------------|---------------------|
| **Knowledge Graphs** | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Agent Memory** | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| **AST Parsing** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Temporal Awareness** | ❌ | ✅ | ❌ | ❌ | ❌ | ⚠️ Basic |
| **Community Detection** | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ |
| **EXTRACTED/INFERRED** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Graph Visualization** | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **MCP Support** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ |
| **Simple to Use** | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ |
| **Confidence Scoring** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Failure Learning** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Quality Badges** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Suggested Questions** | ⚠️ Basic | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Novel Features (ContextON_Graph Only)

### 1. Failure Learning

**What it does:**
When an agent gives a wrong answer, ContextON_Graph:
- Marks the knowledge path as unreliable
- Reduces confidence of involved nodes/edges
- Future queries avoid this unreliable path

**Why it matters:**
No other tool learns from mistakes. Agents repeat errors forever.

**Example:**
```python
# Agent gives wrong answer
graph.record_failure(
    query="What is PM-JAY?",
    answer="It's a housing scheme",
    reason="Incorrect - it's health insurance"
)

# Future queries now avoid this path
results = graph.query("PM-JAY")
# Returns reliable paths, not the failed one
```

**Competitors:**
- Graphify: Nothing happens
- Graphiti: Nothing happens
- Mem0: Nothing happens

### 2. Confidence Scoring

**What it does:**
Every node and edge has a trust score (0.0-1.0) based on:
- Verification count (how many times confirmed)
- Time decay (old information loses confidence)
- Failure penalty (failures reduce confidence)

**Why it matters:**
You know which information to trust. Traditional tools just return "what matches."

**Example:**
```python
results = graph.query("PM-JAY coverage")
for r in results:
    print(f"{r['badge']} {r['node']['content']}")
    print(f"   Confidence: {r['confidence']:.1%}")

# Output:
# 🟢 PM-JAY covers 5 lakh per family
#    Confidence: 92.0%
# 🟡 PM-JAY is for poor families
#    Confidence: 78.0%
# 🔴 PM-JAY is housing scheme
#    Confidence: 31.0%
```

**Competitors:**
- Graphify: No confidence scoring
- Graphiti: No confidence scoring
- Mem0: No confidence scoring

### 3. Quality Badges

**What it does:**
Visual indicators for trust levels:
- 🟢 High (≥0.8): Safe to use
- 🟡 Medium (0.5-0.8): Verify first
- 🔴 Low (<0.5): Don't trust without checking

**Why it matters:**
Quick visual trust assessment. No other tool does this.

---

## What ContextON_Graph Does NOT Have

These are intentionally excluded (enterprise features):

| Feature | Status | Why Excluded |
|---------|--------|--------------|
| Isolation engine | ❌ | Core IP |
| Quality scoring formulas | ❌ | Proprietary |
| Drift detection | ❌ | Core IP |
| Multi-tenant isolation | ❌ | Enterprise feature |
| Enterprise connectors | ❌ | SAP, ServiceNow, etc. |
| Compliance reporting | ❌ | Enterprise feature |

---

## Use Case Comparison

| Use Case | Best Tool | Why |
|----------|-----------|-----|
| Code knowledge graphs | Graphify | AST parsing, 36+ languages |
| Temporal agent memory | Graphiti | Bi-temporal, real-time |
| Simple drop-in memory | Mem0 | Easy API, vector-based |
| Enterprise RAG | GraphRAG | Scalable, Neo4j |
| Domain modeling | TrustGraph | Ontology-driven |
| **Confidence-aware memory** | **ContextON_Graph** | **Only tool with confidence + failure learning** |

---

## Key Differentiator Summary

| Differentiator | ContextON_Graph | Competitors |
|----------------|-----------------|-------------|
| **Learns from failures** | ✅ Yes | ❌ No |
| **Confidence scoring** | ✅ Yes | ❌ No |
| **Quality badges** | ✅ Yes | ❌ No |
| **Simple to use** | ✅ Yes | ⚠️ Varies |
| **MCP support** | ✅ Yes | ⚠️ Varies |

---

## Market Position

ContextON_Graph occupies a **unique position**:

```
                    Simple
                      ↑
                      │
    Mem0 ─────────────┼──────────── ContextON_Graph
    (vector memory)   │            (confidence-aware)
                      │
    ──────────────────┼──────────────────→ Structured
                      │
    Graphify ─────────┼──────────── Graphiti
    (code graphs)     │            (temporal memory)
                      │
                      ↓
                    Complex
```

**ContextON_Graph is:**
- Simple like Mem0
- Structured like Graphify
- Memory-aware like Graphiti
- **PLUS: Confidence scoring and failure learning (unique)**

---

## Verification Notes

This comparison was verified on August 16, 2026 using:
- GitHub repositories (star counts, feature lists)
- Official documentation
- Published papers (Zep/Graphiti arXiv paper)
- Community discussions

**Data Sources:**
- Graphify: github.com/Graphify-Labs/graphify (105k+ stars)
- Graphiti: github.com/getzep/graphiti (45k+ stars)
- Mem0: github.com/mem0ai/mem0 (48k+ stars)
- GraphRAG: github.com/microsoft/graphrag (25k+ stars)
- TrustGraph: github.com/trustgraph-ai/trustgraph (10k+ stars)

---

## Conclusion

ContextON_Graph is the **only tool** that offers:
1. Failure learning
2. Confidence scoring
3. Quality badges

This makes it unique in the market and positions it as a teaching tool that leads to the enterprise platform.

---

*This document is part of the ContextON_Graph documentation. For enterprise features, see the enterprise platform.*
