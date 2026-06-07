# Listening Farm AI Architecture

## Overview
Listening Farm AI is an independent product running on top of Dakol-AI-OS. It serves as the primary data ingestion and analysis pipeline for tracking music trends and scoring metadata.

## Execution Model
- Consumes `core.api`.
- Operates under strict capability permissions: `ingestion`, `crawling`, `trend_analysis`, `scoring`.
- Traces and policies are segregated into `logs/execution/listening_farm_ai/` and `policies/listening_farm_ai/`.

## Replay Guarantees
- The app's tasks execute via deterministic `core.api` endpoints.
- All router and orchestrator engagements maintain invariant bounds and generate consistent execution fingerprints.
