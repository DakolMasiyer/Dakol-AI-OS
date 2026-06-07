# Execution Flow

```mermaid
flowchart TD
    A[Input task] --> B[Deterministic routing]
    B --> C[Model execution]
    B --> D[Agent fusion]
    C --> E[Execution snapshot]
    D --> E
    E --> F[Trace write]
    E --> G[Audit ledger append]
    F --> H[Replay verifier]
    G --> I[Certification status]
```

## Boundary Notes

- routing decisions are part of the trace
- selected agent is part of the trace
- invariant state is part of the trace
- replay compares output, route path, and invariant state

