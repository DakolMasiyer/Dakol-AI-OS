import json
import os
import re
from abc import ABC, abstractmethod

from planning.schema import Plan, PlanStep
from planning.validator import DEFAULT_ALLOWED_TOOLS, validate_plan


class PlanningProviderUnavailable(RuntimeError):
    pass


class PlanningProvider(ABC):
    name = "base"

    @abstractmethod
    def create_plan(self, task, max_steps=8, allowed_tools=None):
        raise NotImplementedError


class DeterministicPlanningProvider(PlanningProvider):
    name = "deterministic"

    def create_plan(self, task, max_steps=8, allowed_tools=None):
        allowed = set(allowed_tools or DEFAULT_ALLOWED_TOOLS)
        tool_name = _select_tool(task, allowed)
        slug = _slugify(task) or "task"

        steps = [
            PlanStep(
                id="step_1",
                description="Clarify the requested outcome and constraints.",
                tool_name="local_model" if "local_model" in allowed else tool_name,
                inputs={"task": task},
            ),
            PlanStep(
                id="step_2",
                description="Execute the primary work for the task.",
                tool_name=tool_name,
                dependencies=["step_1"],
                inputs=_inputs_for_tool(tool_name, task),
            ),
        ]

        if max_steps >= 3:
            review_tool = "memory" if "memory" in allowed else tool_name
            steps.append(
                PlanStep(
                    id="step_3",
                    description="Review the result and prepare a concise handoff.",
                    tool_name=review_tool,
                    dependencies=["step_2"],
                    inputs={"task": task},
                )
            )

        plan = Plan(
            id=f"plan_{slug}",
            objective=str(task).strip(),
            provider=self.name,
            steps=steps[:max_steps],
        )
        return validate_plan(plan, max_steps=max_steps, allowed_tools=allowed)


class ClaudePlanningProvider(PlanningProvider):
    name = "claude"

    def __init__(self, client=None, api_key=None, model=None):
        self.client = client
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    def is_available(self):
        return self.client is not None or bool(self.api_key)

    def create_plan(self, task, max_steps=8, allowed_tools=None):
        if self.client is None:
            if not self.api_key:
                raise PlanningProviderUnavailable("Claude planning requires ANTHROPIC_API_KEY")
            try:
                from anthropic import Anthropic
            except ImportError as exc:
                raise PlanningProviderUnavailable("anthropic package is not installed") from exc
            self.client = Anthropic(api_key=self.api_key)

        allowed = sorted(set(allowed_tools or DEFAULT_ALLOWED_TOOLS))
        prompt = _build_claude_prompt(task, max_steps, allowed)
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text
        plan = Plan.from_dict(json.loads(_extract_json_object(text)))
        return validate_plan(plan, max_steps=max_steps, allowed_tools=allowed)


def select_planning_provider(preferred=None):
    selected = (preferred or os.getenv("PLANNING_PROVIDER", "auto")).lower()

    if selected == "deterministic":
        return DeterministicPlanningProvider()
    if selected == "claude":
        provider = ClaudePlanningProvider()
        if provider.is_available():
            return provider
        return DeterministicPlanningProvider()
    if selected == "auto":
        provider = ClaudePlanningProvider()
        if provider.is_available():
            return provider
        return DeterministicPlanningProvider()

    raise ValueError(f"unknown planning provider: {selected}")


def create_plan(task, provider=None, max_steps=8, allowed_tools=None):
    planner = provider or select_planning_provider()
    return planner.create_plan(task, max_steps=max_steps, allowed_tools=allowed_tools)


def _select_tool(task, allowed):
    lowered = str(task).lower()
    candidates = [
        (
            ("composer", "brief match", "match composer", "match track", "catalog match"),
            "syncmaster_match_brief",
        ),
        (
            ("license", "licensing", "sync fit", "placement", "cue", "brief"),
            "syncmaster_recommend_sync_fit",
        ),
        (
            ("metadata", "bpm", "key", "genre", "mood", "tag", "track analysis"),
            "syncmaster_analyze_metadata",
        ),
        (("code", "test", "python", "api", "debug", "script"), "code_agent"),
        (("audio", "bpm", "key", "genre", "metadata", "song"), "audio_agent"),
        (("sync", "license", "cue", "placement"), "sync_agent"),
    ]

    for terms, tool_name in candidates:
        if tool_name in allowed and any(term in lowered for term in terms):
            return tool_name

    return "local_model" if "local_model" in allowed else sorted(allowed)[0]


def _inputs_for_tool(tool_name, task):
    if tool_name == "syncmaster_analyze_metadata":
        return {"payload": {"description": task, "tags": [task]}}
    if tool_name == "syncmaster_recommend_sync_fit":
        return {
            "track_metadata": {"description": task, "tags": [task]},
            "brief": {"description": task, "keywords": [task]},
        }
    if tool_name == "syncmaster_match_brief":
        return {"brief": {"description": task, "keywords": [task]}, "candidates": []}
    return {"task": task}


def _slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return slug[:48].strip("_")


def _build_claude_prompt(task, max_steps, allowed_tools):
    return f"""
Create a JSON plan for this task.

Task: {task}
Maximum steps: {max_steps}
Allowed tool names: {", ".join(allowed_tools)}

Return only JSON with this shape:
{{
  "id": "plan_short_slug",
  "objective": "original objective",
  "provider": "claude",
  "steps": [
    {{
      "id": "step_1",
      "description": "actionable step",
      "tool_name": "one allowed tool name",
      "dependencies": [],
      "inputs": {{}}
    }}
  ]
}}
""".strip()


def _extract_json_object(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Claude response did not contain a JSON object")
    return text[start:end + 1]
