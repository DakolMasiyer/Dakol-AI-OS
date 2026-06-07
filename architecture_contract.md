# Architecture Contract: Dakol AI-OS

This document defines the core invariants and architectural constraints governing the Dakol AI-OS. These rules ensure strict runtime determinism, learning isolation, and system immutability.

---

## 🏛️ Core Principles

### 1. Routing is Strictly Deterministic
* Model selection and task routing (e.g., routing to Claude, Codex, or Local fallback) are pure functions of lexical and semantic inputs.
* The content of `learning_state.json` must **NEVER** modify or affect active routing decisions or execution targets at runtime.
* For any identical task input, the router **MUST** produce identical outputs.

### 2. Learning is Advisory-Only
* The learning system acts strictly as an offline/analytical advisor.
* Recommendation payloads computed by the learning system (e.g., model biases and agent weight multipliers) are stored exclusively as passive metadata.
* Learning outputs are logged as recommendations only, with **ZERO** active influence on system execution paths.

### 3. Agent Attributes are Immutable
* Dynamic updates or runtime overrides of agent attributes (e.g., `domain_weight`, `learning_multiplier`) are strictly prohibited.
* Agent class structures employ read-only properties returning fixed base weights (`self.base_weight`). Any runtime attempt to mutate domain weights will result in an immediate `AttributeError`.

### 4. Encapsulated Learning State Access
* Only `memory/learning.py` is permitted to parse, read, import, or write to `learning_state.json` directly.
* All other modules requiring recommendation details must query them through the unified advisory API: `get_learning_recommendations()`.
* Direct calls to `json.load(open("learning_state.json"))` or equivalent parsing outside of the memory layer will raise a `RuntimeError` at runtime.

---

## 🔒 Enforcement Mechanism

All constraints are enforced centrally in a single module: `core/invariants.py`. The enforcement is composed of four checks:

1. `assert_routing_determinism(task, decision_before, decision_after)`: Centralized validator comparing execution paths.
2. `assert_agent_immutability(agents)`: Proves no agent domain weight has been altered or contaminated.
3. `assert_learning_is_advisory_only()`: Raises a runtime failure if any advisory state lookup is attempted within the execution path.
4. `assert_no_learning_state_direct_access(caller_module)`: Blocks unauthorized direct imports or parsing of `learning_state.json` by inspecting the runtime call stack.

---

## 🧪 Verification Policy

* All architecture contract validations are consolidated into a single, authoritative test suite: `tests/test_architecture_contracts.py`.
* Duplicate validation code in other testing scopes is avoided to maintain clean, non-redundant test coverage.
