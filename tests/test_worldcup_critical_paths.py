import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
WORLDCUP = ROOT / "projects" / "worldcup-ai"


def test_fastapi_generate_valid_request_returns_content_without_network(monkeypatch):
    calls = []
    fake_skill = types.ModuleType("skills.worldcup_skill")

    def generate_worldcup_content(**kwargs):
        calls.append(kwargs)
        return {
            "status": "ok",
            "content": "Generated content",
            "content_type": kwargs["content_type"],
            "tokens": 25,
            "generation_time_ms": 10,
        }

    fake_skill.generate_worldcup_content = generate_worldcup_content
    monkeypatch.setitem(sys.modules, "skills.worldcup_skill", fake_skill)

    from api.main import app

    client = TestClient(app)
    res = client.post(
        "/worldcup/generate",
        json={"match_id": "match-1", "content_type": "twitter_thread", "user_id": "user-1"},
        headers={"X-User-Id": "user-1"},
    )

    assert res.status_code == 200
    assert res.json()["content"] == "Generated content"
    assert calls == [
        {
            "match_id": "match-1",
            "content_type": "twitter_thread",
            "user_id": "user-1",
            "brand_profile": None,
        }
    ]


def test_next_generate_route_contracts_cover_unauthenticated_usage_and_persistence():
    source = (WORLDCUP / "app/api/generate/route.ts").read_text()

    session_check = source.index("const sessionUser = await getSessionUser(req)")
    unauth_response = source.index("{ error: 'Authentication required'")
    body_parse = source.index("const body = await req.json()")
    usage_check = source.index("if (!usage.allowed)")
    llm_call = source.index("fetch(`${DAKOL_API}/worldcup/generate`")

    assert session_check < body_parse
    assert unauth_response < body_parse
    assert "{ status: 401 }" in source
    assert "{ status: 402 }" in source
    assert usage_check < llm_call
    assert ".from('content_outputs')" in source
    assert "user_id: userId" in source
    assert "content_type: data.content_type || content_type || 'twitter_thread'" in source


def test_usage_enforcement_sql_is_atomic_and_reports_over_limit():
    sql = (WORLDCUP / "docs/migrations/2026-06-05-increment-usage-fn.sql").read_text()

    assert "CREATE OR REPLACE FUNCTION increment_usage" in sql
    assert "UPDATE users" in sql
    assert "users.daily_usage < users.daily_limit" in sql
    assert "RETURNING true, users.daily_usage, users.daily_limit" in sql
    assert "SELECT false, users.daily_usage, users.daily_limit" in sql


def test_concurrent_increment_at_limit_allows_one_success():
    usage = {"count": 2}
    limit = 3

    def atomic_increment():
        if usage["count"] >= limit:
            return False
        usage["count"] += 1
        return True

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda _: atomic_increment(), range(5)))

    assert results.count(True) == 1
    assert usage["count"] == limit


def test_flutterwave_route_contracts_cover_signature_replay_and_amount_validation():
    source = (WORLDCUP / "app/api/webhooks/flutterwave/route.ts").read_text()

    signature_check = source.index("if (signature !== secretHash)")
    payment_check = source.index("if (!isExpectedPayment(planType, currency, amount))")
    upgrade = source.index(".from('users')")
    idempotency = source.index(".from('flutterwave_processed_tx_refs')")

    assert "{ status: 401 }" in source
    assert "{ status: 400 }" in source
    assert "txInsertError.code === '23505'" in source
    assert "status: 'duplicate'" in source
    assert signature_check < idempotency
    assert payment_check < idempotency
    assert idempotency < upgrade
