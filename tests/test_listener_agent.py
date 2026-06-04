from agents.listener_agent import ListenerAgent


def test_listener_agent_wins_on_evaluation_task():
    agent = ListenerAgent()
    result = agent.run("evaluate this uploaded track against the brief")
    assert result["intent"] == "sync_evaluation"
    assert result["confidence"] >= 0.9


def test_listener_agent_wins_on_upload_task():
    agent = ListenerAgent()
    result = agent.run("upload track and listen for brief matches")
    assert result["intent"] == "sync_evaluation"


def test_listener_agent_wins_on_metadata_task():
    agent = ListenerAgent()
    result = agent.run("tag the BPM and key for this audio file")
    assert result["intent"] == "metadata_extraction"
    assert result["confidence"] >= 0.8


def test_listener_agent_has_high_domain_weight():
    agent = ListenerAgent()
    assert agent.domain_weight >= 1.4
