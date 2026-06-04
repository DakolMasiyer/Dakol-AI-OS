from agents.base_agent import BaseAgent

# Content type → system prompt templates
CONTENT_PROMPTS = {
    "twitter_thread": {
        "system": (
            "You are an expert sports journalist writing for Twitter/X. "
            "Create engaging, viral-worthy threads about football matches. "
            "Structure: Hook → Context → Tactical breakdown → Player spotlight → Prediction. "
            "Use emojis sparingly. Keep each tweet under 280 chars. Number tweets 1/, 2/, etc."
        ),
        "template": (
            "Write a Twitter thread for: {home_team} vs {away_team}\n"
            "Stage: {stage} | Status: {status} | Date: {date}\n"
            "Score: {score}\n"
            "Tone: Conversational, enthusiastic, viral."
        ),
        "max_tokens": 800,
    },
    "instagram_caption": {
        "system": (
            "You are a social media expert creating Instagram captions for football content. "
            "Hook in first line. Emojis (football, flags). Max 30 hashtags. CTA at end."
        ),
        "template": (
            "Write an Instagram caption for: {home_team} vs {away_team}\n"
            "Stage: {stage} | Date: {date} | Score: {score}\n"
            "Include: #WorldCup2026 and relevant team hashtags."
        ),
        "max_tokens": 300,
    },
    "match_preview": {
        "system": (
            "You are a professional football analyst. "
            "Write a compelling match preview covering: team form, key players, tactical matchup, "
            "historical head-to-head, and a bold prediction. Be authoritative and specific."
        ),
        "template": (
            "Write a match preview for: {home_team} vs {away_team}\n"
            "Stage: {stage} | Kickoff: {date} | Venue: {venue}\n"
            "Include tactical analysis and your prediction."
        ),
        "max_tokens": 600,
    },
    "post_match_analysis": {
        "system": (
            "You are a post-match analyst. Break down the result with: "
            "key moments, tactical shifts, player ratings (best/worst), "
            "what this result means for the tournament, and what to watch next."
        ),
        "template": (
            "Write a post-match analysis for: {home_team} vs {away_team}\n"
            "Final Score: {score} | Stage: {stage}\n"
            "Make it insightful and shareable."
        ),
        "max_tokens": 700,
    },
    "player_spotlight": {
        "system": (
            "You are a football journalist writing a player spotlight piece. "
            "Cover: current form, role in this match, strengths/weaknesses to exploit, "
            "historical stats vs this opponent, and a storyline angle."
        ),
        "template": (
            "Write a player spotlight in context of: {home_team} vs {away_team}\n"
            "Stage: {stage} | Date: {date}\n"
            "Pick the most compelling player storyline and explore it deeply."
        ),
        "max_tokens": 500,
    },
    "linkedin_post": {
        "system": (
            "You are a professional sports analyst writing for LinkedIn. "
            "Draw business/leadership parallels to football. "
            "Start with a hook, give analysis, end with a takeaway. 1-2 hashtags max."
        ),
        "template": (
            "Write a LinkedIn post about: {home_team} vs {away_team}\n"
            "Stage: {stage} | Result: {score}\n"
            "Professional angle — what business leaders can learn from this match."
        ),
        "max_tokens": 400,
    },
    "youtube_script": {
        "system": (
            "You are an expert football YouTuber and video editor. "
            "Write an engaging, high-energy 45-60 second YouTube script about a football match. "
            "Structure the script clearly with timestamps and visual cue brackets like: "
            "[HOOK - 5 seconds] (action hook), [CONTEXT - 15 seconds] (match setup), "
            "[TENSION - 15 seconds] (tactical conflict/climax), and [PAYOFF + CTA - 10 seconds] (outcome and channel sub invitation). "
            "Keep the tone extremely energetic, fast-paced, and hook-driven."
        ),
        "template": (
            "Write a YouTube Shorts script for: {home_team} vs {away_team}\n"
            "Stage: {stage} | Venue: {venue} | Score: {score}\n"
            "Ensure it has high-energy hooks and a strong call-to-action to subscribe."
        ),
        "max_tokens": 600,
    },
}

DOMAIN_KEYWORDS = [
    "match", "preview", "analysis", "football", "soccer", "world cup", "worldcup",
    "tweet", "thread", "instagram", "linkedin", "caption", "content", "generate",
    "team", "player", "goal", "stadium", "fixture", "tournament", "copa",
    "spotlight", "post-match", "preview", "lineup",
]


class WorldCupContentAgent(BaseAgent):
    """
    Dakol AI OS — World Cup Content Agent.
    Specialist agent for AI-powered football content generation.
    Handles: Twitter threads, match previews, post-match analysis,
             player spotlights, Instagram captions, LinkedIn posts.
    """

    def __init__(self):
        super().__init__("worldcup_content_agent", domain_weight=1.5)

    def analyze_task(self, task: str) -> dict:
        t = task.lower()

        # ----------------------------
        # HIGH CONFIDENCE — CONTENT GENERATION
        # ----------------------------
        if any(w in t for w in ["generate", "write", "create", "draft"]):
            if any(w in t for w in ["match", "football", "world cup", "preview", "analysis", "thread"]):
                return {"intent": "worldcup_content_generation", "confidence": 0.95}

        # ----------------------------
        # MEDIUM — FOOTBALL DOMAIN DETECTED
        # ----------------------------
        if any(w in t for w in DOMAIN_KEYWORDS):
            return {"intent": "worldcup_content_generation", "confidence": 0.75}

        # ----------------------------
        # FALLBACK
        # ----------------------------
        return {"intent": "general", "confidence": 0.2}

    def build_prompt(
        self,
        content_type: str,
        match_context: dict,
        h2h_context: str = None,
        squad_home: str = None,
        squad_away: str = None,
        standings_context: str = None,
        top_scorers_context: str = None,
    ) -> tuple:
        """
        Build system + user prompt enriched with all available context.

        Args:
            content_type:       One of the CONTENT_PROMPTS keys.
            match_context:      home_team, away_team, stage, status, date, score, venue.
            h2h_context:        Historical H2H summary from Supabase.
            squad_home:         Home team squad + coach string.
            squad_away:         Away team squad + coach string.
            standings_context:  Live group standings table.
            top_scorers_context: Tournament top scorers leaderboard.
        """
        config = CONTENT_PROMPTS.get(content_type, CONTENT_PROMPTS["match_preview"])

        ctx = {
            "home_team": match_context.get("home_team", "Team A"),
            "away_team": match_context.get("away_team", "Team B"),
            "stage":     match_context.get("stage", "Group Stage"),
            "status":    match_context.get("status", "scheduled"),
            "date":      match_context.get("date", "TBD"),
            "score":     match_context.get("score", "TBD"),
            "venue":     match_context.get("venue", "TBD"),
        }

        user_prompt = config["template"].format(**ctx)

        # Assemble enrichment block — only include sections that have data
        enrichment_parts = []

        if h2h_context:
            enrichment_parts.append(f"=== HISTORICAL HEAD-TO-HEAD ===\n{h2h_context}")

        if squad_home or squad_away:
            squads = "\n".join(filter(None, [squad_home, squad_away]))
            enrichment_parts.append(f"=== SQUAD INFORMATION ===\n{squads}")

        if standings_context:
            enrichment_parts.append(f"=== CURRENT GROUP STANDINGS ===\n{standings_context}")

        if top_scorers_context:
            enrichment_parts.append(f"=== TOURNAMENT TOP SCORERS ===\n{top_scorers_context}")

        if enrichment_parts:
            user_prompt += (
                "\n\n--- DATA CONTEXT (use naturally — do not dump raw stats) ---\n"
                + "\n\n".join(enrichment_parts)
                + "\n\nIMPORTANT: Weave the above facts (specific scorelines, years, player names, "
                "standings position, form run) naturally into the copy. Make it feel authoritative "
                "and data-rich, not like a stats dump. Prioritise the most compelling facts."
            )

        return config["system"], user_prompt

    def get_max_tokens(self, content_type: str) -> int:
        return CONTENT_PROMPTS.get(content_type, CONTENT_PROMPTS["match_preview"])["max_tokens"]

    def run(self, task: str) -> dict:
        analysis = self.analyze_task(task)
        adjusted_confidence = analysis["confidence"] * self.domain_weight

        return {
            "agent": self.name,
            "intent": analysis["intent"],
            "confidence": adjusted_confidence,
            "input": task,
            "status": "processed",
            "supported_types": list(CONTENT_PROMPTS.keys()),
        }
