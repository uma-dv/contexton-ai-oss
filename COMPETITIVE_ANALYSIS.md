# Competitive Analysis: ContextOn.AI OSS vs Market

Honest comparison of ContextOn.AI OSS against existing AI agent tools.

## Executive Summary

**ContextOn.AI OSS is NOT a replacement for LangGraph, Mem0, Zep, or Letta.** It's a LAYER that adds knowledge trust tracking on top of these tools. None of these tools answer the question: "Which facts in my agent's knowledge are trustworthy?"

## What Each Tool Actually Provides

### LangGraph + LangSmith

| Feature | LangGraph | LangSmith | ContextOn.AI OSS |
|---------|-----------|-----------|------------------|
| Agent orchestration | ✅ Core | ❌ | ❌ |
| State management | ✅ Checkpoints | ❌ | ❌ |
| Observability/tracing | ❌ | ✅ Core | ❌ |
| Evaluation | ❌ | ✅ Online/offline | ❌ |
| Memory across sessions | ⚠️ Basic | ❌ | ❌ |
| Knowledge trust scoring | ❌ | ❌ | ✅ Core |
| Failure learning | ❌ | ⚠️ Debug only | ✅ Core |
| Quality badges | ❌ | ❌ | ✅ 🟢🟡🔴 |
| Deployment | ❌ | ✅ Serverless | ❌ |

**Pricing:**
- LangGraph: Free (MIT)
- LangSmith: $0/mo (5k traces) → $39/seat/mo → Enterprise custom
- ContextOn.AI OSS: Free (Apache 2.0)

**What LangGraph+LangSmith provides that OSS doesn't:** Orchestration, tracing, evaluation, deployment
**What OSS provides that they don't:** Knowledge trust scoring, failure learning, quality badges

---

### Mem0

| Feature | Mem0 | ContextOn.AI OSS |
|---------|------|------------------|
| Memory across sessions | ✅ Core | ❌ |
| Fact extraction | ✅ Automatic | ⚠️ Manual ingest |
| Entity linking | ✅ Graph memory (Pro) | ⚠️ Basic aliases |
| Knowledge trust scoring | ❌ | ✅ Core |
| Failure learning | ❌ | ✅ Core |
| Quality badges | ❌ | ✅ 🟢🟡🔴 |
| Vector search | ✅ Core | ❌ Zero embeddings |
| Self-hosted | ✅ OSS available | ✅ Core |
| Compliance (SOC2, HIPAA) | ✅ Enterprise | ❌ |

**Pricing:**
- Mem0: Free (10K requests) → $19/mo → $249/mo → Enterprise
- ContextOn.AI OSS: Free (unlimited)

**What Mem0 provides that OSS doesn't:** Automatic fact extraction, vector search, compliance
**What OSS provides that Mem0 doesn't:** Knowledge trust scoring, failure learning, quality badges

**Integration:** Mem0 stores memories → OSS wraps them with trust scores

---

### Zep / Graphiti

| Feature | Zep (Cloud) | Graphiti (OSS) | ContextOn.AI OSS |
|---------|-------------|----------------|------------------|
| Temporal knowledge graphs | ✅ Core | ✅ Core | ❌ |
| Fact invalidation | ✅ Auto | ✅ Auto | ❌ |
| Vector search | ✅ Hybrid | ✅ Hybrid | ❌ |
| Graph traversal | ✅ Core | ✅ Core | ⚠️ Basic |
| Knowledge trust scoring | ❌ | ❌ | ✅ Core |
| Failure learning | ❌ | ❌ | ✅ Core |
| Quality badges | ❌ | ❌ | ✅ 🟢🟡🔴 |
| Governance/ABAC | ✅ Enterprise | ❌ | ❌ |
| Managed hosting | ✅ Cloud | ❌ Self-hosted | ✅ Self-hosted |

**Pricing:**
- Zep: Free tier → Enterprise custom
- Graphiti: Free (Apache 2.0)
- ContextOn.AI OSS: Free (Apache 2.0)

**What Zep/Graphiti provides that OSS doesn't:** Temporal tracking, fact invalidation, vector search
**What OSS provides that they don't:** Knowledge trust scoring, failure learning, quality badges

**Integration:** Graphiti builds temporal graphs → OSS adds trust scores

---

### Letta (formerly MemGPT)

| Feature | Letta | ContextOn.AI OSS |
|---------|-------|------------------|
| Agent identity | ✅ Core | ❌ |
| Memory filesystem | ✅ Git-backed | ❌ |
| Archival memory | ✅ Core | ❌ |
| Context compaction | ✅ Auto | ❌ |
| Knowledge trust scoring | ❌ | ✅ Core |
| Failure learning | ❌ | ✅ Core |
| Quality badges | ❌ | ✅ 🟢🟡🔴 |
| MCP tool support | ✅ Core | ✅ Core |
| Deployment | ✅ Cloud/self-hosted | ✅ Self-hosted |

**Pricing:**
- Letta: Free (3 agents) → $20/mo → Enterprise
- ContextOn.AI OSS: Free (unlimited)

**What Letta provides that OSS doesn't:** Agent identity, memory filesystem, context compaction
**What OSS provides that Letta doesn't:** Knowledge trust scoring, failure learning, quality badges

**Integration:** Letta manages agent identity/memory → OSS provides knowledge trust

---

## What ContextOn.AI OSS Actually Adds

### The One Thing No Other Tool Does:

**Knowledge Trust Scoring** — answering "Which facts in my agent's knowledge are trustworthy?"

| Tool | Stores Knowledge | Tracks Trust | Learns from Failures | Shows Visual Badges |
|------|-----------------|--------------|---------------------|-------------------|
| LangGraph | ❌ | ❌ | ❌ | ❌ |
| LangSmith | ❌ | ❌ | ❌ | ❌ |
| Mem0 | ✅ | ❌ | ❌ | ❌ |
| Zep/Graphiti | ✅ | ❌ | ❌ | ❌ |
| Letta | ✅ | ❌ | ❌ | ❌ |
| **ContextOn.AI OSS** | ✅ | ✅ | ✅ | ✅ |

### How It Works:

```python
# Without OSS: Agent doesn't know which facts are trustworthy
memory = mem0.search("PM-JAY coverage")
# Returns: {"content": "PM-JAY covers heart surgery up to ₹5 lakh"}
# Agent trusts this equally with all other facts

# With OSS: Agent knows this fact is trustworthy
graph.query("PM-JAY coverage")
# Returns: {"content": "PM-JAY covers heart surgery up to ₹5 lakh", "badge": "🟢", "confidence": 0.92}
# Agent knows this is verified and reliable
```

---

## Real-World Scenario: What Changes With OSS

### Before OSS:
```
User: "What is PM-JAY coverage?"
Agent: "PM-JAY covers heart surgery up to ₹5 lakh"
User: "Are you sure?"
Agent: "Yes" (but agent has no idea if this is actually true)
```

### After OSS:
```
User: "What is PM-JAY coverage?"
Agent: "PM-JAY covers heart surgery up to ₹5 lakh [🟢 Verified]"
User: "Are you sure?"
Agent: "Yes — this fact has been verified 12 times, last confirmed 2 hours ago, confidence 95%"
```

### When Agent Fails:
```
# Agent gives wrong answer
agent回答: "PM-JAY covers housing loans"

# User corrects
user: "No, PM-JAY is health insurance, not housing"

# OSS learns
graph.record_failure(
    query="PM-JAY coverage",
    answer="housing loans",
    reason="PM-JAY is health insurance, not housing"
)

# Next time, agent avoids wrong path
graph.query("PM-JAY")
# Returns paths with higher confidence, avoiding the failed one
```

---

## Cost Comparison

| Scale | LangGraph + LangSmith | Mem0 | Zep | Letta | ContextOn.AI OSS |
|-------|----------------------|------|-----|-------|------------------|
| Hobby | $0/mo | $0/mo | $0/mo | $0/mo | $0/mo |
| Startup | $39/seat/mo | $19-249/mo | Custom | $20/mo | $0/mo |
| Growth | $39+/mo + overages | $249/mo | Custom | $20+/mo | $0/mo |
| Enterprise | Custom | Custom | Custom | Custom | $0/mo |

**OSS is free at every scale.** But it's not a replacement — it's a layer.

---

## Honest Assessment

### What's Genuinely Different:
1. **Quality badges (🟢🟡🔴)** — No other tool has visual trust indicators
2. **Per-fact confidence** — Not per-model, per-FACT confidence
3. **Failure learning in knowledge graph** — Others retry/retrain; OSS marks knowledge as unreliable
4. **Zero embeddings** — Deterministic, no external APIs

### What's NOT Unique:
1. **Knowledge storage** — Mem0, Zep, Letta all do this
2. **Failure handling** — Many tools have retry/reflection logic
3. **Confidence scoring** — Common in ML (but not per-fact in knowledge graphs)
4. **Agent memory** — Everyone has this

### When to Use OSS:
- ✅ You already have Mem0/Zep/Letta for memory
- ✅ You already have LangGraph for orchestration
- ✅ You want to know WHICH facts are trustworthy
- ✅ You want agents to learn from failures
- ✅ You want visual quality badges
- ✅ You want zero-cost knowledge trust

### When NOT to Use OSS:
- ❌ You need agent orchestration (use LangGraph)
- ❌ You need observability/tracing (use LangSmith)
- ❌ You need memory across sessions (use Mem0/Zep/Letta)
- ❌ You need vector search (use Graphiti)
- ❌ You need temporal tracking (use Graphiti)

---

## Integration Matrix

| Your Stack | Add OSS? | What You Get |
|------------|----------|--------------|
| LangGraph alone | ✅ Yes | Knowledge trust + failure learning |
| LangGraph + LangSmith | ✅ Yes | Knowledge trust + tracing |
| Mem0 alone | ✅ Yes | Memory + trust scores |
| Zep alone | ✅ Yes | Temporal graphs + trust scores |
| Letta alone | ✅ Yes | Agent identity + knowledge trust |
| LangGraph + Mem0 | ✅ Yes | Orchestration + memory + trust |
| LangGraph + Zep | ✅ Yes | Orchestration + temporal + trust |
| LangGraph + Letta | ✅ Yes | Orchestration + identity + trust |
| Nothing (standalone) | ⚠️ Maybe | Basic knowledge graph with trust |

---

## Bottom Line

| Question | Answer |
|----------|--------|
| Is OSS a replacement for LangGraph? | **NO** — different purpose |
| Is OSS a replacement for Mem0? | **NO** — different purpose |
| Is OSS a replacement for Zep? | **NO** — different purpose |
| Is OSS a replacement for Letta? | **NO** — different purpose |
| Can OSS work WITH these tools? | **YES** — it's a layer |
| Is knowledge trust scoring unique? | **YES** — no one else does this |
| Should you use OSS? | **YES** — if you want to know which facts are trustworthy |
