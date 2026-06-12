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
