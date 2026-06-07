# Tool Governance Model

## Policy Enforcement
- Tools must be explicitly approved in an app's `manifest.json`.
- Tools are app-scoped. Accessing a forbidden tool will instantly raise a `ToolPolicyViolation` (Fail Closed).

## Execution Tracing
- When an app executes a tool via `core.api.execute_tool`, an isolated execution trace is generated in the app's log namespace.
- Trace contains `execution_fingerprint`, ensuring strict auditability.
- Invariants checks (like `tool_policy_verified`) are written to the trace to certify compliance.

## Cross-App Integrity
- Cross-app tool access is mathematically impossible through the policy gateway since an app_id's manifest enforces tool restrictions.
