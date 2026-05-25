from agents.base_agent import BaseAgent


class CodeAgent(BaseAgent):
    def __init__(self):
        super().__init__("code_agent")

    def analyze_task(self, task: str):
        t = task.lower()

        if any(word in t for word in ["code", "api", "fastapi", "build", "implement"]):
            return {
                "intent": "code_execution",
                "confidence": 0.9
            }

        return {
            "intent": "code_general",
            "confidence": 0.5
        }
