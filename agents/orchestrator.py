from agents.sync_agent import SyncAgent
from agents.audio_agent import AudioAgent
from agents.code_agent import CodeAgent
from agents.listener_agent import ListenerAgent
from agents.worldcup_content_agent import WorldCupContentAgent
from agents.football_data_agent import FootballDataAgent
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

        from core.invariants import is_in_execution_path
        if is_in_execution_path():
            self.learning_state = {}
        else:
            if learning_state is not None:
                self.learning_state = learning_state.get("recommendations", learning_state)
            else:
                from memory.learning import get_learning_recommendations
                try:
                    self.learning_state = get_learning_recommendations()
                except RuntimeError:
                    self.learning_state = {}

        self._apply_agent_learning()

        self.memory = []
        self.model_learning = {}

    def _apply_agent_learning(self):
        self.learning_signals = []
        from core.invariants import is_in_execution_path
        if is_in_execution_path():
            # In execution path, accessing the learning state multipliers is strictly forbidden.
            return

        # self.learning_state represents recommendations dictionary
        agent_recs = self.learning_state.get("agent", {}) if isinstance(self.learning_state, dict) else {}
        if not agent_recs and isinstance(self.learning_state, dict) and "agent_bias" in self.learning_state:
            agent_recs = self.learning_state.get("agent_bias", {})

        for agent in self.agents:
            rec = agent_recs.get(agent.name, {})
            # Fallback for old/new schema values
            raw_multiplier = float(rec.get("recommended_multiplier", rec.get("weight_multiplier", 1.0)) or 1.0)
            multiplier = round(max(0.75, min(raw_multiplier, 1.35)), 3)
            
            # Retrieve recommendation reason if it exists in recommendations schema
            reason = rec.get("reason", f"Recommended multiplier {multiplier} based on average score.")
            
            learning_signal = {
                "agent": agent.name,
                "multiplier": multiplier,
                "reason": reason
            }
            self.learning_signals.append(learning_signal)

    # ----------------------------
    # MAIN ROUTE
    # ----------------------------
    def route(self, task: str):
        # Final System Guarantee check before execution starts
        from core.invariants import assert_agent_immutability, assert_learning_is_advisory_only
        assert_agent_immutability(self.agents)
        assert_learning_is_advisory_only()

        results = []

        # ----------------------------
        # COLLECT ALL AGENT OUTPUTS
        # ----------------------------
        for agent in self.agents:
            try:
                result = agent.run(task)
            except Exception as exc:
                result = {
                    "agent": agent.name,
                    "intent": "error",
                    "confidence": 0.0,
                    "input": task,
                    "status": "failed",
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    },
                }

            if "confidence" not in result:
                result["confidence"] = 0.5

            results.append(result)

        # Final System Guarantee check after execution ends
        assert_agent_immutability(self.agents)
        assert_learning_is_advisory_only()

        # ----------------------------
        # LLM FUSION BRAIN
        # ----------------------------
        prompt = self._build_fusion_prompt(task, results)
        fusion_output = self._run_llm(prompt)

        parsed = self._safe_parse(fusion_output)

        return {
            "fusion_output": parsed,
            "all_results": results,
            "learning_signals": self.learning_signals
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
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            try:
                api_key = get_available_key() or ""
            except Exception as exc:
                print(f"[orchestrator] quota manager unavailable: {exc}. Falling back to env key.")
                api_key = os.environ.get("GEMINI_API_KEY", "")
        client = genai.Client(api_key=api_key)
        fallback = '{"final_intent": "unknown", "reasoning": "all LLM backends failed", "best_agent": "unknown", "confidence": 0.0}'

        for model_name in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
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
