from concurrent.futures import ThreadPoolExecutor, TimeoutError
import re
from typing import Any, Optional

from app.core.logging import get_logger


logger = get_logger(__name__)

SEARCH_TIMEOUT_SECONDS = 5
_URL_PATTERN = re.compile(r"https?://[^\s)\]]+")
_SCORELINE_PATTERNS = [
    re.compile(r"\b([A-Z][A-Za-z .'-]+)\s+(\d{1,2})[-–]\s*(\d{1,2})\s+([A-Z][A-Za-z .'-]+)\b"),
    re.compile(r"\b([A-Z][A-Za-z .'-]+)\s+beat\s+([A-Z][A-Za-z .'-]+)\s+(\d{1,2})[-–]\s*(\d{1,2})\b", re.IGNORECASE),
    re.compile(r"\b([A-Z][A-Za-z .'-]+)\s+defeated\s+([A-Z][A-Za-z .'-]+)\s+(\d{1,2})[-–]\s*(\d{1,2})\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,2})[-–]\s*(\d{1,2})\b"),
]
_EVENT_KEYWORDS = (
    "goal",
    "scored",
    "equaliser",
    "equalizer",
    "penalty",
    "red card",
    "yellow card",
    "sent off",
    "substitution",
    "injury",
    "var",
    "own goal",
    "assist",
    "winner",
)


def _empty_result() -> dict[str, Any]:
    return {
        "scoreline": None,
        "key_events": [],
        "source_urls": [],
        "enriched": False,
    }


def _search(query: str) -> str:
    try:
        from smolagents import WebSearchTool
    except ImportError:
        logger.warning("smolagents is not installed; skipping match context enrichment")
        return ""

    tool = WebSearchTool(max_results=5)
    result = tool(query)
    return str(result or "")


def _extract_scoreline(search_text: str) -> Optional[str]:
    for pattern in _SCORELINE_PATTERNS:
        match = pattern.search(search_text)
        if match:
            return match.group(0).strip()
    return None


def _extract_key_events(search_text: str) -> list[str]:
    candidates = re.split(r"[\n.!?]+", search_text)
    events: list[str] = []

    for candidate in candidates:
        event = " ".join(candidate.strip().split())
        if not event or len(event) < 20:
            continue
        if any(keyword in event.lower() for keyword in _EVENT_KEYWORDS):
            events.append(event[:220])
        if len(events) == 5:
            break

    return events


def _extract_source_urls(search_text: str) -> list[str]:
    urls: list[str] = []
    for url in _URL_PATTERN.findall(search_text):
        normalized = url.rstrip(".,")
        if normalized not in urls:
            urls.append(normalized)
        if len(urls) == 5:
            break
    return urls


def enrich_match_context(home_team: str, away_team: str, date: str) -> dict[str, Any]:
    query = f"{home_team} vs {away_team} {date} match report".strip()
    logger.debug("Searching live match context", extra={"query": query})

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_search, query)

    try:
        search_text = future.result(timeout=SEARCH_TIMEOUT_SECONDS)
    except TimeoutError:
        future.cancel()
        logger.warning(
            "Live match context search timed out",
            extra={"query": query, "timeout_seconds": SEARCH_TIMEOUT_SECONDS},
        )
        return _empty_result()
    except Exception:
        logger.warning("Live match context search failed", extra={"query": query}, exc_info=True)
        return _empty_result()
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    if not search_text:
        logger.info("Live match context enrichment skipped", extra={"query": query, "enriched": False})
        return _empty_result()

    scoreline = _extract_scoreline(search_text)
    key_events = _extract_key_events(search_text)
    source_urls = _extract_source_urls(search_text)
    enriched = bool(scoreline or key_events)

    logger.info(
        "Live match context enrichment completed",
        extra={
            "query": query,
            "enriched": enriched,
            "source_count": len(source_urls),
            "event_count": len(key_events),
        },
    )

    if not enriched:
        return _empty_result()

    return {
        "scoreline": scoreline,
        "key_events": key_events,
        "source_urls": source_urls,
        "enriched": True,
    }
