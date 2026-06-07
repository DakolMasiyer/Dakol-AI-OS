import os
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

from agents.orchestrator import Orchestrator
from app.core.logging import get_logger
from app.core.tracing import get_request_id, get_workflow_id
from core.execution_audit import (
    append_audit_ledger,
    classify_certification,
    create_execution_snapshot,
    write_execution_trace,
)
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
    result = execute_task(task, record_memory=True, record_trace=True, capture_metadata=False)
    return result


from typing import Optional

def execute_task(
    task: str,
    *,
    record_memory: bool = True,
    record_trace: bool = True,
    capture_metadata: bool = False,
    app_id: Optional[str] = None,
):
    from core.invariants import ExecutionPathContext, assert_routing_determinism

    execution_id = f"{app_id}-{uuid4()}" if app_id else str(uuid4())
    started_at = datetime.now(timezone.utc)
    started_perf = time.perf_counter()
    route_decision = None
    route_decision_check = None
    agent_result = None
    output = None
    model = ""
    failure_reason = None
    status = "completed"
    best_agent = None
    invariant_checks = {
        "routing_determinism": False,
        "agent_immutability": False,
        "learning_is_advisory_only": False,
    }

    try:
        with ExecutionPathContext():
            route_decision = route_task_semantically(task)
            route_decision_check = route_task_semantically(task)
            assert_routing_determinism(task, route_decision, route_decision_check)
            invariant_checks["routing_determinism"] = True
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
            invariant_checks["agent_immutability"] = True
            invariant_checks["learning_is_advisory_only"] = True

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

        if record_memory:
            entry = log_event(
                task,
                model,
                output,
                agent_result,
            )

            logger.info(
                "Task logged to memory",
                extra={
                    "task": entry["task"],
                    "model_used": entry["model_used"],
                    "saved_at": entry["timestamp"],
                },
            )
    except Exception as exc:
        status = "failed"
        failure_reason = f"{exc.__class__.__name__}: {exc}"
        output = f"Error executing task: {failure_reason}"
    finally:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started_perf) * 1000)
        if record_trace:
            selected_agent = ""
            if isinstance(agent_result, dict):
                fusion_output = agent_result.get("fusion_output") or {}
                best_agent = fusion_output.get("best_agent")
                selected_agent = best_agent or (route_decision.execution_target if route_decision else "")

            snapshot = create_execution_snapshot(
                execution_id=execution_id,
                task=task,
                input_payload={"task": task},
                route_decision=route_decision.to_dict() if route_decision else {},
                selected_model=model,
                selected_agent=selected_agent or model,
                execution_timestamps={
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "duration_ms": duration_ms,
                },
                invariant_checks=invariant_checks,
                output=output,
                agent_result=agent_result,
                status=status,
                failure_reason=failure_reason,
                request_id=get_request_id(),
                workflow_id=get_workflow_id(),
                best_agent=best_agent,
            )
            from pathlib import Path

            trace_dir = None
            if app_id:
                base_dir = Path(__file__).resolve().parents[1]
                trace_dir = base_dir / "logs" / "execution" / app_id

            write_execution_trace(snapshot, trace_dir=trace_dir)
            certification_status = classify_certification(snapshot)
            append_audit_ledger(snapshot, certification_status, trace_dir=trace_dir)

    if capture_metadata:
        selected_agent = ""
        if isinstance(agent_result, dict):
            selected_agent = (agent_result.get("fusion_output") or {}).get("best_agent", "") or (
                route_decision.execution_target if route_decision else ""
            )
        return {
            "output": output,
            "route_decision": route_decision.to_dict() if route_decision else {},
            "agent_result": agent_result or {},
            "invariant_checks": invariant_checks,
            "selected_model": model,
            "selected_agent": selected_agent or model,
            "status": status,
            "failure_reason": failure_reason,
        }

    return output
