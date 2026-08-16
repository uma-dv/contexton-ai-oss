# ContextOn.AI OSS

**Knowledge Graphs with Confidence Scoring and Failure Learning**

By ODEFTO AI Labs | [Enterprise Version (ContextOn.AI)](https://contexton.ai)

---

## What is ContextOn.AI OSS?

ContextOn.AI OSS is an open-source knowledge graph engine for AI agents that introduces **confidence-aware, failure-learning graph memory**.

Unlike existing tools, ContextOn.AI OSS:
- 🟢 **Scores confidence** - Every piece of knowledge has a trust indicator
- 🔴 **Learns from failures** - Marks unreliable knowledge so agents avoid it
- 📊 **Shows quality badges** - Visual trust indicators (🟢🟡🔴)
- 💡 **Suggests questions** - Graph tells you what it can answer
- 🔗 **Resolves entity aliases** - Links "PM-JAY" to "Pradhan Mantri Jan Arogya Yojana"
- 🛠️ **Skills** - Stores reusable procedures ("how to") with steps and confidence
- 🧰 **Tool registry memory** - Tracks tools, their descriptions, and which ones fail
- 📦 **Auto-context injection** - `get_context()` assembles confident, badge-annotated context for agents
- 🧹 **Memory hygiene** - Decay sweeps flag stale / low-confidence knowledge for re-verification
- 🎭 **Per-agent scoping** - Filter knowledge by agent (transparency)
- 🛰️ **Works with Claude/Cursor** - MCP server included
- 🌐 **Web demo** - `contexton-ai-oss web` runs a browser demo of everything

---

## Quick Start

### Installation

```bash
pip install contexton-ai-oss
```

### Basic Usage

```python
from contexton_ai_oss import ContextGraph

# Create a graph
graph = ContextGraph()

# Ingest knowledge from conversations
graph.ingest(
    query="What is PM-JAY?",
    answer="Pradhan Mantri Jan Arogya Yojana is health insurance for poor families",
    agent_id="health-agent"
)

# Query with confidence ranking
results = graph.query("PM-JAY coverage")
for result in results:
    print(f"{result['badge']} {result['node']['content'][:50]}")
    print(f"   Confidence: {result['confidence']:.1%}")
```

### Recording Failures (KEY FEATURE)

```python
# When your agent gives a wrong answer, tell the graph:
graph.record_failure(
    query="What is PM-JAY?",
    answer="It's a housing scheme",
    reason="Incorrect - it's health insurance, not housing"
)

# Confidence in the related knowledge drops (🔴) and failure observations
# are never returned in query results.

# When the agent later gives a correct answer, record the success:
graph.record_success(
    query="What is PM-JAY?",
    answer="It's health insurance for poor families"
)

# Confidence is restored.
```

### Visualizing the Graph

```python
# Generate interactive HTML visualization
graph.visualize("graph.html")
# Open graph.html in your browser
```

---

## Why ContextOn.AI OSS is Different

| Feature | Graphify | Graphiti | Mem0 | **ContextOn.AI OSS** |
|---------|----------|----------|------|---------------------|
| Knowledge graphs | ✅ | ✅ | ❌ | ✅ |
| Agent memory | ❌ | ✅ | ✅ | ✅ |
| **Confidence scoring** | ❌ | ❌ | ❌ | ✅ |
| **Failure learning** | ❌ | ❌ | ❌ | ✅ |
| **Quality badges** | ❌ | ❌ | ❌ | ✅ |
| **Suggested questions** | ❌ | ❌ | ❌ | ✅ |
| Simple to use | ✅ | ❌ | ✅ | ✅ |

**Key Differentiator:** No other tool learns from failures. See [COMPARISON.md](docs/COMPARISON.md) for verified market analysis.

---

## Key Features

### 1. Confidence Scoring

Every node and edge has a confidence score (0.0-1.0) based on:
- How many times it's been verified
- How old the information is
- How many times it's failed

```python
# Get confidence breakdown
node = graph.get_node("node_id")
breakdown = graph.confidence_engine.get_confidence_breakdown(node)
print(breakdown)
# {'mentions': 5, 'base_score': 1.0, 'days_since_verified': 2, ...}
```

### 2. Failure Learning (NOVEL)

No other tool learns from mistakes. ContextOn.AI OSS does:

```python
# Record a failure
graph.record_failure(
    query="What is X?",
    answer="Wrong answer",
    reason="Because Y"
)

# The graph now avoids paths that led to this failure
# Future queries prefer more reliable knowledge
```

### 3. Quality Badges

See at a glance which knowledge is trustworthy:

- 🟢 **High confidence (≥0.8)**: Verified, reliable
- 🟡 **Medium confidence (0.5-0.8)**: Needs verification  
- 🔴 **Low confidence (<0.5)**: Unreliable, verify before using

### 4. Suggested Questions

The graph analyzes itself and suggests questions it can answer:

```python
suggestions = graph.suggest_questions()
for s in suggestions:
    print(f"{s['badge']} {s['question']}")
    print(f"   Reason: {s['reason']}")
```

---

## Use Cases

### 1. AI Agent Memory

Give your agents persistent memory that learns and improves:

```python
# Agent remembers past conversations
graph.ingest("How do I reset password?", "Go to settings → security")

# Later, agent can retrieve this knowledge
results = graph.query("password reset")
```

### 2. Knowledge Base

Build a knowledge base that tracks reliability:

```python
# Add knowledge with confidence
graph.add_node("PM-JAY covers 5 lakh per family", confidence=0.9)

# Query returns confidence scores
results = graph.query("PM-JAY coverage")
```

### 3. Multi-Agent Systems

Agents share knowledge and learn from each other:

```python
# Agent A learns something
graph.ingest("X causes Y", agent_id="agent-a")

# Agent B can query this knowledge
results = graph.query("what causes Y")
```

---

## Integration with AI Assistants

### Claude Code / Cursor / Codex (via MCP)

Install with MCP support, then start the server:

```bash
pip install "contexton-ai-oss[mcp]"

# stdio transport (recommended for Claude Code / Cursor)
contexton-ai-oss serve

# or streamable HTTP
contexton-ai-oss serve --port 8080
```

Add to Claude Code's MCP config (`.mcp.json`):

```json
{
  "mcpServers": {
    "contexton-ai-oss": {
      "command": "contexton-ai-oss",
      "args": ["serve"]
    }
  }
}
```

Exposed tools: `ingest`, `query`, `record_failure`, `record_success`,
`suggest_questions`, `get_stats`, `get_aliases`, `resolve_aliases`,
`get_confidence_breakdown`, `visualize`.

### Cursor

```bash
# Add to .cursor/rules
ContextOn.AI OSS is available for knowledge retrieval.
Use contexton-ai-oss query for knowledge questions.
```

### Custom Agents

```python
from contexton_ai_oss import ContextGraph

class MyAgent:
    def __init__(self):
        self.memory = ContextGraph()
    
    def answer(self, query):
        # Retrieve relevant knowledge
        knowledge = self.memory.query(query)
        
        # Use knowledge to answer
        return self.generate_answer(query, knowledge)
    
    def learn(self, query, answer, correct):
        if correct:
            self.memory.record_success(query, answer)
        else:
            self.memory.record_failure(query, answer)
```

---

## Command Line Interface

```bash
# Ingest a conversation turn
contexton-ai-oss ingest "What is PM-JAY?" "PM-JAY is health insurance for poor families"

# Query with confidence-ranked results
contexton-ai-oss query "PM-JAY coverage"

# Record that an agent gave a wrong / correct answer
contexton-ai-oss record-failure "What is PM-JAY?" "It's a housing scheme" --reason "wrong"
contexton-ai-oss record-success "What is PM-JAY?" "It's health insurance"

# Skills (procedures)
contexton-ai-oss procedure ingest "Reset password" --steps "Open settings; Go to security; Click reset"
contexton-ai-oss procedure get "Reset password"

# Tools
contexton-ai-oss tools register send_email --description "Sends an email"
contexton-ai-oss tools list
contexton-ai-oss tools outcome send_email --error "SMTP timeout"

# Auto-context for agents
contexton-ai-oss context "PM-JAY coverage" --session sess-1

# Memory hygiene + per-agent view
contexton-ai-oss hygiene
contexton-ai-oss agent-memory health-agent

# Statistics, aliases, visualization, browser demo
contexton-ai-oss stats
contexton-ai-oss aliases
contexton-ai-oss visualize graph.html
contexton-ai-oss web --port 8080   # full browser demo

# All commands accept --data-dir DIR to persist the graph to disk
```

## Documentation

- [CONCEPTS.md](docs/CONCEPTS.md) - Why context-aware AI matters
- [TUTORIAL.md](docs/TUTORIAL.md) - Step-by-step guide
- [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) - Market comparison, AI deployment fit, hybrid embedding integration
- [COMPARISON.md](docs/COMPARISON.md) - Verified market comparison
- [UPGRADE.md](docs/UPGRADE.md) - Enterprise upgrade path
- [LAUNCH_STRATEGY.md](docs/LAUNCH_STRATEGY.md) - Launch plan and checklist

---

## Enterprise Features

ContextOn.AI OSS is the **open-source version**, built by [ODEFTO AI Labs](https://github.com/ODEFTO/contexton-ai-oss). For enterprise features, see [ContextOn.AI](https://contexton.ai):

| Feature | ContextOn.AI OSS | ContextOn.AI (Enterprise) |
|---------|-----------------|---------------------------|
| Basic graph building | ✅ | ✅ |
| Confidence scoring | ✅ | ✅ Enhanced |
| Failure learning | ✅ | ✅ Enhanced |
| Quality badges | ✅ | ✅ |
| **Isolation** | ❌ | ✅ |
| **Quality auditing** | ❌ | ✅ 5-dimension scoring |
| **Drift detection** | ❌ | ✅ |
| **Enterprise connectors** | ❌ | ✅ SAP, ServiceNow, Salesforce |
| **Compliance reporting** | ❌ | ✅ |

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

Apache 2.0 - See [LICENSE](LICENSE)

---

## Support

- 📧 Email: contact@contexton.ai
- 💬 Discussions: [GitHub Discussions](https://github.com/ODEFTO/contexton-ai-oss/discussions)
- 🐛 Issues: [GitHub Issues](https://github.com/ODEFTO/contexton-ai-oss/issues)

---

## Acknowledgments

Built by [ODEFTO AI Labs](https://github.com/ODEFTO/contexton-ai-oss).

Inspired by Graphify, Graphiti, and Mem0.
