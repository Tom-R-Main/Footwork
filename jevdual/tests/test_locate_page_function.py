"""The driver's locate page function, executed (FP16).

The Rust tests give the function's result to a mock CDP; nothing there runs it. This takes its text
from the pinned driver source archive and runs it in Node against hand-built stand-ins for the node, its
ancestors, their computed styles and their rectangles. It tests the function's logic on the cases that
decide whether a filmed pointer may be put on a target. It does not test what Chrome reports as a
computed style or a rectangle: only a real page does that.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = "libs/cua-driver/rust/crates/cua-driver-core/src/browser/tools.rs"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the page function")

HARNESS = r"""
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const locate = eval('(' + input.source + ')');
const out = input.cases.map((spec) => {
  const view = { innerWidth: spec.viewport[0], innerHeight: spec.viewport[1], getComputedStyle: (el) => el.style };
  const doc = { defaultView: view, visibilityState: spec.visibility || 'visible' };
  const make = (item, parent, root) => {
    const [left, top, width, height] = item.rect;
    const layout = item.layout || {};
    const el = {
      name: item.name, parentElement: parent, assignedSlot: null, ownerDocument: doc,
      style: Object.assign({ overflowX: 'visible', overflowY: 'visible' }, item.style || {}),
      offsetWidth: layout.offsetWidth ?? width, offsetHeight: layout.offsetHeight ?? height,
      clientLeft: layout.clientLeft ?? 0, clientTop: layout.clientTop ?? 0,
      clientWidth: layout.clientWidth ?? width, clientHeight: layout.clientHeight ?? height,
      getBoundingClientRect: () => ({ left, top, width, height, right: left + width, bottom: top + height }),
      getRootNode: () => root,
      contains: (other) => { for (let o = other; o; o = o.parentElement) if (o === el) return true; return false; },
    };
    if (item.svg) { delete el.offsetWidth; delete el.offsetHeight; }
    return el;
  };
  const byName = {};
  let parent = null;
  for (const item of spec.chain) { parent = make(item, parent, doc); byName[item.name] = parent; }
  doc.documentElement = byName.html; doc.body = byName.body || null;
  let node = parent;
  if (spec.shadow) {
    // the node is the child of a shadow root whose host is the last element of the chain
    const root = { host: parent };
    node = make(spec.shadow, null, root);
    root.elementFromPoint = () => node;
  }
  const child = make({ name: 'icon', rect: [0, 0, 1, 1] }, node, doc);
  const other = make({ name: 'other', rect: [0, 0, 1, 1] }, byName.html, doc);
  const hits = { target: node, descendant: child, other, none: null };
  doc.elementFromPoint = (x, y) => {
    const at = spec.at || {};
    const key = `${x},${y}`;
    return hits[key in at ? at[key] : (spec.hit || 'target')];
  };
  return locate.apply(node, spec.point || []);
});
process.stdout.write(JSON.stringify(out));
"""


def _function() -> str:
    """``DOM_NODE_LOCATE`` as JavaScript, from the pinned archive's tools.rs."""
    with tarfile.open(ROOT / "vendor/cua-driver/native-source.tar.gz") as archive:
        source = archive.extractfile(TOOLS).read().decode()
    literal = re.search(r'const DOM_NODE_LOCATE: &str = "(.*?)";\n', source, re.DOTALL)
    assert literal, "DOM_NODE_LOCATE is not in the pinned tools.rs"
    text = literal.group(1)
    # the only escape the literal uses is a line continuation
    assert '\\"' not in text and "\\\\" not in text and "\\n" not in text
    return re.sub(r"\\\n\s*", "", text)


def _locate(*cases: dict) -> list[dict]:
    done = subprocess.run(["node", "-e", HARNESS], input=json.dumps({"source": _function(), "cases": list(cases)}),
                          capture_output=True, text=True, timeout=30, check=False)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


HTML = {"name": "html", "rect": [0, 0, 800, 2600]}
BODY = {"name": "body", "rect": [0, 0, 800, 2600]}
BUTTON = {"name": "button", "rect": [60, 330, 140, 44]}


def page(*between: dict, button: dict = BUTTON, html: dict = HTML, body: dict = BODY, **extra) -> dict:
    return {"viewport": [800, 600], "chain": [html, body, *between, button], **extra}


def test_a_plain_button_is_located_with_its_rectangle_and_what_is_at_its_centre():
    plain, covered, inner = _locate(page(), page(hit="other"), page(hit="descendant"))
    assert plain == {"rect": [60, 330, 140, 44], "hit": "target", "inner": [800, 600], "clipped": False,
                     "transformed": False, "visibility": "visible", "point": None}
    assert (covered["hit"], inner["hit"]) == ("other", "descendant")


def test_a_point_is_hit_tested_only_when_both_numbers_are_given():
    at = {"130,352": "target", "61.5,331": "other"}
    with_point, half, without = _locate(page(point=[61.5, 331], at=at), page(point=[61.5], at=at), page(at=at))
    assert with_point["point"] == [61.5, 331, "other"] and with_point["hit"] == "target"
    assert half["point"] is None and without["point"] is None


def test_a_hidden_document_is_reported():
    assert _locate(page(visibility="hidden"))[0]["visibility"] == "hidden"


SCROLLER = {"name": "scroller", "rect": [40, 300, 200, 60], "style": {"overflowX": "auto", "overflowY": "auto"}}


@pytest.mark.parametrize(("case", "clipped"), [
    # the probe's Clipped button: centre visible, lower 14 px outside the scrolling box
    (page(SCROLLER), True),
    (page(SCROLLER, button={"name": "button", "rect": [60, 305, 140, 44]}), False),
    (page({**SCROLLER, "style": {"overflowX": "visible", "overflowY": "hidden"}}), True),
    (page({**SCROLLER, "style": {"overflowX": "clip", "overflowY": "visible"}}), True),
    (page({**SCROLLER, "style": {}}), False),
    # a border and a scrollbar narrow the box the button must fit in
    (page({**SCROLLER, "rect": [40, 300, 200, 100], "layout": {"clientLeft": 30, "clientWidth": 170, "clientHeight": 100}}), True),
    (page({**SCROLLER, "rect": [40, 300, 200, 100], "layout": {"clientLeft": 10, "clientWidth": 190, "clientHeight": 100}}), False),
    # a scroller drawn at twice its layout size clips at twice its client box
    (page({**SCROLLER, "rect": [40, 300, 400, 120], "layout": {"offsetWidth": 200, "offsetHeight": 60, "clientWidth": 200, "clientHeight": 60},
           "style": {"overflowX": "auto", "overflowY": "auto", "transform": "matrix(2, 0, 0, 2, 0, 0)"}}), False),
    (page({**SCROLLER, "rect": [40, 300, 400, 120], "layout": {"offsetWidth": 200, "offsetHeight": 60, "clientWidth": 180, "clientHeight": 30},
           "style": {"overflowX": "auto", "overflowY": "auto", "transform": "matrix(2, 0, 0, 2, 0, 0)"}}), True),
    # an SVG ancestor has no layout size: its bounding rectangle is the box
    (page({**SCROLLER, "svg": True, "style": {"overflowX": "hidden", "overflowY": "hidden"}}), True),
    # a clip two levels up counts as well
    (page(SCROLLER, {"name": "row", "rect": [40, 300, 200, 300]}), True),
])
def test_a_clipping_ancestor_that_hides_part_of_the_button_is_reported(case, clipped):
    assert _locate(case)[0]["clipped"] is clipped


SHORT_BODY = {"name": "body", "rect": [0, 0, 800, 100], "style": {"overflowX": "auto", "overflowY": "auto"}}
LOW = {"name": "button", "rect": [10, 85, 100, 20]}  # spans y 85 to 105: centre inside a 100 px body


@pytest.mark.parametrize(("html", "body", "clipped"), [
    # body's overflow propagates to the viewport: body is not a scroller of its own
    (HTML, SHORT_BODY, False),
    # Sol round 3: containment stops the propagation, and body then scrolls like any box
    (HTML, {**SHORT_BODY, "style": {**SHORT_BODY["style"], "contain": "paint"}}, True),
    (HTML, {**SHORT_BODY, "style": {**SHORT_BODY["style"], "containerType": "inline-size"}}, True),
    (HTML, {**SHORT_BODY, "style": {**SHORT_BODY["style"], "contentVisibility": "auto"}}, True),
    ({**HTML, "style": {"contain": "layout"}}, SHORT_BODY, True),
    # the root has its own overflow: it is what propagates, and body scrolls
    ({**HTML, "style": {"overflowX": "hidden", "overflowY": "hidden"}}, SHORT_BODY, True),
    # the root element itself never counts: its overflow is the viewport's
    ({**HTML, "rect": [0, 0, 800, 50], "style": {"overflowX": "hidden", "overflowY": "hidden"}},
     {"name": "body", "rect": [0, 0, 800, 2600]}, False),
])
def test_body_is_skipped_only_when_its_overflow_is_the_viewports(html, body, clipped):
    assert _locate(page(html=html, body=body, button=LOW))[0]["clipped"] is clipped


TURNS = [
    {"rotate": "8deg"},
    {"transform": "matrix(0.990268, 0.139173, -0.139173, 0.990268, 0, 0)"},  # rotate(8deg)
    {"transform": "matrix(1, 0, 0.176327, 1, 0, 0)"},  # skewX(10deg)
    {"transform": "matrix(-1, 0, 0, -1, 0, 0)"},  # a half turn (Sol round 4)
    {"transform": "matrix(-1, 0, 0, 1, 0, 0)"},  # a reflection (Sol round 4)
    {"transform": "matrix(1, 0, 0, -1, 0, 0)"},
    {"scale": "-1 1"},
    {"scale": "-1"},
    {"transform": "matrix3d(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)"},
    {"offsetPath": 'path("M 0 0 L 100 100")'},
    {"transform": "an unknown form"},
]
LEVEL = [
    {},
    {"transform": "none", "rotate": "none", "scale": "none", "offsetPath": "none"},
    {"transform": "matrix(1, 0, 0, 1, 20, 30)"},  # a translation
    {"transform": "matrix(2, 0, 0, 1.5, 0, 0)"},  # a positive scale
    {"scale": "2"},
    {"scale": "1.5 0.5"},
]


@pytest.mark.parametrize("style", TURNS)
@pytest.mark.parametrize("where", ["button", "parent", "grandparent", "body"])
def test_a_rotation_skew_reflection_or_motion_path_anywhere_above_is_reported(style, where):
    box = {"name": "box", "rect": [40, 300, 200, 100]}
    outer = {"name": "outer", "rect": [0, 250, 400, 300]}
    case = {
        "button": page(outer, box, button={**BUTTON, "style": style}),
        "parent": page(outer, {**box, "style": style}),
        "grandparent": page({**outer, "style": style}, box),
        "body": page(outer, box, body={**BODY, "style": style}),
    }[where]
    assert _locate(case)[0]["transformed"] is True


@pytest.mark.parametrize("style", LEVEL)
def test_a_translation_or_a_positive_scale_is_not_a_turn(style):
    box = {"name": "box", "rect": [40, 300, 200, 100], "style": style}
    assert _locate(page(box, button={**BUTTON, "style": style}))[0]["transformed"] is False


def test_the_walk_leaves_a_shadow_tree_through_its_host():
    host = {"name": "host", "rect": [60, 330, 140, 44]}
    inside = {"name": "button", "rect": [60, 330, 140, 44]}
    clipped, clear, turned = _locate(
        page(SCROLLER, button=host, shadow=inside),
        page({**SCROLLER, "rect": [40, 300, 200, 100]}, button=host, shadow=inside),
        page({"name": "box", "rect": [40, 300, 200, 100], "style": {"rotate": "8deg"}}, button=host, shadow=inside),
    )
    assert (clipped["clipped"], clipped["hit"]) == (True, "target")
    assert (clear["clipped"], clear["transformed"]) == (False, False)
    assert turned["transformed"] is True
