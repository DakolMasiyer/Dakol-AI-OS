from agents.sync_agent import SyncAgent
from agents.audio_agent import AudioAgent
from agents.code_agent import CodeAgent
from agents.listener_agent import ListenerAgent
from agents.worldcup_content_agent import WorldCupContentAgent
from agents.football_data_agent import FootballDataAgent
from memory.learning import get_agent_weight_multiplier, load_learning_state
import os
import json
import re


class Orchestrator:
    """
    LLM-powered Fusion Layer + Learning-ready architecture.
    """

    def __init__(self, learning_state=None):
        self.agents = [
            SyncAgent(),
            AudioAgent(),
            CodeAgent(),
            ListenerAgent(),
            WorldCupContentAgent(),
            FootballDataAgent(),
        ]

        self.learning_state = learning_state if learning_state is not None else load_learning_state()
        self._apply_agent_learning()

        self.memory = []
        self.model_learning = {}

    def _apply_agent_learning(self):
        for agent in self.agents:
            multiplier = get_agent_weight_multiplier(agent.name, self.learning_state)
            agent.base_domain_weight = agent.domain_weight
            agent.learning_multiplier = multiplier
            agent.domain_weight = round(agent.domain_weight * multiplier, 3)

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
    def _run_llm(self, prompt: str) -> str:
        from google import genai
        from google.genai import types

        # Get available key from quota manager instead of only primary key
        from farm.quota_manager import get_available_key
        api_key = get_available_key() or os.environ.get("GEMINI_API_KEY", "")
        client = genai.Client(api_key=api_key)
        fallback = '{"final_intent": "unknown", "reasoning": "all LLM backends failed", "best_agent": "unknown", "confidence": 0.0}'

        for model_name in ("gemini-2.5-flash", "gemini-1.5-flash-8b"):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response.text
            except Exception as e:
                print(f"[orchestrator] {model_name} failed: {e}. Trying next.")

        return fallback

    # ----------------------------
    # SAFE PARSER (HARDENED)
    # ----------------------------
    def _safe_parse(self, text: str):
        cleaned = self._clean_output(text)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            json_text = self._extract_json_object(cleaned)
            if json_text:
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    pass

            return {
                "final_intent": "unknown",
                "reasoning": cleaned,
                "best_agent": "unknown",
                "confidence": 0.0,
                "parse_status": "failed"
            }

    def _clean_output(self, text: str):
        ansi_escape = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
        return ansi_escape.sub("", text).strip()

    def _extract_json_object(self, text: str):
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            return fenced.group(1)

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        return text[start:end + 1]
