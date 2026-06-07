# Runtime Lifecycle

```text
request/task -> route decision -> model execution -> agent fusion
            -> invariant check -> execution snapshot -> trace write
            -> audit ledger append -> replay verification
```

## Lifecycle Rules

- routing is deterministic
- execution traces are immutable
- replay uses the recorded snapshot, not live state
- invariant checks are captured with the execution record
- failures are recorded as observable terminal states

## Isolation Model

Each project should have isolated:

- config
- traces
- execution identifiers
- policy scope
- storage namespace

