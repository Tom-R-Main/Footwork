"""Q13's oracles (evals.crossapp) and the fixture server's GET record."""

from __future__ import annotations

import urllib.request

from evals.crossapp import downloaded_and_opened, one_submission, renamed, sha256
from evals.fixtures.server import serve


def test_one_submission_is_exact_and_single():
    assert one_submission({"/confirm.html": [{"message": "624"}]}, "/confirm.html", "message", "624").ok
    assert (
        "not '624'"
        in one_submission({"/confirm.html": [{"message": "625"}]}, "/confirm.html", "message", "624").detail
    )
    assert "2 submissions" in one_submission({"/s": [{"q": "a"}, {"q": "a"}]}, "/s", "q", "a").detail
    assert "nothing was submitted" in one_submission({}, "/s", "q", "a").detail


def test_the_server_records_get_queries_and_serves_downloads():
    url, stop = serve()
    try:
        urllib.request.urlopen(f"{url}/search.html?q=quarterly+report").read()
        with urllib.request.urlopen(f"{url}/quarterly-report.txt") as r:
            body = r.read()
            assert "attachment" in r.headers.get("Content-Disposition", "")
        gets = stop.recorder.gets()
        assert one_submission(gets, "/search.html", "q", "quarterly report").ok
        assert body.startswith(b"Quarterly report")
    finally:
        stop()


def test_downloaded_and_opened(tmp_path):
    served = b"Quarterly report\n"
    (tmp_path / "quarterly-report.txt").write_bytes(served)
    doc = str(tmp_path / "quarterly-report.txt")
    assert downloaded_and_opened(tmp_path, served, "quarterly-report.txt", doc).ok
    assert (
        "no document is open" in downloaded_and_opened(tmp_path, served, "quarterly-report.txt", None).detail
    )
    (tmp_path / "quarterly-report (1).txt").write_bytes(served)
    assert "2 identical copies" in downloaded_and_opened(tmp_path, served, "quarterly-report.txt", doc).detail


def test_renamed(tmp_path):
    (tmp_path / "draft.txt").write_text("x")
    digest = sha256(b"x")
    assert "draft.txt still exists" in renamed(tmp_path, "draft.txt", "A-1042.txt", digest).detail
    (tmp_path / "draft.txt").rename(tmp_path / "A-1042.txt")
    assert renamed(tmp_path, "draft.txt", "A-1042.txt", digest).ok
    (tmp_path / "A-1042.txt").write_text("y")
    assert "contents changed" in renamed(tmp_path, "draft.txt", "A-1042.txt", digest).detail
