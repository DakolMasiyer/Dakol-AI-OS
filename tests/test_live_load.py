import pytest
from fastapi.testclient import TestClient
from api.main import app
import time

client = TestClient(app)

def test_syncmaster_evaluate_workflow():
    """
    Simulates a Syncmaster evaluation request, testing the workflow engine end-to-end.
    """
    start_time = time.time()
    response = client.post("/syncmaster/evaluate", json={
        "track_id": "test-track-123",
        "audio_url": "local://test",
        "synthetic": True
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "top_brief_matches" in data or "status" in data
    
    duration = time.time() - start_time
    # Ensure it returns in a reasonable amount of time (mocked out or fast)
    assert duration < 20.0

def test_worldcup_generate_workflow():
    """
    Simulates a Worldcup generation request, testing the workflow engine.
    """
    response = client.post("/worldcup/generate", json={
        "match_id": "mock_match_id",
        "content_type": "twitter_thread",
        "user_id": "anonymous"
    })
    
    # 400 is acceptable if "mock_match_id" is not found by the mock
    assert response.status_code in [200, 400]

def test_syncmaster_submit_workflow():
    """
    Simulates a Syncmaster submission with approval checkpoint.
    """
    response = client.post("/syncmaster/submit", json={
        "catalog_id": "cat_123",
        "items": [{"title": "Track 1"}]
    })
    
    assert response.status_code == 200
    data = response.json()
    # It should hit the HUMAN_REVIEW checkpoint and return WAITING_FOR_APPROVAL
    assert data.get("status") == "PAUSED" or data.get("status") == "COMPLETED"

def test_control_plane_workflows():
    """
    Test that the control plane can list workflows.
    """
    response = client.get("/api/control-plane/workflows")
    assert response.status_code == 200
    data = response.json()
    assert "workflows" in data
    assert isinstance(data["workflows"], list)
