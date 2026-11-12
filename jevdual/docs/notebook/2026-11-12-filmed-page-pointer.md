# Filmed pointer to page targets (B7, second step)

Step B7 of `docs/repo-learning/app-adaptation/REPORT.md`, continued from ea8933b: a `start --browser`
session can film the real pointer (park, point), but its page actions do not move the pointer to their
targets, because the driver's page observation carries no element geometry. DemoGeek's take script
today reads rectangles through its own DevTools client and moves the pointer with its own glide.py;
the goal is one reusable page and pointer layer in Footwork. Branch claude/b7-filmed-browser-20261112
from main c7cac4f. Nothing is upstreamed.

## FP1 · prediction · 2026-11-12 11:29
Question: can a filmed browser session move the real pointer onto the page element it is about to click or type into, using geometry the driver already computes?
Hypothesis: the driver's semantic snapshot reads every node's layout bounds from DOMSnapshot.captureSnapshot in document coordinates and the visual viewport's scroll offset and size from Page.getLayoutMetrics (cua-driver-core browser/semantic.rs parse_layout, parse_viewport), using them only to classify visibility; it drops both before serializing a ref (tools.rs semantic_ref_value). A main-frame ref that is in the viewport has a viewport rectangle equal to its bounds minus the scroll offset, clipped to the viewport, in CSS pixels. Emitting that rectangle (null for child frames and for refs not in the viewport) and, in a filmed session, approaching its centre through Filmed.viewport (content origin plus CSS px at 100% zoom) before the page click or type puts the real pointer over that element.
Alternatives: (a) DOMSnapshot bounds are not in the same coordinate space as cssVisualViewport's pageX/pageY (for example on a zoomed page or a page with a pinch-zoom offset), so the rectangle is offset; (b) Filmed's content origin is off by the toolbar or a scale factor, so the pointer lands beside the target; (c) the approach's real mouse-moved events change the page (hover menus) so that the following synthetic click hits a different state; (d) a layout change between the observation and the approach moves the target.
Test: a Rust unit test of the rectangle on composed nodes (offset, clipped, null in a child frame and out of the viewport); Footwork unit tests of the filmed browser act (approach to the mapped centre before the driver call, refusal with nothing sent when a target has no rectangle or the take has ended, no change when not filmed); then a live run on an isolated profile and port 9466 in a granted window: a filmed browser session on a fixture whose buttons log every trusted pointer event's target, clicking three buttons at different positions, one after scrolling.
Predicts: Rust and Footwork tests fail before the change and pass after; every existing browser and session test passes. Live: before each click handler runs, the page logs a trusted mouseover or mousemove whose target is that button, and the recorded gesture ends inside the button's screen rectangle; the scrolled case does too.
Against: a trusted pointer event's target is not the button about to be clicked, or the gesture ends outside it; any existing test failing.
Refs: docs/repo-learning/app-adaptation/REPORT.md (B7, D); docs/notebook/2026-11-11-browser-holder.md#bh15; DemoGeek .local-reviews/application-film/best-edit/glide.py
