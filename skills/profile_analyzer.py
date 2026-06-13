"""
Brand-voice inference from a public social profile.

Best-effort: fetches a profile URL and extracts visible meta signals (og:title,
og:description, meta description, <title>), then asks the model router to infer
a tone, style notes, and suggested hashtags. Many platforms (Instagram, X) render
profiles via JS and/or gate them behind auth, so when a fetch yields nothing we
fall back to inferring conservatively from the handle alone. Always returns a
usable result — onboarding must never hard-fail on this.
"""

import json
import re
from typing import Optional

from app.core.logging import get_logger
from skills.model_router import generate_with_fallback

logger = get_logger(__name__)

VALID_TONES = {"hype", "professional", "casual", "analytical"}
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

_META_PATTERNS = (
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
    r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
    r'<title[^>]*>([^<]+)</title>',
)


def _normalize_tag(raw) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "", str(raw).lstrip("#"))
    return f"#{cleaned}" if cleaned else ""


def _extract_meta(html: str) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for pattern in _META_PATTERNS:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            if text and text not in seen:
                seen.add(text)
                parts.append(text)
    return " | ".join(parts)[:1000]


def _fetch_profile_text(url: str) -> str:
    try:
        import httpx

        with httpx.Client(follow_redirects=True, timeout=6.0, headers={"User-Agent": _UA}) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                return ""
            return _extract_meta(resp.text)
    except Exception:
        logger.warning("profile fetch failed", extra={"url": url}, exc_info=True)
        return ""


def analyze_profile(
    url: Optional[str] = None,
    handle: Optional[str] = None,
    platform: Optional[str] = None,
) -> dict:
    profile_text = _fetch_profile_text(url) if url else ""
    coverage = "fetched" if profile_text else "inferred"

    prompt = (
        "You are a brand-voice analyst for a football content tool. "
        "Infer the brand's voice from the social profile signals below.\n"
        f"Handle: {handle or 'unknown'}\n"
        f"Platform: {platform or 'unknown'}\n"
        f"Profile signals: {profile_text or '(none available — infer conservatively from the handle)'}\n\n"
        "Respond with ONLY a JSON object (no prose, no markdown) of the form:\n"
        '{"tone_key": one of ["hype","professional","casual","analytical"], '
        '"style_notes": "a concise <=200 character description of their voice", '
        '"suggested_hashtags": ["#Tag", ... up to 5 relevant football hashtags]}'
    )

    tone_key = "analytical"
    style_notes = ""
    hashtags: list[str] = []

    try:
        routed = generate_with_fallback(prompt, 400)
        match = re.search(r"\{.*\}", routed["content"], re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            candidate = str(data.get("tone_key", "")).lower()
            if candidate in VALID_TONES:
                tone_key = candidate
            style_notes = str(data.get("style_notes", "") or "")[:200]
            raw_tags = data.get("suggested_hashtags", [])
            if isinstance(raw_tags, list):
                seen: set[str] = set()
                for tag in raw_tags:
                    norm = _normalize_tag(tag)
                    if norm and norm not in seen:
                        seen.add(norm)
                        hashtags.append(norm)
                hashtags = hashtags[:5]
    except Exception:
        logger.warning("profile inference failed", exc_info=True)

    return {
        "tone_key": tone_key,
        "style_notes": style_notes,
        "suggested_hashtags": hashtags,
        "coverage": coverage,
        "status": "ok",
    }
