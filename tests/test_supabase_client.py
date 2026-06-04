import unittest
from unittest.mock import patch, MagicMock


class TestSupabaseClient(unittest.TestCase):
    def test_write_evaluation_log_calls_supabase(self):
        from farm.supabase_client import write_evaluation_log
        fake_entry = {
            "track_id": "track-uuid-001",
            "brief_id": "b001",
            "placement_type": "automotive_ad",
            "brief": {"brief_id": "b001", "placement_type": "automotive_ad"},
            "fit_score": 0.82,
            "strengths": ["high energy", "driving rhythm"],
            "weaknesses": ["minor key may not suit brand"],
            "recommendation": "approve",
            "reasoning": "Track energy and BPM align well with automotive brief.",
            "bpm_estimate": 128.0,
            "key_estimate": "F minor",
            "energy_level": 0.85,
            "mood_tags": ["powerful", "driving"],
            "listener_model": "gemini-1.5-pro",
            "synthetic": False,
        }
        with patch("farm.supabase_client._get_client") as mock_client:
            mock_client.return_value.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[fake_entry])
            result = write_evaluation_log(fake_entry)
        self.assertIsNotNone(result)

    def test_write_evaluation_log_marks_synthetic(self):
        from farm.supabase_client import write_evaluation_log
        with patch("farm.supabase_client._get_client") as mock_client:
            mock_client.return_value.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
            write_evaluation_log({"brief_id": "b001", "synthetic": True})
        call_args = mock_client.return_value.table.return_value.insert.call_args
        self.assertTrue(call_args[0][0]["synthetic"])

    def test_get_unevaluated_tracks(self):
        from farm.supabase_client import get_unevaluated_tracks
        with patch("farm.supabase_client._get_client") as mock_client:
            # Mock tracks table select
            mock_tracks = [
                {"id": "track-001", "audio_url": "https://example.com/1.mp3", "title": "Track 1"},
                {"id": "track-002", "audio_url": None, "title": "Track 2 (no audio)"},
                {"id": "track-003", "audio_url": "https://example.com/3.mp3", "title": "Track 3"},
            ]
            # Mock evaluation_log table select
            mock_evals = [
                {"track_id": "track-001"}
            ]
            
            # We need to handle multiple calls to table().select().execute()
            # First call is to "tracks", second is to "evaluation_log"
            mock_table = mock_client.return_value.table
            mock_select = mock_table.return_value.select
            mock_execute = mock_select.return_value.execute
            
            # Set side_effect to return mock data for tracks, then evaluations
            mock_execute.side_effect = [
                MagicMock(data=mock_tracks),
                MagicMock(data=mock_evals)
            ]
            
            result = get_unevaluated_tracks()
            
        # track-001 is evaluated, track-002 has no audio_url, so only track-003 should be returned
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "track-003")
