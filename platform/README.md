# Platform Layer

This directory marks the platform-services tier.

Responsibilities:
- dashboards
- policy systems
- orchestration utilities
- CLI interfaces
- operational tooling

Rules:
- platform services may depend on the core kernel through public APIs
- platform services must not import experimental systems
- platform services must not depend on application-specific state

Approved kernel surface:
- `core.api`
- `core.execution_audit`
- `core.invariants`

