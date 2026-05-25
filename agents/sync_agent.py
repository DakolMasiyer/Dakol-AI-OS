from agents.base_agent import BaseAgent


class SyncAgent(BaseAgent):
    """
    SyncMaster core intelligence agent.
    Handles music metadata reasoning, tagging logic, and sync decisions.
    """

    def __init__(self):
        super().__init__("sync_agent", domain_weight=1.3)

    def analyze_task(self, task: str):
        task = task.lower()

        # ----------------------------
        # HIGH VALUE SYNC INTELLIGENCE
        # ----------------------------
        if any(word in task for word in ["tag", "bpm", "metadata", "tempo", "key"]):
            return {
                "intent": "metadata_analysis",
                "confidence": 0.9
            }

        # ----------------------------
        # AUDIO UNDERSTANDING LAYER
        # ----------------------------
        if any(word in task for word in ["music", "audio", "sound", "track", "song"]):
            return {
                "intent": "audio_understanding",
                "confidence": 0.8
            }

        # ----------------------------
        # GENERAL FALLBACK
        # ----------------------------
        return {
            "intent": "general_analysis",
            "confidence": 0.6
        }