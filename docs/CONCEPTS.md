# ContextOn.AI OSS Concepts

**Understanding Context-Aware AI**

---

## What is a Knowledge Graph?

A knowledge graph is a way to represent information as **nodes** (concepts) and **edges** (relationships).

```
    [PM-JAY] ---implements---> [NHA]
       |
       |--- covers ---> [Health Insurance]
       |
       |--- targets ---> [Poor Families]
```

Instead of storing text in documents, you store **connections** between ideas.

### Why is this useful?

1. **Structure**: Information is organized, not just dumped
2. **Relationships**: You can see how concepts connect
3. **Traversal**: You can follow paths from one concept to another
4. **Querying**: You can ask "what connects X to Y?"

---

## The Problem with Traditional AI Memory

Most AI agents have **no memory**. Every conversation starts fresh.

```
User: "What is PM-JAY?"
Agent: "I don't know."

User: "Tell me about PM-JAY again"
Agent: "I don't know."  ← Forgot everything!
```

Some tools add memory, but they just **store text**:

```
Memory: ["PM-JAY is health insurance", "NHA implements PM-JAY"]
```

This has problems:
- ❌ No structure (just a pile of text)
- ❌ No confidence (is this information reliable?)
- ❌ No learning (doesn't improve over time)

---

## What ContextOn.AI OSS Does Differently

### 1. Confidence Scoring

Every piece of knowledge has a **trust score** (0.0-1.0):

```
[PM-JAY] confidence: 0.95 🟢
  "Verified 10 times, last checked yesterday"

[NHA] confidence: 0.72 🟡
  "Verified 3 times, last checked last week"

[Old Policy] confidence: 0.31 🔴
  "Only verified once, 6 months ago"
```

**Why this matters:** You know which information to trust.

### 2. Failure Learning (NOVEL)

When an agent gives a **wrong answer**, ContextOn.AI OSS remembers:

```
Agent: "PM-JAY is a housing scheme"  ← WRONG!
User: "That's incorrect"

ContextOn.AI OSS: 
  - Marks this path as unreliable
  - Reduces confidence
  - Future queries avoid this path
```

**Why this matters:** Agents learn from mistakes and improve.

### 3. Quality Badges

See at a glance which knowledge is trustworthy:

- 🟢 **High (≥0.8)**: Safe to use
- 🟡 **Medium (0.5-0.8)**: Verify first
- 🔴 **Low (<0.5)**: Don't trust without checking

**Why this matters:** Quick visual trust assessment.

---

## How Confidence is Calculated

Confidence is based on three factors:

### 1. Verification Count

```
Mentions: 1  → Base: 0.20
Mentions: 3  → Base: 0.60
Mentions: 5+ → Base: 1.00
```

More times verified = higher confidence.

### 2. Time Decay

```
Just verified:    × 1.00
1 week old:       × 0.70
1 month old:      × 0.21
6 months old:     × 0.002
```

Old information loses confidence.

### 3. Failure Penalty

```
0 failures: × 1.00
1 failure:  × 0.50
2 failures: × 0.25
3 failures: × 0.125
```

Each failure halves confidence.

**Final formula:**
```
confidence = base × decay × failure_penalty
```

---

## How Failure Learning Works

### Step 1: Agent Gives Wrong Answer

```
Query: "What is PM-JAY?"
Answer: "It's a housing scheme"  ← WRONG
```

### Step 2: User Reports Failure

```python
graph.record_failure(
    query="What is PM-JAY?",
    answer="It's a housing scheme",
    reason="Incorrect - it's health insurance"
)
```

### Step 3: Graph Updates

```
PM-JAY node:
  - failure_count: 1
  - confidence: 0.50 (was 0.95)

Edges to/from PM-JAY:
  - failure_count: 1
  - confidence: 0.50
```

### Step 4: Future Queries Avoid Failed Paths

```
Query: "PM-JAY coverage"

Results (sorted by reliability):
  🟢 "PM-JAY covers 5 lakh per family" (confidence: 0.92)
  🟡 "PM-JAY is for poor families" (confidence: 0.78)
  🔴 ~~"PM-JAY is housing scheme"~~ (confidence: 0.31, filtered out)
```

---

## Why This Matters for AI Agents

### Before ContextOn.AI OSS

```
Agent: "What is PM-JAY?"
Knowledge: ["PM-JAY is health insurance", "PM-JAY is housing scheme"]
Agent: *randomly picks one* ← Might be wrong!
```

### After ContextOn.AI OSS

```
Agent: "What is PM-JAY?"
Knowledge: 
  🟢 "PM-JAY is health insurance" (confidence: 0.92)
  🔴 "PM-JAY is housing scheme" (confidence: 0.31)
Agent: *picks high confidence* ← More likely correct!
```

---

## Comparison with Other Tools

| Concept | Graphify | Graphiti | Mem0 | **ContextOn.AI OSS** |
|---------|----------|----------|------|---------------------|
| Stores knowledge | ✅ | ✅ | ✅ | ✅ |
| Has structure | ✅ | ✅ | ❌ | ✅ |
| **Confidence scoring** | ❌ | ❌ | ❌ | ✅ |
| **Learns from failures** | ❌ | ❌ | ❌ | ✅ |
| **Quality badges** | ❌ | ❌ | ❌ | ✅ |

---

## Use Cases

### 1. AI Agent Memory

Give agents persistent memory that improves over time:

```python
# Agent remembers conversations
graph.ingest("How do I reset password?", "Go to settings")

# Agent learns from mistakes
graph.record_failure("How do I reset password?", "Call support")

# Agent uses reliable knowledge
results = graph.query("password reset")
```

### 2. Knowledge Base

Build a knowledge base that tracks reliability:

```python
# Add knowledge with confidence
graph.add_node("PM-JAY covers 5 lakh", confidence=0.9)

# Query returns confidence scores
results = graph.query("PM-JAY coverage")
# Returns: [{badge: "🟢", confidence: 0.9, ...}]
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

## Key Takeaways

1. **Knowledge graphs** organize information as nodes and edges
2. **Confidence scoring** tells you which knowledge is trustworthy
3. **Failure learning** lets agents learn from mistakes (NOVEL!)
4. **Quality badges** make trust visible at a glance

ContextOn.AI OSS is the **only** tool that combines all four.

---

## Next Steps

- [TUTORIAL.md](TUTORIAL.md) - Try it yourself
- [COMPARISON.md](COMPARISON.md) - See how we compare
- [UPGRADE.md](UPGRADE.md) - Need enterprise features?
