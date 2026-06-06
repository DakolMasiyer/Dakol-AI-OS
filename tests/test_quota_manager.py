from unittest.mock import patch
import farm.quota_manager as qm


class FakeExecute:
    def __init__(self, data=None):
        self.data = data or []


class FakeQuotaTable:
    def __init__(self):
        self.state = None

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def upsert(self, row, on_conflict=None):
        assert on_conflict == "key"
        self.state = row["value"]
        return self

    def execute(self):
        if self.state is None:
            return FakeExecute([])
        return FakeExecute([{"value": self.state}])


class FakeSupabase:
    def __init__(self):
        self.quota_table = FakeQuotaTable()

    def table(self, name):
        assert name == "quota_state"
        return self.quota_table


def _fake_supabase():
    return FakeSupabase()


def test_get_available_key_returns_key_when_quota_available():
    fake_supabase = _fake_supabase()
    with patch("farm.key_rotator._load_keys", return_value=["key-aaaaaaaa", "key-bbbbbbbb"]), \
         patch.object(qm, "_get_client", return_value=fake_supabase):
        key = qm.get_available_key()
    assert key is not None


def test_mark_exhausted_skips_key():
    fake_supabase = _fake_supabase()
    with patch("farm.key_rotator._load_keys", return_value=["key-aaaaaaaa", "key-bbbbbbbb"]), \
         patch.object(qm, "_get_client", return_value=fake_supabase):
        qm.mark_exhausted("key-aaaaaaaa")
        key = qm.get_available_key()
    assert key == "key-bbbbbbbb"


def test_quota_summary_returns_all_keys():
    fake_supabase = _fake_supabase()
    with patch("farm.key_rotator._load_keys", return_value=["key-aaaaaaaa"]), \
         patch.object(qm, "_get_client", return_value=fake_supabase):
        summary = qm.quota_summary()
    assert len(summary["keys"]) == 1
    assert summary["keys"][0]["remaining"] == 1400


def test_record_call_increments_counter():
    fake_supabase = _fake_supabase()
    with patch("farm.key_rotator._load_keys", return_value=["key-aaaaaaaa"]), \
         patch.object(qm, "_get_client", return_value=fake_supabase):
        qm.record_call("key-aaaaaaaa")
        summary = qm.quota_summary()
    assert summary["keys"][0]["calls_today"] == 1
    assert summary["keys"][0]["remaining"] == 1399
