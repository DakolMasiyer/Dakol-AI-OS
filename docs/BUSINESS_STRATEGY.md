# Business Strategy

## The Moat

The competitive moat is `memory/logs.json` — or rather, what it becomes.

Every task routed through Dakol-AI-OS produces a log entry containing the full agent decision trail: which agents fired, what confidence scores they returned, which model was used, and what the output was. This is the `agent_result` field added in `memory/log.py`.

Competitors can copy the code. They cannot copy the accumulated data. As the log grows, Steps 8 and 9 (not yet implemented) will use it to:
- Tune keyword routing heuristics automatically based on low-confidence patterns (Step 8)
- Adjust agent `domain_weight` values based on historical accuracy (Step 9)

The longer the system runs, the smarter it becomes — and the harder it is for a new entrant to replicate the same routing quality from scratch. That compounding intelligence is the moat.

---

## Three Monetisation Paths

### Path A — Vertical SaaS: SyncMaster First

Build a polished, domain-specific product for the music licensing industry powered by Dakol-AI-OS underneath. End users never see the AI OS — they see a music intelligence platform.

**Target customers:** Music supervisors, sync licensing agents, independent publishers, music libraries, streaming platforms

**What they pay for:** Automated BPM and metadata tagging, sync licensing pipeline assistance, rights clearance support, track recommendation for briefs

**Pricing model:** Monthly subscription per seat — £49–£299/month depending on volume and features

**Why start here:** SyncMaster is the domain the system was originally built around. The SyncAgent already exists. The keyword routing is already tuned for music. This is the path of least resistance to first revenue.

---

### Path B — API Platform: Developer Market

Expose `POST /task` as a public API. Developers and companies integrate it into their own products. They bring their domain expertise; you provide the routing intelligence and multi-agent fusion layer.

This is the "Stripe for AI routing" framing: infrastructure that removes a complex problem (which model do I call, how do I orchestrate multiple agents, how do I log decisions for future learning) so developers can focus on their product.

**Target customers:** Developers building AI-powered tools who need a plug-and-play multi-agent routing layer

**Pricing model:**
- Free tier: 500 tasks/month
- Growth: £49/month, 10,000 tasks
- Scale: £299/month, 100,000 tasks
- Enterprise: custom pricing, dedicated agent configuration, SLA

**Why this works:** The memory layer becomes a shared intelligence asset across all API customers. Each customer's usage improves the routing quality for everyone.

---

### Path C — White-Label Per Domain: Enterprise

License a fully configured instance of Dakol-AI-OS to an enterprise client in a specific vertical. They get their own domain agents, their own isolated memory, and their own branded dashboard — deployed on their infrastructure or yours.

**Target verticals from this session:** Film (licensing pipeline), Media (content strategy), Defense (threat detection and intelligence analysis)

**Pricing model:**
- Implementation fee: £10,000–£50,000 per deployment
- Monthly licence + support: £2,000–£10,000/month
- Model costs passed through with a margin

**Why this works:** Enterprise clients in defense and media cannot use shared SaaS products for sensitive tasks. A white-label deployment with isolated memory and custom agents solves their compliance requirement while giving you a high-value contract.

---

## Four-Phase Roadmap

| Phase | Timeframe | Key Milestones | Success Metric |
|---|---|---|---|
| **Phase 1: Fix and Ship** | 0–3 months | Fix router bug, FastAPI wrapper, Railway deployment, Gemini 2.0 Flash fusion brain, 10 beta users | Working HTTPS endpoint, first 10 users giving feedback |
| **Phase 2: First Revenue** | 3–6 months | SyncMaster paid tier launched, 5 paying customers, Supabase memory, multi-tenant config foundation | £5,000 MRR |
| **Phase 3: Platform Play** | 6–18 months | Public API (Path B), agent marketplace or partner onboarding, 50+ customers, Steps 8+9 implemented, usage dashboard | £50,000–£100,000 MRR |
| **Phase 4: Exit-Ready** | 18–36 months | Metrics package prepared, strategic conversations begun, memory dataset meaningful in size | Acquisition offer or Series A |

---

## Exit Paths

### Option 1 — Acqui-hire
An AI lab or tech company acquires the team and codebase for the engineering talent and the multi-agent routing architecture. The system demonstrates a deep understanding of LLM orchestration that is valuable to companies building agent platforms.

**Most likely buyers:** AI-native companies building agent infrastructure, or large tech companies standing up their own agent layers

**What they're buying:** The team's expertise + the routing architecture + the memory/learning system design

---

### Option 2 — Strategic Acquisition by Media/Music Tech
A company in the music or media industry acquires SyncMaster as a product add-on. The memory log — containing thousands of real sync licensing and metadata decisions — is the primary asset.

**Most likely buyers:** Spotify, SoundCloud, Epidemic Sound, BMI, ASCAP, a major music publisher

**What they're buying:** SyncMaster product + its user base + the accumulated routing intelligence for music tasks

**Valuation driver:** ARR × 5–10, with a premium for the proprietary dataset

---

### Option 3 — Platform Acquisition by Enterprise Software
A large software company acquires the white-label platform as an AI orchestration layer for their enterprise suite.

**Most likely buyers:** Salesforce (AI for CRM), Adobe (AI for creative workflows), Microsoft (AI for enterprise productivity)

**What they're buying:** Multi-tenant AI OS infrastructure + domain agent extensibility pattern + the memory/learning architecture

**Valuation driver:** MRR × 8–15, with a significant premium if multiple verticals are live

---

## Multi-Tenant Architecture Implications

Paths B and C both require multi-tenancy. The implementation follows a `TenantConfig` pattern:

```python
class TenantConfig:
    agents: list          # tenant-specific agent instances
    model_preferences: dict  # override which LLM routes where
    routing_keywords: dict   # tenant-specific keyword overrides
    memory_namespace: str    # Supabase table prefix or schema name
    usage_limits: dict       # max tasks/month, max output length
```

At request time, `Orchestrator` is instantiated with the tenant's config. The `log_event` call writes to the tenant's isolated namespace. A usage dashboard reads aggregated logs per tenant.

The core codebase serves all tenants from a single deployment. Tenant isolation is achieved through the config layer and database namespacing — not separate deployments.

---

## What to Prioritise Right Now

1. **Fix the broken import bug in `router.py`** — five minutes of work. Nothing can be tested, demonstrated, or shipped until this is done. Three lines.

2. **Deploy to Railway with a live URL** — a live HTTPS endpoint changes every conversation. Investors, potential customers, and co-founders need to see something working. The technical plan for this is in `PRODUCTION_PLAN.md`.

3. **Get one real SyncMaster beta user** — a real user generating real tasks produces log data that is worth more than any planning document. Even one active user starts building the memory moat and surfaces routing gaps that cannot be found any other way.
