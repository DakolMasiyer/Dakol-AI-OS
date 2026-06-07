# Import Topology

The repository uses a fail-closed import policy.

## Dependency Direction

- `tests` may inspect any layer for verification.
- `core` may not import `experimental` or `apps`.
- `platform` services may not import `experimental` or `apps`.
- `experimental` may only use stable public APIs.
- `apps` may only use stable public APIs.

## Public API Surfaces

- `core.api` is the stable entrypoint for kernel execution and audit helpers.
- `api/main.py` is the HTTP application entrypoint.
- `scripts/replay_execution.py` is the replay certification entrypoint.
- `scripts/validate_traces.py` is the trace validation entrypoint.
- `scripts/import_graph_snapshot.py` is the topology certification entrypoint.

## Current Freeze

- learning imports are frozen to approved files only
- import graph snapshot is stored in `artifacts/import_graph_snapshot.json`
- boundary tests fail closed on illegal dependency direction

