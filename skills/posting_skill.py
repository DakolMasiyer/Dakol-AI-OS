"""
Posting helpers for World Cup AI.

Twitter posting uses Composio connected accounts and posts each parsed tweet as
a reply to the previous tweet. Instagram and LinkedIn use Ayrshare's single
post endpoint.
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


def _get_connection(user_id: str, platform: str) -> dict[str, Any]:
    supabase = _supabase_client()
    result = (
        supabase.table("social_connections")
        .select("access_token, platform_username, platform_user_id")
        .eq("user_id", user_id)
        .eq("platform", platform)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise RuntimeError(f"{platform} is not connected")
    return result.data


def post_twitter_thread(user_id: str, tweets: list[str]) -> dict[str, Any]:
    api_key = os.environ.get("COMPOSIO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing COMPOSIO_API_KEY")
    if not tweets:
        raise RuntimeError("No tweets to post")

    connection = _get_connection(user_id, "twitter")
    connected_account_id = connection["access_token"]

    posted: list[dict[str, Any]] = []
    reply_to_id: str | None = None

    with httpx.Client(timeout=30) as client:
        for tweet in tweets:
            payload: dict[str, Any] = {"text": tweet}
            if reply_to_id:
                payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

            response = client.post(
                COMPOSIO_ACTION_URL.format(action=TWITTER_POST_ACTION),
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "connected_account_id": connected_account_id,
                    "arguments": payload,
                },
            )
            response.raise_for_status()
            data = response.json()
            tweet_id = (
                data.get("data", {}).get("id")
                or data.get("data", {}).get("tweet_id")
                or data.get("id")
                or data.get("tweet_id")
            )
            if not tweet_id:
                raise RuntimeError("Composio did not return a tweet id")
            reply_to_id = str(tweet_id)
            posted.append({"id": reply_to_id, "text": tweet})

    return {"platform": "twitter", "tweets": posted, "status": "ok"}


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
    return {"platform": platform, "result": data, "status": "ok"}


def post_generated_content(user_id: str, platform: str, content: str) -> dict[str, Any]:
    if platform == "twitter":
        return post_twitter_thread(user_id, parse_thread(content))
    return post_to_platform(platform, content)
