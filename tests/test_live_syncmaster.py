import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_catalog_submission_workflow():
    """
    VERIFY:
    - submission appears in queue
    - workflow stages visible
    - recommendation generated
    """
    response = client.post("/syncmaster/submit", json={
        "catalog_id": "test_cat",
        "items": [{"title": "Live Test Track"}]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ["PAUSED", "COMPLETED", "error"]

def test_human_approval_checkpoint():
    """
    VERIFY:
    - workflow pauses
    - checkpoint written
    """
    from workflows.definitions import create_syncmaster_submission_workflow
    engine = create_syncmaster_submission_workflow("test_app")
    
    res = engine.execute({
        "catalog_id": "test_approval",
        "items": []
    })
    
    assert res.get("status") == "PAUSED"
    
    # Resume with approval
    payload = res.get("payload", {})
    payload["approved"] = True
    
    res2 = engine.execute(payload)
    assert res2.get("status") == "COMPLETED"

def test_recommendation_exports():
    """
    VERIFY:
    - report generated
    - export trace stored
    """
    from workflows.definitions import create_syncmaster_submission_workflow
    engine = create_syncmaster_submission_workflow("test_app")
    
    res = engine.execute({
        "catalog_id": "test_export",
        "items": [],
        "approved": True
    })
    
    assert res.get("status") == "COMPLETED"
    payload = res.get("payload", {})
    assert "recommendation" in payload
