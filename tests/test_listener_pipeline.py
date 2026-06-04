from unittest.mock import patch, MagicMock
import uuid

MOCK_EVALUATION = {
    "fit_score": 0.78,
    "strengths": ["high energy", "driving BPM"],
    "weaknesses": ["minor key"],
    "recommendation": "approve",
    "reasoning": "Good automotive fit. BPM 128 matches brief energy.",
    "mood_tags": ["powerful", "driving"],
}


def test_pipeline_returns_top_matches():
    from farm.listener_pipeline import process_uploaded_track
    with patch("farm.listener_pipeline._layer1_extract") as mock_l1, \
         patch("farm.listener_pipeline._layer2_evaluate") as mock_l2, \
         patch("farm.listener_pipeline.write_evaluation_log") as mock_write, \
         patch("urllib.request.urlretrieve"):
        mock_l1.return_value = {"bpm": 128.0, "key": "F minor", "energy": 0.85}
        mock_l2.return_value = MOCK_EVALUATION
        mock_write.return_value = {}
        result = process_uploaded_track(str(uuid.uuid4()), "https://example.com/track.wav")
    assert "metadata" in result
    assert "top_brief_matches" in result
    assert len(result["top_brief_matches"]) <= 5


def test_pipeline_writes_to_evaluation_log():
    from farm.listener_pipeline import process_uploaded_track
    with patch("farm.listener_pipeline._layer1_extract") as mock_l1, \
         patch("farm.listener_pipeline._layer2_evaluate") as mock_l2, \
         patch("farm.listener_pipeline.write_evaluation_log") as mock_write, \
         patch("urllib.request.urlretrieve"):
        mock_l1.return_value = {"bpm": 120.0, "key": "C major", "energy": 0.7}
        mock_l2.return_value = MOCK_EVALUATION
        mock_write.return_value = {}
        process_uploaded_track(str(uuid.uuid4()), "https://example.com/track.wav")
    assert mock_write.call_count == 20  # one write per brief


def test_layer1_extract_returns_required_fields(tmp_path):
    import wave, struct, math
    wav_path = tmp_path / "test.wav"
    with wave.open(str(wav_path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        samples = [int(32767 * math.sin(2 * math.pi * 440 * i / 44100)) for i in range(44100)]
        f.writeframes(struct.pack(f"{len(samples)}h", *samples))
    from farm.listener_pipeline import _layer1_extract
    result = _layer1_extract(str(wav_path))
    assert "bpm" in result
    assert "energy" in result
