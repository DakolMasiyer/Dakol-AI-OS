import json
from datetime import datetime
import os
from uuid import uuid4

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "memory", "logs.json")
VALID_FEEDBACK = {"good", "bad", "wrong_model", "retry_needed"}


# ----------------------------
# LOAD MEMORY
# ----------------------------
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# ----------------------------
# SAVE MEMORY
# ----------------------------
def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record_feedback(event_id, feedback, note=None):
    if feedback not in VALID_FEEDBACK:
        valid = ", ".join(sorted(VALID_FEEDBACK))
        raise ValueError(f"feedback must be one of: {valid}")

    memory = load_memory()
    for entry in memory:
        if entry.get("event_id") == event_id:
            entry["feedback"] = {
                "label": feedback,
                "value": feedback,
                "timestamp": datetime.now().isoformat(),
            }
            if note:
                entry["feedback"]["note"] = str(note)[:500]

            save_memory(memory)
            return entry

    raise ValueError(f"No memory event found for event_id: {event_id}")


# ----------------------------
# LOG EVENT (LEARNING-READY VERSION)
# ----------------------------
def log_event(task, model, output, agent_result=None):
    memory = load_memory()

    entry = {
        "event_id": str(uuid4()),
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "model_used": model,
        "output": str(output or "")[:800],
        "agent_result": agent_result  # 🔥 IMPORTANT FOR STEP 8
    }

    try:
        from app.core.tracing import get_request_id, get_workflow_id
        req_id = get_request_id()
        if req_id:
            entry["request_id"] = req_id
        work_id = get_workflow_id()
        if work_id:
            entry["workflow_id"] = work_id
    except ImportError:
        pass

    memory.append(entry)

    save_memory(memory)

    # DEBUG LAYER
    print("\n[MEMORY LOGGED]")
    print("Task:", task)
    print("Model:", model)
    print("Saved at:", entry["timestamp"])

    if agent_result:
        fusion = agent_result.get("fusion_output", agent_result)

        print("\n[AGENT LEARNING DATA STORED]")
        print("Intent:", fusion.get("final_intent", "unknown"))
        print("Best Agent:", fusion.get("best_agent", "unknown"))
        print("Confidence:", fusion.get("confidence", "unknown"))

    return entry
