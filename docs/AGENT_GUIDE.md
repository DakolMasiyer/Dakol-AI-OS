# Agent Guide

## The Agent Contract

Every domain agent in this system is a subclass of `agents/base_agent.py:BaseAgent`. The contract is minimal:

```python
class BaseAgent:
    def __init__(self, name: str, domain_weight: float = 1.0):
        self.name = name
        self.domain_weight = domain_weight

    def analyze_task(self, task: str) -> dict:
        # Override this. Return {"intent": str, "confidence": float}
        return {"intent": "generic", "confidence": 0.5}

    def run(self, task: str) -> dict:
        # Do not override this. It applies the domain_weight boost.
        analysis = self.analyze_task(task)
        return {
            "agent": self.name,
            "intent": analysis["intent"],
            "confidence": analysis["confidence"] * self.domain_weight,
            "input": task,
            "status": "processed"
        }
```

Any new agent must: subclass `BaseAgent`, call `super().__init__(name, domain_weight)`, and override `analyze_task()` to return an `{intent, confidence}` dict. Never override `run()` — the boost logic lives there.

## Existing Agents at a Glance

| Agent | Domain | `domain_weight` | High-confidence keywords | Intent values produced |
|---|---|---|---|---|
| `SyncAgent` | Music metadata / sync licensing | 1.3 | `tag`, `bpm`, `metadata`, `tempo`, `key` | `metadata_analysis`, `audio_understanding`, `general_analysis` |
| `AudioAgent` | Audio / sound analysis | 1.0 | `audio`, `sound`, `track` | `audio_analysis`, `audio_general` |
| `CodeAgent` | Software development | 1.0 | `code`, `api`, `fastapi`, `build`, `implement` | `code_execution`, `code_general` |

## How to Build a New Domain Agent

**Step 1** — Create `agents/your_domain_agent.py`:

```python
from agents.base_agent import BaseAgent

class YourDomainAgent(BaseAgent):
    def __init__(self):
        super().__init__("your_domain_agent", domain_weight=1.0)

    def analyze_task(self, task: str) -> dict:
        t = task.lower()
        if any(word in t for word in ["keyword1", "keyword2", "keyword3"]):
            return {"intent": "primary_intent", "confidence": 0.9}
        if any(word in t for word in ["keyword4", "keyword5"]):
            return {"intent": "secondary_intent", "confidence": 0.7}
        return {"intent": "general", "confidence": 0.5}
```

**Step 2** — Register it in `agents/orchestrator.py:Orchestrator.__init__`:

```python
from agents.your_domain_agent import YourDomainAgent

self.agents = [
    SyncAgent(),
    AudioAgent(),
    CodeAgent(),
    YourDomainAgent(),   # add here
]
```

**Step 3** — Optionally add routing keywords to `skills/router_skills.py:analyze_task()` if this domain needs its own dedicated LLM backend. If the existing Claude/GPT/local routing already covers it, no change needed.

That is the complete integration. The router, Orchestrator, fusion brain, and memory logger require no other changes.

## Domain Case Studies

Four domains explored in the 2026-05-26 session — each shows the pattern a real domain agent would follow:

### Tech Domain — Build an API Endpoint
- **Example task:** "Build a REST API for user authentication"
- **LLM routed to:** OpenAI GPT (`gpt-4o-mini`) — task contains `api`, `build`
- **Winning agent:** `CodeAgent` — `code`, `api` trigger 0.9 raw confidence
- **Final intent:** `code_execution`
- **Other agents:** SyncAgent (0.78), AudioAgent (0.5) — both low, step back

### Film Domain — Score Licensing Pipeline
- **Example task:** "Design a licensing pipeline for film score distribution"
- **LLM routed to:** Claude — task contains `design`, `licensing`, `pipeline`
- **Winning agent:** `FilmAgent` (hypothetical) — detects `score`, `license`, `distribute` at 0.9
- **Final intent:** `licensing_pipeline`
- **Other agents:** AudioAgent (0.7), CodeAgent (0.5)

### Media Domain — Content Strategy
- **Example task:** "Analyse audience data and suggest content strategy"
- **LLM routed to:** Claude — task contains `design`/`architecture` framing
- **Winning agent:** `MediaAgent` (hypothetical) — detects `content`, `audience`, `publish` at 0.9
- **Final intent:** `content_strategy`
- **Other agents:** CodeAgent (0.5), SyncAgent (0.5)

### Defense Domain — Threat Detection
- **Example task:** "Design a threat detection pipeline for cyber intrusion signals"
- **LLM routed to:** Claude — task contains `design`, `pipeline`
- **Winning agent:** `DefenseAgent` (hypothetical) — detects `threat`, `intrusion`, `intel`, `surveillance` at 0.95
- **Final intent:** `threat_detection`
- **Other agents:** CodeAgent (0.6), SyncAgent (0.5)

## Multi-Tenant Configuration Pattern

Not yet implemented — this is the architectural direction for enterprise deployment.

The model: each customer (tenant) has their own configured instance of the system with:
- Their own set of domain agents (e.g., a legal firm gets `ContractAgent`, `ComplianceAgent`)
- Their own model preferences (some may only use Claude; others may want GPT only)
- Their own keyword routing overrides
- An isolated memory namespace (their logs do not mix with other tenants)
- A usage dashboard showing their task history and agent performance

At runtime, a `TenantConfig` object would be passed to `Orchestrator`, which swaps in the tenant-specific `self.agents` list. The `log_event` call would write to a tenant-namespaced table or file prefix.

The core codebase does not change per tenant. One deployment serves all customers.

## Domain Weight Strategy

Set `domain_weight > 1.0` when:
- This is the primary commercial domain of the product (e.g., SyncAgent at 1.3 for a music platform)
- You want this agent to win tie-breakers against generalist agents
- The domain has high-signal keywords that strongly predict the correct routing

Keep `domain_weight = 1.0` when:
- The agent is a generalist or utility agent
- You want pure confidence scores to determine the winner
- You are still calibrating the agent's keyword coverage

Note: adjusted scores exceeding 1.0 are valid. The fusion brain does not clamp scores — it reads all values and selects the highest. A SyncAgent score of 1.17 is simply a stronger signal than a CodeAgent score of 0.9.
