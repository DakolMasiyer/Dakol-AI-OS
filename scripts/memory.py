import json
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "memory", "logs.json")


def load_memory():
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def log_event(task, model, output):
    memory = load_memory()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "model_used": model,
        "output": output[:800]
    }

    memory.append(entry)
    save_memory(memory)

    return entry
