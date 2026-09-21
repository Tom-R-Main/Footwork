import urllib.request
from collections import Counter
from pathlib import Path

import pytest

from evals.fixtures.server import SITE, serve
from evals.predicates import EndState, checkpoints_missed
from evals.tasks.schema import DEV, HELDOUT, LIVE_DEV, LIVE_HELDOUT, Task, load_all, load_tasks


@pytest.fixture(scope="module")
def tasks() -> dict[str, list[Task]]:
    return load_all()


def test_both_files_load(tasks):
    assert len(tasks["dev"]) >= 20
    assert len(tasks["heldout"]) >= 10
    assert len(tasks["live-dev"]) >= 40
    assert len(tasks["live-heldout"]) >= 20


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
    for name in ("dev", "heldout"):
        live = [t for t in tasks[name] if t.is_live]
        assert 1 <= len(live) <= 4, name
        assert all(t.start_url.startswith("https://") for t in live)


def test_live_splits_hold_only_live_https_tasks(tasks):
    for name in ("live-dev", "live-heldout"):
        for t in tasks[name]:
            assert t.is_live and t.start_url.startswith("https://"), t.id
            assert "{site}" not in t.start_url, t.id


def test_live_splits_cover_the_experiments(tasks):
    """Q4 needs multistep tasks with checkpoints; Q8 needs consent tasks on both sides of the policy."""
    live = tasks["live-dev"] + tasks["live-heldout"]
    multistep = [t for t in live if "multistep" in t.tags]
    consent = [t for t in live if "consent" in t.tags]
    assert len(multistep) >= 15
    assert all(t.checkpoints for t in multistep), [t.id for t in multistep if not t.checkpoints]
    assert len(consent) >= 15
    assert any(t.authorize for t in consent) and any(t.predicate.kind == "not_reached" for t in consent)
    for t in consent:
        assert t.authorize or t.predicate.kind == "not_reached", t.id


def test_live_secrets_never_in_task_text(tasks):
    for name in ("live-dev", "live-heldout"):
        for t in tasks[name]:
            for value in t.secrets.values():
                assert value not in t.task, t.id


def test_checkpoints_only_url_contains(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "split: live-dev\ntasks:\n  - id: x\n    task: do the thing please\n    start_url: https://example.com/\n"
        "    tags: [live, multistep]\n    requirements: [a]\n    predicate: {kind: url_contains, value: b}\n"
        "    checkpoints: [{kind: page_text_contains, value: c}]\n"
    )
    with pytest.raises(ValueError, match="url_contains"):
        load_tasks(bad)


def test_checkpoints_missed_reads_visited_and_final_urls(tasks):
    t = next(t for t in tasks["live-dev"] if len(t.checkpoints) >= 2)
    first = t.checkpoints[0].value
    end = EndState(final_url="https://x/" + first, page_text="", answer=None, visited_urls=("https://x/start",))
    missed = checkpoints_missed(t, end)
    assert first not in missed and len(missed) == len(t.checkpoints) - 1


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
    text = (HELDOUT.parent / "README.md").read_text()
    assert "never debugged" in text
    assert LIVE_HELDOUT.name in text and LIVE_DEV.name in text
