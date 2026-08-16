# ContextOn.AI OSS + Understand-Anything Integration Plan

**Date:** August 2026
**Author:** ODEFTO AI Labs

---

## What Understand-Anything Is

| Aspect | Detail |
|--------|--------|
| Stars | 79.5K (massive adoption) |
| License | MIT |
| What it does | Turns codebases into interactive knowledge graphs |
| How it works | Multi-agent pipeline: tree-sitter (structural) + LLM (semantic) |
| Output | `.ua/knowledge-graph.json` — nodes (files, functions, classes) + edges (imports, calls) |
| Platforms | Claude Code, Codex, Cursor, Copilot, Gemini CLI, OpenCode, 15+ platforms |
| Key limitation | **No confidence scoring, no failure learning, no trust tracking** |

## Where ContextOn.AI OSS Fits

Understand-Anything builds the graph. ContextOn adds the trust layer.

```
Codebase
    │
    ▼
Understand-Anything (multi-agent pipeline)
    │
    ▼
.knowledge-graph.json (structure + semantic summaries)
    │
    ▼
ContextOn.AI OSS (confidence + failure learning)
    │
    ▼
Trust-aware codebase knowledge
```

## How It Works (Step by Step)

### Step 1: Understand-Anything Analyzes Code

Understand-Anything creates a graph like:

```json
{
  "nodes": [
    {"id": "file:src/auth/login.ts", "type": "file", "summary": "Handles user authentication"},
    {"id": "func:loginUser", "type": "function", "summary": "Validates credentials and creates session"},
    {"id": "class:AuthService", "type": "class", "summary": "Manages authentication lifecycle"}
  ],
  "edges": [
    {"source": "file:src/auth/login.ts", "target": "func:loginUser", "type": "contains"},
    {"source": "func:loginUser", "target": "class:AuthService", "type": "uses"}
  ]
}
```

### Step 2: Convert to ContextOn Format

A bridge script converts Understand-Anything nodes into ContextOn facts:

```python
import json
from contexton_ai_oss import ContextGraph

# Load Understand-Anything graph
with open(".ua/knowledge-graph.json") as f:
    ua_graph = json.load(f)

# Create ContextOn graph
graph = ContextGraph(data_dir="./codebase_memory")

# Ingest each node as a fact
for node in ua_graph["nodes"]:
    graph.ingest(
        query=f"What is {node['id']}?",
        answer=node.get("summary", f"Node: {node['id']}"),
        agent_id="understand-anything"
    )
```

### Step 3: Add Trust Layer

Now ContextOn tracks which code knowledge is trustworthy:

```python
# Developer confirms login.ts summary is accurate
graph.record_success(
    "What is src/auth/login.ts?",
    "Handles user authentication with OAuth2 and session tokens"
)

# Developer finds a wrong summary
graph.record_failure(
    "What is src/payment/process.ts?",
    "Processes Stripe payments only",
    reason="Also processes PayPal and bank transfers"
)

# Query with confidence ranking
results = graph.query("payment processing")
# Returns facts ranked by confidence, with 🟢🟡🔴 badges
```

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPER WORKFLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Developer runs: /understand (Understand-Anything)           │
│     │                                                           │
│     ▼                                                           │
│  2. Codebase analyzed → .ua/knowledge-graph.json                │
│     │                                                           │
│     ▼                                                           │
│  3. Bridge script converts to ContextOn format                  │
│     │                                                           │
│     ▼                                                           │
│  4. ContextOn graph created with codebase knowledge             │
│     │                                                           │
│     ▼                                                           │
│  5. Developer queries: "How does auth work?"                    │
│     │                                                           │
│     ▼                                                           │
│  6. ContextOn returns ranked facts with confidence badges       │
│     │                                                           │
│     ▼                                                           │
│  7. Developer corrects wrong summaries → record_failure         │
│     │                                                           │
│     ▼                                                           │
│  8. Developer confirms correct summaries → record_success       │
│     │                                                           │
│     ▼                                                           │
│  9. Codebase knowledge improves over time                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Value Proposition

| Without ContextOn | With ContextOn |
|-------------------|----------------|
| Graph shows structure | Graph shows structure + trust |
| All summaries treated equally | Summaries ranked by confidence |
| Wrong summaries persist forever | Wrong summaries flagged with 🔴 |
| No learning from corrections | Developer corrections improve confidence |
| Static snapshot | Living, learning knowledge base |

## Files to Create

| File | Purpose |
|------|---------|
| `bridge.py` | Convert Understand-Anything JSON → ContextOn graph |
| `cli.py` | `contexton-ai-oss from-ua .ua/knowledge-graph.json` |
| `README` | Integration guide for Understand-Anything users |

## Why This Matters for ContextOn Adoption

| Metric | Impact |
|--------|--------|
| Understand-Anything users | 79.5K stars = massive potential audience |
| Integration effort | Low — JSON bridge, no core changes needed |
| Value add | Immediate — trust layer on top of existing tool |
| Cross-promotion | Understand-Anything users discover ContextOn |
| Paper evidence | Real-world integration with established tool |

## Paper Angle

This integration strengthens the paper by showing ContextOn works as a **reliability layer on top of existing tools**, not just standalone:

> "ContextOn.AI OSS can be integrated with codebase analysis tools like Understand-Anything (79.5K GitHub stars) to add confidence scoring and failure learning to generated knowledge graphs. This demonstrates ContextOn's value as a general-purpose reliability infrastructure that enhances existing knowledge systems."
