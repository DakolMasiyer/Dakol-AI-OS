class BaseAgent:
    def __init__(self, name: str, domain_weight: float = 1.0):
        self.name = name
        self.domain_weight = domain_weight

    def analyze_task(self, task: str):
        return {
            "intent": "generic",
            "confidence": 0.5
        }

    def run(self, task: str):
        analysis = self.analyze_task(task)

        # ----------------------------
        # INTELLIGENCE SCORING BOOST
        # ----------------------------
        adjusted_confidence = analysis["confidence"] * self.domain_weight

        return {
            "agent": self.name,
            "intent": analysis["intent"],
            "confidence": adjusted_confidence,
            "input": task,
            "status": "processed"
        }