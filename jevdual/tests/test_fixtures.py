from tests.fixtures.loader import fixture_slugs, load_fixture, manifest

SENSITIVE_VALUES = ("hunter2-SECRET-9f3a", "4111111111111111", "998877", "hidden-token-ZZTOP")


def test_enough_fixtures_load():
    slugs = fixture_slugs()
    assert len(slugs) >= 10, slugs
    for slug in slugs:
        fx = load_fixture(slug)
        assert fx.snapshot["documents"], slug
        assert fx.snapshot["strings"], slug
        assert fx.dom["root"], slug
        assert "nodes" in fx.ax, slug
        assert fx.element_count > 0, slug
        assert len(fx.selector_backend_node_ids) == fx.element_count, slug


def test_manifest_matches_files():
    m = manifest()
    assert {f["slug"] for f in m["fixtures"]} == set(fixture_slugs())


def test_one_fixture_exceeds_choice_cap():
    assert any(load_fixture(s).element_count > 255 for s in fixture_slugs())


def test_sensitive_fixture_has_secret_values_in_raw_snapshot():
    """The raw snapshot must contain the secret so later tests can prove the pipeline strips it."""
    fx = load_fixture("sensitive-fields")
    strings = set(fx.snapshot["strings"])
    present = [v for v in SENSITIVE_VALUES if v in strings]
    assert present, "no sensitive value found in the raw strings table"
    attrs = fx.snapshot["strings"]
    assert "password" in attrs and "cc-number" in attrs


def test_fixture_rebuilds_target_all_trees():
    fx = load_fixture("wikipedia-python")
    trees = fx.to_target_all_trees()
    assert trees.snapshot is fx.snapshot
    assert trees.device_pixel_ratio == fx.device_pixel_ratio
