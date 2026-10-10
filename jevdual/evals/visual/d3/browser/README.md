# D3 browser fixtures

`evals.d3_browser.capture(out)` launches one headless Chrome instance using the local
read-only arc-cua reference checkout, with a new project-local profile. It renders
twelve authored fixtures, captures 640x360 PNGs, reads actual rendered DOM text,
target bounds, accessible names and Chrome AX nodes, and closes its owned process.
The profile is removed after the run. No normal browser profile or existing tab
is opened, and no provider API is called.

Families are toolbar glyph identity, marker containment in a rendered canvas
polygon, and current versus old target binding. Each has supported, near-miss,
ambiguous, and accessible text control variants. Canvas geometry and hidden fixture
state are excluded from model text. Ground truth remains separate evaluation
metadata. Images are unmodified CDP PNG captures; no OCR is supplied.

`replay_case(case, accepted, out)` reconstructs a fresh fixture, verifies captured
content identity, checks target scope/revision/bounds, and uses actual CDP mouse
input only when the model-derived accepted band and deterministic binding permit
it. The expected label never decides admission. An incorrectly accepted icon or
map proposal can produce a wrong safe fixture effect, which the independent
postcondition records. Stale evidence is rejected before dispatch. Replay timing
separates cold setup/capture, validation, input, and readback.

The scripted capture conformance uses authored ground truth to establish correct
trajectories and absence of effects for negative/ambiguous cases; it is distinct
from provider-guided replay. These fixtures establish neither native desktop app
coverage nor independent real-product acceptance.

Exploratory `capture-dev*` and `replay-dev-*` outputs are development evidence.
The parent experiment creates frozen official run receipts under `results/`.
