# Graph Report - .  (2026-06-13)

## Corpus Check
- 242 files · ~82,188 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1735 nodes · 3740 edges · 100 communities (86 shown, 14 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 287 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Memory Graph Layer|Memory Graph Layer]]
- [[_COMMUNITY_Core API Kernel|Core API Kernel]]
- [[_COMMUNITY_API Gateway & Workflow Policy|API Gateway & Workflow Policy]]
- [[_COMMUNITY_WorldCup Context Enrichment|WorldCup Context Enrichment]]
- [[_COMMUNITY_Grading & Scoring Engine|Grading & Scoring Engine]]
- [[_COMMUNITY_Governance & Quotas|Governance & Quotas]]
- [[_COMMUNITY_Football Data Agent|Football Data Agent]]
- [[_COMMUNITY_SyncMaster Metadata|SyncMaster Metadata]]
- [[_COMMUNITY_Architecture & Docs|Architecture & Docs]]
- [[_COMMUNITY_Control Plane API|Control Plane API]]
- [[_COMMUNITY_Planning & Providers|Planning & Providers]]
- [[_COMMUNITY_Adaptive Learning|Adaptive Learning]]
- [[_COMMUNITY_Tracing & Logging|Tracing & Logging]]
- [[_COMMUNITY_Audio Analysis|Audio Analysis]]
- [[_COMMUNITY_API Main & Middleware|API Main & Middleware]]
- [[_COMMUNITY_Audio Agent|Audio Agent]]
- [[_COMMUNITY_Determinism Tests|Determinism Tests]]
- [[_COMMUNITY_SyncMaster Matching|SyncMaster Matching]]
- [[_COMMUNITY_Listening Farm Briefs|Listening Farm Briefs]]
- [[_COMMUNITY_Sync Licensing|Sync Licensing]]
- [[_COMMUNITY_Import Graph Snapshot|Import Graph Snapshot]]
- [[_COMMUNITY_Progress & Dependencies|Progress & Dependencies]]
- [[_COMMUNITY_API Key Rotation|API Key Rotation]]
- [[_COMMUNITY_Batch Processing & Farm DB|Batch Processing & Farm DB]]
- [[_COMMUNITY_Workflow & Tool Tests|Workflow & Tool Tests]]
- [[_COMMUNITY_Requirements & Plans|Requirements & Plans]]
- [[_COMMUNITY_Semantic Router Embeddings|Semantic Router Embeddings]]
- [[_COMMUNITY_Queue Worker & Smoke Tests|Queue Worker & Smoke Tests]]
- [[_COMMUNITY_Storage Adapters|Storage Adapters]]
- [[_COMMUNITY_Architecture Invariants|Architecture Invariants]]
- [[_COMMUNITY_Code Agent|Code Agent]]
- [[_COMMUNITY_Quota Manager Tests|Quota Manager Tests]]
- [[_COMMUNITY_Task Runner|Task Runner]]
- [[_COMMUNITY_Queue Manager|Queue Manager]]
- [[_COMMUNITY_Queue Retry & Workers|Queue Retry & Workers]]
- [[_COMMUNITY_Social Posting Skill|Social Posting Skill]]
- [[_COMMUNITY_Core Logging & Tracing|Core Logging & Tracing]]
- [[_COMMUNITY_Local Storage Backend|Local Storage Backend]]
- [[_COMMUNITY_Trending Injector|Trending Injector]]
- [[_COMMUNITY_Runtime Environment|Runtime Environment]]
- [[_COMMUNITY_OS CLI Tests|OS CLI Tests]]
- [[_COMMUNITY_Multi-Agent Orchestrator|Multi-Agent Orchestrator]]
- [[_COMMUNITY_App Adapter Base|App Adapter Base]]
- [[_COMMUNITY_API Auth Gateway|API Auth Gateway]]
- [[_COMMUNITY_Queue Jobs|Queue Jobs]]
- [[_COMMUNITY_Semantic Route Decision|Semantic Route Decision]]
- [[_COMMUNITY_Task Router Scripts|Task Router Scripts]]
- [[_COMMUNITY_SyncMaster AI Workflow|SyncMaster AI Workflow]]
- [[_COMMUNITY_SyncMaster AI App|SyncMaster AI App]]
- [[_COMMUNITY_Cloud Run Server|Cloud Run Server]]
- [[_COMMUNITY_Listener Agent|Listener Agent]]
- [[_COMMUNITY_Import Graph Artifacts|Import Graph Artifacts]]
- [[_COMMUNITY_Import Graph Snapshots|Import Graph Snapshots]]
- [[_COMMUNITY_Listening Farm Workflow|Listening Farm Workflow]]
- [[_COMMUNITY_Listening Farm Manifest|Listening Farm Manifest]]
- [[_COMMUNITY_SyncMaster Manifest|SyncMaster Manifest]]
- [[_COMMUNITY_Live Ingestion Tests|Live Ingestion Tests]]
- [[_COMMUNITY_Workflow Engines|Workflow Engines]]
- [[_COMMUNITY_API Gateway Tests|API Gateway Tests]]
- [[_COMMUNITY_Live Control Plane Tests|Live Control Plane Tests]]
- [[_COMMUNITY_Live Load Tests|Live Load Tests]]
- [[_COMMUNITY_App Registry|App Registry]]
- [[_COMMUNITY_Workflow Orchestration Tests|Workflow Orchestration Tests]]
- [[_COMMUNITY_API Safety Gateway|API Safety Gateway]]
- [[_COMMUNITY_Memory Log Tests|Memory Log Tests]]
- [[_COMMUNITY_Memory Scripts|Memory Scripts]]
- [[_COMMUNITY_Storage Recovery Tests|Storage Recovery Tests]]
- [[_COMMUNITY_API Tests|API Tests]]
- [[_COMMUNITY_Auth Governance Tests|Auth Governance Tests]]
- [[_COMMUNITY_Extended Load Tests|Extended Load Tests]]
- [[_COMMUNITY_Workflow Engine Tests|Workflow Engine Tests]]
- [[_COMMUNITY_Listening Farm App|Listening Farm App]]
- [[_COMMUNITY_Supabase Config|Supabase Config]]
- [[_COMMUNITY_Workflow Replay Tests|Workflow Replay Tests]]
- [[_COMMUNITY_Farm Policy Config|Farm Policy Config]]
- [[_COMMUNITY_Memory Compat Tests|Memory Compat Tests]]
- [[_COMMUNITY_Farm Ingestion Config|Farm Ingestion Config]]
- [[_COMMUNITY_Gateway Middleware|Gateway Middleware]]
- [[_COMMUNITY_Architecture Drift Tests|Architecture Drift Tests]]
- [[_COMMUNITY_App Capabilities|App Capabilities]]
- [[_COMMUNITY_Phase 8B Migration|Phase 8B Migration]]
- [[_COMMUNITY_VS Code Settings|VS Code Settings]]
- [[_COMMUNITY_WorldCup Config Docs|WorldCup Config Docs]]
- [[_COMMUNITY_WorldCup README|WorldCup README]]

## God Nodes (most connected - your core abstractions)
1. `Orchestrator` - 42 edges
2. `route_task_semantically()` - 41 edges
3. `LocalStorageBackend` - 32 edges
4. `ToolRegistry` - 30 edges
5. `MemoryGraph` - 26 edges
6. `BaseAgent` - 26 edges
7. `create_default_registry()` - 25 edges
8. `WorkflowPolicyEngine` - 25 edges
9. `WorkflowEngine` - 24 edges
10. `DistributedWorker` - 24 edges

## Surprising Connections (you probably didn't know these)
- `SyncMaster Intelligence Layer (Phase 6)` --implements--> `SyncMaster Three-Layer Intelligence Stack`  [INFERRED]
  progress.md → docs/syncmaster_architecture.svg
- `bool` --uses--> `LocalStorageBackend`  [INFERRED]
  farm/listener_pipeline.py → core/storage/local_storage.py
- `Platform Layer README` --depends_on--> `execute_tool()`  [EXTRACTED]
  platform/README.md → core/api.py
- `bool` --uses--> `Orchestrator`  [INFERRED]
  core/invariants.py → agents/orchestrator.py
- `Progress & Next Steps Guide` --describes_implementation_of--> `SyncMaster Three-Layer Intelligence Stack`  [INFERRED]
  progress.md → docs/syncmaster_architecture.svg

## Communities (100 total, 14 thin omitted)

### Community 0 - "Memory Graph Layer"
Cohesion: 0.07
Nodes (50): add_edge(), _coerce_properties(), create_node(), _edge_index(), _empty_graph(), get_node(), list_edges(), list_nodes() (+42 more)

### Community 1 - "Core API Kernel"
Cohesion: 0.06
Nodes (67): build_import_graph(), classify_certification(), create_execution_snapshot(), execute_task(), execute_tool(), list_execution_traces(), load_execution_trace(), Any (+59 more)

### Community 2 - "API Gateway & Workflow Policy"
Cohesion: 0.06
Nodes (44): Any, str, float, int, str, WorkflowFailure, WorkflowPolicyEngine, str (+36 more)

### Community 3 - "WorldCup Context Enrichment"
Cohesion: 0.09
Nodes (44): _empty_result(), enrich_match_context(), _extract_key_events(), _extract_scoreline(), _extract_source_urls(), Any, str, _search() (+36 more)

### Community 4 - "Grading & Scoring Engine"
Cohesion: 0.07
Nodes (22): str, str, Rubric, Any, Path, Rubric, str, FinalGrade (+14 more)

### Community 5 - "Governance & Quotas"
Cohesion: 0.06
Nodes (25): bool, int, Path, str, Any, Path, str, _get_registry() (+17 more)

### Community 6 - "Football Data Agent"
Cohesion: 0.08
Nodes (45): _fetch_backup_api_1_coach(), _fetch_backup_api_1_squad(), _fetch_backup_api_1_team(), _fetch_backup_api_2(), _fetch_football_api(), FootballDataAgent, _format_api_matches(), _get_cached() (+37 more)

### Community 7 - "SyncMaster Metadata"
Cohesion: 0.10
Nodes (30): MetadataAnalysis, analyze_metadata(), _as_list(), _canonical_label(), _collect_tags(), _combined_text(), _confidence(), _contains_term() (+22 more)

### Community 8 - "Architecture & Docs"
Cohesion: 0.07
Nodes (48): Admin UI Mission Control, Application Layer README, Agent Attribute Immutability, AppRegistry, AppRuntimeAdapter, Google Cloud Run, Control Plane API (/api/control-plane), core.api (Stable Kernel Entrypoint) (+40 more)

### Community 9 - "Control Plane API"
Cohesion: 0.08
Nodes (42): Any, int, Path, str, _coerce_state(), get_metrics(), list_workflows(), _load_incidents() (+34 more)

### Community 10 - "Planning & Providers"
Cohesion: 0.12
Nodes (18): ABC, _build_claude_prompt(), ClaudePlanningProvider, create_plan(), DeterministicPlanningProvider, _extract_json_object(), _inputs_for_tool(), PlanningProvider (+10 more)

### Community 11 - "Adaptive Learning"
Cohesion: 0.11
Nodes (25): _add_event(), _agent_weight_multiplier(), analyze_logs(), _as_float(), _average_model_scores(), _build_agent_bias(), _build_model_bias(), _clamp() (+17 more)

### Community 12 - "Tracing & Logging"
Cohesion: 0.10
Nodes (22): Any, Request, str, JsonLogFormatter, assert_clean_outputs(), Set the request ID in context, returning a reset token., Set the workflow ID in context, returning a reset token., Reset the request ID in context using a token. (+14 more)

### Community 13 - "Audio Analysis"
Cohesion: 0.14
Nodes (29): analyze_audio_file(), analyze_audio_intelligence(), analyze_audio_with_optional_model(), _analyze_pcm_wav(), _analyze_with_best_backend(), _analyze_with_librosa(), _coerce_tempo(), _convert_to_wav() (+21 more)

### Community 14 - "API Main & Middleware"
Cohesion: 0.15
Nodes (30): debug_evaluate(), evaluate_track(), EvaluateRequest, _generate_with_fallback_adapter(), handle_task(), Any, int, Request (+22 more)

### Community 15 - "Audio Agent"
Cohesion: 0.09
Nodes (15): AudioAgent, str, BaseAgent, float, str, str, SyncMaster core intelligence agent.     Handles music metadata reasoning, taggin, SyncAgent (+7 more)

### Community 16 - "Determinism Tests"
Cohesion: 0.10
Nodes (8): DeterminismProofTests, MutationSafetyTests, ExecutionPathContext, analyze_task(), Route the task to the most suitable model family.      - claude: architecture, p, _configured_embedding_provider(), route_task_semantically(), SemanticRouterTests

### Community 17 - "SyncMaster Matching"
Cohesion: 0.19
Nodes (26): _as_mapping(), _candidate_summary(), _first_present(), _get_value(), _json_safe(), match_to_brief(), _number(), Any (+18 more)

### Community 18 - "Listening Farm Briefs"
Cohesion: 0.11
Nodes (23): get_active_briefs(), Any, str, Sync placement brief library. Source of truth for all evaluation contexts., Return all briefs available for evaluation., _evaluation_fallback(), _layer1_extract(), _layer1_wav_fallback() (+15 more)

### Community 19 - "Sync Licensing"
Cohesion: 0.19
Nodes (24): Recommendation, _bool_value(), _clearance_notes(), _duration_score(), _fit_label(), _list_value(), _match_score(), _number_value() (+16 more)

### Community 20 - "Import Graph Snapshot"
Cohesion: 0.14
Nodes (20): build_import_graph(), _fingerprint(), ImportEdge, load_snapshot(), main(), Any, bool, int (+12 more)

### Community 21 - "Progress & Dependencies"
Cohesion: 0.09
Nodes (28): SyncMaster Architecture SVG, librosa, soundfile, transformers + torch (Model Tagging), Adaptive Learning Layer (Phase 4), Autonomous Agent OS (Phase 5), Progress & Next Steps Guide, memory/graph.py (Persistent JSON Memory Graph) (+20 more)

### Community 22 - "API Key Rotation"
Cohesion: 0.16
Nodes (23): get_next_key(), key_count(), _load_keys(), int, str, Gemini API key rotator. Cycles through all available keys round-robin. Add keys, get_available_key(), _get_client() (+15 more)

### Community 23 - "Batch Processing & Farm DB"
Cohesion: 0.14
Nodes (19): batch_run_evaluate(), Daily automated job: pulls unevaluated tracks from Supabase and evaluates them a, _get_client(), get_monthly_output_count(), get_unevaluated_tracks(), get_user(), increment_user_usage(), Any (+11 more)

### Community 24 - "Workflow & Tool Tests"
Cohesion: 0.24
Nodes (14): Raised when a tool cannot be registered or executed., ToolRegistryError, ValueError, _extract_path(), _find_references(), Any, str, ToolRegistry (+6 more)

### Community 25 - "Requirements & Plans"
Cohesion: 0.12
Nodes (23): FastAPI, google-genai SDK, slowapi (Rate Limiting), supabase Python SDK, Implementation Engineer Plan, Requirements: Base, Requirements: Dev, Requirements: Lock (Deterministic) (+15 more)

### Community 26 - "Semantic Router Embeddings"
Cohesion: 0.24
Nodes (15): _cosine_similarity(), _dense_cosine_similarity(), _embed_texts(), _embed_with_openai(), _get_route_embeddings(), IntentProfile, IsolatedEmbeddingCache, _matched_terms() (+7 more)

### Community 27 - "Queue Worker & Smoke Tests"
Cohesion: 0.16
Nodes (9): DistributedWorker, main(), int, str, _smoke_web(), _smoke_worker(), DistributedQueueTests, RetryIntegrityTests (+1 more)

### Community 28 - "Storage Adapters"
Cohesion: 0.15
Nodes (12): Any, bool, bytes, str, Saves content to the given logical path.          :param logical_path: Determini, Loads content from the given logical path.          :param logical_path: Determi, Deletes the file at the given logical path.          :param logical_path: Determ, Generates a standardized, deterministic logical path.          :param prefix: Th (+4 more)

### Community 29 - "Architecture Invariants"
Cohesion: 0.16
Nodes (9): assert_agent_immutability(), assert_no_learning_state_direct_access(), assert_routing_determinism(), str, Assert routing determinism by comparing two decisions for the same task., Assert no runtime mutation of agents., Enforce that NO module except memory/learning.py (or tests) may import or parse, AdversarialDriftTests (+1 more)

### Community 30 - "Code Agent"
Cohesion: 0.16
Nodes (9): CodeAgent, str, assert_learning_is_advisory_only(), is_in_execution_path(), bool, Assert learning state is not accessed during execution path., get_learning_recommendations(), Single interface to retrieve advisory recommendations.     learning_state.json i (+1 more)

### Community 31 - "Quota Manager Tests"
Cohesion: 0.16
Nodes (8): _fake_supabase(), FakeExecute, FakeQuotaTable, FakeSupabase, test_get_available_key_returns_key_when_quota_available(), test_mark_exhausted_skips_key(), test_quota_summary_returns_all_keys(), test_record_call_increments_counter()

### Community 32 - "Task Runner"
Cohesion: 0.25
Nodes (6): str, TaskRunner, _now(), str, TaskStore, TaskStore

### Community 33 - "Queue Manager"
Cohesion: 0.24
Nodes (9): int, JobState, Path, str, Number of jobs not yet in a terminal state., Manages job leases across workers for a single queue.      In local mode jobs ar, Attempt to acquire (or recover) the lease for a job.          Returns the locked, Reset jobs whose lease has expired back to PENDING so another worker         can (+1 more)

### Community 34 - "Queue Retry & Workers"
Cohesion: 0.18
Nodes (8): Any, int, Any, JobState, Path, str, Deterministically calculate backoff delay., RetryPolicy

### Community 35 - "Social Posting Skill"
Cohesion: 0.37
Nodes (16): _composio_api_key(), _execute_composio_action(), _extract_composio_id(), _get_connection(), parse_thread(), post_generated_content(), post_to_platform(), post_twitter_thread() (+8 more)

### Community 36 - "Core Logging & Tracing"
Cohesion: 0.20
Nodes (11): str, get_request_id(), get_workflow_id(), Retrieve the current request ID from context., Retrieve the current workflow ID from context., LogRecord, load_memory(), log_event() (+3 more)

### Community 37 - "Local Storage Backend"
Cohesion: 0.28
Nodes (7): Any, bool, bytes, str, LocalStorageBackend, Local filesystem implementation of the StorageAdapter., Helper to get the physical path. Use only when bridging with legacy libraries.

### Community 38 - "Trending Injector"
Cohesion: 0.43
Nodes (14): _build_result(), _empty_result(), _extract_hashtags(), _extract_hashtags_from_value(), _extract_text(), _fetch_dataset_items(), _get_cache(), get_trending_angles() (+6 more)

### Community 39 - "Runtime Environment"
Cohesion: 0.32
Nodes (13): configure_logging(), build_runtime_manifest(), _distribution_version(), ensure_runtime_environment(), Any, bool, str, _runtime_container_id() (+5 more)

### Community 40 - "OS CLI Tests"
Cohesion: 0.19
Nodes (5): OsCliTests, float, int, Path, _write_click_wav()

### Community 41 - "Multi-Agent Orchestrator"
Cohesion: 0.29
Nodes (4): Orchestrator, str, LLM-powered Fusion Layer + Learning-ready architecture., OrchestratorLearningTests

### Community 42 - "App Adapter Base"
Cohesion: 0.21
Nodes (5): Any, str, Path, AppRuntimeAdapter, AppManifest

### Community 43 - "API Auth Gateway"
Cohesion: 0.24
Nodes (12): Any, str, get_current_user(), get_supabase_jwt_secret(), Dependency to verify Supabase JWT token and extract user identity.     Returns t, Strict dependency that requires a valid authenticated user., Extract the set of application scopes a token is allowed to access.      Support, Build a dependency that requires an authenticated user whose token is     scoped (+4 more)

### Community 44 - "Queue Jobs"
Cohesion: 0.22
Nodes (6): bool, int, str, Distributed queue manager with lease-based crash recovery.  This is the orchestr, JobLease, JobState

### Community 45 - "Semantic Route Decision"
Cohesion: 0.23
Nodes (3): RouteDecision, FailureInjectionTests, ReplayEngineTests

### Community 46 - "Task Router Scripts"
Cohesion: 0.35
Nodes (11): clean_model_output(), execute_task(), bool, str, Execute the task through Claude via the Anthropic SDK., Execute the task through OpenAI for code-oriented work., Execute the task through the shared fallback router., route_task() (+3 more)

### Community 47 - "SyncMaster AI Workflow"
Cohesion: 0.39
Nodes (3): Any, str, SyncMasterOrchestratedWorkflow

### Community 48 - "SyncMaster AI App"
Cohesion: 0.18
Nodes (4): str, SyncMasterAI, TestCase, AppIsolationTests

### Community 49 - "Cloud Run Server"
Cohesion: 0.22
Nodes (4): CloudRunServer, int, str, Runs initialization and marks server as ready.

### Community 50 - "Listener Agent"
Cohesion: 0.29
Nodes (6): ListenerAgent, str, test_listener_agent_has_high_domain_weight(), test_listener_agent_wins_on_evaluation_task(), test_listener_agent_wins_on_metadata_task(), test_listener_agent_wins_on_upload_task()

### Community 51 - "Import Graph Artifacts"
Cohesion: 0.20
Nodes (9): edge_count, edges, fingerprint, forbidden_learning_imports, generated_at, module_count, modules, root (+1 more)

### Community 52 - "Import Graph Snapshots"
Cohesion: 0.20
Nodes (9): edge_count, edges, fingerprint, forbidden_learning_imports, generated_at, module_count, modules, root (+1 more)

### Community 53 - "Listening Farm Workflow"
Cohesion: 0.44
Nodes (3): Any, str, ListeningFarmWorkflow

### Community 54 - "Listening Farm Manifest"
Cohesion: 0.22
Nodes (8): allowed_capabilities, allowed_tools, app_id, execution_profile, policy_scope, replay_policy, trace_namespace, trace_retention_policy

### Community 55 - "SyncMaster Manifest"
Cohesion: 0.22
Nodes (8): allowed_capabilities, allowed_tools, app_id, execution_profile, policy_scope, replay_policy, trace_namespace, trace_retention_policy

### Community 57 - "Live Ingestion Tests"
Cohesion: 0.22
Nodes (8): VERIFY:     - ingestion workflow runs     - evaluation_log updated     - fingerp, VERIFY:     - run parallel ingestion jobs     - no duplicated evaluation IDs, VERIFY:     - simulate exhausted Gemini quota     - workflow halts gracefully, VERIFY:     - evaluation history queryable, test_concurrent_ingestion_no_duplicates(), test_ingestion_creates_evaluation_entries(), test_intelligence_accumulation_persists(), test_quota_exhaustion_fails_safely()

### Community 58 - "Workflow Engines"
Cohesion: 0.28
Nodes (3): WorkflowEngine(), WorkflowPolicyEngine(), AsyncReplayTests

### Community 59 - "API Gateway Tests"
Cohesion: 0.22
Nodes (8): Verify that the Gateway middleware is adding the custom observability headers., Verify that the control plane metrics endpoint is accessible and returns expecte, JWT sub claim takes priority over user_id in the request body., Verify the main health endpoint is accessible through the gateway setup., test_control_plane_metrics(), test_gateway_health(), test_gateway_middleware_headers(), test_generate_ignores_body_user_id()

### Community 60 - "Live Control Plane Tests"
Cohesion: 0.22
Nodes (8): VERIFY:     - active jobs reflected accurately, VERIFY:     - trigger intentional worker failure     - incident appears in dashb, VERIFY:     - inspect completed execution, VERIFY:     - workers appear live, test_failure_dashboard_operational(), test_queue_depth_visible(), test_replay_inspection_operational(), test_worker_health_visible()

### Community 61 - "Live Load Tests"
Cohesion: 0.22
Nodes (8): Simulates a Worldcup generation request, testing the workflow engine., Simulates a Syncmaster submission with approval checkpoint., Test that the control plane can list workflows., Simulates a Syncmaster evaluation request, testing the workflow engine end-to-en, test_control_plane_workflows(), test_syncmaster_evaluate_workflow(), test_syncmaster_submit_workflow(), test_worldcup_generate_workflow()

### Community 62 - "App Registry"
Cohesion: 0.25
Nodes (4): AppManifest, AppRegistry, Path, str

### Community 64 - "API Safety Gateway"
Cohesion: 0.33
Nodes (6): Any, str, enforce_immutable_approvals(), Ensures that an app-scoped session cannot trigger another app's     operational, Prevents frontend from directly mutating workflows or bypassing     governance a, validate_cross_app_access()

### Community 66 - "Memory Scripts"
Cohesion: 0.48
Nodes (6): load_memory(), log_event(), Compatibility wrapper for the canonical memory logger.  Older code imported memo, record_feedback(), save_memory(), _with_legacy_memory_file()

### Community 67 - "Storage Recovery Tests"
Cohesion: 0.29
Nodes (6): VERIFY:     - workflow records persisted, VERIFY:     - kill active worker process     - another worker safely recovers le, VERIFY:     - traces remain queryable, test_supabase_stores_lineage(), test_worker_crash_recovery(), test_workflow_traces_persist()

### Community 69 - "Auth Governance Tests"
Cohesion: 0.29
Nodes (6): VERIFY:     - WorldCup token cannot access SyncMaster workflows, VERIFY:     - attempt direct workflow mutation, VERIFY:     - invalid JWT rejected, test_cross_app_access_blocked(), test_frontend_mutation_attempts_fail(), test_unauthorized_request_blocked()

### Community 70 - "Extended Load Tests"
Cohesion: 0.29
Nodes (6): VERIFY:     - launch many simultaneous jobs     - no duplicate execution, VERIFY:     - replay workflows during active load, VERIFY:     - queue depth increases safely, test_async_replay_stable(), test_concurrent_workflows_stable(), test_queue_scaling_verified()

### Community 72 - "Listening Farm App"
Cohesion: 0.60
Nodes (3): Any, str, ListeningFarmAI

### Community 75 - "Supabase Config"
Cohesion: 0.40
Nodes (4): name, organization_id, organization_slug, ref

### Community 78 - "Farm Policy Config"
Cohesion: 0.50
Nodes (3): enforce_sandbox, max_memory_mb, timeout_seconds

## Knowledge Gaps
- **139 isolated node(s):** `str`, `Any`, `int`, `bool`, `edge_count` (+134 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `route_task_semantically()` connect `Determinism Tests` to `WorldCup Context Enrichment`, `Semantic Route Decision`, `Task Router Scripts`, `Semantic Router Embeddings`, `Architecture Invariants`, `Code Agent`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `create_default_registry()` connect `WorldCup Context Enrichment` to `Memory Graph Layer`, `Core API Kernel`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `get_logger()` connect `Control Plane API` to `WorldCup Context Enrichment`, `Core Logging & Tracing`, `Trending Injector`, `Runtime Environment`, `Football Data Agent`, `Tracing & Logging`, `API Main & Middleware`, `Task Router Scripts`, `Listening Farm Briefs`, `Batch Processing & Farm DB`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `Orchestrator` (e.g. with `AudioAgent` and `CodeAgent`) actually correct?**
  _`Orchestrator` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `LocalStorageBackend` (e.g. with `EvaluateRequest` and `Any`) actually correct?**
  _`LocalStorageBackend` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `ToolRegistry` (e.g. with `ToolRegistryTests` and `TracingTests`) actually correct?**
  _`ToolRegistry` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `MemoryGraph` (e.g. with `int` and `MemoryGraph`) actually correct?**
  _`MemoryGraph` has 7 INFERRED edges - model-reasoned connections that need verification._