"""Sync placement brief library. Source of truth for all evaluation contexts."""

from typing import Any

BRIEF_LIBRARY: list[dict[str, Any]] = [
    {"brief_id": "b001", "placement_type": "automotive_ad", "tone": "powerful, aspirational", "energy": "high", "vocal": "instrumental_preferred", "keywords": ["drive", "speed", "luxury"]},
    {"brief_id": "b002", "placement_type": "romantic_drama", "tone": "tender, emotional", "energy": "low", "vocal": "vocal_preferred", "keywords": ["love", "longing", "intimacy"]},
    {"brief_id": "b003", "placement_type": "sports_highlight", "tone": "aggressive, triumphant", "energy": "very_high", "vocal": "either", "keywords": ["victory", "hustle", "power"]},
    {"brief_id": "b004", "placement_type": "travel_documentary", "tone": "expansive, curious", "energy": "medium", "vocal": "instrumental_preferred", "keywords": ["journey", "discovery", "world"]},
    {"brief_id": "b005", "placement_type": "fashion_ad", "tone": "cool, minimalist", "energy": "medium", "vocal": "instrumental_preferred", "keywords": ["style", "aesthetic", "luxury"]},
    {"brief_id": "b006", "placement_type": "nollywood_drama", "tone": "emotional, narrative", "energy": "medium", "vocal": "vocal_preferred", "keywords": ["family", "conflict", "culture"]},
    {"brief_id": "b007", "placement_type": "horror_film", "tone": "tense, unsettling", "energy": "building", "vocal": "instrumental_preferred", "keywords": ["dread", "suspense", "dark"]},
    {"brief_id": "b008", "placement_type": "feel_good_ad", "tone": "warm, uplifting", "energy": "medium_high", "vocal": "vocal_preferred", "keywords": ["joy", "community", "bright"]},
    {"brief_id": "b009", "placement_type": "tech_product_launch", "tone": "clean, forward", "energy": "medium_high", "vocal": "instrumental_preferred", "keywords": ["innovation", "future", "precision"]},
    {"brief_id": "b010", "placement_type": "ngo_campaign", "tone": "earnest, moving", "energy": "low_medium", "vocal": "vocal_preferred", "keywords": ["hope", "humanity", "change"]},
    {"brief_id": "b011", "placement_type": "action_film", "tone": "intense, cinematic", "energy": "very_high", "vocal": "instrumental_preferred", "keywords": ["chase", "explosion", "adrenaline"]},
    {"brief_id": "b012", "placement_type": "comedy_series", "tone": "playful, quirky", "energy": "medium", "vocal": "either", "keywords": ["fun", "banter", "lighthearted"]},
    {"brief_id": "b013", "placement_type": "meditation_app", "tone": "calm, spacious", "energy": "very_low", "vocal": "instrumental_preferred", "keywords": ["breath", "stillness", "focus"]},
    {"brief_id": "b014", "placement_type": "fitness_app", "tone": "motivating, rhythmic", "energy": "high", "vocal": "either", "keywords": ["energy", "push", "endurance"]},
    {"brief_id": "b015", "placement_type": "afrobeats_commercial", "tone": "celebratory, rhythmic", "energy": "high", "vocal": "vocal_preferred", "keywords": ["dance", "celebration", "africa"]},
    {"brief_id": "b016", "placement_type": "period_drama", "tone": "orchestral, grand", "energy": "medium", "vocal": "instrumental_preferred", "keywords": ["history", "epic", "emotion"]},
    {"brief_id": "b017", "placement_type": "gaming_trailer", "tone": "epic, synthetic", "energy": "very_high", "vocal": "either", "keywords": ["battle", "world", "immersive"]},
    {"brief_id": "b018", "placement_type": "food_and_beverage_ad", "tone": "warm, sensory", "energy": "medium", "vocal": "vocal_preferred", "keywords": ["taste", "comfort", "delight"]},
    {"brief_id": "b019", "placement_type": "social_justice_documentary", "tone": "urgent, grounded", "energy": "medium", "vocal": "vocal_preferred", "keywords": ["truth", "resistance", "dignity"]},
    {"brief_id": "b020", "placement_type": "streaming_title_sequence", "tone": "distinctive, memorable", "energy": "medium", "vocal": "either", "keywords": ["identity", "brand", "hook"]},
]


def get_active_briefs() -> list[dict[str, Any]]:
    """Return all briefs available for evaluation."""
    return list(BRIEF_LIBRARY)
