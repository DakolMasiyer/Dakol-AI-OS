from farm.briefs import BRIEF_LIBRARY, get_active_briefs


def test_brief_library_has_minimum_count():
    assert len(BRIEF_LIBRARY) >= 20


def test_all_briefs_have_required_fields():
    required = {"brief_id", "placement_type", "tone", "energy", "vocal"}
    for brief in BRIEF_LIBRARY:
        missing = required - brief.keys()
        assert not missing, f"{brief['brief_id']} missing fields: {missing}"


def test_get_active_briefs_returns_list():
    briefs = get_active_briefs()
    assert isinstance(briefs, list)
    assert len(briefs) >= 20


def test_brief_ids_are_unique():
    ids = [b["brief_id"] for b in BRIEF_LIBRARY]
    assert len(ids) == len(set(ids))
