"""Menu builder over every recorded fixture via the offline replay."""

import json

import pytest
from jevdual.menu import (
    MAX_CHOICE_OPTIONS,
    OPERATIONS,
    STATE_TOKEN_BUDGET,
    MenuBudget,
    build_menu,
    group_candidates,
)

from tests.fixtures.loader import fixture_slugs, load_fixture
from tests.fixtures.replay import replay_state

SLUGS = fixture_slugs()

# Values baked into tests/fixtures/pages/sensitive_fields.html.
SECRETS = ("hunter2-SECRET-9f3a", "4111111111111111", "998877", "hidden-token-ZZTOP")


@pytest.fixture(scope="module")
def menus():
    return {slug: build_menu(replay_state(slug)) for slug in SLUGS}


def test_replay_matches_recorded_selector_map():
    for slug in SLUGS:
        state = replay_state(slug)
        fixture = load_fixture(slug)
        sm = state.dom_state.selector_map
        assert len(sm) == fixture.element_count, slug
        assert set(sm) == set(fixture.selector_backend_node_ids), slug
        assert all(sm[k].backend_node_id == v for k, v in fixture.selector_backend_node_ids.items()), slug


def test_every_fixture_builds_within_budget(menus):
    for slug, menu in menus.items():
        assert menu.candidates, slug
        assert menu.estimated_tokens <= STATE_TOKEN_BUDGET, (slug, menu.estimated_tokens)
        assert menu.url and menu.title, slug
        ids = [c.id for c in menu.candidates]
        assert len(ids) == len(set(ids)), slug
        assert menu.omitted == {}, (slug, menu.omitted)  # all fixtures fit without trimming at default budget


def test_by_operation_matches_candidate_operations(menus):
    for slug, menu in menus.items():
        assert set(menu.by_operation) == set(OPERATIONS), slug
        for op, cands in menu.by_operation.items():
            assert all(op in c.operations for c in cands), (slug, op)
            expected = [c.id for c in menu.candidates if op in c.operations]
            assert [c.id for c in cands] == expected, (slug, op)  # document order preserved
        for c in menu.candidates:
            assert c.operations, (slug, c.id)
            assert all(o in OPERATIONS for o in c.operations)


def test_dense_links_exceeds_choice_cap_and_groups_cover_once(menus):
    menu = menus["dense-links"]
    clicks = menu.by_operation["click"]
    assert len(clicks) > MAX_CHOICE_OPTIONS
    groups = group_candidates(clicks, MenuBudget().group_size)
    assert all(len(g) <= MenuBudget().group_size for g in groups)
    flat = [c.id for g in groups for c in g]
    assert flat == [c.id for c in clicks]
    assert len(groups) <= MAX_CHOICE_OPTIONS


def test_sensitive_values_never_reach_the_menu(menus):
    menu = menus["sensitive-fields"]
    blob = json.dumps({"text": menu.page_text, "elements": [c.to_state() for c in menu.candidates]})
    for secret in SECRETS:
        assert secret not in blob, secret
    by_type = {c.input_type: c for c in menu.candidates if c.input_type}
    assert "password" in by_type and "type" in by_type["password"].operations
    assert by_type["password"].value is None
    cc = [c for c in menu.candidates if c.label == "Card number"]
    assert cc and cc[0].value is None and "type" in cc[0].operations
    # A non-sensitive text input keeps its value.
    user = [c for c in menu.candidates if c.label == "Username" and c.input_type == "text"]
    assert user and user[0].value == "alice@example.com"


def test_modal_fixture_builds(menus):
    menu = menus["modal-over-content"]
    assert menu.candidates
    assert any("modal" in (c.label + (c.section or "")).lower() or c.role == "button" for c in menu.candidates)


def test_wikipedia_text_and_sections(menus):
    menu = menus["wikipedia-python"]
    assert len(menu.page_text) > 1000
    assert "Python" in menu.page_text
    assert sum(1 for c in menu.candidates if c.section) > len(menu.candidates) // 2
    search = [c for c in menu.candidates if c.role == "searchbox"]
    assert search and {"type", "enter", "click"} <= set(search[0].operations)
    links = [c for c in menu.candidates if c.href]
    assert links and all(len(c.href) <= 200 for c in links)


def test_offscreen_uses_document_bounds(menus):
    # Everything on the small local page is inside the 1280x900 viewport.
    assert not any(c.offscreen for c in menus["sensitive-fields"].candidates)
    # A long article has many elements below the fold.
    assert sum(1 for c in menus["wikipedia-python"].candidates if c.offscreen) > 50


def test_budget_trims_text_then_offscreen_then_overflow():
    state = replay_state("wikipedia-python")
    full = build_menu(state)
    # Tight budget: page text hits the floor, then off-screen candidates go, then on-screen ones.
    tight = build_menu(state, MenuBudget(state_tokens=3000))
    assert tight.estimated_tokens <= 3000
    assert tight.omitted.get("page_text_chars", 0) > 0
    assert len(tight.page_text) >= MenuBudget().min_page_text_chars or len(full.page_text) < MenuBudget().min_page_text_chars
    assert tight.omitted.get("offscreen", 0) > 0
    # No off-screen candidate survives while on-screen ones were dropped.
    if tight.omitted.get("overflow"):
        assert not any(c.offscreen for c in tight.candidates)
    # Document order of survivors is preserved and they are a prefix-filtered subset of the full menu.
    full_ids = [c.id for c in full.candidates]
    tight_ids = [c.id for c in tight.candidates]
    assert tight_ids == [i for i in full_ids if i in set(tight_ids)]


def test_group_candidates_rejects_bad_size():
    with pytest.raises(ValueError):
        group_candidates((), 0)
