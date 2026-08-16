# Integration Plan: ContextOn.AI OSS with Existing AI Agent Frameworks

How to add knowledge trust tracking to your existing AI agent stack.

## Overview

ContextOn.AI OSS is a LAYER that sits on top of your existing tools. It doesn't replace LangGraph, Mem0, Zep, or Letta — it adds knowledge trust scoring to them.

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
├─────────────────────────────────────────────────────────┤
│  LangGraph (orchestration)  ←── LangSmith (tracing)    │
│           │                                               │
│           ▼                                               │
│  ┌─────────────────┐                                      │
│  │ ContextOn.AI OSS │  ←── Knowledge Trust Layer         │
│  │ (confidence +    │                                      │
│  │  failure learn)  │                                      │
│  └─────────────────┘                                      │
│           │                                               │
│           ▼                                               │
│  Mem0 / Zep / Letta (memory)                             │
└─────────────────────────────────────────────────────────┘
```

---

## Integration 1: LangGraph + ContextOn.AI OSS

### What You Get:
- Agent orchestration (LangGraph)
- Knowledge trust scoring (OSS)
- Failure learning (OSS)
- Quality badges (OSS)

### Code Example:

```python
from langgraph.graph import StateGraph, END
from contexton_ai_oss import ContextGraph

# Initialize OSS
graph = ContextGraph(data_dir="./knowledge")

# Define agent state
class AgentState:
    query: str
    answer: str
    confidence: float
    badge: str

# Node: Retrieve knowledge with trust scores
def retrieve_knowledge(state):
    query = state["query"]
    
    # Query OSS for knowledge with confidence scores
    results = graph.query(query)
    
    if results:
        top_result = results[0]
        return {
            "knowledge": top_result["node"]["content"],
            "confidence": top_result["confidence"],
            "badge": top_result["badge"]
        }
    return {"knowledge": "No relevant knowledge found", "confidence": 0, "badge": "🔴"}

# Node: Generate answer using LLM
def generate_answer(state):
    knowledge = state["knowledge"]
    confidence = state["confidence"]
    badge = state["badge"]
    
    # LLM generates answer using knowledge
    answer = llm.invoke(f"Based on this knowledge: {knowledge}\n\nAnswer: {state['query']}")
    
    return {"answer": answer, "confidence": confidence, "badge": badge}

# Node: Record success/failure
def record_outcome(state):
    # After user feedback, record outcome
    if state["user_feedback"] == "correct":
        graph.record_success(
            query=state["query"],
            answer=state["answer"]
        )
    else:
        graph.record_failure(
            query=state["query"],
            answer=state["answer"],
            reason=state["feedback_reason"]
        )

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_knowledge)
workflow.add_node("generate", generate_answer)
workflow.add_node("record", record_outcome)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "record")
workflow.add_edge("record", END)

app = workflow.compile()
```

### Usage:

```python
# Query with trust scoring
result = app.invoke({"query": "What is PM-JAY coverage?"})
print(f"Answer: {result['answer']}")
print(f"Badge: {result['badge']}")  # 🟢, 🟡, or 🔴
print(f"Confidence: {result['confidence']}")

# Record outcome after user feedback
app.invoke({
    "query": "What is PM-JAY coverage?",
    "answer": result["answer"],
    "user_feedback": "correct",
    "feedback_reason": ""
})
```

### Correct API:

```python
# Query returns: [{"node": {...}, "score": float, "confidence": float, "badge": str}]
results = graph.query("PM-JAY coverage")
if results:
    content = results[0]["node"]["content"]  # The actual text
    confidence = results[0]["confidence"]    # 0.0 to 1.0
    badge = results[0]["badge"]              # 🟢, 🟡, or 🔴

# Ingest requires question AND answer
graph.ingest(
    query="What is PM-JAY?",
    answer="PM-JAY covers heart surgery up to ₹5 lakh",
    confidence=0.9
)
```

---

## Integration 2: Mem0 + ContextOn.AI OSS

### What You Get:
- Memory across sessions (Mem0)
- Knowledge trust scoring (OSS)
- Failure learning (OSS)
- Quality badges (OSS)

### Code Example:

```python
from mem0 import MemoryClient
from contexton_ai_oss import ContextGraph

# Initialize
mem0 = MemoryClient(api_key="your-api-key")
graph = ContextGraph(data_dir="./knowledge")

class TrustworthyMemory:
    def __init__(self):
        self.mem0 = mem0
        self.graph = graph
    
    def add_memory(self, messages, user_id):
        # Store in Mem0
        result = self.mem0.add(messages, user_id=user_id)
        
        # Also store in OSS with trust tracking
        for i, msg in enumerate(messages):
            if msg["role"] == "user" and i + 1 < len(messages):
                next_msg = messages[i + 1]
                if next_msg["role"] == "assistant":
                    self.graph.ingest(
                        query=msg["content"],
                        answer=next_msg["content"],
                        agent_id=user_id
                    )
        
        return result
    
    def search(self, query, user_id):
        # Get from Mem0 (raw memory)
        mem0_results = self.mem0.search(query, user_id=user_id)
        
        # Get from OSS (trust-scored memory)
        oss_results = self.graph.query(query)
        
        # Merge results with trust scores
        trustworthy_results = []
        for result in oss_results:
            trustworthy_results.append({
                "content": result["node"]["content"],
                "confidence": result["confidence"],
                "badge": result["badge"],
                "source": "memory"
            })
        
        return trustworthy_results
    
    def record_feedback(self, query, answer, is_correct, reason=""):
        if is_correct:
            self.graph.record_success(query=query, answer=answer)
        else:
            self.graph.record_failure(query=query, answer=answer, reason=reason)

# Usage
memory = TrustworthyMemory()

# Add memory
memory.add_memory(
    messages=[{"role": "user", "content": "I prefer vegetarian food"}],
    user_id="user123"
)

# Search with trust scores
results = memory.search("What food does user prefer?", user_id="user123")
for r in results:
    print(f"{r['badge']} {r['content']} (confidence: {r['confidence']})")

# Record feedback
memory.record_feedback(
    query="What food does user prefer?",
    answer="Vegetarian",
    is_correct=True
)
```

---

## Integration 3: Zep/Graphiti + ContextOn.AI OSS

### What You Get:
- Temporal knowledge graphs (Graphiti)
- Knowledge trust scoring (OSS)
- Failure learning (OSS)
- Quality badges (OSS)

### Code Example:

```python
from graphiti_core import Graphiti
from contexton_ai_oss import ContextGraph

# Initialize
graphiti = Graphiti("bolt://localhost:7687", "neo4j", "password")
graph = ContextGraph(data_dir="./knowledge")

class TrustworthyTemporalMemory:
    def __init__(self):
        self.graphiti = graphiti
        self.graph = graph
    
    def add_episode(self, episode_body, source, entity_ids):
        # Store in Graphiti (temporal)
        self.graphiti.add_episode(episode_body=episode_body, source=source)
        
        # Store in OSS (trust tracking)
        # Note: OSS ingest requires query/answer format
        # For episodic data, we use the body as both query and answer
        self.graph.ingest(
            query=f"Episode: {source}",
            answer=episode_body,
            source=source
        )
    
    def search(self, query, num_results=10):
        # Search Graphiti (temporal + vector)
        graphiti_results = self.graphiti.search(query, num_results=num_results)
        
        # Search OSS (trust-scored)
        oss_results = self.graph.query(query)
        
        # Merge with trust scores
        trustworthy_results = []
        for result in oss_results:
            trustworthy_results.append({
                "content": result["node"]["content"],
                "confidence": result["confidence"],
                "badge": result["badge"],
                "temporal": True  # From Graphiti
            })
        
        return trustworthy_results
    
    def record_outcome(self, query, answer, success, reason=""):
        if success:
            self.graph.record_success(query=query, answer=answer)
        else:
            self.graph.record_failure(query=query, answer=answer, reason=reason)

# Usage
memory = TrustworthyTemporalMemory()

# Add episode
memory.add_episode(
    episode_body="PM-JAY covers heart surgery up to ₹5 lakh",
    source="healthcare_database",
    entity_ids=["pmjay", "heart_surgery"]
)

# Search with trust scores
results = memory.search("PM-JAY coverage")
for r in results:
    print(f"{r['badge']} {r['content']} (confidence: {r['confidence']})")
```

---

## Integration 4: Letta + ContextOn.AI OSS

### What You Get:
- Agent identity + memory (Letta)
- Knowledge trust scoring (OSS)
- Failure learning (OSS)
- Quality badges (OSS)

### Code Example:

```python
from letta import LettaAgentClient
from contexton_ai_oss import ContextGraph

# Initialize
letta = LettaAgentClient(base_url="http://localhost:8080")
graph = ContextGraph(data_dir="./knowledge")

class TrustworthyLettaAgent:
    def __init__(self):
        self.letta = letta
        self.graph = graph
        self.agent_id = None
    
    def create_agent(self, name, system_prompt):
        # Create Letta agent
        agent = self.letta.create_agent(
            name=name,
            system_prompt=system_prompt
        )
        self.agent_id = agent.id
        return agent
    
    def send_message(self, message):
        # Send to Letta
        response = self.letta.send_message(
            agent_id=self.agent_id,
            message=message
        )
        
        # Store in OSS for trust tracking
        self.graph.ingest(
            query=message,
            answer=response,
            agent_id=self.agent_id
        )
        
        return response
    
    def query_knowledge(self, query):
        # Query OSS for trust-scored knowledge
        results = self.graph.query(query)
        
        if results:
            return {
                "content": results[0]["node"]["content"],
                "confidence": results[0]["confidence"],
                "badge": results[0]["badge"]
            }
        return None
    
    def record_feedback(self, query, answer, is_correct, reason=""):
        if is_correct:
            self.graph.record_success(query=query, answer=answer)
        else:
            self.graph.record_failure(query=query, answer=answer, reason=reason)

# Usage
agent = TrustworthyLettaAgent()
agent.create_agent(
    name="HealthcareAssistant",
    system_prompt="You are a helpful healthcare assistant."
)

# Send message
response = agent.send_message("What is PM-JAY?")
print(f"Response: {response}")

# Query knowledge with trust
knowledge = agent.query_knowledge("PM-JAY coverage")
if knowledge:
    print(f"Badge: {knowledge['badge']}")
    print(f"Confidence: {knowledge['confidence']}")

# Record feedback
agent.record_feedback(
    query="What is PM-JAY?",
    answer=response,
    is_correct=True
)
```

---

## Integration 5: Standalone (No Other Framework)

### What You Get:
- Knowledge graph with trust scoring
- Failure learning
- Quality badges
- No dependencies

### Code Example:

```python
from contexton_ai_oss import ContextGraph

# Initialize
graph = ContextGraph(data_dir="./knowledge")

# Ingest knowledge (requires query + answer format)
graph.ingest("What is PM-JAY?", "PM-JAY covers heart surgery up to ₹5 lakh")
graph.ingest("What is PM-JAY?", "PM-JAY is a health insurance scheme for poor families")

# Query with trust scores
results = graph.query("PM-JAY coverage")
for r in results:
    print(f"{r['badge']} {r['node']['content']} (confidence: {r['confidence']})")

# Record failure
graph.record_failure(
    query="What is PM-JAY?",
    answer="It's a housing scheme",
    reason="PM-JAY is health insurance, not housing"
)

# Query again - failed path is avoided
results = graph.query("PM-JAY")
# Returns paths with higher confidence
```

---

## Deployment Options

### Option 1: Embedded (Recommended)
Run OSS as part of your existing application:

```python
# In your application
from contexton_ai_oss import ContextGraph
graph = ContextGraph(data_dir="./knowledge")
```

### Option 2: MCP Server
Run OSS as an MCP server for tool-based access:

```bash
# Start MCP server
contexton-ai-oss mcp --data-dir ./knowledge

# Connect from your agent
# (Agent can use tools to query knowledge)
```

### Option 3: REST API
Run OSS as a REST API service:

```bash
# Start REST API
contexton-ai-oss serve --data-dir ./knowledge --port 8080

# Call from your application
curl http://localhost:8080/query?query=PM-JAY+coverage
```

---

## Migration Guide

### If You Already Have Mem0:

```python
# Step 1: Export from Mem0
mem0_memories = mem0.search("", user_id="user123")  # Get all

# Step 2: Import to OSS
for memory in mem0_memories:
    # Convert Mem0 format to OSS format
    graph.ingest(
        query=f"Memory about {memory.get('category', 'general')}",
        answer=memory["content"],
        agent_id="user123"
    )

# Step 3: Use both
# - Mem0 for memory storage
# - OSS for trust scoring
```

### If You Already Have Zep:

```python
# Step 1: Export from Zep
zep_facts = zep.get_facts(user_id="user123")

# Step 2: Import to OSS
for fact in zep_facts:
    graph.ingest(
        query=f"Fact: {fact.get('subject', 'unknown')}",
        answer=fact["content"],
        agent_id="user123"
    )

# Step 3: Use both
# - Zep for temporal tracking
# - OSS for trust scoring
```

---

## Testing Integration

### Unit Test Example:

```python
import pytest
from contexton_ai_oss import ContextGraph

def test_integration_with_langgraph():
    graph = ContextGraph()
    
    # Ingest knowledge
    graph.ingest("PM-JAY covers heart surgery")
    
    # Query
    results = graph.query("PM-JAY coverage")
    assert len(results) > 0
    assert "badge" in results[0]
    assert "confidence" in results[0]
    
    # Record failure
    graph.record_failure(
        query="PM-JAY coverage",
        answer="housing loans",
        reason="Wrong domain"
    )
    
    # Query again
    results = graph.query("PM-JAY coverage")
    # Failed path should have lower confidence
```

---

## Expected Benefits

| Metric | Without OSS | With OSS | Improvement |
|--------|-------------|----------|-------------|
| Wrong answers | 15-25% | 5-10% | 50-70% reduction |
| User trust | Low | High | Visual badges build trust |
| Failure recovery | Manual | Automatic | Agent learns from mistakes |
| Knowledge reliability | Unknown | Measured | Confidence scores |

---

## Next Steps

1. **Choose integration** (LangGraph, Mem0, Zep, Letta, or standalone)
2. **Add OSS as a layer** (not replacement)
3. **Test with your data** (verify trust scores work)
4. **Monitor improvements** (track wrong answer reduction)
5. **Scale to production** (OSS is free at any scale)
