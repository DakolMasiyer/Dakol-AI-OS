"""Pre-post fact gate.

Cross-checks generated football content against the data context that was
available at generation time. It is intentionally conservative and heuristic —
a *review flag*, not a hard truth oracle. Two signals:

  (a) named individuals in the copy that don't appear in any provided source
      (squads, scorers, match events, top scorers); and
  (b) scorer / player-rating / performance claims made when NO verified in-match
      event data was available (the common cause of fabrication).

Signal (b) is the strong one: in degraded mode (empty key_events) any specific
player-performance claim is unverifiable by construction.
"""

import re
from typing import Any

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


def check_content_facts(content: str, data_context: dict) -> dict[str, Any]:
    """Return {"status": "ok"|"flagged", "issues": [{"claim", "reason"}]}."""
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
