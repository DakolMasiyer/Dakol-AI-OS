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

# ─── Few-shot examples ────────────────────────────────────────────────────────
# Keyed by (content_type, tone). Each value is one curated example that shows
# the structure, voice, and rhythm of high-performing football content.
# Gemini uses this as a style reference — not to copy, but to understand format.

FEW_SHOT_EXAMPLES: dict = {

    # ── TWITTER THREAD ────────────────────────────────────────────────────────

    ("twitter_thread", "hype"): """\
EXAMPLE of high-performing hype Twitter thread (structure to follow):

🚨 ARGENTINA JUST WON THE WORLD CUP AND I'M NOT OKAY

36 years. They waited 36 years for this.

Thread 🧵

1/ Mbappe scored a hat-trick in the FINAL and STILL lost. Let that sink in. Three goals in a World Cup final. Not enough.

2/ Messi played 1,179 professional matches to get here. Every single one of them led to this moment.

3/ The penalty shootout was the most nerve-shredding 15 minutes in football history. Montiel stepped up knowing the whole country was watching.

4/ France played 90 minutes of average football then scored 3 in 10 minutes. That's the World Cup. That's why we watch.

5/ Argentina's journey: Beaten by Saudi Arabia → Survived every knockout round → Won it all. THAT IS FOOTBALL.

One word: REDEMPTION. 🏆🇦🇷

#WorldCup #Argentina #Messi""",

    ("twitter_thread", "analytical"): """\
EXAMPLE of high-performing analytical Twitter thread (structure to follow):

Why France couldn't stop Argentina despite having the better tactical setup. A thread 📐🧵

1/ France set up in a 4-3-3 with Tchouaméni as the pivot. The plan was to press high and force Argentina long. It worked for 78 minutes.

2/ But Argentina's build-up bypassed this press by design. Di María dropped to receive from de Paul, dragging Tchouaméni out of position. The half-space opened every time.

3/ Messi's positioning was the tactical key. He didn't play as a traditional #10. He floated into pockets between France's midfield and back line — targeting the space vacated by Tchouaméni.

4/ When France went 2-0 down they were forced to push higher. This created the transition windows that nearly cost them the game even when they came back.

5/ Verdict: France had the better team on paper. Argentina had the better STRUCTURE.

#Tactics #WorldCupFinal #Football""",

    ("twitter_thread", "casual"): """\
EXAMPLE of high-performing casual Twitter thread (structure to follow):

me watching the World Cup final as a neutral fan:

→ 80 mins: ok this is boring
→ 81 mins: oh Mbappé scored
→ 82 mins: ...wait what
→ 83 mins: HE SCORED AGAIN???
→ extra time: I need a doctor
→ penalties: I've aged 10 years
→ result: I have no idea what just happened but I need to lie down

football is genuinely the worst sport for your heart and I would not change a single thing about it 😭

#WorldCup #Football""",

    ("twitter_thread", "professional"): """\
EXAMPLE of high-performing professional Twitter thread (structure to follow):

The 2022 World Cup Final: a statistical breakdown of how Argentina prevailed. Thread.

1/ Argentina xG: 2.3. Actual goals: 3. France xG: 2.8. Actual: 3. Decided by moments, not patterns.

2/ Mbappé's hat-trick — the second in a World Cup final after Geoff Hurst in 1966 — came in the 97th, 105th and 118th minutes. His xG contribution in the final alone: 1.67.

3/ Messi became the player with most WC matches (26), most appearances in knockout stages (16), and the first to score in every round of a single tournament.

4/ Argentina's 3-4-3 structure conceded significant space in behind yet maintained shape for 78 minutes. Credit: Scaloni's tactical preparation over 4 years.

Conclusion: The better-structured team won. Not the more talented one.

#WorldCupFinal #Analysis #Football""",

    ("twitter_thread", "editorial"): """\
EXAMPLE of high-performing editorial Twitter thread (structure to follow):

On December 18, 2022, in Lusail, football finally gave Lionel Messi what he deserved.

A reflection. 🧵

1/ For 36 years, Argentina searched for a third World Cup. For 17 years, Messi carried that weight — often alone, often unfairly, always with dignity.

2/ There were nights when it felt like the game had conspired against him. The 2014 Final loss. The Copa América defeats. The retirement that lasted three weeks.

3/ But football has a long memory. And in the end, it gave him Lusail. It gave him 90 minutes of sweat and belief and one outrageous moment of brilliance at 35.

4/ The image of Scaloni and Messi embracing at the final whistle will define the era. Two men who understood what they'd carried.

5/ History doesn't always correct itself in real time. When it does, you feel it. Yesterday, football was generous.

This is what the World Cup is for.

#Messi #Argentina #WorldCup""",

    # ── INSTAGRAM CAPTION ─────────────────────────────────────────────────────

    ("instagram_caption", "hype"): """\
EXAMPLE of high-performing hype Instagram caption (structure to follow):

THE GOAT SEALED HIS LEGACY 🐐🏆🇦🇷

36 years of hurt. 17 years of questions. One night in Qatar to answer them ALL.

Lionel Messi — World Cup winner. Say it slowly. Let it land.

Best final in football history? Not even a debate.

Drop a 🏆 if you witnessed history last night 👇

#Messi #Argentina #WorldCup2022 #WorldCupFinal #GOAT #Football #FifaWorldCup #Qatar2022""",

    ("instagram_caption", "casual"): """\
EXAMPLE of high-performing casual Instagram caption (structure to follow):

that World Cup final had me going through all 5 stages of grief and back again in 90 minutes 😭⚽

I'm okay. I think I'm okay.

(I'm not okay)

tag someone who aged 20 years watching penalties 👇

#WorldCup2022 #Football #WorldCupFinal #Footballfans""",

    ("instagram_caption", "analytical"): """\
EXAMPLE of high-performing analytical Instagram caption (structure to follow):

The numbers behind the greatest World Cup Final ever played 📊

• Argentina xG: 2.3 → scored 3
• France xG: 2.8 → scored 3
• Mbappé: 3 goals in 26 mins — best individual final performance since Hurst 1966
• Messi: first player to score in every round of a single WC tournament

What the stats tell you: this final was decided by moments, not patterns. Both teams performed above expected output. Football reminder: the data explains what happened. Not why it felt like that.

#WorldCup2022 #Football #Stats #Analysis #WorldCupFinal""",

    # ── MATCH PREVIEW ─────────────────────────────────────────────────────────

    ("match_preview", "analytical"): """\
EXAMPLE of high-performing analytical match preview (structure to follow):

Brazil vs Argentina: The most tactically interesting fixture of the tournament.

Neither team will admit it publicly, but both are set up to exploit the exact weakness the other has.

**The key battle:** Brazil's high press vs Argentina's positional build-up

Argentina under Scaloni have mastered the third-man combination — short pass, switch, diagonal run. Brazil's press is trigger-based, not man-to-man, which means pockets in the half-space will open every time Fernández drops deep.

**The player to watch:** Not Messi, not Vinicius Jr. Watch Lucas Paquetá. If he plays as the left 8, he drags the defensive shape and creates overloads that decide the match.

**Bold prediction:** This goes to extra time. Both defences are too well-organised for a comfortable result. The team that scores first wins.

**Predicted score: 1-0 AET**""",

    ("match_preview", "professional"): """\
EXAMPLE of high-performing professional match preview (structure to follow):

**Team A vs Team B — Match Preview**
*Stage | Competition | Venue*

**Context**
Both sides arrive in contrasting form. [Team A] have been the tournament's most consistent side, conceding just once in three group games. [Team B] have shown vulnerability at set pieces but possess the tournament's most dangerous forward line.

**Key Matchup**
The fullback vs winger battle on the right side will define the first half hour. If [Player X] gets in behind [Player Y] early, the defensive shape collapses.

**Tactical Note**
[Team A]'s high press requires full-back cover. [Team B] will look to exploit the channel between the centre-back and right-back in transition.

**Prediction**
[Team A] 2-1 [Team B] — quality in the final third proves decisive.""",

    ("match_preview", "editorial"): """\
EXAMPLE of high-performing editorial match preview (structure to follow):

There are matches and there are *events*. This is the latter.

The fixture carries weight beyond the 90 minutes — historical, cultural, personal for millions of people who have been waiting years to see these two nations meet at this stage.

What the numbers won't capture: the charge in the stadium when both teams walk out. The silences. The noise. The sense that something irreversible is about to happen.

This is football at its most elemental — two nations, one pitch, everything on the line.

We find out soon. And whatever happens, it will be remembered.""",

    # ── POST-MATCH ANALYSIS ───────────────────────────────────────────────────

    ("post_match_analysis", "analytical"): """\
EXAMPLE of high-performing analytical post-match analysis (structure to follow):

**[Team A] 3-2 [Team B] | Full Tactical Breakdown**

**How [Team A] won:**
Their 3-4-3 was built to neutralise [Team B]'s wide attacks. The wing-backs had a clear brief: contain the wingers, don't chase them. Hold the line. Trust the central defence. For 78 minutes, it worked.

**The collapse:**
The substitutions at 65' changed everything. The introduced players brought directness the defence couldn't handle in transition. The third goal was predictable once [Team B] equalised — tournament fatigue was visible in the backline.

**Player ratings (key performers):**
- Goalkeeper: 8/10 — won the shootout with two saves
- Striker: 9/10 — decisive in both directions
- Opposing forward: 9.5/10 — lost, but individually brilliant

**What this means:**
Their system has a ceiling. If they meet a high-pressing side in the knockouts, that 65-80 minute window is the danger zone.""",

    ("post_match_analysis", "hype"): """\
EXAMPLE of high-performing hype post-match analysis (structure to follow):

WHAT DID I JUST WATCH 😱⚽

I have been watching football for 20 years. I have NEVER seen anything like that.

2-0 up with 10 minutes left. THE GAME WAS OVER.

Then. Everything. Changed.

That comeback. Those penalties. That celebration. This is why football is the greatest sport ever invented and I will not be taking questions.

Final rating: 11/10. Historic. Unrepeatable. Perfect.

#WorldCup #Football""",

    ("post_match_analysis", "casual"): """\
EXAMPLE of high-performing casual post-match analysis (structure to follow):

ok so here's my completely unqualified analysis of what just happened:

✅ the team that scored more goals: won
✅ the goalkeeper: made saves (good)
✅ the striker everyone was worried about: scored (phew)
❌ my heart: not okay

in conclusion: football is a simulation and I refuse to believe any of that was real

see you in the next round 😭

#WorldCup #Football""",

    # ── PLAYER SPOTLIGHT ──────────────────────────────────────────────────────

    ("player_spotlight", "hype"): """\
EXAMPLE of high-performing hype player spotlight (structure to follow):

🧵 THIS PLAYER IS ABOUT TO DESTROY THIS WORLD CUP

And here's why defenders have no answer for him.

1/ His pace doesn't register the way it should on a screen. You have to see it in person to understand. He covers 40 metres like most players cover 20.

2/ Left-footed. Right-footed. Both. Doesn't matter. He scores with his weaker foot like it's his stronger one.

3/ The stat you need: 17 goals and 10 assists last season. The most direct player in European football. Fullbacks don't want it.

4/ At 24 years old, this is the World Cup that confirms what his club fans have known for 3 years: generational talent.

5/ Watch him. He's about to go off. 🔥

#WorldCup #Football""",

    ("player_spotlight", "analytical"): """\
EXAMPLE of high-performing analytical player spotlight (structure to follow):

Why [Player] is the most important player in this tournament that nobody is talking about.

A tactical breakdown 📐

1/ His role isn't traditional. He doesn't play as a #9 or a #10. He operates in the space *between* — specifically in the left half-space where the opposition's right-back and central midfielder create a gap in the 4-3-3.

2/ The numbers: 4.3 progressive carries per 90, 2.1 key passes, 0.31 non-penalty xG. Elite in all three. But the raw stats miss the point.

3/ His real value is positional. When he drops to receive, he pulls a midfielder out of shape. When he accelerates, he creates 2v1s. Both things happening in the same phase of play is what makes him unplayable.

4/ The defender who can contain him in this tournament doesn't exist yet. He'll expose every team that doesn't press aggressively from the front.

Watch the defensive shape when he gets on the ball. That's the tell.""",

    ("player_spotlight", "editorial"): """\
EXAMPLE of high-performing editorial player spotlight (structure to follow):

Before the tournament started, [Player] had nothing left to prove to anyone — except himself.

Three major honours. Recognition. The respect of the game. And yet, the World Cup remained unfinished business: a quarter-final exit four years ago, a performance that was brilliant in flashes but not decisive when it mattered most.

This is the tournament that changes the narrative or confirms it.

At [age], he is in the peak years. His club manager has made him the axis around which everything turns. The question is not whether he is good enough. The question — the only one that matters in football — is whether he is *decisive* when it counts.

The answer will come in the knockout rounds. It always does.""",

    # ── LINKEDIN POST ─────────────────────────────────────────────────────────

    ("linkedin_post", "professional"): """\
EXAMPLE of high-performing professional LinkedIn post (structure to follow):

The World Cup Final taught me more about leadership under pressure than any management book.

Here's what the winning team's performance revealed about elite decision-making:

**1. Composure is a skill, not a trait**
When the opposition equalised, the team didn't retreat. They pressed forward. High performers go *toward* pressure, not away from it.

**2. The team that trusts their system wins**
The manager built a structure over four years. Every player knew their role. In the most chaotic 90 minutes imaginable, that clarity held.

**3. Legacy isn't built in a single moment — it's confirmed by one**
The captain had already done everything at club level. The World Cup simply ratified what the game knew. In business, the same applies: your reputation is built by consistency, confirmed by how you perform on the biggest stage.

What leadership lessons have you taken from elite sport? I'd love to hear in the comments.

#Leadership #WorldCup #HighPerformance #Football #Management""",

    # ── YOUTUBE SCRIPT ────────────────────────────────────────────────────────

    ("youtube_script", "hype"): """\
EXAMPLE of high-performing hype YouTube script (structure to follow):

[HOOK — 5 seconds]
"In 8 minutes, he scored 3 goals in a World Cup final — and STILL lost."

[CONTEXT — 15 seconds]
"The 2022 World Cup Final is the greatest football match ever played. The winning team were 2-0 up in the 80th minute. The other side were dead. Then the comeback started — and football broke everyone watching."

[TENSION — 15 seconds]
"Goal. 97 minutes. Another goal. 98 minutes. Penalty. THREE goals in EIGHT minutes. The most insane comeback in World Cup history — but it still wasn't enough. Penalties. Two saves. Heartbreak."

[PAYOFF + CTA — 10 seconds]
"One team lifted the trophy. The other gave us the greatest final we'll ever see. If you watched it live, you know. If you didn't — our full tactical breakdown is pinned on the channel. Subscribe so you never miss a moment like this again."

---
NOTE: Replace bracketed placeholders with the actual match details. Keep energy levels HIGH throughout — this style depends on pace and momentum.""",
}

# Fallback for any (content_type, tone) combination not explicitly defined.
# Uses the analytical thread as a structural reference.
_FALLBACK_EXAMPLE = FEW_SHOT_EXAMPLES[("twitter_thread", "analytical")]

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
        tone: str = None,
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
            tone:               Brand tone (e.g. 'analytical', 'hype', 'casual'). Selects
                                the matching few-shot example as a style reference.
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

        # Inject few-shot example as style reference
        if tone:
            example = FEW_SHOT_EXAMPLES.get(
                (content_type, tone),
                FEW_SHOT_EXAMPLES.get((content_type, "analytical"), _FALLBACK_EXAMPLE)
            )
            user_prompt = (
                f"STYLE REFERENCE — study the structure, voice, and format below. "
                f"Do NOT copy the content. Apply this style to the actual match data.\n\n"
                f"{example}\n\n"
                f"---\n\n"
                f"NOW WRITE THE ACTUAL CONTENT:\n\n"
                + user_prompt
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
