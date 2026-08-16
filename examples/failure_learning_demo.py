"""
Failure Learning Demo - The KEY DIFFERENTIATOR

This script demonstrates how ContextOn.AI OSS learns from failures.
No other knowledge graph tool does this!

Usage:
    python failure_learning_demo.py
"""

import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from contexton_ai_oss import ContextGraph


def main():
    print("=" * 60)
    print("ContextOn.AI OSS - Failure Learning Demo")
    print("=" * 60)
    print()
    
    # Create graph
    graph = ContextGraph()
    
    print("1. INGESTING KNOWLEDGE")
    print("-" * 40)
    
    # Ingest correct knowledge
    graph.ingest(
        query="What is PM-JAY?",
        answer="Pradhan Mantri Jan Arogya Yojana is health insurance for poor families covering 5 lakh per family per year",
        agent_id="health-agent"
    )
    print("[OK] ingested correct knowledge about PM-JAY")
    
    graph.ingest(
        query="Who implements PM-JAY?",
        answer="National Health Authority (NHA) implements PM-JAY under the Ministry of Health and Family Welfare",
        agent_id="health-agent"
    )
    print("[OK] ingested correct knowledge about NHA")
    
    print()
    print("2. QUERYING BEFORE FAILURE")
    print("-" * 40)
    
    results = graph.query("PM-JAY coverage")
    print(f"Found {len(results)} results:")
    for r in results:
        badge = r['badge']
        content = r['node']['content'][:60]
        confidence = r['confidence']
        print(f"  {badge} {content}...")
        print(f"     Confidence: {confidence:.1%}")
    
    print()
    print("3. RECORDING A FAILURE (KEY FEATURE)")
    print("-" * 40)
    
    # Agent gives wrong answer
    print("[FAIL] Agent gave WRONG answer: 'PM-JAY is a housing scheme'")
    failure_result = graph.record_failure(
        query="What is PM-JAY?",
        answer="PM-JAY is a housing scheme for urban poor",
        reason="Incorrect - PM-JAY is health insurance, not housing"
    )
    print(f"   Recorded: {failure_result['message']}")
    print(f"   Affected edges: {failure_result['affected_edges']}")
    print(f"   Affected nodes: {failure_result['affected_nodes']}")
    
    print()
    print("4. QUERYING AFTER FAILURE")
    print("-" * 40)
    
    results = graph.query("PM-JAY coverage")
    print(f"Found {len(results)} results (notice lower confidence):")
    for r in results:
        badge = r['badge']
        content = r['node']['content'][:60]
        confidence = r['confidence']
        print(f"  {badge} {content}...")
        print(f"     Confidence: {confidence:.1%}")
    
    print()
    print("5. RECORDING A SUCCESS")
    print("-" * 40)
    
    # Agent gives correct answer
    print("[OK] Agent gave CORRECT answer about PM-JAY")
    success_result = graph.record_success(
        query="What is PM-JAY?",
        answer="PM-JAY is health insurance for poor families"
    )
    print(f"   Recorded: {success_result['message']}")
    
    print()
    print("6. QUERYING AFTER SUCCESS")
    print("-" * 40)
    
    results = graph.query("PM-JAY coverage")
    print(f"Found {len(results)} results (confidence restored):")
    for r in results:
        badge = r['badge']
        content = r['node']['content'][:60]
        confidence = r['confidence']
        print(f"  {badge} {content}...")
        print(f"     Confidence: {confidence:.1%}")
    
    print()
    print("7. SUGGESTED QUESTIONS")
    print("-" * 40)
    
    suggestions = graph.suggest_questions(top_n=3)
    print("The graph suggests these questions:")
    for s in suggestions:
        badge = s['badge']
        question = s['question']
        reason = s['reason']
        print(f"  {badge} {question}")
        print(f"     Reason: {reason}")
    
    print()
    print("8. GRAPH STATISTICS")
    print("-" * 40)
    
    stats = graph.get_stats()
    print(f"Nodes: {stats['node_count']}")
    print(f"Edges: {stats['edge_count']}")
    print(f"Average confidence: {stats['avg_confidence']:.1%}")
    print(f"High confidence nodes: {stats['high_confidence_nodes']}")
    print(f"Medium confidence nodes: {stats['medium_confidence_nodes']}")
    print(f"Low confidence nodes: {stats['low_confidence_nodes']}")
    
    print()
    print("=" * 60)
    print("KEY TAKEAWAY:")
    print("ContextOn.AI OSS learned from the failure and adjusted confidence!")
    print("No other knowledge graph tool does this.")
    print("=" * 60)


if __name__ == "__main__":
    main()
