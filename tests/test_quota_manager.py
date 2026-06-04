from unittest.mock import patch
import tempfile
import farm.quota_manager as qm


def _fresh_state():
    return tempfile.mktemp(suffix=".json")


def test_get_available_key_returns_key_when_quota_available():
    with patch("farm.key_rotator._load_keys", return_value=["key-aaaaaaaa", "key-bbbbbbbb"]), \
         patch.object(qm, "STATE_FILE", _fresh_state()):
        key = qm.get_available_key()
    assert key is not None


def test_mark_exhausted_skips_key():
    with patch("farm.key_rotator._load_keys", return_value=["key-aaaaaaaa", "key-bbbbbbbb"]), \
         patch.object(qm, "STATE_FILE", _fresh_state()):
        qm.mark_exhausted("key-aaaaaaaa")
        key = qm.get_available_key()
    assert key == "key-bbbbbbbb"


def test_quota_summary_returns_all_keys():
    with patch("farm.key_rotator._load_keys", return_value=["key-aaaaaaaa"]), \
         patch.object(qm, "STATE_FILE", _fresh_state()):
        summary = qm.quota_summary()
    assert len(summary["keys"]) == 1
    assert summary["keys"][0]["remaining"] == 1400


def test_record_call_increments_counter():
    with patch("farm.key_rotator._load_keys", return_value=["key-aaaaaaaa"]), \
         patch.object(qm, "STATE_FILE", _fresh_state()):
        qm.record_call("key-aaaaaaaa")
        summary = qm.quota_summary()
    assert summary["keys"][0]["calls_today"] == 1
    assert summary["keys"][0]["remaining"] == 1399
