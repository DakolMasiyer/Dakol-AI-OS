# Application Layer

This directory is reserved for user-facing AI applications, assistants, workflows, and products.

Rules:
- apps must use stable public interfaces only
- apps must not access internal runtime state directly
- apps must not import learning internals or execution audit internals
- apps must remain project-isolated by configuration and storage namespace

Approved kernel surface:
- `core.api`

Payment integrations should be routed through the shared Flutterwave service configured by `FLUTTERWAVE_ROUTER_URL`.

