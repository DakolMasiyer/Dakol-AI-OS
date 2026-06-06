"""
Posting helpers for World Cup AI.

Twitter posting uses Composio connected accounts and posts each parsed tweet as
a reply to the previous tweet. Instagram and LinkedIn try Composio first and
fall back to Ayrshare if the user's Composio connection is unavailable or the
Composio call fails.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

COMPOSIO_ACTION_URL = "https://backend.composio.dev/api/v3/actions/{action}/execute"
AYRSHARE_POST_URL = "https://api.ayrshare.com/api/post"
TWITTER_POST_ACTION = os.environ.get("COMPOSIO_TWITTER_POST_ACTION", "TWITTER_CREATION_OF_A_POST")
INSTAGRAM_POST_ACTION = os.environ.get("COMPOSIO_INSTAGRAM_POST_ACTION", "INSTAGRAM_CREATE_POST")
LINKEDIN_POST_ACTION = os.environ.get("COMPOSIO_LINKEDIN_POST_ACTION", "LINKEDIN_CREATE_LINKED_IN_POST")
LINKEDIN_ME_ACTION = os.environ.get("COMPOSIO_LINKEDIN_ME_ACTION", "LINKEDIN_GET_MY_INFO")


def parse_thread(content: str) -> list[str]:
    """
    Split generated thread content into tweets.
    Handles numbered tweets like "1/ ...", "1. ...", or "Tweet 1: ..."
    and falls back to paragraph chunks. Tweets are capped to Twitter's
    280-character limit.
    """
    cleaned = content.strip()
    if not cleaned:
        return []

    numbered_marker = r"(?:\d+\s*[/.]\s+|tweet\s+\d+\s*:\s*)"
    parts = re.split(rf"\n\s*(?={numbered_marker})", cleaned, flags=re.IGNORECASE)
    if len(parts) == 1:
        parts = [part for part in re.split(r"\n{2,}", cleaned) if part.strip()]

    tweets: list[str] = []
    for part in parts:
        text = re.sub(rf"^\s*{numbered_marker}", "", part.strip(), flags=re.IGNORECASE)
        if not text:
            continue
        while len(text) > 280:
            cut = text.rfind(" ", 0, 277)
            if cut < 120:
                cut = 277
            tweets.append(text[:cut].strip())
            text = text[cut:].strip()
        tweets.append(text)

    return tweets


def _supabase_client():
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
    )
    if not url or not key:
        raise RuntimeError("Missing Supabase credentials for posting skill")

    from supabase import create_client

    return create_client(url, key)


def _get_connection(user_id: str, platform: str) -> dict[str, Any] | None:
    supabase = _supabase_client()
    result = (
        supabase.table("social_connections")
        .select("access_token, platform_username, platform_user_id")
        .eq("user_id", user_id)
        .eq("platform", platform)
        .maybe_single()
        .execute()
    )
    return result.data or None


def _composio_api_key() -> str:
    api_key = os.environ.get("COMPOSIO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing COMPOSIO_API_KEY")
    return api_key


def _execute_composio_action(action: str, api_key: str, connected_account_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=30) as client:
        response = client.post(
            COMPOSIO_ACTION_URL.format(action=action),
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json={
                "connectedAccountId": connected_account_id,
                "connected_account_id": connected_account_id,
                "arguments": arguments,
                "input": arguments,
            },
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            raise RuntimeError("Composio returned an empty response")
        return data


def _extract_composio_id(data: dict[str, Any]) -> str | None:
    candidates = (
        data.get("data", {}).get("id"),
        data.get("data", {}).get("tweet_id"),
        data.get("data", {}).get("share_id"),
        data.get("data", {}).get("author"),
        data.get("data", {}).get("author_id"),
        data.get("data", {}).get("authorId"),
        data.get("id"),
        data.get("tweet_id"),
        data.get("share_id"),
        data.get("author"),
        data.get("author_id"),
        data.get("authorId"),
    )
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return None


def _post_twitter_thread_with_composio(user_id: str, tweets: list[str]) -> dict[str, Any]:
    api_key = _composio_api_key()
    if not tweets:
        raise RuntimeError("No tweets to post")

    connection = _get_connection(user_id, "twitter")
    if not connection:
        raise RuntimeError("twitter is not connected")
    connected_account_id = connection["access_token"]

    posted: list[dict[str, Any]] = []
    reply_to_id: str | None = None

    for tweet in tweets:
        payload: dict[str, Any] = {"text": tweet}
        if reply_to_id:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

        data = _execute_composio_action(TWITTER_POST_ACTION, api_key, connected_account_id, payload)
        tweet_id = _extract_composio_id(data)
        if not tweet_id:
            raise RuntimeError("Composio did not return a tweet id")
        reply_to_id = tweet_id
        posted.append({"id": reply_to_id, "text": tweet})

    return {"platform": "twitter", "tweets": posted, "status": "ok"}


def _resolve_linkedin_author(api_key: str, connected_account_id: str, fallback_author: str | None) -> str:
    try:
        data = _execute_composio_action(LINKEDIN_ME_ACTION, api_key, connected_account_id, {})
        author = _extract_composio_id(data)
        if author:
            return author
    except Exception:
        pass

    if fallback_author:
        return fallback_author
    raise RuntimeError("Unable to resolve LinkedIn author id")


def _post_with_composio(user_id: str, platform: str, content: str) -> dict[str, Any]:
    api_key = _composio_api_key()
    connection = _get_connection(user_id, platform)
    if not connection:
        raise RuntimeError(f"{platform} is not connected")

    connected_account_id = connection["access_token"]
    if platform == "instagram":
        data = _execute_composio_action(
            INSTAGRAM_POST_ACTION,
            api_key,
            connected_account_id,
            {"text": content, "caption": content},
        )
        post_id = _extract_composio_id(data)
        return {
            "platform": platform,
            "result": data,
            "post_id": post_id,
            "status": "ok",
            "provider": "composio",
        }

    if platform == "linkedin":
        author = _resolve_linkedin_author(
            api_key,
            connected_account_id,
            connection.get("platform_user_id") or connection.get("platform_username"),
        )
        data = _execute_composio_action(
            LINKEDIN_POST_ACTION,
            api_key,
            connected_account_id,
            {"author": author, "commentary": content},
        )
        post_id = _extract_composio_id(data)
        return {
            "platform": platform,
            "result": data,
            "post_id": post_id,
            "status": "ok",
            "provider": "composio",
        }

    raise RuntimeError(f"Unsupported Composio platform: {platform}")


def post_twitter_thread(user_id: str, tweets: list[str]) -> dict[str, Any]:
    return _post_twitter_thread_with_composio(user_id, tweets)


def post_to_platform(platform: str, content: str) -> dict[str, Any]:
    api_key = os.environ.get("AYRSHARE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing AYRSHARE_API_KEY")
    if platform not in {"instagram", "linkedin"}:
        raise RuntimeError(f"Unsupported Ayrshare platform: {platform}")

    response = httpx.post(
        AYRSHARE_POST_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"post": content, "platforms": [platform]},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return {"platform": platform, "result": data, "status": "ok", "provider": "ayrshare"}


def post_generated_content(user_id: str, platform: str, content: str) -> dict[str, Any]:
    if platform == "twitter":
        return post_twitter_thread(user_id, parse_thread(content))

    composio_error: Exception | None = None
    try:
        return _post_with_composio(user_id, platform, content)
    except Exception as exc:
        composio_error = exc

    try:
        fallback = post_to_platform(platform, content)
        fallback["fallback_from"] = "composio"
        return fallback
    except Exception as fallback_error:
        if composio_error:
            raise RuntimeError(
                f"Composio posting failed for {platform}: {composio_error}; "
                f"Ayrshare fallback failed: {fallback_error}"
            ) from fallback_error
        raise
