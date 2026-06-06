from skills import posting_skill as ps


def test_instagram_falls_back_to_ayrshare_when_composio_fails(monkeypatch):
    calls = []

    def fail_composio(*args, **kwargs):
        raise RuntimeError("Composio down")

    def fake_post_to_platform(platform, content):
        calls.append((platform, content))
        return {
            "platform": platform,
            "result": {"ok": True},
            "status": "ok",
            "provider": "ayrshare",
        }

    monkeypatch.setattr(ps, "_post_with_composio", fail_composio)
    monkeypatch.setattr(ps, "post_to_platform", fake_post_to_platform)

    result = ps.post_generated_content("user-1", "instagram", "caption text")

    assert result["provider"] == "ayrshare"
    assert result["fallback_from"] == "composio"
    assert calls == [("instagram", "caption text")]


def test_linkedin_uses_composio_when_available(monkeypatch):
    calls = []

    def fake_composio(user_id, platform, content):
        calls.append((user_id, platform, content))
        return {"platform": platform, "status": "ok", "provider": "composio"}

    def fail_fallback(*args, **kwargs):
        raise AssertionError("Ayrshare fallback should not run when Composio succeeds")

    monkeypatch.setattr(ps, "_post_with_composio", fake_composio)
    monkeypatch.setattr(ps, "post_to_platform", fail_fallback)

    result = ps.post_generated_content("user-2", "linkedin", "post text")

    assert result["provider"] == "composio"
    assert calls == [("user-2", "linkedin", "post text")]


def test_twitter_remains_composio_only(monkeypatch):
    calls = []

    def fake_post_twitter_thread(user_id, tweets):
        calls.append((user_id, tweets))
        return {"platform": "twitter", "status": "ok"}

    monkeypatch.setattr(ps, "post_twitter_thread", fake_post_twitter_thread)

    result = ps.post_generated_content("user-3", "twitter", "1. First\n2. Second")

    assert result["platform"] == "twitter"
    assert calls == [("user-3", ["First", "Second"])]
