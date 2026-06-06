import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

import requests

from app.core.logging import get_logger

logger = get_logger(__name__)

MODEL_CHAIN = [
    "groq/llama3-70b-8192",
    "gemini/gemini-1.5-flash",
    "hf/mistralai/Mistral-7B-Instruct-v0.3",
]

_MODEL_TIMEOUT_SECONDS = 30
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_ALL_MODELS_UNAVAILABLE_MESSAGE = (
    "Generation temporarily unavailable. Please try again in a few minutes."
)


class AllModelsUnavailableError(RuntimeError):
    pass


def _run_with_timeout(fn: Callable[[], str]) -> str:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=_MODEL_TIMEOUT_SECONDS)
    finally:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)


def _extract_choice_text(response: Any) -> str:
    if isinstance(response, str):
        return response

    choices = getattr(response, "choices", None)
    if choices:
        choice = choices[0]
        message = getattr(choice, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                joined = "".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )
                if joined:
                    return joined

    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text

    return ""


def _run_groq(prompt: str, max_tokens: int) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY")

    def _call() -> str:
        response = requests.post(
            _GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.8,
            },
            timeout=_MODEL_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Groq returned {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        content = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not content.strip():
            raise RuntimeError("Groq returned empty content")
        return content

    return _run_with_timeout(_call)


def _run_gemini(prompt: str, max_tokens: int) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Gemini client is unavailable") from exc

    def _call() -> str:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        content = getattr(response, "text", "") or ""
        if not content.strip():
            raise RuntimeError("Gemini returned empty content")
        return content

    return _run_with_timeout(_call)


def _run_hf(prompt: str, max_tokens: int) -> str:
    token = os.getenv("HF_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing HF_API_TOKEN")

    try:
        from huggingface_hub import InferenceClient
    except ImportError as exc:
        raise RuntimeError("Hugging Face client is unavailable") from exc

    def _call() -> str:
        client = InferenceClient(api_key=token)
        response = client.chat_completion(
            model="mistralai/Mistral-7B-Instruct-v0.3",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        content = _extract_choice_text(response)
        if not content.strip():
            raise RuntimeError("Hugging Face returned empty content")
        return content

    return _run_with_timeout(_call)


def generate_with_fallback(prompt: str, max_tokens: int) -> dict[str, Any]:
    last_error: Optional[Exception] = None

    for index, model in enumerate(MODEL_CHAIN):
        provider, _ = model.split("/", 1)
        try:
            if provider == "groq":
                content = _run_groq(prompt, max_tokens)
            elif provider == "gemini":
                content = _run_gemini(prompt, max_tokens)
            elif provider == "hf":
                content = _run_hf(prompt, max_tokens)
            else:
                raise RuntimeError(f"Unsupported provider: {provider}")

            logger.info(
                "Model generation succeeded",
                extra={"model": model, "used_fallback": index > 0},
            )
            return {
                "content": content,
                "model": model,
                "used_fallback": index > 0,
            }
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Model generation failed, trying next model",
                extra={"model": model},
                exc_info=True,
            )

    raise AllModelsUnavailableError(_ALL_MODELS_UNAVAILABLE_MESSAGE) from last_error
