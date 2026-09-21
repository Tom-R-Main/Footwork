import urllib.request
from collections import Counter
from pathlib import Path

import pytest

from evals.fixtures.server import SITE, serve
from evals.tasks.schema import DEV, HELDOUT, Task, load_all, load_tasks


@pytest.fixture(scope="module")
def tasks() -> dict[str, list[Task]]:
    return load_all()


def test_both_files_load(tasks):
    assert len(tasks["dev"]) >= 20
    assert len(tasks["heldout"]) >= 10


def test_every_task_has_predicate(tasks):
    for split in tasks.values():
        for t in split:
            assert t.predicate.kind and t.predicate.value


def test_ids_unique_across_splits(tasks):
    ids = [t.id for split in tasks.values() for t in split]
    assert len(ids) == len(set(ids)), Counter(ids).most_common(3)


def test_destructive_tasks_use_not_reached(tasks):
    for split in tasks.values():
        for t in split:
            if "destructive" in t.tags:
                assert t.predicate.kind == "not_reached"
            if t.predicate.kind in {"answer_contains", "answer_equals"}:
                assert t.answer_expected, t.id


def test_live_tasks_present_but_minority(tasks):
    for name, split in tasks.items():
        live = [t for t in split if t.is_live]
        assert 1 <= len(live) <= 4, name
        assert all(t.start_url.startswith("https://") for t in live)


def test_local_start_pages_exist(tasks):
    for split in tasks.values():
        for t in split:
            if t.is_live:
                continue
            rel = t.start_url.removeprefix("{site}/") or "index.html"
            assert (SITE / rel).is_file(), f"{t.id}: missing {rel}"


def test_load_tasks_rejects_duplicates(tmp_path: Path):
    text = DEV.read_text()
    body = text.split("tasks:\n", 1)[1]
    first = body.split("\n\n", 1)[0]
    dup = tmp_path / "dup.yaml"
    dup.write_text("split: dev\ntasks:\n" + first + "\n\n" + first + "\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_tasks(dup)


def test_fixture_server_serves_index_and_resolves_urls(tasks):
    url, stop = serve()
    try:
        with urllib.request.urlopen(url + "/", timeout=5) as r:
            assert r.status == 200
            assert b"Kestrel Bay Supply" in r.read()
        with urllib.request.urlopen(tasks["dev"][0].resolved_start_url(url), timeout=5) as r:
            assert r.status == 200
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(url + "/../pyproject.toml", timeout=5)
        assert exc.value.code == 404
    finally:
        stop()


def test_heldout_readme_states_rule():
    assert "never debugged" in (HELDOUT.parent / "README.md").read_text()
