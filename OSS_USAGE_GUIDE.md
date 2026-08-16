# ContextOn.AI OSS — Real Enterprise Usage Guide

**How a developer uses ContextOn.AI OSS in production (step by step)**

---

## Scenario: Enterprise AI Support Agent

**Company:** A bank deploying an AI agent to answer customer queries about loans, fraud, and account issues.

**Problem:** The agent gives wrong answers. Customers complain. The bank loses trust.

**Solution:** ContextOn.AI OSS tracks which knowledge is trustworthy and learns from failures.

---

## Step-by-Step Usage

### Phase 1: Setup (Day 1)

| Step | Action | Command | What Happens |
|------|--------|---------|--------------|
| 1 | Install | `pip install contexton-ai-oss` | Package installed |
| 2 | Initialize | `from contexton_ai_oss import ContextGraph` | Graph created in memory |
| 3 | Persist to disk | `graph = ContextGraph(data_dir="./bank_memory")` | Graph saves to JSON files |

### Phase 2: Ingest Knowledge (Day 1-2)

| Step | Action | Command | What Happens |
|------|--------|---------|--------------|
| 4 | Ingest loan info | `graph.ingest("What is a home loan?", "A home loan is...", agent_id="support-agent")` | Facts stored as nodes |
| 5 | Ingest fraud rules | `graph.ingest("What triggers fraud alert?", "Unusual transactions over $5000...", agent_id="support-agent")` | More knowledge added |
| 6 | Ingest procedures | `graph.ingest_procedure("Block stolen card", ["Verify identity", "Freeze card", "Issue new"], agent_id="support-agent")` | Procedure stored with steps |
| 7 | Register tools | `graph.register_tool("crm_lookup", "Look up customer in CRM", agent_id="support-agent")` | Tool registered |

### Phase 3: Agent Uses Knowledge (Day 2+)

| Step | Action | Command | What Happens |
|------|--------|---------|--------------|
| 8 | Query | `results = graph.query("home loan interest rate")` | Returns facts ranked by confidence |
| 9 | Get context | `ctx = graph.get_context("fraud alert", session_id="cust-123")` | Badge-annotated context for agent |
| 10 | Use in LLM | `prompt = f"Context: {ctx['context_text']}\n\nUser asks: {query}"` | Agent uses trusted knowledge |

### Phase 4: Learn from Failures (Day 3+)

| Step | Action | Command | What Happens |
|------|--------|---------|--------------|
| 11 | Agent gives WRONG answer | `graph.record_failure("What is fraud alert?", "Only triggered by missing payment", reason="Wrong - also triggered by unusual transactions")` | Confidence drops, badge turns 🔴 |
| 12 | Query again | `results = graph.query("fraud alert")` | Same facts now show lower confidence |
| 13 | Agent gives CORRECT answer | `graph.record_success("What is fraud alert?", "Unusual transactions above $5000 trigger fraud alert")` | Confidence restored, badge turns 🟢 |
| 14 | Query again | `results = graph.query("fraud alert")` | Trusted knowledge ranked higher |

### Phase 5: Monitor Quality (Day 7+)

| Step | Action | Command | What Happens |
|------|--------|---------|--------------|
| 15 | Check stats | `graph.get_stats()` | See node count, avg confidence, failures |
| 16 | Hygiene sweep | `graph.hygiene_sweep(max_age_days=30)` | Flag stale/low-confidence knowledge |
| 17 | Suggest questions | `graph.suggest_questions()` | Graph tells you what it can answer |
| 18 | Visualize | `graph.visualize("bank_graph.html")` | Interactive HTML graph |

### Phase 6: Production Deployment (Day 14+)

| Step | Action | Command | What Happens |
|------|--------|---------|--------------|
| 19 | Start MCP server | `contexton-ai-oss serve` | Claude/Cursor can use the graph |
| 20 | Or use HTTP | `contexton-ai-oss serve --port 8080` | REST API for any agent |
| 21 | Or use web demo | `contexton-ai-oss web` | Browser UI for testing |

---

## Real Usage Flow (Visual)

```
Day 1: Setup
  $ pip install contexton-ai-oss
  $ python -c "from contexton_ai_oss import ContextGraph; g = ContextGraph(data_dir='./data')"

Day 1-2: Ingest Knowledge
  $ python -c "
  from contexton_ai_oss import ContextGraph
  g = ContextGraph(data_dir='./data')
  g.ingest('What is KYC?', 'Know Your Customer verification process')
  g.ingest('What is AML?', 'Anti-Money Laundering compliance checks')
  g.ingest_procedure('Verify identity', ['Check ID', 'Match photo', 'Record details'])
  "

Day 2+: Agent Runs
  $ python -c "
  from contexton_ai_oss import ContextGraph
  g = ContextGraph(data_dir='./data')
  ctx = g.get_context('customer wants to open account')
  print(ctx['context_text'])
  "

Day 3+: Learning
  $ python -c "
  from contexton_ai_oss import ContextGraph
  g = ContextGraph(data_dir='./data')
  g.record_failure('What is KYC?', 'Only needed for new accounts', reason='Wrong - needed for all')
  g.record_success('What is KYC?', 'Required for all account openings')
  "

Day 7+: Monitoring
  $ contexton-ai-oss stats
  $ contexton-ai-oss hygiene
  $ contexton-ai-oss visualize graph.html

Day 14+: Production
  $ contexton-ai-oss serve --port 8080
```

---

## What the User Gets (Value Proposition)

| Before OSS | After OSS |
|------------|-----------|
| Agent gives wrong answers | Agent knows which answers are trustworthy |
| No memory of past mistakes | Agent learns from failures |
| Customer complains | Confidence drops, agent avoids bad knowledge |
| Agent corrects itself | Confidence restored, agent uses good knowledge |
| No way to inspect knowledge | Visual graph shows what agent learned |
| No quality metrics | 🟢🟡🔴 badges show trust level |

---

## Key Metrics the User Tracks

| Metric | What It Means | How to Get It |
|--------|--------------|---------------|
| `node_count` | Total knowledge stored | `graph.get_stats()['node_count']` |
| `avg_confidence` | Overall trust level | `graph.get_stats()['avg_confidence']` |
| `high_confidence_nodes` | Trusted knowledge count | `graph.get_stats()['high_confidence_nodes']` |
| `low_confidence_nodes` | Unreliable knowledge count | `graph.get_stats()['low_confidence_nodes']` |
| `failure_count` | How many mistakes recorded | `graph.get_stats()['failure_count']` |

---

## Why This Is Different

| Traditional Approach | ContextOn.AI OSS |
|---------------------|------------------|
| Agent stores everything equally | Agent tracks trust per fact |
| Wrong answers stay wrong forever | Wrong answers lower confidence |
| No way to know what's reliable | Quality badges (🟢🟡🔴) |
| No learning from mistakes | Failure learning engine |
| Embeddings needed | Deterministic keyword match |
| External services required | Zero dependencies |
