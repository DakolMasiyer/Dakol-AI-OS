"""Pre-post fact gate.

Cross-checks generated football content against the data context that was
available at generation time, and returns {"status": "ok"|"flagged", "issues"}.

Primary path is an LLM check (`_llm_check`): it reads the structured verified
facts (who actually scored / was carded, the scoreline) and flags claims in the
post that CONTRADICT or are NOT SUPPORTED by them — so it catches "Casemiro
scored the winner" when the data says Casemiro was only booked and Vinícius
scored. This is the accuracy the heuristic can't reach (the heuristic only knows
Casemiro is *in the squad*, not what he did).

Fallback path is the heuristic (`_heuristic_check`): if every LLM provider is
unavailable, we still flag (a) unknown named individuals and (b) performance
claims made with no verified event data. Same return shape, so callers and the
frontend are unaffected.
"""

import json
import re
from typing import Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Capitalised football-generic / structural terms that are not player names.
_STOPWORDS = {
    "group", "world", "cup", "stage", "final", "semi", "quarter", "round",
    "var", "fifa", "uefa", "matchday", "man", "match", "full", "time", "half",
    "coach", "manager", "goalkeeper", "defender", "midfielder", "forward",
    "north", "south", "east", "west", "united", "city", "fc", "national",
    "the", "this", "that", "what", "with", "and", "but", "for", "from",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "stadium", "arena", "park", "league", "table", "draw", "both", "neither",
    "first", "second", "extra", "penalties", "kickoff", "fulltime", "halftime",
}

# Phrases that assert an individual performance / in-match event.
_PERFORMANCE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in (
        r"\bscored?\b", r"\bgoal(s)?\b", r"\bassist(s|ed)?\b", r"\bbrace\b",
        r"\bhat[- ]?trick\b", r"\bpenalt", r"\bown goal\b", r"\bred card\b",
        r"\byellow card\b", r"\bsent off\b", r"\bman of the match\b",
        r"\bbest performer\b", r"\bworst performer\b", r"\bplayer rating",
        r"\brated\b", r"\bsingle[- ]handed", r"\bdismantled\b", r"\bmasterclass\b",
        r"\bpulled (them|it) level\b", r"\bwinner\b", r"\bequali[sz]er\b",
    )
]

_NAME_RE = re.compile(r"\b([A-ZÀ-Ý][a-zà-ÿ'’.-]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ'’.-]+){0,2})\b")


def _norm(value: str) -> str:
    return re.sub(r"[^a-zà-ÿ]", "", (value or "").lower())


def _names_from_squad(squad_text: str) -> set[str]:
    """Squad strings look like 'GK: Alisson, Ederson\\nDEF: Marquinhos, ...'."""
    names: set[str] = set()
    for line in (squad_text or "").splitlines():
        part = line.split(":", 1)[1] if ":" in line else line
        for chunk in part.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            names.add(_norm(chunk))
            # Index individual tokens so "Vinicius" matches "Vinicius Junior".
            for tok in re.findall(r"[A-ZÀ-Ý][a-zà-ÿ'’.-]+", chunk):
                if len(tok) > 2:
                    names.add(_norm(tok))
    return names


def _allowed_names(data_context: dict) -> set[str]:
    allowed: set[str] = set()
    for key in ("squad_home", "squad_away", "h2h", "standings", "top_scorers"):
        text = data_context.get(key)
        if isinstance(text, str):
            allowed |= _names_from_squad(text)
    for ev in data_context.get("key_events") or []:
        if isinstance(ev, dict) and ev.get("player"):
            allowed.add(_norm(ev["player"]))
            for tok in re.findall(r"[A-ZÀ-Ý][a-zà-ÿ'’.-]+", ev["player"]):
                if len(tok) > 2:
                    allowed.add(_norm(tok))
    return allowed


def _team_tokens(data_context: dict) -> set[str]:
    toks: set[str] = set()
    for key in ("home_team", "away_team"):
        for tok in re.findall(r"[A-ZÀ-Ý][a-zà-ÿ'’.-]+", str(data_context.get(key) or "")):
            toks.add(_norm(tok))
    return toks


def _candidate_names(content: str) -> list[str]:
    out: list[str] = []
    for m in _NAME_RE.finditer(content):
        phrase = m.group(1).strip()
        words = phrase.split()
        # Require 2+ tokens, each a real word (len>=2), with a non-stopword lead.
        # Drops structural phrases like "Group C", "World Cup", "Both Teams".
        if len(words) < 2:
            continue
        if any(len(w.strip(".'’-")) < 2 for w in words):
            continue
        if _norm(words[0]) in _STOPWORDS:
            continue
        if all(_norm(w) in _STOPWORDS for w in words):
            continue
        out.append(phrase)
    return out


def _heuristic_check(content: str, data_context: dict) -> dict[str, Any]:
    """Fast, no-cost fallback. Return {"status", "issues"}."""
    content = content or ""
    data_context = data_context or {}
    allowed = _allowed_names(data_context)
    teams = _team_tokens(data_context)
    has_events = bool(data_context.get("key_events"))
    issues: list[dict] = []
    seen: set[str] = set()

    # (a) Named individuals not present in any provided source. Only meaningful
    # when we actually have a roster to compare against.
    for name in (_candidate_names(content) if allowed else []):
        n = _norm(name)
        if n in seen:
            continue
        if n in allowed or n in teams:
            continue
        # Skip multi-word phrases whose every token is a team/stopword token.
        if all((_norm(w) in allowed or _norm(w) in teams or _norm(w) in _STOPWORDS)
               for w in name.split()):
            continue
        seen.add(n)
        issues.append({
            "claim": name,
            "reason": "Named individual not found in squad, scorers, or verified match events",
        })

    # (b) Performance / scorer claims with no verified event data.
    if not has_events:
        for sentence in re.split(r"(?<=[.!?\n])\s+", content):
            s = sentence.strip()
            if len(s) < 12:
                continue
            if any(p.search(s) for p in _PERFORMANCE_PATTERNS):
                issues.append({
                    "claim": s[:180],
                    "reason": "Individual performance/scorer claim, but no verified match-event data was available",
                })

    return {"status": "flagged" if issues else "ok", "issues": issues[:12]}


# ─── LLM check (primary) ────────────────────────────────────────────────────────

def _facts_brief(data_context: dict) -> str:
    """Compact ledger of the ONLY facts the post is allowed to rely on."""
    dc = data_context or {}
    lines: list[str] = []
    home, away = dc.get("home_team"), dc.get("away_team")
    if home and away:
        lines.append(f"MATCH: {home} vs {away}")
    if dc.get("scoreline"):
        lines.append(f"SCORELINE: {dc['scoreline']}")

    events = dc.get("key_events") or []
    if events:
        lines.append("VERIFIED EVENTS:")
        for ev in events:
            if not isinstance(ev, dict):
                continue
            minute = ev.get("minute")
            when = f"{minute}'" if isinstance(minute, int) else "?"
            etype = (ev.get("type") or "event").replace("_", " ").upper()
            team = f" ({ev['team']})" if ev.get("team") else ""
            lines.append(f"  - {when} {etype}: {ev.get('player') or 'unknown'}{team}")
    else:
        lines.append("VERIFIED EVENTS: none (no scorers/cards/lineups known for this match)")

    for label, key in (("HOME SQUAD", "squad_home"), ("AWAY SQUAD", "squad_away"),
                        ("STANDINGS", "standings"), ("TOP SCORERS", "top_scorers")):
        text = dc.get(key)
        if isinstance(text, str) and text.strip():
            lines.append(f"{label}:\n{text.strip()}")
    return "\n".join(lines)


_LLM_GATE_INSTRUCTION = (
    "You are a strict fact-checker for a football social media post. The FACTS block below is the "
    "ONLY verified information about this match. Identify every claim in the POST that CONTRADICTS "
    "these facts, or that asserts a specific in-match event or individual performance NOT supported "
    "by them — e.g. who scored, assists, cards, player ratings (best/worst), who started or featured, "
    "or league/group standings. If VERIFIED EVENTS is 'none', flag ANY specific claim about an "
    "individual's in-match performance (scoring, assisting, being booked, being best/worst). Do NOT "
    "flag opinions, predictions, hype, tone, or general statements that make no factual assertion. "
    'Respond with JSON ONLY: {"issues":[{"claim":"<quoted text>","reason":"<why unverifiable/wrong>"}]}. '
    "Return an empty issues array if the post makes no unsupported factual claims."
)


def _llm_check(content: str, data_context: dict) -> Optional[dict[str, Any]]:
    """LLM-backed verdict. Returns {"status","issues"} or None if unavailable."""
    if not (content or "").strip():
        return {"status": "ok", "issues": []}
    try:
        from skills.model_router import generate_with_fallback
    except Exception:
        return None
    prompt = (
        f"{_LLM_GATE_INSTRUCTION}\n\n--- FACTS ---\n{_facts_brief(data_context)}\n\n"
        f"--- POST ---\n{content.strip()}\n\n--- JSON ---"
    )
    try:
        out = generate_with_fallback(prompt, 600, temperature=0).get("content", "")
    except Exception as e:
        logger.warning("fact_gate LLM check unavailable: %s", e)
        return None
    m = re.search(r"\{.*\}", out, re.DOTALL)
    if not m:
        logger.warning("fact_gate LLM returned no JSON object")
        return None
    try:
        parsed = json.loads(m.group(0))
    except Exception as e:
        logger.warning("fact_gate LLM JSON parse failed: %s", e)
        return None
    issues: list[dict] = []
    for item in (parsed.get("issues") or []):
        if isinstance(item, dict) and item.get("claim"):
            issues.append({
                "claim": str(item["claim"])[:200],
                "reason": str(item.get("reason") or "Not supported by verified match facts")[:200],
            })
    return {"status": "flagged" if issues else "ok", "issues": issues[:12]}


def check_content_facts(content: str, data_context: dict, prefer_llm: bool = True) -> dict[str, Any]:
    """Verify content against the generation-time facts.

    LLM-backed when available (accurate: distinguishes "in squad" from "actually
    scored"); falls back to the heuristic if every provider is down. Return shape
    {"status": "ok"|"flagged", "issues": [{"claim", "reason"}]}.
    """
    if prefer_llm:
        verdict = _llm_check(content, data_context)
        if verdict is not None:
            return verdict
    return _heuristic_check(content, data_context)
