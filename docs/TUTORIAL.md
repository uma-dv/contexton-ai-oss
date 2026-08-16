# Tutorial: ContextOn.AI OSS Step by Step

This tutorial walks through the features that are actually implemented:
graph building, confidence scoring, failure learning, entity resolution,
visualization, and the MCP server.

## 1. Install and Run

```bash
pip install contexton-ai-oss
python examples/failure_learning_demo.py
```

You should see the demo ingest knowledge about PM-JAY, record a wrong
answer, watch confidence drop, record a correct answer, and watch
confidence recover.

## 2. Build a Graph

```python
from contexton_ai_oss import ContextGraph

graph = ContextGraph()  # pass data_dir="path" to persist to disk

graph.ingest(
    query="What is PM-JAY?",
    answer="Pradhan Mantri Jan Arogya Yojana is health insurance for poor families",
    agent_id="health-agent",
)
```

`ingest` creates:
- a **conversation node** (question + answer)
- **entity nodes** (capitalized names like "PM-JAY", "Pradhan Mantri Jan Arogya Yojana")
- **fact nodes** (sentences from the answer)

## 3. Query with Confidence

```python
results = graph.query("PM-JAY coverage")
for r in results:
    print(r["badge"], f"{r['confidence']:.0%}", r["node"]["content"][:60])
```

Results are ranked by relevance and confidence, and carry a quality badge:
🟢 (≥ 0.8), 🟡 (0.5–0.8), 🔴 (< 0.5). Query matching is
punctuation-insensitive, so `PM-JAY?` and `PM-JAY` match the same nodes.

## 4. Learn from Failures (the key feature)

```python
# Agent gave a wrong answer
graph.record_failure(
    query="What is PM-JAY?",
    answer="PM-JAY is a housing scheme",
    reason="It's health insurance, not housing",
)

# Confidence in the related knowledge drops
graph.query("PM-JAY")  # results now show 🔴

# Agent later gives the correct answer
graph.record_success(
    query="What is PM-JAY?",
    answer="PM-JAY is health insurance for poor families",
)

# Confidence is restored
graph.query("PM-JAY")  # results back to 🟢
```

Failure observations are bookkeeping - they are never returned in query
results.

## 5. Entity Resolution

Aliases are resolved automatically at ingestion:

```python
graph.ingest("What is PM-JAY?", "Pradhan Mantri Jan Arogya Yojana is health insurance")
graph.ingest("Who implements PM-JAY?", "NHA implements it")

graph.get_aliases()
# {'PM-JAY': ['Pradhan Mantri Jan Arogya Yojana'], 'National Health Authority': ['NHA']}
```

"PM-JAY" and "Pradhan Mantri Jan Arogya Yojana" map to one canonical
entity node (initialism matching). Run `graph.resolve_aliases()` to merge
any duplicates that already exist.

## 6. Visualize

```python
graph.visualize("graph.html")  # open in a browser
```

Nodes are colored by confidence and show 🟢🟡🔴 badges. Requires internet
access for the vis.js CDN.

## 7. Use with Claude / Cursor via MCP

```bash
pip install "contexton-ai-oss[mcp]"
contexton-ai-oss serve            # stdio
# or
contexton-ai-oss serve --port 8080
```

The server exposes tools for `ingest`, `query`, `record_failure`,
`record_success`, `suggest_questions`, `get_stats`, `get_aliases`,
`resolve_aliases`, `get_confidence_breakdown`, and `visualize`.

## 8. Suggested Questions

```python
for s in graph.suggest_questions(top_n=3):
    print(s["badge"], s["question"], "—", s["reason"])
```

The graph suggests questions about high-confidence entities it knows
about but that haven't been asked yet.

## 9. Inspect Confidence

```python
node = graph.get_node(node_id)
breakdown = graph.confidence_engine.get_confidence_breakdown(node)
print(breakdown)
```

Shows how the score was derived: stored confidence, mentions, time decay,
and failure penalty.

## 10. Skills (Procedures)

```python
graph.ingest_procedure(
    name="Reset password",
    steps=["Open settings", "Go to security", "Click reset", "Confirm email"],
    agent_id="support-agent",
)

proc = graph.get_procedure("Reset password")
print(proc["steps"])   # ordered steps
print(proc["badge"])   # 🟢 confidence badge

# Procedures are retrievable like any knowledge
results = graph.query("reset password", node_type="procedure")
```

## 11. Tool Registry Memory

```python
graph.register_tool("send_email", "Sends an email", agent_id="mail-agent")
graph.register_tool("calculator", "Performs arithmetic")

# Tools carry confidence; failures penalize them
result = graph.record_tool_outcome("send_email", success=False, error="SMTP timeout")
print(result["confidence"])  # dropped

graph.list_tools()  # badge, confidence, failure_count per tool
```

## 12. Auto-Context Injection

```python
# Ingest with a session so context can be scoped to a conversation thread
graph.ingest("What is PM-JAY?", "PM-JAY is health insurance...", session_id="sess-1")

# Assemble a confident, badge-annotated context pack for an agent
ctx = graph.get_context("PM-JAY", session_id="sess-1")
print(ctx["context_text"])   # ready-to-use context for the agent
print(ctx["item_count"])     # how many items were included
```

`get_context` filters below `min_confidence`, dedupes, and packs items to
a token budget - this is the "context" layer an agent consumes.

## 13. Memory Hygiene (Schedule)

```python
report = graph.hygiene_sweep(max_age_days=30, min_confidence=0.5)
print(report["stale_count"], report["low_confidence_count"])
print(report["recommendation"])

# Dry-run prune first, then actually prune old low-confidence facts
print(graph.prune(dry_run=True)["message"])
graph.prune(dry_run=False)
```

Run this nightly (cron) - it keeps the graph trustworthy without
manual effort.

## 14. Per-Agent Scoping (Transparency)

```python
graph.ingest("How do I fix the server?", "Restart nginx", agent_id="ops-agent")

# Only see knowledge owned by one agent
results = graph.query("server", agent_id="ops-agent")
memory = graph.get_agent_memory("ops-agent")
print(memory["by_type"])
```

This is a read filter, not security - the enterprise platform
enforces real isolation.

## 15. Browser Demo

```bash
contexton-ai-oss web --port 8080
# open http://127.0.0.1:8080
```

The web demo covers everything: ingest, query, auto-context, skills,
tools, failure learning, aliases, hygiene, stats, and a live graph.
