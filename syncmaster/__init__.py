from syncmaster.graph import query_graph, save_brief, save_recommendation, save_track
from syncmaster.metadata import analyze_metadata, tag_metadata
from syncmaster.schema import Brief, ComposerProfile, MetadataAnalysis, TrackMetadata

try:
    from syncmaster.audio import analyze_audio_file, analyze_audio_intelligence
except Exception:
    analyze_audio_file = None
    analyze_audio_intelligence = None

try:
    from syncmaster.licensing import recommend_licensing, recommend_sync_fit
except Exception:
    recommend_licensing = None
    recommend_sync_fit = None

try:
    from syncmaster.matching import match_to_brief, rank_matches
except Exception:
    match_to_brief = None
    rank_matches = None

__all__ = [
    "Brief",
    "ComposerProfile",
    "MetadataAnalysis",
    "TrackMetadata",
    "analyze_audio_intelligence",
    "analyze_audio_file",
    "analyze_metadata",
    "match_to_brief",
    "query_graph",
    "rank_matches",
    "recommend_licensing",
    "recommend_sync_fit",
    "save_brief",
    "save_recommendation",
    "save_track",
    "tag_metadata",
]
