import os
import re
import subprocess

from agents.orchestrator import Orchestrator
from memory.learning import update_learning_state
from memory.log import log_event
from scripts.semantic_router import route_task_semantically


try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(override=True)


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
        print("[ROUTER] Warning: ANTHROPIC_API_KEY not found in environment.")
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
        print(f"[ROUTER] Claude API failed: {exc}")
        return f"Error executing Claude: {exc}"


def run_codex(task: str) -> str:
    """Execute the task through OpenAI for code-oriented work."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ROUTER] Warning: OPENAI_API_KEY not found in environment.")
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
        print(f"[ROUTER] Codex/OpenAI API failed: {exc}")
        return f"Error executing Codex: {exc}"


def run_local(task: str) -> str:
    """Execute the task through the local Ollama model."""
    model = os.getenv("OLLAMA_MODEL", "coder-pro:latest")

    try:
        result = subprocess.run(
            ["ollama", "run", model, task],
            capture_output=True,
            text=True,
            check=True,
        )
        return clean_model_output(result.stdout)
    except FileNotFoundError:
        print("[ROUTER] Local Ollama executable not found.")
        return "Error executing local model: Ollama executable not found."
    except subprocess.CalledProcessError as exc:
        print(f"[ROUTER] Local Ollama execution failed: {exc}")
        return f"Error executing local model: {exc}"


def route_task(task: str):
    route_decision = route_task_semantically(task)
    model = route_decision.model

    print("\nSelected model:", model)
    print("Route intent:", route_decision.intent)
    print("Route confidence:", route_decision.confidence)
    print("Matched terms:", ", ".join(route_decision.matched_terms) or "none")

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

    print("\n--- AGENT FUSION OUTPUT ---")
    print("Final Intent:", fusion.get("final_intent"))
    print("Reasoning:", fusion.get("reasoning"))
    print("Best Agent:", fusion.get("best_agent"))
    print("Confidence:", fusion.get("confidence"))

    # ----------------------------
    # MEMORY LOGGING (SAFE + CONSISTENT)
    # ----------------------------
    entry = log_event(
        task,
        model,
        output,
        agent_result
    )

    print("\n--- MEMORY CONFIRMATION ---")
    print("Logged task:", entry["task"])
    print("Model used:", entry["model_used"])
    print("Saved at:", entry["timestamp"])

    learning_state = update_learning_state()
    print("\n--- LEARNING STATE ---")
    print("Events analyzed:", learning_state["event_count"])
    print("Known intents:", ", ".join(sorted(learning_state["intents"])) or "none")

    return output
