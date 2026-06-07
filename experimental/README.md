# Experimental Layer

This directory is reserved for unstable systems, prototypes, and research code.

Rules:
- experimental code must use stable public APIs only
- experimental code must not mutate runtime state directly
- experimental code must not bypass invariants or replay logging
- experimental code must be isolated from application layers by default

Approved entrypoint:
- `core.api`

