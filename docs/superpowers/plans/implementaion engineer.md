Read every source file across both the Next.js frontend and the Python backend it proxies to, plus all SQL migrations and configs. Below is the delta document.

---
SECTION 1 — IMPLEMENTED AND WORKING

api/main.py:42 — /health endpoint returns {"status":"ok"} (verified live).
api/main.py:185 — POST /worldcup/generate, runs blocking LLM in a thread via asyncio.to_thread.
api/main.py:211 — GET /worldcup/matches returns live/mock fixtures.
api/main.py:221 — GET /worldcup/content-types returns the 7 content types.
skills/worldcup_skill.py:174 — generate_worldcup_content full pipeline: match lookup → parallel enrichment → LLM → structured result.
skills/worldcup_skill.py:32 — Groq integration (llama-3.3-70b-versat
skills/worldcup_skill.py:66 — Gemini integration on the new google-genai SDK (gemini-2.5-flashy rotation.
skills/worldcup_skill.py:149 — fallback dispatcher (short            content→Groq-first, l
skills/worldcup_skill.py:191 — content-type/match-status validation  (post-match→finished,
agents/football_data_agent.py:172 — get_matches live football-data.orv4 with 8-fixture mocg real WC2026 data).
agents/football_data_agent.py:193 — get_match_by_id resolves live + mIDs.
agents/football_data_agent.py:297 — get_historical_h2h reads Supabasehistorical_matches.
agents/football_data_agent.py:394 — get_squad_context (squad + coach)agents/football_data_gs_context (grouptable).                                                              agents/football_data_s_context (goldenboot).                                                               agents/football_data_cache (12h matches,30min standings/scorers).                                            agents/worldcup_conteTS for all 7 contenttypes.                                                               agents/worldcup_conteAMPLES keyed by(content_type, tone).                                                agents/worldcup_contet assembles enrichment block + tone directives.                                             agents/orchestrator.pn_llm on google-genai(used by /task, not worldcup).                                       scripts/router.py:99 + fusion + logging(imports intact; not broken).                                        scripts/import_historal WC importer(martj42 CSV → historical_matches).                                  farm/quota_manager.pyota tracking(functional single-instance).                                        projects/worldcup-ai- — tables matches,users, content_outputs, usage_logs, prompts with RLS + service-role  policies.
projects/worldcup-ai-migration.sql:167 — increment_user_usage plpgsqlfunction.
projects/worldcup-ai-migration-hist.sql:6 — historical_matches table indexes.
docs/migrations/2026-06-05-increment-usage-fn.sql:1 — increment_usageatomic SECURITY DEFIN).
projects/worldcup-ai/app/page.tsx:1 — landing page (hero, content grihow-it-works, CTA).
projects/worldcup-ai/app/dashboard/page.tsx:31 — main app (match selegenerate, output, his.
projects/worldcup-ai/app/upgrade/page.tsx:19 — pricing page (USD/NGN,monthly/yearly) wired
projects/worldcup-ai/app/auth/callback/route.ts:35 — OAuth/email     code-for-session exch
projects/worldcup-ai/app/auth/reset-password/page.tsx:33 — password  reset (recovery-sessi
projects/worldcup-ai/app/api/generate/route.ts:64 — generate proxy; uidentity from sessionr check, atomicincrement on success.                                                projects/worldcup-ai/matches proxy withfallback fixtures.                                                   projects/worldcup-ai/ackend health +content-types (verified dakol_online:true).                          projects/worldcup-ai//route.ts:6 — dailyusage/limit for authed user.                                         projects/worldcup-ai/ute.ts:6,40 — GET/POST saved content, IDOR-protected (session id must equal requested id).  projects/worldcup-ai/route.ts:7 —Flutterwave payment init (session-auth, tx_ref carries userId).      projects/worldcup-ai/route.ts:13 — webhookwith unconditional verif-hash signature check, upgrades user to pro +expiry.
projects/worldcup-ai/lib/server-auth.ts:10 — getSessionUser validatesJWT via getUser over
projects/worldcup-ai/lib/supabase-admin.ts:13 — service-role client  singleton.
projects/worldcup-ai/lib/user-db.ts:35 — getOrCreateUser with UTC daireset + expired-pro d
projects/worldcup-ai/proxy.ts:4,34 — Next 16 middleware gating       /dashboard + /upgradeo /).
projects/worldcup-ai/context/UserContext.tsx:31 — auth state, plan,  usage sync, saved-con
projects/worldcup-ai/components/auth/AuthModal.tsx:11 —              signup/signin/forgot,e + X/Twitter OAuth.
projects/worldcup-ai/components/dashboard/MatchSearch.tsx:13 — match search + live/upcomin
projects/worldcup-ai/components/dashboard/ContentTypeSelector.tsx:23 content-type pills witing.
projects/worldcup-ai/components/freemium/PaywallModal.tsx:24 —       daily-limit paywall w
projects/worldcup-ai/components/freemium/GenerationCounter.tsx:5 — X/free counter.
projects/worldcup-ai/components/saved/SavedLibrary.tsx:11 /          SavedItem.tsx:9 — sav
projects/worldcup-ai/components/dashboard/MobileTabBar.tsx:18 — mobiltab navigation.
projects/worldcup-ai/components/onboarding/OnboardingWizard.tsx:1 —  onboarding flow wired
projects/worldcup-ai/types/index.ts:62 — shared types + CONTENT_TYPESFREE_GENERATION_LIMIT
                                                                     SECTION 2 — PARTIALLY
                                                                     projects/worldcup-ai/— unauthenticatedcallers resolve to userId='anonymous', isRealUser=false; the limit blis skipped, so direct (proxy.ts:35 gatesonly /dashboard,/upgrade, not /api). Unmetered LLM cost vector.      projects/worldcup-ai/+ lib/user-db.ts:84 —limit is check-then-increment (TOCTOU); concurrent requests can exceethe free cap.
farm/quota_manager.py:14 — quota persisted to flat                   memory/quota_state.jsess threading.Lock;per-instance and ephemeral on Cloud Run, so quota is not shared acrosinstances and resets
memory/log.py:7,56 — log_event writes flat memory/logs.json (ephemerain cloud) and is neve_content; generationsare not logged to the learning store.                                projects/worldcup-ai-tputs table is defined but never written by any code (orphan); server-side generation historis not persisted.
projects/worldcup-ai/app/api/user/saved-content/route.ts:16 — uses tasaved_content which hn the repo; schemalives only in the live DB (unversioned).                             projects/worldcup-ai/ts:4 — in-memory Mapcounter, resets on cold start, keyed off client-controlled x-user-id header; not productioer/generation-count.
projects/worldcup-ai/app/api/checkout/flutterwave/route.ts:9 + webhooks/flutterwave/FLW_SECRET_KEY/FLW_SECRET_HASH, both absent from .env.local; checkreturns 500 and webhonon-operational untilsecrets are set.                                                  projects/worldcup-ai/route.ts:25 — upgrades to pro on charge.completed without validating amount/currency, witcalling Flutterwave’s idempotency on tx_ref (replayable).                                                     projects/worldcup-ai/et.tsx:48 — the sameCopy/X buttons render for every content type; instagram_caption,  linkedin_post, and yoost” button (noper-platform mapping).                                            projects/worldcup-ai/:257 +app/auth/reset-password/page.tsx:80 — password inputs have no     show/reveal toggle.
projects/worldcup-ai/app/dashboard/page.tsx:460 +                 components/brand/Branto /settings/brand,which does not exist → 404.                                       projects/worldcup-ai/out.tsx:25 — track()calls window.gtag, but no GA4/gtag script is injected; analytics isilent no-op in produ
projects/worldcup-ai/app/page.tsx:31 — landing nav shows static “LApp”/“Create Free Accno logged-inpersonalization.                                                  projects/worldcup-ai/projects/worldcup-ai-migration.sql:45 (daily_limit DEFAULT 10) vs app/api/user/generatied 3) — free-tierlimit value diverges; users created under the old default carry   daily_limit=10.
projects/worldcup-ai/types/index.ts:55 — comment says “5 for free”the constant is 3 (st
agents/football_data_agent.py:333 — dead no-op expression (a_wins ht==team_a else b_winally loop.
agents/football_data_agent.py:508,579 — backup football APIs are sgated on unset BACKUPoach context silentlyreturns None when the primary key lacks data.                     skills/worldcup_skillnal fallback; in cloud it always fails, so on Groq+Gemini exhaustion the userthe “at capacity” erry:272.
agents/football_data_agent.py:297 — H2H requires historical_matchebe seeded; the importis unverified againstthe live DB; empty table injects “No previous World Cup matches.” scripts/router.py:44,laude/run_codex import anthropic/openai, neither listed in requirements.txt, and         ANTHROPIC_API_KEY is s (worldcup pathunaffected).                                                      .gitignore — memory/qgs.json are notignored; runtime state can be committed.                          
SECTION 3 — COMPLETELY MISSING                                    
Rate limiting / abuse protection — no per-IP or per-user throttle LLM endpoint in eithei/app/api/ (noslowapi/limiter present).                                         Settings/account pagerofile, preferences,connected accounts, usage, notifications, change password, delete account).
Server-side brand-profile persistence — brand profile is localStorage
only (lib/brand-profile or endpoint; lostacross devices.
Direct social postingter API postinganywhere (no Composio/Ayrshare/OAuth token exchange); only clipboard + X
web-intent.
social_connections — no table or flow for storing connected social
accounts / tokens.
Distributed usage + quota store — no Redis/Postgres-backed shared
counter; all counterst) or flat-file(quota_manager), so nothing survives multi-instance scale.
Monthly usage enforcenthly_limit exist inschema but no code reads or enforces them (daily only).
Generation history / rites tocontent_outputs or the learning log from the generate flow.
Cost tracking — cost_s exist but no codecomputes or writes per-generation cost.                          Observability — no errics, no structuredlogging; backend uses print(), frontend analytics is a no-op.    Test coverage / CI — ng the worldcup path;frontend has one test (tests/dashboard.test.tsx); no e2e and no Cconfig.
Transactional email ownership — relies on Supabase default email;deliverability and raare unaddressed.
Shared match-data cache — only a per-process in-memory TTL cache (football_data_agent.he/CDN at scale.
Admin / moderation tooling — none.
Account deletion / GD

Audit complete. Ready
