# Announcing ContextOn.AI OSS

**Knowledge Graphs with Confidence Scoring and Failure Learning**

*By ODEFTO AI Labs*

---

## The Problem

AI agents today have **no memory**. Every conversation starts fresh. They don't learn from mistakes. They don't know which information is trustworthy.

Existing tools like Graphify, Graphiti, and Mem0 help, but they all miss something critical:

**None of them learn from failures.**

When an agent gives a wrong answer, the mistake is repeated forever.

---

## The Solution: ContextOn.AI OSS

ContextOn.AI OSS is an open-source knowledge graph engine that introduces three novel features:

### 1. Confidence Scoring

Every piece of knowledge has a trust score (0.0-1.0):

```
[PM-JAY] confidence: 0.95 (verified 10 times)
[Old Policy] confidence: 0.31 (only verified once, 6 months ago)
```

You know which information to trust.

### 2. Failure Learning (NOVEL)

When an agent gives a wrong answer, ContextOn.AI OSS remembers:

```python
graph.record_failure(
    query="What is PM-JAY?",
    answer="It's a housing scheme",
    reason="Incorrect - it's health insurance"
)

# Future queries now avoid this unreliable path!
```

**No other tool does this.**

### 3. Quality Badges

See at a glance which knowledge is trustworthy:

- 🟢 **High (≥0.8)**: Safe to use
- 🟡 **Medium (0.5-0.8)**: Verify first
- 🔴 **Low (<0.5)**: Don't trust without checking

---

## How It Works

```python
from contexton_ai_oss import ContextGraph

# Create a graph
graph = ContextGraph()

# Ingest knowledge from conversations
graph.ingest("What is PM-JAY?", "Health insurance for poor families")

# Query with confidence ranking
results = graph.query("PM-JAY coverage")
for r in results:
    print(f"{r['badge']} {r['node']['content'][:50]}")
    print(f"   Confidence: {r['confidence']:.1%}")

# Record failures
graph.record_failure("What is PM-JAY?", "It's housing", reason="Wrong")

# Now future queries avoid unreliable paths!
```

---

## Why This Matters

| Tool | What It Does | What It Misses |
|------|-------------|----------------|
| Graphify | Code knowledge graphs | No memory, no learning |
| Graphiti | Temporal agent memory | No confidence, no failure learning |
| Mem0 | Vector-based memory | No structure, no quality |
| **ContextOn.AI OSS** | **Confidence-aware graphs** | **Learns from failures** |

---

## Getting Started

```bash
# Install
pip install contexton-ai-oss

# Try the demo
python -m examples.failure_learning_demo
```

---

## What's Next

ContextOn.AI OSS is the **open-source version**. For enterprise features:

- **Isolation**: Different teams see different knowledge
- **Quality auditing**: Every answer scored on 5 dimensions
- **Drift detection**: Automatic context corruption prevention
- **Enterprise connectors**: SAP, ServiceNow, Salesforce

---

## Links

- **GitHub**: github.com/ODEFTO/contexton-ai-oss
- **Documentation**: github.com/ODEFTO/contexton-ai-oss/tree/main/docs
- **PyPI**: pypi.org/project/contexton-ai-oss

---

## About ODEFTO AI Labs

ODEFTO AI Labs builds AI infrastructure. ContextOn.AI OSS is our open-source project to teach the concept of confidence-aware knowledge graphs.

---

*Built with confidence. Learning from failures.*
