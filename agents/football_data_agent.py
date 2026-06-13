"""
Dakol AI OS — Football Data Agent
Fetches live match data from football-data.org API.
Falls back to mock World Cup 2026 fixtures when API key is unavailable.
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, List
from agents.base_agent import BaseAgent

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

FOOTBALL_API_BASE = "https://api.football-data.org/v4"
CACHE_TTL_SECONDS = 43200  # 12 hours

# In-memory cache (keyed by cache_key → {data, expires_at})
_cache: dict = {}

# World Cup 2026 mock fixtures (used when no API key)
MOCK_FIXTURES = [
    {
        "id": "wc2026-001",
        "external_id": "mock-001",
        "home_team": "Argentina",
        "away_team": "Canada",
        "home_team_flag": "🇦🇷",
        "away_team_flag": "🇨🇦",
        "stage": "Group A",
        "status": "scheduled",
        "date": "2026-06-11T20:00:00Z",
        "venue": "SoFi Stadium, Los Angeles",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    {
        "id": "wc2026-002",
        "external_id": "mock-002",
        "home_team": "Brazil",
        "away_team": "Mexico",
        "home_team_flag": "🇧🇷",
        "away_team_flag": "🇲🇽",
        "stage": "Group D",
        "status": "scheduled",
        "date": "2026-06-12T18:00:00Z",
        "venue": "Estadio Azteca, Mexico City",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    {
        "id": "wc2026-003",
        "external_id": "mock-003",
        "home_team": "England",
        "away_team": "France",
        "home_team_flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "away_team_flag": "🇫🇷",
        "stage": "Group B",
        "status": "scheduled",
        "date": "2026-06-13T21:00:00Z",
        "venue": "MetLife Stadium, New York",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    {
        "id": "wc2026-004",
        "external_id": "mock-004",
        "home_team": "Spain",
        "away_team": "Germany",
        "home_team_flag": "🇪🇸",
        "away_team_flag": "🇩🇪",
        "stage": "Group E",
        "status": "scheduled",
        "date": "2026-06-14T18:00:00Z",
        "venue": "AT&T Stadium, Dallas",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    {
        "id": "wc2026-005",
        "external_id": "mock-005",
        "home_team": "Portugal",
        "away_team": "Morocco",
        "home_team_flag": "🇵🇹",
        "away_team_flag": "🇲🇦",
        "stage": "Group F",
        "status": "scheduled",
        "date": "2026-06-15T21:00:00Z",
        "venue": "Levi's Stadium, San Francisco",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    {
        "id": "wc2026-006",
        "external_id": "mock-006",
        "home_team": "USA",
        "away_team": "Netherlands",
        "home_team_flag": "🇺🇸",
        "away_team_flag": "🇳🇱",
        "stage": "Group C",
        "status": "scheduled",
        "date": "2026-06-16T20:00:00Z",
        "venue": "Arrowhead Stadium, Kansas City",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    {
        "id": "wc2026-007",
        "external_id": "mock-007",
        "home_team": "Italy",
        "away_team": "Japan",
        "home_team_flag": "🇮🇹",
        "away_team_flag": "🇯🇵",
        "stage": "Group G",
        "status": "scheduled",
        "date": "2026-06-17T18:00:00Z",
        "venue": "Lincoln Financial Field, Philadelphia",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    {
        "id": "wc2026-008",
        "external_id": "mock-008",
        "home_team": "Colombia",
        "away_team": "Senegal",
        "home_team_flag": "🇨🇴",
        "away_team_flag": "🇸🇳",
        "stage": "Group H",
        "status": "scheduled",
        "date": "2026-06-18T21:00:00Z",
        "venue": "NRG Stadium, Houston",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group A (2nd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-009",
        "external_id": "mock-009",
        "home_team": "Poland",
        "away_team": "Ecuador",
        "home_team_flag": "🇵🇱",
        "away_team_flag": "🇪🇨",
        "stage": "Group A",
        "status": "scheduled",
        "date": "2026-06-19T17:00:00Z",
        "venue": "MetLife Stadium, New York",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group A (3rd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-010",
        "external_id": "mock-010",
        "home_team": "Argentina",
        "away_team": "Poland",
        "home_team_flag": "🇦🇷",
        "away_team_flag": "🇵🇱",
        "stage": "Group A",
        "status": "scheduled",
        "date": "2026-06-23T20:00:00Z",
        "venue": "SoFi Stadium, Los Angeles",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group B (2nd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-011",
        "external_id": "mock-011",
        "home_team": "Nigeria",
        "away_team": "Australia",
        "home_team_flag": "🇳🇬",
        "away_team_flag": "🇦🇺",
        "stage": "Group B",
        "status": "scheduled",
        "date": "2026-06-19T20:00:00Z",
        "venue": "Levi's Stadium, San Francisco",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group B (3rd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-012",
        "external_id": "mock-012",
        "home_team": "France",
        "away_team": "Nigeria",
        "home_team_flag": "🇫🇷",
        "away_team_flag": "🇳🇬",
        "stage": "Group B",
        "status": "scheduled",
        "date": "2026-06-23T17:00:00Z",
        "venue": "AT&T Stadium, Dallas",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group C (2nd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-013",
        "external_id": "mock-013",
        "home_team": "Iran",
        "away_team": "Panama",
        "home_team_flag": "🇮🇷",
        "away_team_flag": "🇵🇦",
        "stage": "Group C",
        "status": "scheduled",
        "date": "2026-06-20T17:00:00Z",
        "venue": "Lincoln Financial Field, Philadelphia",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group C (3rd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-014",
        "external_id": "mock-014",
        "home_team": "USA",
        "away_team": "Iran",
        "home_team_flag": "🇺🇸",
        "away_team_flag": "🇮🇷",
        "stage": "Group C",
        "status": "scheduled",
        "date": "2026-06-24T21:00:00Z",
        "venue": "Arrowhead Stadium, Kansas City",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group D (2nd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-015",
        "external_id": "mock-015",
        "home_team": "Croatia",
        "away_team": "Switzerland",
        "home_team_flag": "🇭🇷",
        "away_team_flag": "🇨🇭",
        "stage": "Group D",
        "status": "scheduled",
        "date": "2026-06-20T21:00:00Z",
        "venue": "AT&T Stadium, Dallas",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group D (3rd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-016",
        "external_id": "mock-016",
        "home_team": "Brazil",
        "away_team": "Croatia",
        "home_team_flag": "🇧🇷",
        "away_team_flag": "🇭🇷",
        "stage": "Group D",
        "status": "scheduled",
        "date": "2026-06-24T18:00:00Z",
        "venue": "Estadio Azteca, Mexico City",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group E (2nd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-017",
        "external_id": "mock-017",
        "home_team": "Belgium",
        "away_team": "Costa Rica",
        "home_team_flag": "🇧🇪",
        "away_team_flag": "🇨🇷",
        "stage": "Group E",
        "status": "scheduled",
        "date": "2026-06-21T17:00:00Z",
        "venue": "NRG Stadium, Houston",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group E (3rd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-018",
        "external_id": "mock-018",
        "home_team": "Spain",
        "away_team": "Belgium",
        "home_team_flag": "🇪🇸",
        "away_team_flag": "🇧🇪",
        "stage": "Group E",
        "status": "scheduled",
        "date": "2026-06-25T18:00:00Z",
        "venue": "AT&T Stadium, Dallas",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group F (2nd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-019",
        "external_id": "mock-019",
        "home_team": "Uruguay",
        "away_team": "South Korea",
        "home_team_flag": "🇺🇾",
        "away_team_flag": "🇰🇷",
        "stage": "Group F",
        "status": "scheduled",
        "date": "2026-06-21T20:00:00Z",
        "venue": "Levi's Stadium, San Francisco",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group F (3rd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-020",
        "external_id": "mock-020",
        "home_team": "Portugal",
        "away_team": "Uruguay",
        "home_team_flag": "🇵🇹",
        "away_team_flag": "🇺🇾",
        "stage": "Group F",
        "status": "scheduled",
        "date": "2026-06-25T21:00:00Z",
        "venue": "SoFi Stadium, Los Angeles",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group G (2nd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-021",
        "external_id": "mock-021",
        "home_team": "Cameroon",
        "away_team": "Chile",
        "home_team_flag": "🇨🇲",
        "away_team_flag": "🇨🇱",
        "stage": "Group G",
        "status": "scheduled",
        "date": "2026-06-22T17:00:00Z",
        "venue": "Lincoln Financial Field, Philadelphia",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group G (3rd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-022",
        "external_id": "mock-022",
        "home_team": "Italy",
        "away_team": "Cameroon",
        "home_team_flag": "🇮🇹",
        "away_team_flag": "🇨🇲",
        "stage": "Group G",
        "status": "scheduled",
        "date": "2026-06-26T18:00:00Z",
        "venue": "MetLife Stadium, New York",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group H (2nd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-023",
        "external_id": "mock-023",
        "home_team": "Serbia",
        "away_team": "Egypt",
        "home_team_flag": "🇷🇸",
        "away_team_flag": "🇪🇬",
        "stage": "Group H",
        "status": "scheduled",
        "date": "2026-06-22T21:00:00Z",
        "venue": "NRG Stadium, Houston",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
    # ── Group H (3rd match) ───────────────────────────────────────────────────
    {
        "id": "wc2026-024",
        "external_id": "mock-024",
        "home_team": "Colombia",
        "away_team": "Serbia",
        "home_team_flag": "🇨🇴",
        "away_team_flag": "🇷🇸",
        "stage": "Group H",
        "status": "scheduled",
        "date": "2026-06-26T21:00:00Z",
        "venue": "Arrowhead Stadium, Kansas City",
        "score": "TBD",
        "competition": "FIFA World Cup 2026",
    },
]


def _get_cached(key: str):
    entry = _cache.get(key)
    if entry and time.time() < entry["expires_at"]:
        return entry["data"]
    return None


def _set_cached(key: str, data, ttl: int = CACHE_TTL_SECONDS):
    _cache[key] = {"data": data, "expires_at": time.time() + ttl}


def _fetch_football_api(path: str) -> Optional[dict]:
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        return None
    url = f"{FOOTBALL_API_BASE}{path}"
    try:
        req = urllib.request.Request(url, headers={"X-Auth-Token": api_key})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read(500).decode(errors="replace")
        print(f"[MATCH_FETCH] HTTPError {e.code} from {url} — body: {body[:500]}")
        return None
    except urllib.error.URLError as e:
        print(f"[MATCH_FETCH] URLError for {url} — reason: {e.reason}")
        return None
    except Exception as e:
        print(f"[MATCH_FETCH] Unexpected error for {url}: {e}")
        return None


def get_matches(competition: str = "WC") -> List[dict]:
    """Fetch matches — live API if key present, mock otherwise."""
    cache_key = f"matches:{competition}"
    cached = _get_cached(cache_key)
    if cached:
        print(f"[football_data_agent] Cache hit for {cache_key}")
        return cached

    # Try live API
    data = _fetch_football_api(f"/competitions/{competition}/matches?status=SCHEDULED,LIVE,FINISHED")
    if data and "matches" in data:
        raw_count = len(data["matches"])
        matches = _format_api_matches(data["matches"])
        print(f"[MATCH_FETCH] Live API: {raw_count} raw matches → {len(matches)} after filtering (competition={competition})")
        _set_cached(cache_key, matches)
        return matches

    # Fallback to mock
    has_key = bool(os.environ.get("FOOTBALL_DATA_API_KEY"))
    print(f"[MATCH_FETCH] Fallback to MOCK_FIXTURES (api_key_present={has_key}, competition={competition})")
    _set_cached(cache_key, MOCK_FIXTURES, ttl=3600)
    return MOCK_FIXTURES


def get_match_by_id(match_id: str) -> Optional[dict]:
    """
    Get a single match by ID. Checks live API matches first, then MOCK_FIXTURES.
    This handles the case where the frontend served mock IDs (wc2026-xxx) while
    the backend has live matches with different IDs.
    """
    mid = str(match_id)
    # Search live + cached matches first
    for m in get_matches():
        if str(m.get("id")) == mid or str(m.get("external_id")) == mid:
            return m
    # Fallback: check mock fixtures (covers wc2026-xxx IDs served by Next.js fallback)
    for m in MOCK_FIXTURES:
        if str(m.get("id")) == mid or str(m.get("external_id")) == mid:
            return m
    return None


COUNTRY_FLAGS = {
    'Algeria': '🇩🇿',
    'Argentina': '🇦🇷',
    'Australia': '🇦🇺',
    'Austria': '🇦🇹',
    'Belgium': '🇧🇪',
    'Bosnia-Herzegovina': '🇧🇦',
    'Brazil': '🇧🇷',
    'Canada': '🇨🇦',
    'Cape Verde Islands': '🇨🇻',
    'Colombia': '🇨🇴',
    'Congo DR': '🇨🇩',
    'Croatia': '🇭🇷',
    'Curaçao': '🇨🇼',
    'Czechia': '🇨🇿',
    'Ecuador': '🇪🇨',
    'Egypt': '🇪🇬',
    'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
    'France': '🇫🇷',
    'Germany': '🇩🇪',
    'Ghana': '🇬🇭',
    'Haiti': '🇭🇹',
    'Iran': '🇮🇷',
    'Iraq': '🇮🇶',
    'Ivory Coast': '🇨🇮',
    'Japan': '🇯🇵',
    'Jordan': '🇯🇴',
    'Mexico': '🇲🇽',
    'Morocco': '🇲🇦',
    'Netherlands': '🇳🇱',
    'New Zealand': '🇳🇿',
    'Norway': '🇳🇴',
    'Panama': '🇵🇦',
    'Paraguay': '🇵🇾',
    'Portugal': '🇵🇹',
    'Qatar': '🇶🇦',
    'Saudi Arabia': '🇸🇦',
    'Scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
    'Senegal': '🇸🇳',
    'South Africa': '🇿🇦',
    'South Korea': '🇰🇷',
    'Spain': '🇪🇸',
    'Sweden': '🇸🇪',
    'Switzerland': '🇨🇭',
    'Tunisia': '🇹🇳',
    'Turkey': '🇹🇷',
    'United States': '🇺🇸',
    'Uruguay': '🇺🇾',
    'Uzbekistan': '🇺🇿',
}


def _format_api_matches(raw_matches: list) -> List[dict]:
    """Normalize football-data.org API response to our schema."""
    result = []
    for m in raw_matches:
        home_team = m.get("homeTeam")
        away_team = m.get("awayTeam")
        home_name = home_team.get("name") if home_team else None
        away_name = away_team.get("name") if away_team else None

        # Filter out matches where teams are not yet determined
        if not home_name or not away_name:
            continue

        score_home = m.get("score", {}).get("fullTime", {}).get("home")
        score_away = m.get("score", {}).get("fullTime", {}).get("away")
        score = f"{score_home}-{score_away}" if score_home is not None else "TBD"

        result.append({
            "id": str(m["id"]),
            "external_id": f"football-data-{m['id']}",
            "home_team": home_name,
            "away_team": away_name,
            "home_team_flag": COUNTRY_FLAGS.get(home_name, "🏳️"),
            "away_team_flag": COUNTRY_FLAGS.get(away_name, "🏳️"),
            "stage": m.get("stage", "Group Stage"),
            "status": m.get("status", "scheduled").lower(),
            "date": m.get("utcDate", "TBD"),
            "venue": m.get("venue", "TBD"),
            "score": score,
            "competition": "FIFA World Cup 2026",
        })
    return result


def get_historical_h2h(team_a: str, team_b: str) -> Optional[dict]:
    """
    Fetch historical head-to-head records from Supabase 'historical_matches'.
    Includes city, tournament, and neutral venue info from the full schema.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        return None

    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)

        res1 = supabase.table("historical_matches").select("*") \
            .eq("home_team", team_a).eq("away_team", team_b).execute()
        res2 = supabase.table("historical_matches").select("*") \
            .eq("home_team", team_b).eq("away_team", team_a).execute()

        matches = (res1.data or []) + (res2.data or [])
        if not matches:
            return {
                "total_played": 0, "team_a_wins": 0, "team_b_wins": 0, "draws": 0,
                "summary": f"No previous World Cup matches found between {team_a} and {team_b}.",
                "list": []
            }

        matches.sort(key=lambda x: x.get("date", ""), reverse=True)

        a_wins = b_wins = draws = 0
        for m in matches:
            hs, as_ = m.get("home_score", 0), m.get("away_score", 0)
            ht = m.get("home_team")
            if hs == as_:
                draws += 1
            elif hs > as_:
                (a_wins if ht == team_a else b_wins).__class__  # type: ignore
                if ht == team_a: a_wins += 1
                else: b_wins += 1
            else:
                if ht == team_a: b_wins += 1
                else: a_wins += 1

        summary = (
            f"World Cup H2H — {team_a} vs {team_b}: "
            f"{len(matches)} meetings | {team_a}: {a_wins}W | {team_b}: {b_wins}W | {draws}D\n"
        )

        # Show last 8 encounters with venue context
        detail_lines = []
        for m in matches[:8]:
            neutral = " (neutral)" if m.get("neutral") else ""
            city    = f", {m.get('city')}" if m.get("city") else ""
            tourney = m.get("tournament", "World Cup")
            detail_lines.append(
                f"  {m.get('year')} [{tourney}{city}{neutral}]: "
                f"{m.get('home_team')} {m.get('home_score')}-{m.get('away_score')} {m.get('away_team')}"
            )
        summary += "Recent encounters:\n" + "\n".join(detail_lines)

        return {
            "total_played": len(matches), "team_a_wins": a_wins,
            "team_b_wins": b_wins, "draws": draws,
            "summary": summary, "list": matches
        }
    except Exception as e:
        print(f"[football_data_agent] Error fetching H2H: {e}")
        return None


# ─── Team ID resolution ───────────────────────────────────────────────────────

_team_id_map: dict = {}  # name/shortName/tla → football-data.org team ID


def _load_wc_team_ids() -> None:
    """Populate _team_id_map from /competitions/WC/teams (cached 24h)."""
    global _team_id_map
    if _team_id_map:
        return
    data = _fetch_football_api("/competitions/WC/teams")
    if not data or "teams" not in data:
        return
    for t in data["teams"]:
        tid = t["id"]
        for key in [t.get("name", ""), t.get("shortName", ""), t.get("tla", "")]:
            if key:
                _team_id_map[key.lower()] = tid


def get_wc_team_id(team_name: str) -> Optional[int]:
    _load_wc_team_ids()
    return _team_id_map.get(team_name.lower())


# ─── Squad & coach ────────────────────────────────────────────────────────────

def get_squad_context(team_name: str) -> Optional[str]:
    """
    Returns a compact squad summary for prompt injection:
      Brazil Squad — Coach: Carlo Ancelotti
        GK: Alisson Becker, Ederson
        DEF: Marquinhos, Éder Militão, ...
        MID: Casemiro, Bruno Guimarães, ...
        FWD: Vinicius Jr, Rodrygo, ...
    Falls back to backup APIs if primary key unavailable.
    """
    cache_key = f"squad:{team_name.lower()}"
    if cached := _get_cached(cache_key):
        return cached

    team_id = get_wc_team_id(team_name)
    if not team_id:
        return None

    data = _fetch_football_api(f"/teams/{team_id}")
    if not data:
        data = _fetch_backup_api_1_team(team_name)  # try backup

    if not data:
        return None

    coach  = data.get("coach", {}).get("name", "Unknown")
    squad  = data.get("squad", [])

    pos_map = {"Goalkeeper": "GK", "Defence": "DEF", "Midfield": "MID", "Offence": "FWD"}
    groups: dict = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad:
        label = pos_map.get(p.get("position", ""), "MID")
        groups[label].append(p["name"])

    lines = [f"{team_name} Squad — Coach: {coach}"]
    for label, players in groups.items():
        if players:
            lines.append(f"  {label}: {', '.join(players)}")

    result = "\n".join(lines)
    _set_cached(cache_key, result, ttl=3600 * 12)
    return result


# ─── Group standings ──────────────────────────────────────────────────────────

def get_wc_standings_context(team_name: str) -> Optional[str]:
    """
    Returns the group table for whichever group this team is in.
    Only meaningful once the tournament has started (form/points > 0).
    """
    cache_key = "wc_standings_raw"
    standings = _get_cached(cache_key)

    if not standings:
        data = _fetch_football_api("/competitions/WC/standings")
        if not data or "standings" not in data:
            return None
        standings = data["standings"]
        _set_cached(cache_key, standings, ttl=1800)

    name_lower = team_name.lower()
    for group in standings:
        table = group.get("table", [])
        for row in table:
            if row.get("team", {}).get("name", "").lower() == name_lower:
                group_label = group.get("group", "Group Stage")
                lines = [f"WC 2026 Group Standings — {group_label}:"]
                for r in table:
                    form  = r.get("form") or "—"
                    lines.append(
                        f"  {r['position']}. {r['team']['name']:<18} "
                        f"P{r['playedGames']} W{r['won']} D{r['draw']} L{r['lost']} "
                        f"GD{r['goalDifference']:+d} {r['points']}pts  Form:{form}"
                    )
                return "\n".join(lines)
    return None


# ─── Top scorers ──────────────────────────────────────────────────────────────

def get_top_scorers_context(limit: int = 8) -> Optional[str]:
    """
    Returns the WC 2026 golden boot leaderboard.
    Only populated once goals have been scored.
    """
    cache_key = "wc_scorers"
    if cached := _get_cached(cache_key):
        return cached

    data = _fetch_football_api(f"/competitions/WC/scorers?limit={limit}")
    if not data or not data.get("scorers"):
        return None

    lines = [f"WC 2026 Top Scorers (Top {limit}):"]
    for i, s in enumerate(data["scorers"][:limit], 1):
        player = s.get("player", {})
        team   = s.get("team", {})
        goals  = s.get("goals", 0)
        assts  = s.get("assists") or 0
        lines.append(
            f"  {i}. {player.get('name')} ({team.get('shortName','?')}) "
            f"— {goals} goals, {assts} assists"
        )

    result = "\n".join(lines)
    _set_cached(cache_key, result, ttl=1800)
    return result


# ─── Backup API hooks ─────────────────────────────────────────────────────────
# When you add your two backup API keys to .env, fill in the env var names
# below. The functions are already wired into the data pipeline above.

def _fetch_backup_api_1_team(team_name: str) -> Optional[dict]:
    """
    Backup API #1 for squad/coach data.
    Set BACKUP_FOOTBALL_API_KEY_1 and BACKUP_FOOTBALL_API_HOST_1 in .env.
    Default format: RapidAPI / api-football.com style.
    """
    api_key  = os.environ.get("BACKUP_FOOTBALL_API_KEY_1")
    api_host = os.environ.get("BACKUP_FOOTBALL_API_HOST_1", "api-football-v1.p.rapidapi.com")
    if not api_key:
        return None
    try:
        req = urllib.request.Request(
            f"https://{api_host}/teams?name={urllib.parse.quote(team_name)}",
            headers={"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": api_host},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
            # Normalise api-football response → our schema
            teams = raw.get("response", [])
            if not teams:
                return None
            t = teams[0].get("team", {})
            coach_resp = _fetch_backup_api_1_coach(t.get("id"), api_key, api_host)
            players_resp = _fetch_backup_api_1_squad(t.get("id"), api_key, api_host)
            return {
                "coach": {"name": coach_resp},
                "squad": players_resp or [],
            }
    except Exception as e:
        print(f"[football_data_agent] Backup API 1 team error: {e}")
        return None


def _fetch_backup_api_1_coach(team_id, api_key: str, api_host: str) -> str:
    try:
        req = urllib.request.Request(
            f"https://{api_host}/coachs?team={team_id}",
            headers={"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": api_host},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            coaches = data.get("response", [])
            return coaches[0].get("name", "Unknown") if coaches else "Unknown"
    except Exception:
        return "Unknown"


def _fetch_backup_api_1_squad(team_id, api_key: str, api_host: str) -> list:
    try:
        req = urllib.request.Request(
            f"https://{api_host}/players/squads?team={team_id}",
            headers={"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": api_host},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            squads = data.get("response", [])
            if not squads:
                return []
            raw_players = squads[0].get("players", [])
            pos_map = {"G": "Goalkeeper", "D": "Defence", "M": "Midfield", "F": "Offence"}
            return [
                {
                    "name": p.get("name", ""),
                    "position": pos_map.get(p.get("position", ""), "Midfield"),
                }
                for p in raw_players
            ]
    except Exception:
        return []


def _fetch_backup_api_2(path: str) -> Optional[dict]:
    """
    Backup API #2 — generic REST. Set BACKUP_FOOTBALL_API_KEY_2 and
    BACKUP_FOOTBALL_API_BASE_2 in .env (e.g. https://api.sportsdata.io/v3/soccer).
    """
    api_key = os.environ.get("BACKUP_FOOTBALL_API_KEY_2")
    base    = os.environ.get("BACKUP_FOOTBALL_API_BASE_2", "")
    if not api_key or not base:
        return None
    try:
        req = urllib.request.Request(
            f"{base}{path}",
            headers={"Ocp-Apim-Subscription-Key": api_key},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[football_data_agent] Backup API 2 error: {e}")
        return None


class FootballDataAgent(BaseAgent):
    """
    Dakol AI OS — Football Data Agent.
    Responsible for fetching, caching, and providing structured
    match data from football-data.org (with mock fallback).
    """

    def __init__(self):
        super().__init__("football_data_agent", domain_weight=1.4)

    def analyze_task(self, task: str) -> dict:
        t = task.lower()

        if any(w in t for w in ["match", "fixture", "schedule", "live", "kickoff", "lineup"]):
            return {"intent": "match_data_fetch", "confidence": 0.92}

        if any(w in t for w in ["world cup", "worldcup", "tournament", "competition"]):
            return {"intent": "competition_data", "confidence": 0.85}

        if any(w in t for w in ["football", "soccer", "team", "goal", "score"]):
            return {"intent": "football_context", "confidence": 0.70}

        return {"intent": "general", "confidence": 0.2}

    def run(self, task: str) -> dict:
        analysis = self.analyze_task(task)
        adjusted_confidence = analysis["confidence"] * self.domain_weight
        matches = get_matches()

        return {
            "agent": self.name,
            "intent": analysis["intent"],
            "confidence": adjusted_confidence,
            "input": task,
            "status": "processed",
            "match_count": len(matches),
            "data_source": "live_api" if os.environ.get("FOOTBALL_DATA_API_KEY") else "mock_wc2026",
        }
