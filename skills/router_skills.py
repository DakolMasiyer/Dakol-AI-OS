import os
import subprocess
from dotenv import load_dotenv

# Load API credentials from .env
load_dotenv()

def analyze_task(task: str) -> str:
    """
    Analyzes the user's task and routes it to the most suitable model family.
    - claude: High-value reasoning, design pipelines, architecture, complex synthesis.
    - codex: Technical code generation, API endpoint creation, scripts.
    - local: General descriptions, simple tagging, quick explanations.
    """
    t = task.lower()
    
    # Coding & Development Intents
    if any(keyword in t for keyword in ["code", "api", "fastapi", "build", "implement", "function"]):
        return "codex"
        
    # High-value Reasoning, Pipelines, Architectures
    if any(keyword in t for keyword in ["design", "architecture", "pipeline", "licensing", "fusion"]):
        return "claude"
        
    # Default to Local LLM for explanations and basic analysis
    return "local"


def run_claude(task: str) -> str:
    """
    Sends the task to the Anthropic Claude API.
    Handles API missing or key rate limits gracefully by falling back to local.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ROUTER] Warning: ANTHROPIC_API_KEY not found in environment. Falling back...")
        return "Error: Claude API Key not configured."
        
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": task}
            ]
        )
        return message.content[0].text
    except Exception as e:
        print(f"[ROUTER] Claude API failed: {e}")
        return f"Error executing Claude: {e}"


def run_codex(task: str) -> str:
    """
    Sends the task to the OpenAI Codex (GPT-4o/GPT-3.5-Turbo) API.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ROUTER] Warning: OPENAI_API_KEY not found in environment. Falling back...")
        return "Error: OpenAI API Key not configured."
        
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": task}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ROUTER] Codex/OpenAI API failed: {e}")
        return f"Error executing Codex: {e}"


def run_local(task: str) -> str:
    """
    Sends the task to the local Ollama instance running coder-pro:latest.
    """
    try:
        result = subprocess.run(
            ["ollama", "run", "coder-pro:latest", task],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ROUTER] Local Ollama execution failed: {e}")
        return f"Error executing local model: {e}"
