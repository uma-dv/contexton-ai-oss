# ContextOn.AI OSS - Technical Design Document

**By ODEFTO AI Labs**
**Version: 1.0 MVP**
**Date: August 2026**

---

## 1. Executive Summary

ContextOn.AI OSS is an open-source knowledge graph engine for AI agents that introduces **confidence-aware, failure-learning graph memory**. Unlike existing tools (Graphify, Graphiti, Mem0), ContextOn.AI OSS:

- **Learns from failures** - Marks unreliable knowledge paths
- **Scores confidence** - Every node/edge has trust indicators
- **Suggests questions** - Graph tells you what it can answer
- **Shows quality badges** - Visual trust indicators (🟢🟡🔴)
- **Cross-agent learning** - Agents share learned knowledge

This is the **lite version** - a teaching tool that demonstrates the concept. Enterprise features (isolation, quality auditing, compliance) are in the enterprise platform.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ContextOn.AI OSS Architecture                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Ingestion  │───►│  Graph Core  │───►│  Retrieval   │      │
│  │   Layer      │    │              │    │  Layer       │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Entity      │    │  Confidence  │    │  Query       │      │
│  │  Resolution  │    │  Engine      │    │  Engine      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             ▼                                   │
│                    ┌──────────────┐                             │
│                    │  Failure     │                             │
│                    │  Learning    │                             │
│                    └──────────────┘                             │
│                             │                                   │
│                             ▼                                   │
│                    ┌──────────────┐                             │
│                    │  Visualization│                             │
│                    │  (graph.html)│                             │
│                    └──────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 Graph Data Model

```python
# Node Structure
{
    "id": "sha256[:12]",
    "type": "fact|decision|conversation|entity|procedure|observation",
    "content": "The actual knowledge",
    "content_lower": "lowercase for search",
    "source": "conversation|task|manual",
    "confidence": 0.0-1.0,          # NOVEL: Trust score
    "mentions": 1,                   # How many times verified
    "last_verified": "ISO timestamp",
    "created_at": "ISO timestamp",
    "tags": ["extracted", "inferred", "ambiguous"]
}

# Edge Structure
{
    "source": "node_id",
    "target": "node_id",
    "type": "caused_by|related_to|depends_on|learned_from|contradicts|supports",
    "weight": 0.0-1.0,
    "confidence": 0.0-1.0,          # NOVEL: Edge trust score
    "rationale": "WHY this connection exists",  # NOVEL: Human-readable explanation
    "verified": True/False,          # NOVEL: Has been verified
    "failure_count": 0,              # NOVEL: Times this path failed
    "success_count": 0,              # NOVEL: Times this path succeeded
    "last_outcome": "success|failure|null",
    "created_at": "ISO timestamp"
}
```

### 3.2 Confidence Engine (NOVEL)

```python
class ConfidenceEngine:
    """Calculates confidence scores for nodes and edges."""
    
    def node_confidence(self, node: dict) -> float:
        """
        Confidence = f(mentions, last_verified, failure_count)
        
        Formula:
        - Base: min(1.0, mentions / 5)  # More mentions = higher confidence
        - Decay: * (0.95 ^ days_since_verified)  # Old knowledge decays
        - Failure penalty: * (0.5 ^ failure_count)  # Failures reduce confidence
        
        Returns: 0.0 to 1.0
        """
        base = min(1.0, node["mentions"] / 5)
        days_old = (now - node["last_verified"]).days
        decay = 0.95 ** days_old
        failure_penalty = 0.5 ** node.get("failure_count", 0)
        return base * decay * failure_penalty
    
    def edge_confidence(self, edge: dict) -> float:
        """
        Edge confidence = f(success_count, failure_count, weight)
        
        Formula:
        - Success rate: success_count / (success_count + failure_count + 1)
        - Weight factor: weight
        - Combined: success_rate * 0.7 + weight * 0.3
        
        Returns: 0.0 to 1.0
        """
        total = edge["success_count"] + edge["failure_count"] + 1
        success_rate = edge["success_count"] / total
        return success_rate * 0.7 + edge["weight"] * 0.3
```

### 3.3 Failure Learning Engine (NOVEL - Core Differentiator)

```python
class FailureLearningEngine:
    """Learns from agent failures to improve future retrieval."""
    
    def record_failure(self, query: str, answer: str, 
                       path: List[str], reason: str):
        """
        When an agent gives a bad answer:
        1. Mark all edges in the path as failed
        2. Reduce confidence of involved nodes
        3. Add failure metadata for analysis
        
        This ensures future queries avoid unreliable paths.
        """
        for edge_id in path:
            edge = self.graph.get_edge(edge_id)
            edge["failure_count"] += 1
            edge["last_outcome"] = "failure"
            edge["confidence"] *= 0.5  # Reduce confidence
        
        # Add observation node about the failure
        self.graph.add_node(
            content=f"FAILED: {query[:100]} → {answer[:100]}",
            type="observation",
            metadata={"reason": reason, "query": query, "answer": answer}
        )
    
    def record_success(self, query: str, answer: str, path: List[str]):
        """
        When an agent gives a good answer:
        1. Mark all edges in the path as successful
        2. Increase confidence of involved nodes
        3. Verify the knowledge is still valid
        """
        for edge_id in path:
            edge = self.graph.get_edge(edge_id)
            edge["success_count"] += 1
            edge["last_outcome"] = "success"
            edge["confidence"] = min(1.0, edge["confidence"] * 1.1)
        
        # Verify nodes in path
        for node_id in path:
            node = self.graph.get_node(node_id)
            node["last_verified"] = now()
            node["mentions"] += 1
    
    def get_reliable_paths(self, query: str, top_k: int = 5) -> List[dict]:
        """
        Retrieve paths ranked by RELIABILITY, not just relevance.
        
        Reliability = confidence * (1 - failure_rate)
        
        This ensures agents use knowledge that has been verified,
        avoiding paths that have failed before.
        """
        candidates = self.query(query)
        for path in candidates:
            path["reliability"] = self.calculate_reliability(path)
        
        return sorted(candidates, key=lambda x: -x["reliability"])[:top_k]
```

### 3.4 Suggested Questions Engine (NOVEL)

```python
class SuggestionEngine:
    """Analyzes graph to suggest questions it can answer."""
    
    def suggest_questions(self, top_n: int = 5) -> List[str]:
        """
        Analyzes graph structure to find:
        1. High-confidence nodes with few incoming queries
        2. Community gaps (connected concepts not yet asked about)
        3. Temporal patterns (topics that should be revisited)
        
        Returns: List of suggested questions
        """
        suggestions = []
        
        # Find high-confidence nodes with low query count
        for node in self.graph.get_high_confidence_nodes():
            if node["query_count"] < 3:
                suggestions.append({
                    "question": f"What is {node['content'][:50]}?",
                    "reason": "High confidence, rarely asked",
                    "confidence": node["confidence"]
                })
        
        # Find community gaps
        communities = self.graph.detect_communities()
        for comm_id, nodes in communities.items():
            if len(nodes) < 3:
                suggestions.append({
                    "question": f"Tell me about {nodes[0]['content'][:50]}",
                    "reason": "Underexplored community",
                    "confidence": 0.7
                })
        
        return sorted(suggestions, key=lambda x: -x["confidence"])[:top_n]
```

### 3.5 Quality Badge System (NOVEL)

```python
class QualityBadges:
    """Visual quality indicators for graph nodes."""
    
    def get_badge(self, confidence: float) -> str:
        """
        Returns visual badge based on confidence:
        - 🟢 High: confidence >= 0.8 (verified, reliable)
        - 🟡 Medium: 0.5 <= confidence < 0.8 (needs verification)
        - 🔴 Low: confidence < 0.5 (unreliable, verify before using)
        """
        if confidence >= 0.8:
            return "🟢"
        elif confidence >= 0.5:
            return "🟡"
        else:
            return "🔴"
    
    def get_quality_summary(self, node: dict) -> dict:
        """Returns comprehensive quality info for a node."""
        return {
            "badge": self.get_badge(node["confidence"]),
            "confidence": node["confidence"],
            "mentions": node["mentions"],
            "last_verified": node["last_verified"],
            "failure_count": node.get("failure_count", 0),
            "status": self.get_status(node)
        }
    
    def get_status(self, node: dict) -> str:
        """Returns human-readable status."""
        if node["confidence"] >= 0.8:
            return "Verified and reliable"
        elif node["confidence"] >= 0.5:
            return "Needs verification"
        elif node.get("failure_count", 0) > 2:
            return "Frequently fails - verify before using"
        else:
            return "Low confidence - use with caution"
```

---

## 4. Data Flow

### 4.1 Ingestion Flow

```
User Input → Entity Extraction → Graph Building → Confidence Scoring
     │              │                    │                │
     ▼              ▼                    ▼                ▼
  "What is    Extract: PM-JAY,     Add nodes and     Calculate
   PM-JAY?"   NHA, health          edges with        confidence
              insurance            EXTRACTED tags    scores
```

### 4.2 Query Flow

```
User Query → Query Expansion → Confidence-Ranked Retrieval → Quality Badges
     │              │                    │                         │
     ▼              ▼                    ▼                         ▼
  "Tell me    "PM-JAY, Pradhan     Get paths sorted        Add 🟢🟡🔴
   about      Mantri, health       by reliability         badges
   PM-JAY"    insurance"           (not just relevance)
```

### 4.3 Failure Learning Flow

```
Agent Answer → User Feedback → Path Marking → Confidence Update
     │              │               │               │
     ▼              ▼               ▼               ▼
  Agent gives   "That's wrong"   Mark edges as   Reduce confidence
  answer        OR "That's good" failed/success   of failed paths
```

---

## 5. API Design

### 5.1 Core API

```python
from contexton_ai_oss import ContextGraph

# Initialize
graph = ContextGraph()

# Ingest knowledge
graph.ingest(
    query="What is PM-JAY?",
    answer="Pradhan Mantri Jan Arogya Yojana is health insurance...",
    agent_id="health-agent",
    confidence=0.9  # Optional: agent's confidence in answer
)

# Query with confidence ranking
results = graph.query(
    "PM-JAY coverage",
    min_confidence=0.5,  # Only return reliable results
    max_results=5
)

# Record failure
graph.record_failure(
    query="What is PM-JAY?",
    answer="It's a housing scheme",  # Wrong answer
    reason="Incorrect - it's health insurance, not housing"
)

# Record success
graph.record_success(
    query="What is PM-JAY?",
    answer="Health insurance for poor families"
)

# Get suggestions
suggestions = graph.suggest_questions(top_n=5)

# Visualize
graph.visualize("graph.html")
```

### 5.2 MCP Server

```bash
# Start MCP server over stdio (for Claude/Cursor MCP configs)
contexton-ai-oss serve

# Start MCP server over streamable HTTP
contexton-ai-oss serve --port 8080

# Persist the graph to a directory
contexton-ai-oss serve --data-dir ./data
```

Exposed tools: `ingest`, `query`, `record_failure`, `record_success`,
`suggest_questions`, `get_stats`, `get_aliases`, `resolve_aliases`,
`get_confidence_breakdown`, `visualize`.

---

## 6. File Structure

```
contexton-ai-oss/
├── README.md                    # Quick start guide
├── TECHNICAL_DESIGN.md          # This document
├── LICENSE                      # Apache 2.0
├── pyproject.toml               # Package config
├── contexton_ai_oss/
│   ├── __init__.py              # Package exports
│   ├── graph.py                 # Core graph data structure + query + ingestion
│   ├── confidence.py            # Confidence engine (single source of truth)
│   ├── failure_learning.py      # Failure learning engine
│   ├── quality.py               # Quality badge system
│   ├── entities.py              # Entity extraction + alias resolution
│   ├── text_utils.py            # Normalization / tokenization helpers
│   ├── visualization.py         # Graph visualization
│   ├── mcp_server.py            # MCP server (tools for Claude/Cursor)
│   └── cli.py                   # `contexton-ai-oss` command-line interface
├── docs/
│   ├── CONCEPTS.md              # Teaching the concept
│   ├── TUTORIAL.md              # Step-by-step guide
│   ├── COMPARISON.md            # vs Graphify, Graphiti, etc.
│   └── UPGRADE.md               # Enterprise upgrade path
├── examples/
│   └── failure_learning_demo.py # Demonstrates failure learning
└── tests/
    └── test_core.py             # Unit tests (23 passing)
```

---

## 7. Dependencies

```toml
[project]
name = "contexton-ai-oss"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
mcp = ["mcp>=2.0"]       # MCP server support
vis = ["plotly>=5.0"]    # Interactive visualization
dev = ["pytest>=7.0", "mcp>=2.0"]

[project.scripts]
contexton-ai-oss = "contexton_ai_oss.cli:main"
```

---

## 8. What's NOT in Open Source (Core IP)

| Feature | In Open Source? | In Paid Platform? |
|---------|----------------|-------------------|
| Basic graph building | ✅ | ✅ |
| Confidence scoring | ✅ | ✅ Enhanced |
| Failure learning | ✅ | ✅ Enhanced |
| Quality badges | ✅ | ✅ |
| Suggested questions | ✅ | ✅ Enhanced |
| Entity aliases | ✅ | ✅ Enhanced |
| Graph visualization | ✅ | ✅ |
| MCP server | ✅ | ✅ |
| **Isolation engine** | ❌ | ✅ |
| **Quality scoring** | ❌ | ✅ |
| **Drift detection** | ❌ | ✅ |
| **Multi-tenant isolation** | ❌ | ✅ |
| **Enterprise connectors** | ❌ | ✅ |
| **Compliance reporting** | ❌ | ✅ |

---

## 9. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| GitHub stars | 10,000+ in 6 months | GitHub analytics |
| PyPI downloads | 50,000+ in 6 months | PyPI stats |
| Failure learning demo | "Aha!" moment in < 5 min | User testing |
| Upgrade conversion | 5% of users upgrade | Analytics |
| Community contributions | 10+ PRs in 6 months | GitHub |

---

## 10. Roadmap

### Phase 1: MVP (Weeks 1-3)
- [x] Core graph engine
- [x] Confidence scoring
- [x] Failure learning
- [x] Quality badges
- [x] Basic visualization

### Phase 2: Polish (Weeks 4-6)
- [x] Suggested questions
- [x] Entity resolution (aliases)
- [x] MCP server (`contexton-ai-oss serve`)
- [x] Documentation
- [x] Examples

### Phase 3: Launch (Weeks 7-8)
- [ ] GitHub release
- [ ] PyPI publish
- [ ] Blog post
- [ ] Community setup

---

*This document describes the open-source ContextON_Graph. For enterprise features (isolation, quality auditing, compliance), see the enterprise platform documentation.*
