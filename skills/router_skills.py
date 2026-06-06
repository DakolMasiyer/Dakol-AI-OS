import os
from dotenv import load_dotenv
from app.core.logging import get_logger
from skills.model_router import AllModelsUnavailableError, generate_with_fallback

# Load API credentials from .env
load_dotenv()
logger = get_logger(__name__)

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
        logger.warning("ANTHROPIC_API_KEY not found in environment; falling back")
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
        logger.error("Claude API failed", exc_info=True)
        return f"Error executing Claude: {e}"


def run_codex(task: str) -> str:
    """
    Sends the task to the OpenAI Codex (GPT-4o/GPT-3.5-Turbo) API.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not found in environment; falling back")
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
        logger.error("Codex/OpenAI API failed", exc_info=True)
        return f"Error executing Codex: {e}"


def run_local(task: str) -> str:
    """Execute the task through the shared fallback router."""
    try:
        result = generate_with_fallback(task, max_tokens=1024)
        return result["content"].strip()
    except AllModelsUnavailableError as exc:
        logger.error("Fallback generation failed", exc_info=True)
        return f"Error executing fallback model: {exc}"
