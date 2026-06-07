# SyncMaster Workflow

## Lifecycle
1. Accepts an artist catalog and brief as inputs.
2. Interates over tracks.
3. Performs `syncmaster_analyze_metadata` on each track.
4. Performs `syncmaster_recommend_sync_fit`.
5. If confidence > 80%, commits the recommendation to the graph via `syncmaster_save_recommendation`.

## Governance
- Tools used in the workflow are pre-authorized in the `manifest.json`.
- Uses `core.api.execute_tool` to securely execute each task.
- Each tool execution creates an independent execution trace within the `logs/execution/syncmaster_ai/` namespace.
- Preserves full replayability of the orchestration loop.
