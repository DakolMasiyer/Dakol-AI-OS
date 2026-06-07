# Workflow Execution Maps

This document outlines the strict execution diagrams and policy checkpoints for Dakol-AI-OS governed workflows.

## SyncMaster AI Workflow

```mermaid
graph TD
    A[METADATA_VALIDATION] --> B[GENRE_CLASSIFICATION]
    B --> C[MOOD_ANALYSIS]
    C --> D[SYNC_SCORING]
    D --> E[RECOMMENDATION_GENERATION]
    E -->|Checkpoint| F[HUMAN_APPROVAL]
    F -->|Wait & Resume| G[REPORT_GENERATION]
    G --> H[COMPLETED]
```

**Policy Checkpoints:**
- At `HUMAN_APPROVAL`, the workflow engine yields a `WAITING_FOR_APPROVAL` state.
- An immutable `checkpoint_xxx.json` is generated under `logs/workflows/`.
- Execution is strictly paused until deterministic resumption is triggered.

## Listening Farm AI Workflow

```mermaid
graph TD
    A[METADATA_EXTRACTION] --> B[TREND_ANALYSIS]
    B --> C[SIMILARITY_SCORING]
    C --> D[RECOMMENDATION_SIMULATION]
    D --> E[SIGNAL_RANKING]
    E --> F[COMPLETED]
```

**Execution Safety:**
- Fails closed on any invalid transition.
- Max execution depth limits prevent infinite looping.
- Immutable fingerprints track stage inputs and outputs.
