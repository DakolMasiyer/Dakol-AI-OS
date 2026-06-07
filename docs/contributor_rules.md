# Contributor Rules

These rules apply to all contributors working on Dakol-AI-OS.

## Mandatory Rules

- No runtime mutation unless it is explicitly covered by the certification flow.
- Deterministic routing is required.
- Replay invariants are required for kernel changes.
- Every trace is immutable and append-only.
- Every import must be intentional.
- Every failure must be observable.
- Every capability must have an owner and a boundary.
- Certification gates are mandatory for core-kernel changes.

## Freeze Scope

The following systems are kernel-frozen and require elevated review:

- router
- invariants
- replay engine
- execution audit
- execution tracing
- certification pipeline

## Contributor Workflow

1. Make the smallest change that satisfies the requirement.
2. Keep the public API surface stable.
3. Add or update boundary tests when a dependency changes.
4. Run replay, drift, adversarial, and regression validation before merge.
5. Stop and restabilize if the structure becomes ambiguous.

