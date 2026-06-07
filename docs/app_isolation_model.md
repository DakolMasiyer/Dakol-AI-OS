# Application Isolation Model

Dakol-AI-OS provides a multi-application governed AI platform, allowing independent apps to safely coexist using a unified `core.api` without destabilizing the kernel.

## App Lifecycle
1. **Registration**: Applications are registered via `AppRegistry.register(app_path)`. The registry reads `manifest.json` and prepares isolated contexts.
2. **Execution**: Apps execute tasks using their assigned `AppRuntimeAdapter`, which automatically tags tasks with the app's `app_id`.
3. **Trace Generation**: The kernel generates traces and places them strictly within `logs/execution/{app_id}/`.

## Namespace Isolation
Every application operates in an independent namespace for:
- **Configs**: Stored in `configs/{app_id}/`
- **Policies**: Stored in `policies/{app_id}/`
- **Traces**: Stored in `logs/execution/{app_id}/`

## Execution Governance
- Applications MUST NOT bypass `core.api` to access internal router, orchestrator, or learning modules directly.
- The execution ID format is `app_id-<uuid>` to guarantee isolation and prevent collisions.
- Any attempt by an app to mutate shared kernel states will fail tests and be rejected in certification.
