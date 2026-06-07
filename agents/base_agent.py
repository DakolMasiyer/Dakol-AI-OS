class BaseAgent:
    def __init__(self, name: str, domain_weight: float = 1.0):
        self.name = name
        self.base_weight = domain_weight

    @property
    def domain_weight(self) -> float:
        return self.base_weight

    def analyze_task(self, task: str):
        return {
            "intent": "generic",
            "confidence": 0.5
        }

    def run(self, task: str):
        analysis = self.analyze_task(task)

        # Final weight computation uses base weight only, keeping it strictly advisory
        final_weight = self.base_weight

        # ----------------------------
        # INTELLIGENCE SCORING BOOST
        # ----------------------------
        adjusted_confidence = analysis["confidence"] * final_weight

        return {
            "agent": self.name,
            "intent": analysis["intent"],
            "confidence": adjusted_confidence,
            "input": task,
            "status": "processed"
        }