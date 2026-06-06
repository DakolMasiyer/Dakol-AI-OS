from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import os
import re
import threading
import time
from typing import Any, Optional

from app.core.logging import get_logger


logger = get_logger(__name__)

APIFY_ACTOR_ID = "viralanalyzer/twitter-scraper"
APIFY_MAX_TWEETS = 50
APIFY_TIMEOUT_SECONDS = 15
CACHE_TTL_SECONDS = 15 * 60

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()
_HASHTAG_PATTERN = re.compile(r"#\w+")


def _empty_result() -> dict[str, Any]:
    return {
        "hashtags": [],
        "angles": [],
        "injected": False,
    }


def _normalize_query(match_query: str) -> str:
    return " ".join((match_query or "").split()).lower()


def _get_cache(match_query: str) -> Optional[dict[str, Any]]:
    cache_key = _normalize_query(match_query)
    if not cache_key:
        return None

    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if not cached:
            return None

        expires_at, result = cached
        if expires_at <= now:
            _CACHE.pop(cache_key, None)
            return None

        logger.info("Trending angles cache hit", extra={"match_query": match_query})
        return result


def _set_cache(match_query: str, result: dict[str, Any]) -> None:
    cache_key = _normalize_query(match_query)
    if not cache_key:
        return

    with _CACHE_LOCK:
        _CACHE[cache_key] = (time.monotonic() + CACHE_TTL_SECONDS, result)


def _parse_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _extract_text(item: dict[str, Any]) -> str:
    for key in ("text", "tweet_text", "content", "full_text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_hashtags_from_value(value: Any) -> set[str]:
    hashtags: set[str] = set()

    if isinstance(value, str):
        for tag in _HASHTAG_PATTERN.findall(value):
            hashtags.add(f"#{tag.lstrip('#').lower()}")
        return hashtags

    if isinstance(value, (list, tuple, set)):
        for entry in value:
            if isinstance(entry, str) and entry.strip():
                normalized = entry.strip().lstrip("#").lower()
                if normalized:
                    hashtags.add(f"#{normalized}")
        return hashtags

    return hashtags


def _extract_hashtags(item: dict[str, Any]) -> set[str]:
    hashtags = set()
    hashtags.update(_extract_hashtags_from_value(item.get("hashtags")))
    hashtags.update(_extract_hashtags_from_value(_extract_text(item)))
    return hashtags


def _fetch_dataset_items(match_query: str) -> list[dict[str, Any]]:
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        logger.warning("APIFY_API_TOKEN is missing; skipping trending angles", extra={"match_query": match_query})
        return []

    try:
        from apify_client import ApifyClient
    except ImportError:
        logger.warning("apify-client is not installed; skipping trending angles", extra={"match_query": match_query})
        return []

    client = ApifyClient(token=token)
    run = client.actor(APIFY_ACTOR_ID).call(
        run_input={
            "searchQuery": f"{match_query} lang:en",
            "maxTweets": APIFY_MAX_TWEETS,
        }
    )

    if not run:
        return []

    dataset_id = None
    if isinstance(run, dict):
        dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
    else:
        dataset_id = getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None)

    if not dataset_id:
        return []

    dataset = client.dataset(dataset_id)
    items = dataset.list_items().items
    return [item for item in items if isinstance(item, dict)]


def _build_result(items: list[dict[str, Any]]) -> dict[str, Any]:
    hashtag_counts: Counter[str] = Counter()
    high_like_tweets: list[tuple[int, str]] = []

    for item in items:
        text = _extract_text(item)
        if not text:
            continue

        hashtag_counts.update(_extract_hashtags(item))

        likes = _parse_int(item.get("likes") or item.get("likeCount") or item.get("favoriteCount") or item.get("favouritesCount"))
        if likes > 100:
            high_like_tweets.append((likes, text))

    hashtags = [tag for tag, _ in hashtag_counts.most_common(3)]
    angles = []
    seen_texts: set[str] = set()

    for _, text in sorted(high_like_tweets, key=lambda pair: (-pair[0], pair[1])):
        if text in seen_texts:
            continue
        seen_texts.add(text)
        angles.append(text)
        if len(angles) == 3:
            break

    injected = bool(hashtags or angles)
    if not injected:
        return _empty_result()

    return {
        "hashtags": hashtags,
        "angles": angles,
        "injected": True,
    }


def get_trending_angles(match_query: str) -> dict[str, Any]:
    normalized_query = _normalize_query(match_query)
    if not normalized_query:
        return _empty_result()

    cached = _get_cache(match_query)
    if cached is not None:
        return cached

    logger.debug("Searching trending Twitter angles", extra={"match_query": match_query})

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_fetch_dataset_items, match_query)

    try:
        items = future.result(timeout=APIFY_TIMEOUT_SECONDS)
    except TimeoutError:
        future.cancel()
        logger.warning(
            "Trending Twitter search timed out",
            extra={"match_query": match_query, "timeout_seconds": APIFY_TIMEOUT_SECONDS},
        )
        result = _empty_result()
    except Exception:
        logger.warning("Trending Twitter search failed", extra={"match_query": match_query}, exc_info=True)
        result = _empty_result()
    else:
        if not items:
            logger.info("Trending Twitter search returned no tweets", extra={"match_query": match_query, "injected": False})
            result = _empty_result()
        else:
            result = _build_result(items)
            logger.info(
                "Trending angles fetched",
                extra={
                    "match_query": match_query,
                    "tweet_count": len(items),
                    "hashtag_count": len(result.get("hashtags", [])),
                    "angle_count": len(result.get("angles", [])),
                    "injected": result.get("injected", False),
                },
            )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    _set_cache(match_query, result)
    return result
