I’ll read the implementation engineer plan first, then I’ll separate
  existing working pieces from implementation gaps and sequence the work
  without making edits.

• Explored
  └ Read implementaion engineer.md

──────────────────────────────────────────────────────────────────────────

• Based on that plan:

  1. Already Working

  I would not touch these unless a later change directly depends on them:

  - Backend health and World Cup API routes:
      - /health
      - /worldcup/generate
      - /worldcup/matches
      - /worldcup/content-types

  - Core World Cup generation pipeline:
      - match lookup
      - enrichment
      - LLM generation
      - structured result
      - content-type and match-status validation

  - Existing LLM provider routing:
      - Groq
      - Gemini
      - fallback dispatcher behavior

  - Football data agent basics:
      - live/mock fixtures
      - match lookup
      - H2H lookup
      - squad/coach context
      - group table context
      - golden boot context
      - in-process cache

  - Existing frontend app surfaces:
      - landing page
      - dashboard
      - upgrade page
      - auth callback
      - reset password
      - match search
      - content type selector
      - saved library UI
      - onboarding
      - paywall modal
      - generation counter UI

  - Existing auth/session plumbing:
      - Supabase session validation
      - service-role admin client
      - user creation/reset logic
      - dashboard/upgrade middleware gating

  - Existing payment skeleton:
      - Flutterwave checkout route
      - Flutterwave webhook route

  - Existing database tables/functions that are already defined:
      - users
      - matches
      - content_outputs
      - usage_logs
      - prompts
      - historical_matches
      - increment_user_usage
      - increment_usage

  2. Confirmed Gaps To Implement

  I would implement these confirmed gaps:

  - Protect unauthenticated /api/generate usage so anonymous callers
    cannot bypass metering and generate unmetered LLM cost.

  - Replace check-then-increment usage logic with atomic usage enforcement
    so concurrent requests cannot exceed the free cap.

  - Align free-tier limits across schema, constants, comments, and runtime
    behavior.

  - Add production-grade rate limiting or abuse protection for the
    generation endpoint.

  - Persist generation history server-side by writing successful
    generations to content_outputs.

  - Add missing/versioned schema for saved_content if the app depends on
    that table.

  - Move brand profile persistence from localStorage only to server-side
    storage.

  - Add a real settings/account page because existing UI links point to /
    settings/brand, which currently 404s.

  - Fix generation counter backend behavior so it does not rely on an in-
    memory Map keyed by client-controlled x-user-id.

  - Harden Flutterwave webhook handling:
      - verify payment amount
      - verify currency
      - add idempotency/replay protection around tx_ref
      - keep existing signature verification

  - Make payment routes operational by ensuring required secret handling
    is validated clearly.

  - Add per-content-type share/action mapping instead of rendering the
    same Copy/X buttons for every output type.

  - Add password reveal toggles to password fields.
  - Fix analytics by injecting GA4/gtag or removing the silent no-op
    tracking path.

  - Add observability basics:
      - structured logs
      - useful error logging around generation/payment
      - generation outcome logging

  - Add test coverage and CI for the risky paths:
      - generate API
      - usage limit enforcement
      - webhook verification
      - saved content/history persistence

  I would not prioritize direct social posting, admin/moderation tooling,
  full GDPR deletion, monthly billing enforcement, or distributed match
  cache first unless the product requirement is immediate. They are real
  gaps, but they are downstream of making generation, usage, persistence,
  and payments reliable.

  3. Implementation Order

  1. Lock down /api/generate and usage enforcement first.
     This is the highest-risk gap because it can create direct LLM cost
     exposure. I would require a real session or apply a strict anonymous
     path, then enforce limits atomically through the database.

  2. Normalize limits and counter behavior.
     The app currently has conflicting values and a weak in-memory
     counter. I would make one source of truth for the free limit and
     remove client-controlled or cold-start-reset behavior from production
     paths.

  3. Persist successful generations.
     Once generation is safely metered, I would write outputs to
     content_outputs and connect that to history. This turns the existing
     orphan table into useful product behavior.

  4. Version missing database schema.
     If saved_content exists only in the live DB, I would add a migration
     before touching more saved-content logic. That prevents local/dev/
     prod drift.

  5. Harden payments.
     After usage and persistence are reliable, I would fix Flutterwave
     verification, amount/currency validation, replay protection, and
     secret checks. Payment bugs are high impact, but they sit behind the
     upgrade path rather than every generation request.

  6. Add settings and brand-profile persistence.
     Then I would resolve the broken /settings/brand route and make brand
     profiles durable across devices.

  7. Fix UI correctness issues.
     Platform-specific action buttons, password reveal toggles, logged-in
     landing personalization, and analytics wiring are worthwhile but
     lower risk than metering/payment/data consistency.

  8. Add tests and CI around the completed critical paths.
     I would test after each major backend change, but the focused CI
     suite should land once the generate, usage, persistence, and payment
     contracts are clear.
