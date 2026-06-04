from agents.base_agent import BaseAgent


class ListenerAgent(BaseAgent):
    def __init__(self):
        super().__init__("listener_agent", domain_weight=1.4)

    def analyze_task(self, task: str) -> dict:
        t = task.lower()
        if any(w in t for w in ("upload", "listen", "evaluate", "brief", "sync fit", "placement")):
            return {"intent": "sync_evaluation", "confidence": 0.95}
        if any(w in t for w in ("tag", "bpm", "metadata", "key", "tempo", "audio")):
            return {"intent": "metadata_extraction", "confidence": 0.85}
        return {"intent": "general_audio", "confidence": 0.5}
