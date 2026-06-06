import os
import re

from agents.orchestrator import Orchestrator
from app.core.logging import get_logger
from memory.learning import update_learning_state
from memory.log import log_event
from scripts.semantic_router import route_task_semantically
from skills.model_router import AllModelsUnavailableError, generate_with_fallback


try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(override=True)

logger = get_logger(__name__)


def clean_model_output(text: str) -> str:
    ansi_escape = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", text).strip()


def analyze_task(task: str) -> str:
    """
    Route the task to the most suitable model family.

    - claude: architecture, pipelines, licensing, and synthesis work
    - codex: code generation, APIs, scripts, and implementation work
    - local: general explanations and quick analysis
    """
    return route_task_semantically(task).model


def run_claude(task: str) -> str:
    """Execute the task through Claude via the Anthropic SDK."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not found in environment")
        return "Error: Claude API key not configured."

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            max_tokens=1024,
            messages=[{"role": "user", "content": task}],
        )
        return clean_model_output(message.content[0].text)
    except Exception as exc:
        logger.error("Claude API failed", exc_info=True)
        return f"Error executing Claude: {exc}"


def run_codex(task: str) -> str:
    """Execute the task through OpenAI for code-oriented work."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not found in environment")
        return "Error: OpenAI API key not configured."

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": task}],
        )
        return clean_model_output(response.choices[0].message.content)
    except Exception as exc:
        logger.error("Codex/OpenAI API failed", exc_info=True)
        return f"Error executing Codex: {exc}"


def run_local(task: str) -> str:
    """Execute the task through the shared fallback router."""
    try:
        result = generate_with_fallback(task, max_tokens=1024)
        return clean_model_output(result["content"])
    except AllModelsUnavailableError as exc:
        logger.error("Fallback generation failed", exc_info=True)
        return f"Error executing fallback model: {exc}"


def route_task(task: str):
    route_decision = route_task_semantically(task)
    model = route_decision.model

    logger.info(
        "Task route selected",
        extra={
            "model": model,
            "intent": route_decision.intent,
            "confidence": route_decision.confidence,
            "matched_terms": route_decision.matched_terms,
        },
    )

    # ----------------------------
    # EXECUTE MODEL LAYER
    # ----------------------------
    if model == "claude":
        output = run_claude(task)

    elif model == "codex":
        output = run_codex(task)

    else:
        output = run_local(task)

    # ----------------------------
    # MULTI-AGENT FUSION LAYER
    # ----------------------------
    orchestrator = Orchestrator()
    agent_result = orchestrator.route(task)
    agent_result["route_decision"] = route_decision.to_dict()

    fusion = agent_result.get("fusion_output", {})

    logger.info(
        "Agent fusion completed",
        extra={
            "final_intent": fusion.get("final_intent"),
            "reasoning": fusion.get("reasoning"),
            "best_agent": fusion.get("best_agent"),
            "confidence": fusion.get("confidence"),
        },
    )

    # ----------------------------
    # MEMORY LOGGING (SAFE + CONSISTENT)
    # ----------------------------
    entry = log_event(
        task,
        model,
        output,
        agent_result
    )

    logger.info(
        "Task logged to memory",
        extra={
            "task": entry["task"],
            "model_used": entry["model_used"],
            "saved_at": entry["timestamp"],
        },
    )

    learning_state = update_learning_state()
    logger.info(
        "Learning state updated",
        extra={
            "event_count": learning_state["event_count"],
            "known_intents": sorted(learning_state["intents"]),
        },
    )

    return output
