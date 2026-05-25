from agents.base_agent import BaseAgent


class AudioAgent(BaseAgent):
    def __init__(self):
        super().__init__("audio_agent")

    def analyze_task(self, task: str):
        t = task.lower()

        if "audio" in t or "sound" in t or "track" in t:
            return {
                "intent": "audio_analysis",
                "confidence": 0.9
            }

        return {
            "intent": "audio_general",
            "confidence": 0.5
        }
