import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestApi(unittest.TestCase):
    def test_health_check(self):
        from api.main import app
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_task_endpoint_accepts_valid_task(self):
        from api.main import app
        client = TestClient(app)
        with patch("api.main.route_task") as mock_route:
            mock_route.return_value = "routing complete"
            response = client.post("/task", json={"task": "tag the BPM for this track"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("output", response.json())

    def test_task_endpoint_rejects_empty_task(self):
        from api.main import app
        client = TestClient(app)
        response = client.post("/task", json={"task": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json())

    def test_evaluate_endpoint_returns_result(self):
        from api.main import app
        client = TestClient(app)
        with patch("api.main.process_uploaded_track") as mock_pipeline:
            mock_pipeline.return_value = {"metadata": {}, "top_brief_matches": []}
            response = client.post("/syncmaster/evaluate", json={
                "track_id": "abc-123",
                "audio_url": "https://example.com/track.wav"
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn("top_brief_matches", response.json())

    def test_batch_run_endpoint(self):
        from api.main import app
        client = TestClient(app)
        
        with patch("farm.supabase_client.get_unevaluated_tracks") as mock_get_tracks, \
             patch("farm.listener_pipeline.process_uploaded_track") as mock_process:
             
            mock_get_tracks.return_value = [
                {"id": "track-abc", "audio_url": "https://example.com/abc.mp3", "title": "Track ABC"},
                {"id": "track-def", "audio_url": "https://example.com/def.mp3", "title": "Track DEF"}
            ]
            mock_process.return_value = {"top_brief_matches": [{"brief_id": "b001", "fit_score": 0.9}]}
            
            response = client.post("/syncmaster/batch-run")
            
        self.assertEqual(response.status_code, 200)
        res_json = response.json()
        self.assertEqual(res_json["status"], "ok")
        self.assertEqual(res_json["processed_count"], 2)
        self.assertEqual(res_json["evaluated"][0]["track_id"], "track-abc")
        self.assertEqual(res_json["evaluated"][0]["status"], "success")
