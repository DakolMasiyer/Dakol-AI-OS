from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_gateway_health():
    """Verify the main health endpoint is accessible through the gateway setup."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_gateway_middleware_headers():
    """Verify that the Gateway middleware is adding the custom observability headers."""
    response = client.get("/health")
    assert "X-Gateway-Processed" in response.headers
    assert response.headers["X-Gateway-Processed"] == "true"
    assert "X-Gateway-Latency-Ms" in response.headers

def test_control_plane_metrics():
    """Verify that the control plane metrics endpoint is accessible and returns expected structure."""
    response = client.get("/api/control-plane/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "workers" in data
    assert "queues" in data
    assert "incidents" in data


def test_generate_ignores_body_user_id():
    """JWT sub claim takes priority over user_id in the request body."""
    import os
    import jwt as pyjwt
    from unittest.mock import patch, MagicMock

    secret = os.environ.get("SUPABASE_JWT_SECRET", "ci-test-jwt-secret")
    token = pyjwt.encode(
        {"sub": "jwt-user-123", "aud": "authenticated", "role": "authenticated"},
        secret,
        algorithm="HS256",
    )

    mock_engine = MagicMock()
    mock_engine.execute.return_value = {
        "status": "COMPLETED",
        "payload": {
            "generation_result": {
                "status": "ok",
                "content": "test content",
                "user_id": "jwt-user-123",
                "model": "groq/llama-3.3-70b",
                "tokens": 10,
                "generation_time_ms": 100,
                "content_type": "twitter_thread",
            }
        },
    }

    with patch("workflows.definitions.create_worldcup_generation_workflow", return_value=mock_engine), \
         patch("farm.supabase_client.increment_user_usage", return_value={"allowed": True}), \
         patch("farm.supabase_client.get_user", return_value={"tier": "pro"}), \
         patch("farm.supabase_client.get_monthly_output_count", return_value=0):

        response = client.post(
            "/worldcup/generate",
            json={
                "match_id": "wc2026-001",
                "content_type": "twitter_thread",
                "user_id": "body-injected-user-999",  # should be ignored
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code != 401, f"Auth rejected valid JWT: {response.json()}"

    # The workflow must have been called with the JWT sub, not the body user_id.
    assert mock_engine.execute.called, "Workflow engine was not invoked"
    execute_payload = mock_engine.execute.call_args[0][0]
    assert execute_payload["user_id"] == "jwt-user-123"
    assert execute_payload["user_id"] != "body-injected-user-999"
