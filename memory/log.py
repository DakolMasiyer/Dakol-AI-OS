import json
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "memory", "logs.json")


# ----------------------------
# LOAD MEMORY
# ----------------------------
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


# ----------------------------
# SAVE MEMORY
# ----------------------------
def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ----------------------------
# LOG EVENT (LEARNING-READY VERSION)
# ----------------------------
def log_event(task, model, output, agent_result=None):
    memory = load_memory()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "model_used": model,
        "output": output[:800],
        "agent_result": agent_result  # 🔥 IMPORTANT FOR STEP 8
    }

    memory.append(entry)
    save_memory(memory)

    # DEBUG LAYER
    print("\n[MEMORY LOGGED]")
    print("Task:", task)
    print("Model:", model)
    print("Saved at:", entry["timestamp"])

    if agent_result:
        print("\n[AGENT LEARNING DATA STORED]")
        print("Intent:", agent_result.get("final_intent", "unknown"))
        print("Best Agent:", agent_result.get("best_agent", "unknown"))
        print("Confidence:", agent_result.get("confidence", "unknown"))

    return entry