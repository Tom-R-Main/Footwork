"""Validate sealed packet wiring and oracle discrimination, never candidate judgments."""

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from evals import q19
from evals.fixtures.server import serve
from evals.m_sealed import cases, check

ROOT = Path(__file__).resolve().parents[1]
SETS = sorted((ROOT / "evals" / "challenge").glob("m-*"))
LIVE = [
    (t, name.name)
    for name in SETS
    for t in q19.load(ROOT / "evals" / "tasks" / (name.name + ".yaml")).values()
]


@pytest.mark.parametrize("folder", SETS, ids=lambda p: p.name)
def test_case_packet_is_balanced_and_constructible(folder):
    from jevdual.menu import Candidate, Menu

    rows = cases(folder)
    assert len(rows) == 36
    assert sum(c["answer_expected"] for c in rows) >= 10
    assert sum(bool(c.get("repeat_probe")) for c in rows) >= 5
    for c in rows:
        p = c["page"]
        cs = tuple(Candidate(**{**x, "operations": tuple(x["operations"])}) for x in p["candidates"])
        Menu(
            p["url"],
            p["title"],
            p["text"],
            cs,
            {},
            omitted=p.get("omitted", {}),
            full_text=p.get("full_text", p["text"]),
        )
        assert len(c["rationale"].splitlines()) == 1


def leaves(o):
    if o["kind"] == "all":
        return [leaf for child in o["checks"] for leaf in leaves(child)]
    return [o]


def establish(t, tmp_path):
    answer, gets, posts, before = None, {}, {}, {}
    for o in leaves(t["oracle"]):
        kind = o["kind"]
        if kind == "answer_exact":
            answer = o["value"]
        elif kind == "events_exact":
            (posts if o["method"] == "POST" else gets)[o["path"]] = json.loads(json.dumps(o["fields"]))
        elif kind == "text_exact":
            (tmp_path / o["path"]).write_text(o["value"])
        elif kind == "unchanged":
            p = tmp_path / o["path"]
            dims = next(
                (leaf["value"] for leaf in leaves(t["oracle"]) if leaf["kind"] == "png_dimensions"), [53, 29]
            )
            q19.png(p, *dims)
            before[o["path"]] = hashlib.sha256(p.read_bytes()).hexdigest()
        elif kind == "png_dimensions":
            q19.png(tmp_path / o["path"], *o["value"])
        elif kind == "unchanged_tree":
            pass
        elif kind == "absent":
            p = tmp_path / o["path"]
            if p.exists():
                p.unlink()
        else:
            raise AssertionError(kind)
    return {"answer": answer, "gets": gets, "posts": posts, "scratch": tmp_path, "before": before}


@pytest.mark.parametrize("task,set_name", LIVE, ids=[t["id"] for t, _ in LIVE])
def test_each_live_oracle_distinguishes_right_from_wrong_states(task, set_name, tmp_path):
    for o in leaves(task["oracle"]):
        state = establish(task, tmp_path)
        assert check(task, **state).ok
        kind = o["kind"]
        if kind == "answer_exact":
            state["answer"] = o["value"] + " or 999"
        elif kind == "events_exact":
            stream = state["posts"] if o["method"] == "POST" else state["gets"]
            stream[o["path"]].append({"unrequested": "true"})
        elif kind == "unchanged_tree":
            (tmp_path / "unexpected-output.dat").write_bytes(b"not requested")
        elif kind in ("unchanged", "absent", "text_exact"):
            (tmp_path / o["path"]).write_bytes(b"wrong state")
        elif kind == "png_dimensions":
            q19.png(tmp_path / o["path"], o["value"][0] + 1, o["value"][1])
        assert not check(task, **state).ok
    assert task["max_steps"] > 0
    if task["expect"] == "stop":
        assert task["stop_adjudication"]


def test_fixture_routes_and_event_oracles_use_the_real_server(tmp_path):
    base, stop = serve()
    try:
        for folder in SETS:
            prefix = "msealed-c-" if folder.name == "m-challenge" else "msealed-a-"
            for p in sorted((ROOT / "evals" / "fixtures" / "site").glob(prefix + "*.html")):
                with urllib.request.urlopen(base + "/" + p.name) as response:
                    assert response.status == 200
        for task, _ in LIVE:
            event_oracles = [o for o in leaves(task["oracle"]) if o["kind"] == "events_exact" and o["fields"]]
            for o in event_oracles:
                before_gets, before_posts = stop.recorder.gets(), stop.recorder.snapshot()
                for fields in o["fields"]:
                    encoded = urllib.parse.urlencode(fields)
                    request = urllib.request.Request(
                        base + o["path"] + ("?" + encoded if o["method"] == "GET" else ""),
                        data=encoded.encode() if o["method"] == "POST" else None,
                    )
                    with urllib.request.urlopen(request) as response:
                        assert response.status == 200
                gets = {k: v[len(before_gets.get(k, [])) :] for k, v in stop.recorder.gets().items()}
                posts = {k: v[len(before_posts.get(k, [])) :] for k, v in stop.recorder.snapshot().items()}
                assert check(task, answer=None, gets=gets, posts=posts, scratch=tmp_path, before={}).ok
                stream = posts if o["method"] == "POST" else gets
                stream[o["path"]].append(dict(o["fields"][0]))
                assert not check(task, answer=None, gets=gets, posts=posts, scratch=tmp_path, before={}).ok
    finally:
        stop()
