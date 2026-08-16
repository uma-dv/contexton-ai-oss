# ContextOn.AI OSS — Architecture Flowcharts

---

## Flowchart 1: OSS in Customer's Existing AI Deployment (ServiceNow/ITSM)

### Current State (Before OSS)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CUSTOMER'S IT INFRASTRUCTURE (ServiceNow)                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │  ServiceNow  │     │   JIRA       │     │   Slack      │                │
│  │   (ITSM)     │     │  (Projects)  │     │  (Comms)     │                │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              │                                              │
│                    ┌─────────▼─────────┐                                    │
│                    │   Integration     │                                    │
│                    │     Layer         │                                    │
│                    │  (Custom APIs)    │                                    │
│                    └─────────┬─────────┘                                    │
│                              │                                              │
│                    ┌─────────▼─────────┐                                    │
│                    │   Existing AI     │                                    │
│                    │   Agent (Basic)   │                                    │
│                    │  - No memory      │                                    │
│                    │  - No trust       │                                    │
│                    │  - No learning    │                                    │
│                    └───────────────────┘                                    │
│                                                                             │
│  PROBLEM: Agent gives wrong answers. No way to know which knowledge is      │
│           trustworthy. Mistakes repeat forever.                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### After OSS Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CUSTOMER'S IT INFRASTRUCTURE + ContextOn.AI OSS             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │  ServiceNow  │     │   JIRA       │     │   Slack      │                │
│  │   (ITSM)     │     │  (Projects)  │     │  (Comms)     │                │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              │                                              │
│                    ┌─────────▼─────────┐                                    │
│                    │   Integration     │                                    │
│                    │     Layer         │                                    │
│                    │  (Custom APIs)    │                                    │
│                    └─────────┬─────────┘                                    │
│                              │                                              │
│  ┌───────────────────────────▼─────────────────────────────────────────┐   │
│  │                    ContextOn.AI OSS Engine                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   Graph     │  │ Confidence  │  │  Failure    │                 │   │
│  │  │   Engine    │  │  Scoring    │  │  Learning   │                 │   │
│  │  │             │  │  (0-1)      │  │             │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │  Quality    │  │   Entity    │  │  Procedure  │                 │   │
│  │  │  Badges     │  │  Resolution │  │  Memory     │                 │   │
│  │  │  🟢🟡🔴      │  │  (Aliases)  │  │  (Skills)   │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   Tool      │  │   Memory    │  │    MCP      │                 │   │
│  │  │  Registry   │  │  Hygiene    │  │   Server    │                 │   │
│  │  │             │  │  (Decay)    │  │  (Claude)   │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  └───────────────────────────┬─────────────────────────────────────────┘   │
│                              │                                              │
│                    ┌─────────▼─────────┐                                    │
│                    │   Existing AI     │                                    │
│                    │   Agent (Enhanced)│                                    │
│                    │  ✅ Has memory    │                                    │
│                    │  ✅ Has trust     │                                    │
│                    │  ✅ Learns        │                                    │
│                    └───────────────────┘                                    │
│                                                                             │
│  RESULT: Agent knows which knowledge is trustworthy. Mistakes are           │
│          remembered. Confidence recovers after corrections.                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Integration Map (ServiceNow Example)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ServiceNow + ContextOn.AI OSS Integration               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SERVICENOW DATA SOURCES                                                    │
│  ═══════════════════════                                                    │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  Incident Mgmt  │  │  Change Mgmt    │  │  Knowledge Base │            │
│  │  ─────────────  │  │  ─────────────  │  │  ─────────────  │            │
│  │  - Incidents    │  │  - Changes      │  │  - Articles     │            │
│  │  - Work Orders  │  │  - Releases     │  │  - Solutions    │            │
│  │  - SLAs         │  │  - Approvals    │  │  - FAQs         │            │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                                │                                            │
│  ┌─────────────────────────────▼────────────────────────────────────────┐  │
│  │              ContextOn.AI OSS — Knowledge Ingestion                  │  │
│  │                                                                      │  │
│  │  graph.ingest(                                                       │  │
│  │      query="How to resolve P1 incident?",                           │  │
│  │      answer="Follow escalation matrix: L1→L2→L3→Manager",          │  │
│  │      agent_id="servicenow-agent"                                     │  │
│  │  )                                                                   │  │
│  │                                                                      │  │
│  │  graph.ingest(                                                       │  │
│  │      query="What causes change failure?",                            │  │
│  │      answer="Missing CAB approval, no rollback plan, testing gaps",  │  │
│  │      agent_id="servicenow-agent"                                     │  │
│  │  )                                                                   │  │
│  │                                                                      │  │
│  │  graph.ingest_procedure(                                             │  │
│  │      "Escalate P1 Incident",                                         │  │
│  │      ["Verify impact", "Page on-call", "Notify management",         │  │
│  │       "Create war room", "Update status every 30 min"],             │  │
│  │      agent_id="servicenow-agent"                                     │  │
│  │  )                                                                   │  │
│  │                                                                      │  │
│  │  graph.register_tool("servicnow_api", "Query ServiceNow REST API")  │  │
│  └─────────────────────────────┬────────────────────────────────────────┘  │
│                                │                                            │
│  ┌─────────────────────────────▼────────────────────────────────────────┐  │
│  │              ContextOn.AI OSS — Query & Context                      │  │
│  │                                                                      │  │
│  │  When ServiceNow agent receives a query:                             │  │
│  │                                                                      │  │
│  │  1. Agent asks OSS: "What do I know about [incident type]?"          │  │
│  │  2. OSS returns: ranked facts with confidence + badges               │  │
│  │  3. Agent uses trusted knowledge (🟢) to answer                      │  │
│  │  4. If answer is wrong → record_failure → confidence drops            │  │
│  │  5. If answer is right → record_success → confidence rises            │  │
│  │                                                                      │  │
│  │  ctx = graph.get_context("P1 incident escalation")                   │  │
│  │  # Returns: "Follow escalation matrix (🟢 0.95 confidence)"          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  REAL-WORLD FLOW                                                           │
│  ═══════════════                                                           │
│                                                                             │
│  User: "We have a P1 database outage"                                      │
│      │                                                                      │
│      ▼                                                                      │
│  ServiceNow Agent queries ContextOn.AI OSS                                 │
│      │                                                                      │
│      ▼                                                                      │
│  OSS returns:                                                               │
│    🟢 "P1 incidents: Follow escalation matrix (0.95 confidence)"           │
│    🟢 "Database outages: Check replication status first (0.88 confidence)"  │
│    🟡 "Contact DBA on-call via PagerDuty (0.72 confidence)"                │
│      │                                                                      │
│      ▼                                                                      │
│  Agent responds with trusted knowledge                                      │
│      │                                                                      │
│      ▼                                                                      │
│  User confirms or corrects                                                  │
│      │                                                                      │
│      ├─ Correct → record_success → confidence rises                        │
│      │                                                                      │
│      └─ Wrong → record_failure → confidence drops                          │
│                  Agent learns not to trust that path                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Flowchart 2: OSS in Enterprise Application (Agentic Node View)

### Enterprise Architecture with OSS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ContextOn.AI Enterprise Platform                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      GOVERNANCE LAYER                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │   │
│  │  │  ScopeTree  │  │    SLCA     │  │  RBAC/Auth  │                │   │
│  │  │  Governance │  │  Scoring    │  │  (OAuth)    │                │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                │   │
│  └─────────────────────────┬───────────────────────────────────────────┘   │
│                            │                                                │
│  ┌─────────────────────────▼───────────────────────────────────────────┐   │
│  │                    SCOPTREE NODE HIERARCHY                          │   │
│  │                                                                      │   │
│  │                        [Root Node]                                   │   │
│  │                             │                                        │   │
│  │              ┌──────────────┼──────────────┐                        │   │
│  │              │              │              │                         │   │
│  │         [Department]   [Department]   [Department]                   │   │
│  │              │              │              │                         │   │
│  │         ┌────┴────┐   ┌────┴────┐   ┌────┴────┐                    │   │
│  │         │         │   │         │   │         │                     │   │
│  │      [Team]   [Team] [Team]  [Team] [Team]  [Team]                  │   │
│  │         │         │   │         │   │         │                     │   │
│  │      [Node]   [Node] [Node]  [Node] [Node]  [Node]                 │   │
│  │         │         │   │         │   │         │                     │   │
│  │      [Agent]  [Agent][Agent] [Agent][Agent] [Agent]                │   │
│  │                                                                      │   │
│  └─────────────────────────┬───────────────────────────────────────────┘   │
│                            │                                                │
│  ┌─────────────────────────▼───────────────────────────────────────────┐   │
│  │              EACH NODE HAS AN AGENT WITH ContextOn.AI OSS           │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │                    AGENTIC NODE VIEW                        │    │   │
│  │  │                                                             │    │   │
│  │  │  ┌─────────────────────────────────────────────────────┐   │    │   │
│  │  │  │                 NODE DETAILS                        │   │    │   │
│  │  │  │  - Node name: "Customer Support Team"              │   │    │   │
│  │  │  │  - Parent: "Support Department"                    │   │    │   │
│  │  │  │  - Children: ["Tier 1", "Tier 2", "Tier 3"]       │   │    │   │
│  │  │  │  - Agent: "support-agent"                          │   │    │   │
│  │  │  └─────────────────────────────────────────────────────┘   │    │   │
│  │  │                                                             │    │   │
│  │  │  ┌─────────────────────────────────────────────────────┐   │    │   │
│  │  │  │              AGENT'S KNOWLEDGE GRAPH                │   │    │   │
│  │  │  │  (ContextOn.AI OSS)                                 │   │    │   │
│  │  │  │                                                     │   │    │   │
│  │  │  │     [Refund Policy]───🟢───[Customer]              │   │    │   │
│  │  │  │          │                    │                     │   │    │   │
│  │  │  │         🔴                   🟢                    │   │    │   │
│  │  │  │          │                    │                     │   │    │   │
│  │  │  │     [Wrong Answer]      [Correct Answer]           │   │    │   │
│  │  │  │                                                     │   │    │   │
│  │  │  │  Nodes: 47 | Edges: 89 | Avg Confidence: 0.82     │   │    │   │
│  │  │  │  🟢 High: 31 | 🟡 Medium: 12 | 🔴 Low: 4          │   │    │   │
│  │  │  └─────────────────────────────────────────────────────┘   │    │   │
│  │  │                                                             │    │   │
│  │  │  ┌─────────────────────────────────────────────────────┐   │    │   │
│  │  │  │              GRAPH VISUALIZATION                    │   │    │   │
│  │  │  │  (Interactive - click nodes to explore)             │   │    │   │
│  │  │  │                                                     │   │    │   │
│  │  │  │      ┌───────┐      ┌───────┐      ┌───────┐      │   │    │   │
│  │  │  │      │ Node  │──────│ Node  │──────│ Node  │      │   │    │   │
│  │  │  │      │  🟢   │      │  🟡   │      │  🔴   │      │   │    │   │
│  │  │  │      └───┬───┘      └───┬───┘      └───┬───┘      │   │    │   │
│  │  │  │          │              │              │           │   │    │   │
│  │  │  │      ┌───▼───┐      ┌───▼───┐      ┌───▼───┐      │   │    │   │
│  │  │  │      │ Edge  │      │ Edge  │      │ Edge  │      │   │    │   │
│  │  │  │      │ 0.95  │      │ 0.62  │      │ 0.31  │      │   │    │   │
│  │  │  │      └───────┘      └───────┘      └───────┘      │   │    │   │
│  │  │  └─────────────────────────────────────────────────────┘   │    │   │
│  │  │                                                             │    │   │
│  │  │  ┌─────────────────────────────────────────────────────┐   │    │   │
│  │  │  │              AGENT ACTIONS                          │   │    │   │
│  │  │  │                                                     │   │    │   │
│  │  │  │  [Query] [Ingest] [Record Failure] [Record Success]│   │    │   │
│  │  │  │  [Skills] [Tools] [Context] [Hygiene] [Visualize]  │   │    │   │
│  │  │  └─────────────────────────────────────────────────────┘   │    │   │
│  │  │                                                             │    │   │
│  │  │  ┌─────────────────────────────────────────────────────┐   │    │   │
│  │  │  │              FAILURE LEARNING LOG                   │   │    │   │
│  │  │  │  (Unique to ContextOn.AI)                           │   │    │   │
│  │  │  │                                                     │   │    │   │
│  │  │  │  ❌ "Refund policy" → wrong answer → 🔴 0.35       │   │    │   │
│  │  │  │  ✅ "Refund policy" → correct answer → 🟢 0.92     │   │    │   │
│  │  │  │  ❌ "Shipping time" → wrong answer → 🔴 0.28       │   │    │   │
│  │  │  │  ✅ "Shipping time" → correct answer → 🟢 0.88     │   │    │   │
│  │  │  └─────────────────────────────────────────────────────┘   │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### How Each Node's Agent Uses OSS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AGENTIC NODE ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SCOPTREE NODE HIERARCHY                                                   │
│  ═══════════════════════                                                   │
│                                                                             │
│                         [Enterprise Root]                                   │
│                              │                                              │
│           ┌──────────────────┼──────────────────┐                          │
│           │                  │                  │                           │
│     [Support Dept]     [Sales Dept]      [Engineering Dept]                │
│           │                  │                  │                           │
│      ┌────┴────┐        ┌────┴────┐        ┌────┴────┐                     │
│      │         │        │         │        │         │                      │
│   [Tier 1]  [Tier 2]  [Inbound] [Outbound] [Backend] [Frontend]           │
│      │         │        │         │        │         │                      │
│   [Agent]   [Agent]   [Agent]  [Agent]   [Agent]   [Agent]                │
│                                                                             │
│  EACH AGENT HAS ITS OWN ContextOn.AI OSS INSTANCE                          │
│  ═══════════════════════════════════════════════                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 1 SUPPORT AGENT                                               │   │
│  │  ─────────────────────                                              │   │
│  │                                                                      │   │
│  │  ContextOn.AI OSS Instance: tier1_support_graph                     │   │
│  │                                                                      │   │
│  │  Knowledge stored:                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 🟢 Password reset: Go to settings → security → reset       │   │   │
│  │  │ 🟢 Login issues: Check browser cache, then VPN status      │   │   │
│  │  │ 🟡 Billing questions: Transfer to billing team             │   │   │
│  │  │ 🔴 Refund policy: [WRONG - needs verification]             │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  Procedures stored:                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 1. Reset password: ["Open settings", "Go to security",     │   │   │
│  │  │    "Click reset", "Confirm email"]                         │   │   │
│  │  │ 2. Escalate ticket: ["Verify issue", "Check KB",           │   │   │
│  │  │    "Transfer to Tier 2 with notes"]                        │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  Tools registered:                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 🟢 password_reset_api - "Resets user password"             │   │   │
│  │  │ 🟡 ticket_system - "Creates/updates tickets"               │   │   │
│  │  │ 🔴 legacy_api - "Old API, often fails"                     │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 2 SUPPORT AGENT                                               │   │
│  │  ─────────────────────                                              │   │
│  │                                                                      │   │
│  │  ContextOn.AI OSS Instance: tier2_support_graph                     │   │
│  │                                                                      │   │
│  │  Knowledge stored:                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 🟢 Database issues: Check connection pool, then replicas    │   │   │
│  │  │ 🟢 API errors: Check rate limits, then auth tokens         │   │   │
│  │  │ 🟡 Complex bugs: Reproduce in staging first                │   │   │
│  │  │ 🔴 Data migration: [WRONG - needs updated procedure]       │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SALES INBOUND AGENT                                                │   │
│  │  ───────────────────                                                │   │
│  │                                                                      │   │
│  │  ContextOn.AI OSS Instance: sales_inbound_graph                     │   │
│  │                                                                      │   │
│  │  Knowledge stored:                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 🟢 Pricing: Enterprise starts at $500/mo, custom plans     │   │   │
│  │  │ 🟢 Demo process: Schedule via Calendly, 30-min slot        │   │   │
│  │  │ 🟡 Competitor comparison: [Needs regular updates]           │   │   │
│  │  │ 🔴 Discount policy: [WRONG - updated Q3 2026]              │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  CROSS-NODE LEARNING (Enterprise Feature)                                  │
│  ═════════════════════════════════════════                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  When Tier 1 agent learns something, Tier 2 can benefit:           │   │
│  │                                                                      │   │
│  │  Tier 1: "Password reset works for all users" (🟢 0.95)           │   │
│  │      │                                                              │   │
│  │      ▼ (Shared knowledge base)                                     │   │
│  │                                                                      │   │
│  │  Tier 2: Inherits "Password reset works for all users"             │   │
│  │                                                                      │   │
│  │  When Tier 2 learns something new, Tier 1 gets updated:            │   │
│  │                                                                      │   │
│  │  Tier 2: "Password reset fails for SSO users" (🟢 0.90)           │   │
│  │      │                                                              │   │
│  │      ▼ (Shared knowledge base)                                     │   │
│  │                                                                      │   │
│  │  Tier 1: Updates "Password reset" with SSO exception               │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Enterprise UI — Agentic Node View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ContextOn.AI Enterprise — Agentic Node View              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  HEADER: Customer Support Team > Tier 1 Support                    │   │
│  │  Agent: support-tier1 | Status: Active | Nodes: 47 | Edges: 89    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  TABS: [Graph] [Knowledge] [Procedures] [Tools] [Failures] [Log]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  GRAPH TAB (Active)                                                │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                                                             │   │   │
│  │  │                    [Password Reset]                         │   │   │
│  │  │                       🟢 0.95                               │   │   │
│  │  │                         │                                   │   │   │
│  │  │                    ┌────┴────┐                              │   │   │
│  │  │                    │         │                               │   │   │
│  │  │               [Settings] [Security]                         │   │   │
│  │  │                 🟢 0.92    🟢 0.88                          │   │   │
│  │  │                    │         │                               │   │   │
│  │  │                    └────┬────┘                              │   │   │
│  │  │                         │                                   │   │   │
│  │  │                    [Reset Button]                           │   │   │
│  │  │                       🟢 0.90                               │   │   │
│  │  │                                                             │   │   │
│  │  │  ────────────────────────────────────────────────────────  │   │   │
│  │  │                                                             │   │   │
│  │  │                    [Refund Policy]                          │   │   │
│  │  │                       🔴 0.35                               │   │   │
│  │  │                         │                                   │   │   │
│  │  │                    [FAILED - needs update]                  │   │   │
│  │  │                                                             │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  Node Details:                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ Selected: Password Reset                                    │   │   │
│  │  │ Confidence: 0.95 (🟢)                                       │   │   │
│  │  │ Mentions: 12 | Failures: 0 | Last verified: 2 hours ago    │   │   │
│  │  │                                                             │   │   │
│  │  │ [Edit] [Record Failure] [Record Success] [Visualize]        │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  FAILURE LEARNING TAB                                               │   │
│  │                                                                      │   │
│  │  Recent Failures & Recoveries:                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ ❌ 2026-08-15 14:30 | "Refund policy" → wrong → 🔴 0.35  │   │   │
│  │  │ ✅ 2026-08-15 14:45 | "Refund policy" → correct → 🟢 0.92│   │   │
│  │  │ ❌ 2026-08-15 10:20 | "Shipping time" → wrong → 🔴 0.28  │   │   │
│  │  │ ✅ 2026-08-15 11:00 | "Shipping time" → correct → 🟢 0.88│   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  Learning Stats:                                                    │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ Total failures: 8 | Recovered: 7 | Pending: 1             │   │   │
│  │  │ Recovery rate: 87.5% | Avg recovery time: 15 min           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary: Where OSS Fits

### In Customer's Deployment

```
ServiceNow/JIRA/Slack → Integration Layer → [ContextOn.AI OSS] → AI Agent → User
```

### In Enterprise Application

```
ScopeTree Governance → Node Hierarchy → [Each Node Has Agent] → [Each Agent Has OSS]
```

### Key Insight

> **The OSS is the "brain" of each agent.** Every agent in the enterprise platform has its own OSS instance that stores knowledge, tracks confidence, and learns from failures. The ScopeTree organizes which agents exist. The OSS makes each agent smart and trustworthy.

---

*Flowcharts prepared by ODEFTO AI Labs — August 2026*
