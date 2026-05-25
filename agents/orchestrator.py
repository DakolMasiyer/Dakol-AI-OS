from agents.sync_agent import SyncAgent
from agents.audio_agent import AudioAgent
from agents.code_agent import CodeAgent
import subprocess
import json


class Orchestrator:
    """
    LLM-powered Fusion Layer + Learning-ready architecture.
    """

    def __init__(self):
        self.agents = [
            SyncAgent(),
            AudioAgent(),
            CodeAgent()
        ]

        # (STEP 9 READY HOOK)
        self.memory = []
        self.model_learning = {}

    # ----------------------------
    # MAIN ROUTE
    # ----------------------------
    def route(self, task: str):
        results = []

        # ----------------------------
        # COLLECT ALL AGENT OUTPUTS
        # ----------------------------
        for agent in self.agents:
            result = agent.run(task)

            if "confidence" not in result:
                result["confidence"] = 0.5

            results.append(result)

        # ----------------------------
        # LLM FUSION BRAIN
        # ----------------------------
        prompt = self._build_fusion_prompt(task, results)
        fusion_output = self._run_llm(prompt)

        parsed = self._safe_parse(fusion_output)

        return {
            "fusion_output": parsed,
            "all_results": results
        }

    # ----------------------------
    # PROMPT BUILDER
    # ----------------------------
    def _build_fusion_prompt(self, task, results):
        return f"""
You are a multi-agent AI fusion engine.

You combine outputs into a single structured decision.

TASK:
{task}

AGENT OUTPUTS:
{json.dumps(results, indent=2)}

Return ONLY valid JSON:

{{
  "final_intent": "string",
  "reasoning": "string",
  "best_agent": "string",
  "confidence": number
}}
"""

    # ----------------------------
    # LLM EXECUTION
    # ----------------------------
    def _run_llm(self, prompt: str):
        return subprocess.run(
            ["ollama", "run", "coder-pro:latest", prompt],
            capture_output=True,
            text=True
        ).stdout.strip()

    # ----------------------------
    # SAFE PARSER (HARDENED)
    # ----------------------------
    def _safe_parse(self, text: str):
        try:
            return json.loads(text)
        except:
            return {
                "final_intent": "unknown",
                "reasoning": text,
                "best_agent": "unknown",
                "confidence": 0.0,
                "parse_status": "failed"
            }