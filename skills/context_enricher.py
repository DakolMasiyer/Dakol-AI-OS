"""Live per-match fact enrichment — the PRIMARY source of in-match events
(goal scorers, cards) for WorldCup AI content generation.

football-data.org's Free plan has no goals/bookings/events, so real per-match
facts come from free, no-key sources only:

  1. ESPN's public, key-less soccer JSON (primary) — structured scoring plays
     with minute / player / team. Reliable from datacenter IPs.
  2. DuckDuckGo search via smolagents (fallback) — messy snippets, coerced to
     the same schema with one cheap LLM extraction pass.

Everything is best-effort and hard-capped at ENRICH_TIMEOUT_SECONDS. On any
failure the caller gets {"enriched": False} and runs in degraded (no named
player performances) mode.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
import json
import re
from typing import Any, Optional

import requests

from app.core.logging import get_logger

logger = get_logger(__name__)

# Whole-call cap (its own budget, separate from callers' enrichment pools).
ENRICH_TIMEOUT_SECONDS = 15
_ESPN_TIMEOUT_SECONDS = 6
_DDG_TIMEOUT_SECONDS = 6

_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
_ESPN_SCOREBOARD = f"{_ESPN_BASE}/scoreboard"
_USER_AGENT = "Mozilla/5.0 (compatible; DakolAI/1.0)"

# Names in ESPN keyEvents.text read like "Ismael Saibari (Morocco) right footed..."
# or "Casemiro (Brazil) is shown the yellow card." — grab the name before "(Team)".
_TEXT_NAME_RE = re.compile(r"([A-ZÀ-Ý][A-Za-zÀ-ÿ'’.\-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’.\-]+){0,2})\s+\(")
_GOAL_EVENT_TYPES = {"goal", "own_goal", "penalty", "penalty_missed", "yellow_card", "red_card"}

# Common name mismatches between football-data.org and ESPN.
_TEAM_ALIASES = {
    "turkiye": "turkey",
    "korearepublic": "southkorea",
    "iranislamicrepublic": "iran",
    "unitedstates": "usa",
    "us": "usa",
    "ivorycoast": "cotedivoire",
    "czechrepublic": "czechia",
    "bosniaherzegovina": "bosnia",
    "capeverdeislands": "capeverde",
}

_URL_PATTERN = re.compile(r"https?://[^\s)\]]+")
_SCORELINE_PATTERNS = [
    re.compile(r"\b([A-Z][A-Za-z .'-]+)\s+(\d{1,2})[-–]\s*(\d{1,2})\s+([A-Z][A-Za-z .'-]+)\b"),
    re.compile(r"\b(\d{1,2})[-–]\s*(\d{1,2})\b"),
]


def _empty_result() -> dict[str, Any]:
    return {"scoreline": None, "key_events": [], "source_urls": [], "enriched": False}


def _norm(value: Optional[str]) -> str:
    n = re.sub(r"[^a-z]", "", (value or "").lower())
    return _TEAM_ALIASES.get(n, n)


def _team_matches(target: str, candidate: str) -> bool:
    if not target or not candidate:
        return False
    return target == candidate or target in candidate or candidate in target


def _date_yyyymmdd(date_str: str) -> Optional[str]:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str or "")
    return f"{m.group(1)}{m.group(2)}{m.group(3)}" if m else None


# ─── ESPN (primary) ───────────────────────────────────────────────────────────

def _http_json(url: str, timeout: int) -> Optional[dict]:
    resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=timeout)
    if resp.status_code != 200:
        return None
    return resp.json()


def _minute_from_clock(clock: str) -> Optional[int]:
    # "21'", "45'+2'", "90+3'" -> base minute
    m = re.search(r"(\d{1,3})", clock or "")
    return int(m.group(1)) if m else None


def _classify_event(type_text: str, scoring: bool) -> str:
    t = (type_text or "").lower()
    if "own goal" in t:
        return "own_goal"
    if "penalty" in t and ("miss" in t or "saved" in t):
        return "penalty_missed"
    if scoring or "goal" in t:
        return "goal"
    if "red" in t:
        return "red_card"
    if "yellow" in t:
        return "yellow_card"
    if "substitut" in t:
        return "substitution"
    return t.replace(" ", "_") or "event"


def _espn_find(home: str, away: str, date: str):
    nh, na = _norm(home), _norm(away)
    ymd = _date_yyyymmdd(date)
    urls = ([f"{_ESPN_SCOREBOARD}?dates={ymd}"] if ymd else []) + [_ESPN_SCOREBOARD]
    for url in urls:
        try:
            data = _http_json(url, _ESPN_TIMEOUT_SECONDS)
        except Exception as e:
            logger.warning("ESPN scoreboard fetch failed: %s", e)
            continue
        if not data:
            continue
        for ev in data.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            competitors = comp.get("competitors", [])
            cnames = [_norm(c.get("team", {}).get("displayName")) for c in competitors]
            if any(_team_matches(nh, c) for c in cnames) and any(_team_matches(na, c) for c in cnames):
                return ev, comp, competitors
    return None, None, None


def _espn_scoreline(competitors: list) -> Optional[str]:
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away:
        return None
    hn = home.get("team", {}).get("displayName", "Home")
    an = away.get("team", {}).get("displayName", "Away")
    hs, as_ = home.get("score"), away.get("score")
    if hs is None or as_ is None:
        return None
    return f"{hn} {hs}-{as_} {an}"


def _espn_key_events(comp: dict, competitors: list) -> list[dict]:
    team_by_id = {
        str(c.get("team", {}).get("id")): c.get("team", {}).get("displayName")
        for c in competitors
    }
    events: list[dict] = []
    for dt in comp.get("details", []) or []:
        type_text = (dt.get("type") or {}).get("text") or ""
        scoring = bool(dt.get("scoringPlay"))
        players = [
            a.get("athlete", {}).get("displayName")
            for a in dt.get("athletesInvolved", []) or []
            if a.get("athlete")
        ]
        # Keep goals/cards/penalties; skip noise without a named athlete.
        if not players and not scoring:
            continue
        events.append({
            "minute": _minute_from_clock((dt.get("clock") or {}).get("displayValue", "")),
            "player": players[0] if players else "",
            "team": team_by_id.get(str((dt.get("team") or {}).get("id")), ""),
            "type": _classify_event(type_text, scoring),
        })
    return events


def _player_from_text(text: str) -> str:
    m = _TEXT_NAME_RE.search(text or "")
    return m.group(1).strip() if m else ""


def _espn_summary_events(event_id: str) -> list[dict]:
    """Richer events from the summary endpoint — scorer/booked names live in
    keyEvents[].text (athletesInvolved is usually empty)."""
    data = _http_json(f"{_ESPN_BASE}/summary?event={event_id}", _ESPN_TIMEOUT_SECONDS)
    if not data:
        return []
    events: list[dict] = []
    for ke in data.get("keyEvents", []) or []:
        type_text = (ke.get("type") or {}).get("text") or ""
        etype = _classify_event(type_text, bool(ke.get("scoringPlay")))
        if etype not in _GOAL_EVENT_TYPES:
            continue
        player = _player_from_text(ke.get("text") or "")
        if not player:
            continue
        events.append({
            "minute": _minute_from_clock((ke.get("clock") or {}).get("displayValue", "")),
            "player": player,
            "team": (ke.get("team") or {}).get("displayName") or "",
            "type": etype,
        })
    return events


def _enrich_espn(home: str, away: str, date: str) -> Optional[dict[str, Any]]:
    ev, comp, competitors = _espn_find(home, away, date)
    if not comp:
        return None
    # Prefer the summary endpoint (has scorer names); fall back to scoreboard
    # details (minutes/teams only) if summary is empty/unavailable.
    key_events: list[dict] = []
    event_id = ev.get("id")
    if event_id:
        try:
            key_events = _espn_summary_events(str(event_id))
        except Exception as e:
            logger.warning("ESPN summary fetch failed: %s", e)
    if not any(e.get("player") for e in key_events):
        key_events = _espn_key_events(comp, competitors)
    scoreline = _espn_scoreline(competitors)
    if not (scoreline or key_events):
        return None
    links = ev.get("links") or []
    source_urls = [l.get("href") for l in links if l.get("href")][:3]
    logger.info(
        "Match enrichment via ESPN",
        extra={"home": home, "away": away, "events": len(key_events)},
    )
    return {
        "scoreline": scoreline,
        "key_events": key_events,
        "source_urls": source_urls,
        "enriched": True,
    }


# ─── DuckDuckGo via smolagents (fallback) ───────────────────────────────────────

def _ddg_search(query: str) -> str:
    """Best-effort DuckDuckGo search. Often blocked from datacenter IPs."""
    tool = None
    try:
        from smolagents import DuckDuckGoSearchTool
        tool = DuckDuckGoSearchTool(max_results=5)
    except Exception:
        try:
            from smolagents import WebSearchTool
            tool = WebSearchTool(max_results=5)
        except Exception as e:
            logger.warning("smolagents/DuckDuckGo unavailable: %s", e)
            return ""
    try:
        return str(tool(query) or "")
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
        return ""


def _llm_extract_events(search_text: str, home: str, away: str) -> list[dict]:
    """Coerce messy search snippets into the structured key_events schema."""
    if not search_text.strip():
        return []
    try:
        from skills.model_router import generate_with_fallback
    except Exception:
        return []
    prompt = (
        "From the football match search results below, extract ONLY goals and cards that are "
        "explicitly stated. Return a JSON array; each item: "
        '{"minute": int|null, "player": str, "team": str, "type": '
        '"goal"|"own_goal"|"penalty"|"yellow_card"|"red_card"}. '
        f"Teams: {home} vs {away}. If nothing is explicitly stated, return []. "
        "Do NOT guess or invent. JSON only.\n\n"
        f"{search_text[:4000]}"
    )
    try:
        out = generate_with_fallback(prompt, 400).get("content", "")
        m = re.search(r"\[.*\]", out, re.DOTALL)
        events = json.loads(m.group(0)) if m else []
    except Exception as e:
        logger.warning("LLM event extraction failed: %s", e)
        return []
    clean: list[dict] = []
    for e in events if isinstance(events, list) else []:
        if isinstance(e, dict) and e.get("player") and e.get("type"):
            clean.append({
                "minute": e.get("minute") if isinstance(e.get("minute"), int) else None,
                "player": str(e["player"]),
                "team": str(e.get("team", "")),
                "type": str(e["type"]),
            })
    return clean


def _enrich_ddg(home: str, away: str, date: str) -> dict[str, Any]:
    query = f'"{home} vs {away}" {date} final score goals scorers'.strip()
    text = _ddg_search(query)
    if not text:
        return _empty_result()
    scoreline = None
    for pat in _SCORELINE_PATTERNS:
        if (m := pat.search(text)):
            scoreline = m.group(0).strip()
            break
    key_events = _llm_extract_events(text, home, away)
    source_urls = []
    for url in _URL_PATTERN.findall(text):
        u = url.rstrip(".,")
        if u not in source_urls:
            source_urls.append(u)
        if len(source_urls) == 3:
            break
    if not (scoreline or key_events):
        return _empty_result()
    logger.info("Match enrichment via DuckDuckGo", extra={"home": home, "away": away, "events": len(key_events)})
    return {
        "scoreline": scoreline,
        "key_events": key_events,
        "source_urls": source_urls,
        "enriched": True,
    }


# ─── Public entrypoint ──────────────────────────────────────────────────────────

def _enrich(home_team: str, away_team: str, date: str) -> dict[str, Any]:
    espn = None
    try:
        espn = _enrich_espn(home_team, away_team, date)
    except Exception as e:
        logger.warning("ESPN enrichment error: %s", e)
    if espn:
        return espn
    return _enrich_ddg(home_team, away_team, date)


def enrich_match_context(home_team: str, away_team: str, date: str) -> dict[str, Any]:
    """Return real per-match facts, hard-capped at ENRICH_TIMEOUT_SECONDS.

    Shape: {"enriched": bool, "scoreline": str|None,
            "key_events": [{"minute": int|None, "player": str, "team": str, "type": str}],
            "source_urls": [...]}
    On timeout/failure returns {"enriched": False, ...}.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_enrich, home_team, away_team, date)
    try:
        return future.result(timeout=ENRICH_TIMEOUT_SECONDS)
    except TimeoutError:
        future.cancel()
        logger.warning("enrich_match_context unavailable: timeout after %ss", ENRICH_TIMEOUT_SECONDS)
        return _empty_result()
    except Exception as e:
        logger.warning("enrich_match_context unavailable: %s", e)
        return _empty_result()
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
